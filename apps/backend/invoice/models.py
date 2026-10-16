# apps/backend/invoice/models.py

"""
Canonical invoice models for Univa.

Architectural boundary
----------------------

An Invoice is a legal request for payment. It knows:

    - who is billing and who is billed
    - what amount is owed, in what currency
    - what tax was charged
    - when it was issued and when it is due
    - what number identifies it

An Invoice does NOT know:

    - what kind of business transaction produced it
    - what the line items mean
    - how payment will be collected
    - which domain created it

Domains attach through:

    InvoiceSource   — soft references (source_type + source_id)
    InvoiceEvent    — append-only audit log

Sharing is a capability of the account holder, not a policy of
the seller. It lives on InvoiceShare, not on Invoice.

This mirrors the design of payment/canonical: the primitive owns
money, the domain owns workflow, and they meet at soft references
and append-only events.
"""

from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, JSONField, Q, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.metadata import (
    CustomJsonEncoder,
    ModelWithMetadata,
)

from .enums import (
    InvoiceEventType,
    InvoicePaymentType,
    InvoiceShareChannel,
    InvoiceStatus,
)


# =====================================================================
# INVOICE NUMBER SEQUENCE
# =====================================================================


class InvoiceNumberSequence(models.Model):
    """
    Per-period sequential counter for invoice numbers.

    One row per (prefix, year, month). Allocation uses
    select_for_update so concurrent invoice creation produces
    unique numbers with no gaps.

    Regulatory considerations: in most jurisdictions invoice
    numbers must be unique and unbroken. This model guarantees
    both.
    """

    prefix = models.CharField(max_length=10, default="INV")
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    next_value = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "invoice_number_sequences"
        constraints = [
            models.UniqueConstraint(
                fields=["prefix", "year", "month"],
                name="unique_invoice_sequence_period",
            ),
        ]

    def __str__(self):
        return f"{self.prefix}-{self.year}{self.month:02d}@{self.next_value}"


# =====================================================================
# INVOICE PARTY
# =====================================================================


