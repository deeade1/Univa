"""
Canonical Earning model for Univa.

An Earning represents a financial entitlement attributable to a
beneficiary.

It does not represent:

    - a payment
    - a bank transaction
    - a settlement
    - a payout
    - a wallet balance

Those concerns belong to their respective financial layers.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .type import EarningType


class Earning(models.Model):
    """
    Canonical financial earning entitlement.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CALCULATED = "calculated", _("Calculated")
        CONFIRMED = "confirmed", _("Confirmed")
        PAYABLE = "payable", _("Payable")
        SETTLED = "settled", _("Settled")
        CANCELLED = "cancelled", _("Cancelled")
        REVERSED = "reversed", _("Reversed")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="earnings",
    )

    earning_type = models.ForeignKey(
        EarningType,
        on_delete=models.PROTECT,
        related_name="earnings",
    )

    source_type = models.CharField(
        max_length=50,
        db_index=True,
    )

    source_id = models.CharField(
        max_length=100,
        db_index=True,
    )

    source_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    calculation_basis = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    calculation_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    calculation_metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    earned_at = models.DateTimeField()

    calculated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    payable_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    settled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
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
        ordering = ["-earned_at", "-created_at"]

        indexes = [
            models.Index(
                fields=["beneficiary", "status"],
                name="earning_beneficiary_status_idx",
            ),
            models.Index(
                fields=["source_type", "source_id"],
                name="earning_source_idx",
            ),
            models.Index(
                fields=["earning_type", "status"],
                name="earning_type_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="earning_status_created_idx",
            ),
            models.Index(
                fields=["beneficiary", "earned_at"],
                name="earning_beneficiary_earned_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Earning {self.id} - "
            f"{self.beneficiary} - "
            f"{self.amount} {self.currency}"
        )

    def clean(self):
        super().clean()

        if self.amount < Decimal("0"):
            raise ValidationError(
                {
                    "amount": _(
                        "Earning amount cannot be negative."
                    )
                }
            )

        if self.calculation_basis is not None:
            if self.calculation_basis < Decimal("0"):
                raise ValidationError(
                    {
                        "calculation_basis": _(
                            "Calculation basis cannot be negative."
                        )
                    }
                )

        if self.calculation_rate is not None:
            if self.calculation_rate < Decimal("0"):
                raise ValidationError(
                    {
                        "calculation_rate": _(
                            "Calculation rate cannot be negative."
                        )
                    }
                )

        if (
            self.status == self.Status.CONFIRMED
            and self.confirmed_at is None
        ):
            raise ValidationError(
                {
                    "confirmed_at": _(
                        "A confirmed earning must have a "
                        "confirmation timestamp."
                    )
                }
            )

        if (
            self.status == self.Status.PAYABLE
            and self.payable_at is None
        ):
            raise ValidationError(
                {
                    "payable_at": _(
                        "A payable earning must have a "
                        "payable timestamp."
                    )
                }
            )

        if (
            self.status == self.Status.SETTLED
            and self.settled_at is None
        ):
            raise ValidationError(
                {
                    "settled_at": _(
                        "A settled earning must have a "
                        "settlement timestamp."
                    )
                }
            )

        if (
            self.status == self.Status.REVERSED
            and self.reversed_at is None
        ):
            raise ValidationError(
                {
                    "reversed_at": _(
                        "A reversed earning must have a "
                        "reversal timestamp."
                    )
                }
            )

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_calculated(self):
        return self.status == self.Status.CALCULATED

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    @property
    def is_payable(self):
        return self.status == self.Status.PAYABLE

    @property
    def is_settled(self):
        return self.status == self.Status.SETTLED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_reversed(self):
        return self.status == self.Status.REVERSED