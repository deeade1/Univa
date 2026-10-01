# apps/backend/invoice/models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.metadata import Job, ModelWithMetadata
from core.models.utils.url_utils import get_frontend_url
from core.utils import build_absolute_uri
from core.utils.json_serializer import CustomJsonEncoder


class InvoiceQueryset(models.QuerySet["Invoice"]):
    """
    Custom queryset for Invoice.
    """

    def ready(self):
        """
        Return successfully completed invoice jobs when JobStatus
        is available.

        Falls back to the normal queryset if the project-level
        JobStatus enum is unavailable.
        """
        try:
            from core import JobStatus

            return self.filter(job__status=JobStatus.SUCCESS)
        except ImportError:
            return self


InvoiceManager = models.Manager.from_queryset(InvoiceQueryset)


class Invoice(ModelWithMetadata, Job):
    """
    Universal invoice model for Univa.

    The model intentionally uses lazy Django model references for
    ecommerce.Order and transport.Booking. This prevents circular
    imports between the invoice and ecommerce applications.
    """

    INVOICE_STATUS = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("CANCELLED", "Cancelled"),
        ("REFUNDED", "Refunded"),
        ("VOID", "Void"),
    ]

    # ------------------------------------------------------------------
    # Core relationships
    # ------------------------------------------------------------------

    order = models.ForeignKey(
        "ecommerce.Order",
        related_name="invoices",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Associated ecommerce order, if applicable.",
    )

    booking = models.ForeignKey(
        "transport.Booking",
        related_name="booking_invoices",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Associated transport booking, if applicable.",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_as_customer",
        help_text="Customer this invoice is for.",
    )

    # ------------------------------------------------------------------
    # Invoice identifiers
    # ------------------------------------------------------------------

    number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary invoice number.",
    )

    invoice_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Alternative invoice number retained for compatibility.",
    )

    # ------------------------------------------------------------------
    # Invoice dates and terms
    # ------------------------------------------------------------------

    issue_date = models.DateField(
        default=timezone.now,
        help_text="Date the invoice was issued.",
    )

    created = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invoice was created.",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the invoice is due.",
    )

    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        default="Net 30",
        help_text="Payment terms.",
    )

    # ------------------------------------------------------------------
    # Financial information
    # ------------------------------------------------------------------

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Subtotal before taxes and discounts.",
    )

    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total tax amount.",
    )

    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total discount amount.",
    )

    shipping_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Shipping cost.",
    )

    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total amount due.",
    )

    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Amount already paid.",
    )

    balance_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Remaining balance due.",
    )

    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO currency code such as USD, EUR, or NGN.",
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS,
        default="DRAFT",
        db_index=True,
        help_text="Current invoice status.",
    )

    # ------------------------------------------------------------------
    # Billing information
    # ------------------------------------------------------------------

    billing_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Billing name.",
    )

    billing_email = models.EmailField(
        blank=True,
        help_text="Billing email.",
    )

    billing_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Billing phone.",
    )

    billing_address = models.TextField(
        blank=True,
        help_text="Billing address.",
    )

    billing_city = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing city.",
    )

    billing_state = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing state or province.",
    )

    billing_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing country.",
    )

    billing_zip = models.CharField(
        max_length=20,
        blank=True,
        help_text="Billing ZIP or postal code.",
    )

    # ------------------------------------------------------------------
    # External URL and invoice file
    # ------------------------------------------------------------------

    external_url = models.URLField(
        null=True,
        blank=True,
        max_length=2048,
        help_text="External URL for the invoice.",
    )

    invoice_file = models.FileField(
        upload_to="invoices",
        null=True,
        blank=True,
        help_text="PDF or invoice file attachment.",
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    notes = models.TextField(
        blank=True,
        help_text="Additional notes.",
    )

    terms_and_conditions = models.TextField(
        blank=True,
        help_text="Invoice terms and conditions.",
    )

    metadata = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
        help_text="Additional invoice metadata.",
    )

    # ------------------------------------------------------------------
    # Payment information
    # ------------------------------------------------------------------

    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method used.",
    )

    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invoice was paid.",
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Payment reference or transaction ID.",
    )

    # ------------------------------------------------------------------
    # Audit fields
    # ------------------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_created",
        help_text="User who created this invoice.",
    )

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_sent",
        help_text="User who sent this invoice.",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_verified",
        help_text="User who verified this invoice.",
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invoice was sent.",
    )

    objects = InvoiceManager()

    class Meta(ModelWithMetadata.Meta):
        db_table = "invoices"

        ordering = ("-created", "-created_at")

        indexes = [
            models.Index(
                fields=["number", "status"],
                name="invoice_num_status_idx",
            ),
            models.Index(
                fields=["invoice_number", "status"],
                name="invoice_alt_num_idx",
            ),
            models.Index(
                fields=["customer", "status"],
                name="invoice_cust_status_idx",
            ),
            models.Index(
                fields=["due_date", "status"],
                name="invoice_due_status_idx",
            ),
            models.Index(
                fields=["created", "status"],
                name="invoice_created_idx",
            ),
            models.Index(
                fields=["created_at", "status"],
                name="invoice_createdat_idx",
            ),
            models.Index(
                fields=["payment_reference"],
                name="invoice_payment_ref_idx",
            ),
            models.Index(
                fields=["order", "status"],
                name="invoice_order_status_idx",
            ),
            models.Index(
                fields=["booking", "status"],
                name="invoice_booking_status_idx",
            ),
        ]

        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    def __str__(self):
        number = (
            self.number
            or self.invoice_number
            or f"INV-{self.pk}"
        )

        customer_name = (
            self.customer.email
            if self.customer
            else "No Customer"
        )

        return (
            f"{number} - "
            f"{customer_name} - "
            f"{self.get_status_display()}"
        )

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @property
    def url(self):
        if self.invoice_file:
            return build_absolute_uri(self.invoice_file.url)

        return self.external_url

    @url.setter
    def url(self, value):
        self.external_url = value

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        if not self.number and not self.invoice_number:
            self.number = self.generate_invoice_number()
            self.invoice_number = self.number

        if not self.created:
            self.created = timezone.now()

        self.calculate_totals()

        if (
            self.balance_due <= Decimal("0.00")
            and self.status not in {"CANCELLED", "VOID"}
        ):
            self.status = "PAID"

        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Financial calculations
    # ------------------------------------------------------------------

    def calculate_totals(self):
        self.total_amount = (
            self.subtotal
            + self.tax_amount
            + self.shipping_amount
            - self.discount_amount
        )

        self.balance_due = (
            self.total_amount
            - self.amount_paid
        )

        return self.total_amount

    # ------------------------------------------------------------------
    # Invoice numbering
    # ------------------------------------------------------------------

    def generate_invoice_number(self):
        prefix = "INV"
        now = timezone.now()

        year = now.strftime("%Y")
        month = now.strftime("%m")

        today_count = (
            self.__class__.objects.filter(
                created_at__date=now.date()
            ).count()
            + 1
        )

        return f"{prefix}-{year}{month}-{today_count:04d}"

    # ------------------------------------------------------------------
    # Invoice updates
    # ------------------------------------------------------------------

    def update_invoice(self, number=None, url=None):
        if number is not None:
            self.number = number
            self.invoice_number = number

        if url is not None:
            self.external_url = url

        self.save(
            update_fields=[
                "number",
                "invoice_number",
                "external_url",
            ]
        )

    # ------------------------------------------------------------------
    # Invoice lifecycle
    # ------------------------------------------------------------------

    def mark_as_sent(self, sent_by=None):
        self.status = "SENT"
        self.sent_at = timezone.now()

        if sent_by:
            self.sent_by = sent_by

        self.save(
            update_fields=[
                "status",
                "sent_at",
                "sent_by",
            ]
        )

        self._send_notification(
            "INVOICE.SENT",
            sent_by,
        )

    def mark_as_paid(
        self,
        payment_method="",
        payment_reference="",
        verified_by=None,
    ):
        self.status = "PAID"
        self.payment_date = timezone.now()
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.amount_paid = self.total_amount
        self.balance_due = Decimal("0.00")

        if verified_by:
            self.verified_by = verified_by

        self.save()

        self._send_notification(
            "INVOICE.PAID",
            verified_by,
        )

    def mark_as_overdue(self):
        if (
            self.status == "SENT"
            and self.due_date
            and timezone.now().date() > self.due_date
        ):
            self.status = "OVERDUE"
            self.save(update_fields=["status"])

            self._send_notification(
                "INVOICE.OVERDUE"
            )

    def partial_payment(
        self,
        amount,
        payment_method="",
        payment_reference="",
    ):
        amount = Decimal(str(amount))

        if amount <= Decimal("0.00"):
            raise ValueError(
                "Payment amount must be greater than zero."
            )

        if amount > self.balance_due:
            raise ValueError(
                "Payment amount exceeds balance due."
            )

        self.amount_paid += amount
        self.balance_due = (
            self.total_amount
            - self.amount_paid
        )

        if self.balance_due <= Decimal("0.00"):
            self.status = "PAID"

        self.payment_method = payment_method
        self.payment_reference = payment_reference

        self.save()

        InvoicePayment.objects.create(
            invoice=self,
            amount=amount,
            payment_method=payment_method,
            payment_reference=payment_reference,
        )

        self._send_notification(
            "INVOICE.PARTIAL_PAYMENT",
            parameters={
                "amount": str(amount),
                "balance_due": str(self.balance_due),
            },
        )

    def cancel_invoice(
        self,
        reason="",
        cancelled_by=None,
    ):
        if self.status in {
            "PAID",
            "CANCELLED",
            "VOID",
        }:
            raise ValueError(
                f"Cannot cancel invoice with status: {self.status}"
            )

        self.status = "CANCELLED"

        if reason:
            self.notes = (
                f"{self.notes}\nCANCELLED: {reason}"
                if self.notes
                else f"CANCELLED: {reason}"
            )

        if cancelled_by:
            self.verified_by = cancelled_by

        self.save()

        self._send_notification(
            "INVOICE.CANCELLED",
            cancelled_by,
            {"reason": reason},
        )

    def void_invoice(
        self,
        reason="",
        voided_by=None,
    ):
        if self.status in {
            "PAID",
            "CANCELLED",
        }:
            raise ValueError(
                f"Cannot void invoice with status: {self.status}"
            )

        self.status = "VOID"

        if reason:
            self.notes = (
                f"{self.notes}\nVOIDED: {reason}"
                if self.notes
                else f"VOIDED: {reason}"
            )

        if voided_by:
            self.verified_by = voided_by

        self.save()

        self._send_notification(
            "INVOICE.VOIDED",
            voided_by,
            {"reason": reason},
        )

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _send_notification(
        self,
        event_type,
        user=None,
        parameters=None,
    ):
        try:
            from notifications.services.emitter import (
                emit_notification_event,
            )

            target_user = user or self.customer

            if not target_user:
                return

            emit_notification_event(
                user=target_user,
                event=event_type,
                module="invoice",
                payload={
                    "invoice_id": str(self.pk),
                    "invoice_number": (
                        self.number
                        or self.invoice_number
                    ),
                    "total_amount": str(
                        self.total_amount
                    ),
                    "status": self.status,
                    "due_date": (
                        str(self.due_date)
                        if self.due_date
                        else None
                    ),
                    "order_id": (
                        str(self.order.pk)
                        if self.order
                        else None
                    ),
                    "booking_id": (
                        str(self.booking.pk)
                        if self.booking
                        else None
                    ),
                    **(parameters or {}),
                },
            )

        except ImportError:
            import logging

            logger = logging.getLogger(__name__)

            logger.warning(
                "Notification system not available. "
                "Event: %s for invoice %s",
                event_type,
                self.pk,
            )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def get_payment_status_display(self):
        if self.balance_due <= Decimal("0.00"):
            return "Fully Paid"

        if self.amount_paid > Decimal("0.00"):
            return (
                "Partially Paid "
                f"(Balance: {self.balance_due})"
            )

        return "Unpaid"

    def get_frontend_url(self):
        return get_frontend_url(
            "invoice",
            {
                "id": self.pk,
                "token": self.pk,
            },
        )

    def get_absolute_url(self):
        return self.get_frontend_url()

    # ------------------------------------------------------------------
    # PDF generation
    # ------------------------------------------------------------------

    def generate_pdf(self) -> bytes | None:
        try:
            from weasyprint import HTML
            from gotomarket.views import build_invoice_html

            seller_name = getattr(
                settings,
                "MARKET_NAME",
                "Univa Market",
            )

            seller_addr = getattr(
                settings,
                "MARKET_ADDRESS",
                "",
            )

            seller_phone = getattr(
                settings,
                "MARKET_PHONE",
                "",
            )

            html_content = build_invoice_html(
                self,
                seller_name,
                seller_addr,
                seller_phone,
            )

            return HTML(
                string=html_content,
                base_url="",
            ).write_pdf()

        except ImportError:
            return None