class InvoiceParty(ModelWithMetadata):
    """
    An entity that can issue or receive an invoice.

    A party is either an individual or an organization. When
    `is_organization=True`, `name` is the legal entity name and
    `tax_id` is the registered tax identifier.

    Parties are not users. A user may have one or more parties
    associated with them (personal, business, etc.), but the
    party is what appears on the invoice.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_parties",
        help_text="Optional link to a Univa account.",
    )
    is_organization = models.BooleanField(
        default=False,
        help_text=(
            "True for companies, NGOs, and government bodies. "
            "The `name` is the legal entity name in that case."
        ),
    )
    name = models.CharField(max_length=255)
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Tax identifier (TIN, VAT number, PIN, etc.). "
            "Often required on B2B invoices."
        ),
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    billing_address = models.TextField(blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    billing_zip = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(ModelWithMetadata.Meta):
        db_table = "invoice_parties"
        ordering = ("name", "pk")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(fields=["user"], name="inv_party_user_idx"),
            models.Index(fields=["name"], name="inv_party_name_idx"),
            models.Index(
                fields=["is_active", "is_organization"],
                name="inv_party_active_org_idx",
            ),
        ]

    def __str__(self):
        return self.name

    def as_billing_dict(self):
        """
        Canonical shape used by templates and the PDF renderer.

        Never includes user-account details; only what appears
        on a legal invoice.
        """
        return {
            "name": self.name,
            "tax_id": self.tax_id,
            "email": self.email,
            "phone": self.phone,
            "address": self.billing_address,
            "city": self.billing_city,
            "state": self.billing_state,
            "country": self.billing_country,
            "zip": self.billing_zip,
            "is_organization": self.is_organization,
        }


# =====================================================================
# INVOICE
# =====================================================================


class InvoiceQueryset(models.QuerySet["Invoice"]):
    """
    Query helpers for Invoice.
    """

    def for_source(self, source_type, source_id):
        """
        Return invoices whose InvoiceSource matches the given
        domain reference.

        This is how a domain finds its invoice without an FK.
        """
        return self.filter(
            sources__source_type=source_type,
            sources__source_id=str(source_id),
        ).distinct()

    def unpaid(self):
        return self.filter(
            status__in=[
                InvoiceStatus.ISSUED,
                InvoiceStatus.SENT,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.OVERDUE,
            ],
        )

    def overdue(self, on=None):
        if on is None:
            on = timezone.now().date()
        return self.filter(
            due_date__lt=on,
            status__in=[
                InvoiceStatus.ISSUED,
                InvoiceStatus.SENT,
                InvoiceStatus.PARTIALLY_PAID,
            ],
        )


InvoiceManager = models.Manager.from_queryset(InvoiceQueryset)


class Invoice(ModelWithMetadata):
    """
    Canonical invoice.

    One Invoice represents one legal request for payment. It does
    not know how it was produced or how it will be collected.
    Domains attach via InvoiceSource; payment is applied via
    InvoicePayment.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
    )
    number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=(
            "Legally significant invoice number. Globally unique "
            "across all invoices, regardless of source domain."
        ),
    )

    # ------------------------------------------------------------------
    # Parties
    # ------------------------------------------------------------------

    issuer = models.ForeignKey(
        InvoiceParty,
        on_delete=models.PROTECT,
        related_name="invoices_issued",
        help_text="The party sending this invoice.",
    )
    recipient = models.ForeignKey(
        InvoiceParty,
        on_delete=models.PROTECT,
        related_name="invoices_received",
        help_text="The party this invoice is addressed to.",
    )

    # ------------------------------------------------------------------
    # Currency and amounts
    # ------------------------------------------------------------------

    currency = models.CharField(
        max_length=3,
        help_text="ISO currency code (e.g. NGN, USD).",
    )
    subtotal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sum of line items before tax, shipping, discount.",
    )
    tax_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="subtotal + tax + shipping − discount.",
    )
    amount_paid = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sum of completed InvoicePayment rows.",
    )
    balance_due = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="total_amount − amount_paid, floored at zero.",
    )

    # ------------------------------------------------------------------
    # Dates and terms
    # ------------------------------------------------------------------

    issue_date = models.DateField(
        default=timezone.now,
        help_text="Date the invoice was issued.",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date payment is due. Null for on-receipt terms.",
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Free-text terms, e.g. 'Net 30'.",
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    rendered_file = models.FileField(
        upload_to="invoices/rendered",
        null=True,
        blank=True,
        help_text="PDF rendering of this invoice, if generated.",
    )
    rendered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------

    notes = models.TextField(
        blank=True,
        help_text="Notes visible on the invoice.",
    )
    terms_and_conditions = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = InvoiceManager()

    class Meta(ModelWithMetadata.Meta):
        db_table = "invoices"
        ordering = ("-issue_date", "-created_at")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["recipient", "status"],
                name="inv_recipient_status_idx",
            ),
            models.Index(
                fields=["issuer", "status"],
                name="inv_issuer_status_idx",
            ),
            models.Index(
                fields=["due_date", "status"],
                name="inv_due_status_idx",
            ),
            models.Index(
                fields=["issue_date", "status"],
                name="inv_issue_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="invoice_total_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(amount_paid__gte=0),
                name="invoice_paid_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(balance_due__gte=0),
                name="invoice_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.number} — {self.recipient.name}"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()
        errors = {}

        if self.currency and len(self.currency) != 3:
            errors["currency"] = _(
                "Currency must be exactly three characters."
            )

        if self.currency:
            self.currency = self.currency.upper()

        if self.due_date and self.due_date < self.issue_date:
            errors["due_date"] = _(
                "Due date cannot be earlier than issue date."
            )

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Computed amounts
    # ------------------------------------------------------------------

    def recalculate_totals(self):
        """
        Recompute subtotal, tax, shipping, total, and balance from
        line items and payments.

        This is the ONLY place that writes those header fields.
        Called by services after mutating line items or payments.
        Does not save.
        """
        line_items = self.line_items.all()

        subtotal = sum(
            (item.line_total for item in line_items),
            Decimal("0.00"),
        )
        tax = sum(
            (item.tax_amount for item in line_items),
            Decimal("0.00"),
        )

        self.subtotal_amount = subtotal
        self.tax_amount = tax
        self.total_amount = (
            self.subtotal_amount
            + self.tax_amount
            + self.shipping_amount
            - self.discount_amount
        )

        paid = (
            self.payments.aggregate(
                total=Coalesce(
                    models.Sum("amount"),
                    Value(Decimal("0.00")),
                )
            )["total"]
            or Decimal("0.00")
        )
        self.amount_paid = paid
        self.balance_due = max(
            self.total_amount - self.amount_paid,
            Decimal("0.00"),
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID

    @property
    def is_terminal(self):
        return self.status in {
            InvoiceStatus.CANCELLED,
            InvoiceStatus.VOID,
            InvoiceStatus.REFUNDED,
        }

    @property
    def source_summary(self):
        """
        Human-readable summary of the sources attached to this
        invoice. Used by templates.
        """
        return ", ".join(
            f"{s.source_type}:{s.source_reference or s.source_id}"
            for s in self.sources.all()
        )


# =====================================================================
# INVOICE SOURCE (soft reference)
# =====================================================================


class InvoiceSource(models.Model):
    """
    A soft reference from an Invoice to the domain object that
    produced it.

    Domains do not FK to Invoice, and Invoice does not FK to
    domains. This table carries the linkage:

        source_type       = "order"           (opaque string)
        source_id         = UUID of the Order
        source_reference  = "ORD-12345"       (optional, display only)

    An Invoice can have zero or more sources. Most have exactly
    one. A compound invoice (e.g. an order plus a booking on the
    same bill) has two.

    This mirrors Payment.source_type / Payment.source_id.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text=(
            "Domain-specific source kind: 'order', 'booking', "
            "'payment', 'lease', 'fare', etc. Opaque to Invoice."
        ),
    )
    source_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text=(
            "Identifier of the source object in its own domain. "
            "Treated as opaque by Invoice."
        ),
    )
    source_reference = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            "Optional human-readable reference, e.g. 'ORD-12345'. "
            "Never parsed for behavior."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoice_sources"
        ordering = ("invoice_id", "source_type", "source_id")
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "source_type", "source_id"],
                name="unique_invoice_source",
            ),
        ]
        indexes = [
            models.Index(
                fields=["source_type", "source_id"],
                name="inv_src_type_id_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.source_type}:{self.source_reference or self.source_id}"
        )


# =====================================================================
# INVOICE LINE ITEM
# =====================================================================


class InvoiceLineItem(models.Model):
    """
    A single line on an invoice.

    Quantity is Decimal(12,3) so that market items sold by weight
    (2.5 kg of beef) are representable.

    Domain-specific line detail (SKU, service period, distance)
    goes in `metadata`. Invoice never reads metadata for behavior.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )

    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Tax rate as a percentage (e.g. 7.5 for 7.5%).",
    )
    tax_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    line_total = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="(quantity × unit_price) − discount + tax.",
    )
    currency = models.CharField(max_length=3)

    metadata = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoice_line_items"
        ordering = ("invoice_id", "pk")
        indexes = [
            models.Index(
                fields=["invoice"],
                name="inv_line_invoice_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.description} — "
            f"{self.quantity} × {self.unit_price}"
        )

    def save(self, *args, **kwargs):
        self.line_total = (
            (self.quantity * self.unit_price)
            - self.discount_amount
            + self.tax_amount
        )
        super().save(*args, **kwargs)


# =====================================================================
# INVOICE PAYMENT
# =====================================================================


class InvoicePayment(models.Model):
    """
    A payment applied to an invoice.

    This model does NOT own the payment lifecycle. The payment
    system owns it. InvoicePayment is a projection: it records
    which payments have been applied to which invoices.

    Every row carries an idempotency_key. A second call to
    apply_payment() with the same key is a no-op that returns
    the existing row. Retries are safe.

    Reversals are represented as separate rows with a negative
    amount (payment_type=REVERSAL), not mutations of the original.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    idempotency_key = models.CharField(
        max_length=150,
        unique=True,
        help_text=(
            "Caller-supplied key. A second call with the same key "
            "is a no-op that returns the existing row."
        ),
    )

    payment_type = models.CharField(
        max_length=50,
        choices=InvoicePaymentType.choices,
        db_index=True,
    )
    payment_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text=(
            "Identifier in the source system (payment execution "
            "UUID, bank reference, etc.). Opaque."
        ),
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("-999999999.99"))],
        help_text=(
            "Positive for applied payments, negative for "
            "reversals and refunds."
        ),
    )
    currency = models.CharField(max_length=3)

    applied_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_payments_applied",
    )

    metadata = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoice_payments"
        ordering = ("-applied_at",)
        indexes = [
            models.Index(
                fields=["invoice", "applied_at"],
                name="inv_pay_invoice_applied_idx",
            ),
            models.Index(
                fields=["payment_type", "payment_id"],
                name="inv_pay_type_id_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment_type} {self.amount} "
            f"on {self.invoice.number}"
        )

    def clean(self):
        super().clean()

        if self.amount == Decimal("0.00"):
            raise ValidationError(
                {"amount": _("Payment amount must not be zero.")}
            )

        if self.currency and len(self.currency) != 3:
            raise ValidationError(
                {"currency": _("Currency must be exactly three characters.")}
            )


# =====================================================================
# INVOICE EVENT (append-only audit log)
# =====================================================================


class InvoiceEvent(models.Model):
    """
    Append-only audit log for invoice lifecycle.

    Mirrors OrderEvent and PaymentExecutionEvent. Notifications
    subscribe to these events via signals; the invoice model
    itself does not send notifications.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="events",
    )
    type = models.CharField(
        max_length=30,
        choices=InvoiceEventType.choices,
        db_index=True,
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_events_acted",
    )
    parameters = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    class Meta:
        db_table = "invoice_events"
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(
                fields=["invoice", "occurred_at"],
                name="inv_event_inv_time_idx",
            ),
            models.Index(
                fields=["type", "occurred_at"],
                name="inv_event_type_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.type} on {self.invoice.number}"


# =====================================================================
# INVOICE SHARE
# =====================================================================


def _generate_share_token():
    """
    Module-level factory so migration files can serialize the
    default. A lambda would break makemigrations.
    """
    return token_urlsafe(32)


class InvoiceShare(ModelWithMetadata):
    """
    A user-authorized share of an Invoice.

    Creating a share does not deliver anything. It mints an
    opaque token that grants the holder read access to a bounded
    representation of the invoice.

    A user creates a share when they want to send an invoice
    receipt to a friend, accountant, tax authority, or support
    agent. They can revoke it at any time. It expires on its own.

    Sharing is a capability of the account holder, not a policy
    of the seller.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="shares",
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=_generate_share_token,
        editable=False,
        help_text=(
            "URL-safe opaque token granting read access. "
            "Never expose the invoice pk in a share URL."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoice_shares_created",
        help_text=(
            "The user who authorized this share. Typically the "
            "invoice recipient, but can be the issuer."
        ),
    )

    label = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "User-supplied label, e.g. 'Accountant Q3'. For the "
            "user's own organization only."
        ),
    )

    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    channel = models.CharField(
        max_length=20,
        choices=InvoiceShareChannel.choices,
        default=InvoiceShareChannel.LINK_COPY,
    )

    include_line_items = models.BooleanField(
        default=True,
        help_text=(
            "Whether the shared view shows individual line items. "
            "False shares a summary-only view (header + totals)."
        ),
    )

    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_shares_revoked",
    )
    revoked_reason = models.CharField(max_length=255, blank=True)

    first_viewed_at = models.DateTimeField(null=True, blank=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(ModelWithMetadata.Meta):
        db_table = "invoice_shares"
        ordering = ("-created_at",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["invoice", "revoked_at"],
                name="inv_share_inv_revoked_idx",
            ),
            models.Index(
                fields=["created_by", "created_at"],
                name="inv_share_user_time_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="inv_share_expires_idx",
            ),
        ]

    def __str__(self):
        return f"Share {self.token[:8]}… of {self.invoice.number}"

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_active(self):
        return (
            self.revoked_at is None
            and self.expires_at > timezone.now()
        )

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_expired(self):
        return (
            self.revoked_at is None
            and self.expires_at <= timezone.now()
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @transaction.atomic
    def revoke(self, *, by=None, reason=""):
        """
        Revoke this share. Idempotent.
        """
        locked = type(self).objects.select_for_update().get(pk=self.pk)

        if locked.revoked_at is not None:
            return

        locked.revoked_at = timezone.now()
        locked.revoked_by = by
        locked.revoked_reason = reason
        locked.save(
            update_fields=[
                "revoked_at",
                "revoked_by",
                "revoked_reason",
                "updated_at",
            ]
        )

        InvoiceEvent.objects.create(
            invoice=locked.invoice,
            type=InvoiceEventType.SHARE_REVOKED,
            actor=by,
            parameters={"share_id": str(locked.pk)},
        )

        self.revoked_at = locked.revoked_at

    @transaction.atomic
    def record_view(self):
        """
        Increment view counters. Called by the public read view.
        """
        now = timezone.now()
        type(self).objects.filter(pk=self.pk).update(
            view_count=F("view_count") + 1,
            last_viewed_at=now,
            first_viewed_at=Coalesce(
                F("first_viewed_at"),
                Value(now),
            ),
        )