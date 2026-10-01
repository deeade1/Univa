"""
Canonical Payment model for Univa.

Payment represents a monetary operation performed by Univa.

Architectural boundary
----------------------

Payment answers:

    "What payment operation is Univa performing?"

Payment does NOT own:

    - entitlement calculation
    - settlement eligibility
    - banking balances
    - ledger entries
    - provider configuration
    - provider execution details
    - rewards
    - discounts
    - order/checkout state

Those concerns belong to their respective domains/services.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    class Direction(models.TextChoices):
        RECEIVE = "receive", _("Receive")
        DISBURSE = "disburse", _("Disburse")

    class Purpose(models.TextChoices):
        CHECKOUT = "checkout", _("Checkout")
        WALLET_FUNDING = "wallet_funding", _("Wallet Funding")
        WITHDRAWAL = "withdrawal", _("Withdrawal")
        VENDOR_PAYOUT = "vendor_payout", _("Vendor Payout")
        DRIVER_PAYOUT = "driver_payout", _("Driver Payout")
        COURIER_PAYOUT = "courier_payout", _("Courier Payout")
        COMMISSION = "commission", _("Commission")
        EARNING = "earning", _("Earning")
        INVESTOR_DISTRIBUTION = "investor_distribution", _(
            "Investor Distribution"
        )
        REFUND = "refund", _("Refund")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        REVERSED = "reversed", _("Reversed")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    direction = models.CharField(
        max_length=20,
        choices=Direction.choices,
    )

    purpose = models.CharField(
        max_length=50,
        choices=Purpose.choices,
    )

    # Generic provenance.
    source_type = models.CharField(
        max_length=50,
    )

    source_id = models.CharField(
        max_length=100,
    )

    source_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_as_payer",
        null=True,
        blank=True,
    )

    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_as_beneficiary",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    idempotency_key = models.CharField(
        max_length=150,
        unique=True,
    )

    processing_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "payment_canonical"
        db_table = "payment_canonical_payment"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["beneficiary", "status"],
                name="payment_ben_status_idx",
            ),
            models.Index(
                fields=["source_type", "source_id"],
                name="payment_source_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="payment_status_created_idx",
            ),
            models.Index(
                fields=["direction", "status"],
                name="payment_direction_status_idx",
            ),
        ]

    def __str__(self):
        return self.reference

    def clean(self):
        errors = {}

        # ---------------------------------------------------------
        # Amount
        # ---------------------------------------------------------
        if self.amount is None or self.amount <= 0:
            errors["amount"] = _(
                "Payment amount must be greater than zero."
            )

        # ---------------------------------------------------------
        # Currency
        # ---------------------------------------------------------
        if not self.currency:
            errors["currency"] = _("Currency is required.")
        elif len(self.currency) != 3:
            errors["currency"] = _(
                "Currency must contain exactly three characters."
            )

        if self.currency:
            self.currency = self.currency.upper()

        # ---------------------------------------------------------
        # Generic provenance
        # ---------------------------------------------------------
        if not self.source_type:
            errors["source_type"] = _(
                "Source type is required."
            )

        if not self.source_id:
            errors["source_id"] = _(
                "Source ID is required."
            )

        # ---------------------------------------------------------
        # Direction-specific party requirements
        # ---------------------------------------------------------
        if self.direction == self.Direction.DISBURSE:
            if self.beneficiary_id is None:
                errors["beneficiary"] = _(
                    "A beneficiary is required for a disbursement."
                )

        if self.direction == self.Direction.RECEIVE:
            # A receive operation may originate from an external payer,
            # therefore payer is intentionally allowed to be NULL.
            pass

        if errors:
            raise ValidationError(errors)

        # ---------------------------------------------------------
        # Immutability after execution begins
        # ---------------------------------------------------------
        if not self._state.adding and self.pk:
            previous = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "direction",
                    "purpose",
                    "source_type",
                    "source_id",
                    "source_reference",
                    "payer_id",
                    "beneficiary_id",
                    "amount",
                    "currency",
                    "status",
                )
                .first()
            )

            if previous and previous["status"] in {
                self.Status.PROCESSING,
                self.Status.COMPLETED,
                self.Status.FAILED,
                self.Status.CANCELLED,
                self.Status.REVERSED,
            }:
                immutable_fields = (
                    "direction",
                    "purpose",
                    "source_type",
                    "source_id",
                    "source_reference",
                    "payer_id",
                    "beneficiary_id",
                    "amount",
                    "currency",
                )

                for field in immutable_fields:
                    current_value = getattr(self, field)
                    previous_value = previous[field]

                    if current_value != previous_value:
                        errors[field] = _(
                            "This field cannot be changed after "
                            "payment execution has begun."
                        )

        if errors:
            raise ValidationError(errors)

    # -------------------------------------------------------------
    # Status helpers
    # -------------------------------------------------------------

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_processing(self):
        return self.status == self.Status.PROCESSING

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_reversed(self):
        return self.status == self.Status.REVERSED

    @property
    def is_terminal(self):
        return self.status in {
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.CANCELLED,
            self.Status.REVERSED,
        }