class InvoiceLineItem(models.Model):
    """
    Individual line item belonging to an invoice.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )

    description = models.CharField(
        max_length=255,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    metadata = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "invoice_line_items"
        ordering = ["id"]

        verbose_name = _("Invoice Line Item")
        verbose_name_plural = _("Invoice Line Items")

    def __str__(self):
        return (
            f"{self.description} - "
            f"{self.quantity} x "
            f"{self.unit_price}"
        )

    def save(self, *args, **kwargs):
        self.total = (
            (self.quantity * self.unit_price)
            - self.discount
            + self.tax
        )

        super().save(*args, **kwargs)


class InvoicePayment(models.Model):
    """
    Payment record associated with an invoice.
    """

    PAYMENT_METHODS = [
        ("BANK_TRANSFER", "Bank Transfer"),
        ("CREDIT_CARD", "Credit Card"),
        ("DEBIT_CARD", "Debit Card"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("PAYPAL", "PayPal"),
        ("CRYPTO", "Cryptocurrency"),
        ("CASH", "Cash"),
        ("WALLET", "Digital Wallet"),
        ("OTHER", "Other"),
    ]

    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
        ("PARTIAL", "Partially Refunded"),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    payment_date = models.DateTimeField(
        auto_now_add=True,
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="PENDING",
        db_index=True,
    )

    transaction_id = models.CharField(
        max_length=100,
        blank=True,
    )

    gateway_response = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    metadata = JSONField(
        default=dict,
        blank=True,
        encoder=CustomJsonEncoder,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_payments_created",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_payments_verified",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "invoice_payments"

        ordering = ["-payment_date"]

        indexes = [
            models.Index(
                fields=["invoice", "status"],
                name="inv_pay_inv_status_idx",
            ),
            models.Index(
                fields=["payment_reference"],
                name="inv_pay_ref_idx",
            ),
            models.Index(
                fields=["payment_date", "status"],
                name="inv_pay_date_status_idx",
            ),
            models.Index(
                fields=["payment_method", "status"],
                name="inv_pay_method_idx",
            ),
        ]

        verbose_name = _("Invoice Payment")
        verbose_name_plural = _("Invoice Payments")

    def __str__(self):
        return (
            f"Payment {self.payment_reference} - "
            f"{self.amount} ({self.status})"
        )

    def clean(self):
        if self.amount <= Decimal("0.00"):
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

        if (
            self.status == "COMPLETED"
            and not self.transaction_id
        ):
            raise ValidationError(
                "Transaction ID is required for completed payments."
            )

    def mark_as_completed(self, verified_by=None):
        self.status = "COMPLETED"

        if verified_by:
            self.verified_by = verified_by

        self.save(
            update_fields=[
                "status",
                "verified_by",
            ]
        )

        invoice = self.invoice

        invoice.amount_paid += self.amount
        invoice.balance_due = (
            invoice.total_amount
            - invoice.amount_paid
        )

        if invoice.balance_due <= Decimal("0.00"):
            invoice.status = "PAID"

        invoice.save()

        invoice._send_notification(
            "INVOICE.PAYMENT_RECEIVED",
            verified_by,
            {
                "payment_id": str(self.pk),
                "amount": str(self.amount),
                "payment_method": self.payment_method,
            },
        )

    def mark_as_failed(self):
        self.status = "FAILED"

        self.save(
            update_fields=["status"]
        )

        self.invoice._send_notification(
            "INVOICE.PAYMENT_FAILED",
            parameters={
                "payment_id": str(self.pk),
                "payment_reference": (
                    self.payment_reference
                ),
            },
        )

    def mark_as_refunded(self, amount=None):
        self.status = "REFUNDED"

        self.save(
            update_fields=["status"]
        )

        refund_amount = (
            Decimal(str(amount))
            if amount is not None
            else self.amount
        )

        invoice = self.invoice

        invoice.amount_paid -= refund_amount

        if invoice.amount_paid < Decimal("0.00"):
            invoice.amount_paid = Decimal("0.00")

        invoice.balance_due = (
            invoice.total_amount
            - invoice.amount_paid
        )

        invoice.save()

        invoice._send_notification(
            "INVOICE.REFUNDED",
            parameters={
                "payment_id": str(self.pk),
                "refund_amount": str(
                    refund_amount
                ),
            },
        )
