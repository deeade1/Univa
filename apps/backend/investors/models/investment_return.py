from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class InvestmentReturn(models.Model):
    class ReturnType(models.TextChoices):
        PROFIT = "PROFIT", "Profit"
        INTEREST = "INTEREST", "Interest"
        DIVIDEND = "DIVIDEND", "Dividend"
        CAPITAL_GAIN = "CAPITAL_GAIN", "Capital Gain"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CALCULATED = "CALCULATED", "Calculated"
        APPROVED = "APPROVED", "Approved"
        PAYABLE = "PAYABLE", "Payable"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        REVERSED = "REVERSED", "Reversed"

    investment = models.ForeignKey(
        "investors.Investment",
        on_delete=models.PROTECT,
        related_name="returns",
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    return_type = models.CharField(
        max_length=20,
        choices=ReturnType.choices,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
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

    earned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    payable_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
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
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["investment", "status"],
                name="invret_invest_status_idx",
            ),
            models.Index(
                fields=["return_type", "status"],
                name="invret_type_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="invret_status_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="invret_amount_positive",
            ),
        ]

    def clean(self):
        errors = {}

        if self.investment_id is None:
            errors["investment"] = "Investment is required."

        if not self.reference:
            errors["reference"] = "Reference is required."

        if not self.return_type:
            errors["return_type"] = "Return type is required."

        if self.amount is None:
            errors["amount"] = "Amount is required."
        elif self.amount <= Decimal("0.00"):
            errors["amount"] = "Amount must be greater than zero."

        if not self.currency:
            errors["currency"] = "Currency is required."
        else:
            self.currency = self.currency.upper()

            if len(self.currency) != 3:
                errors["currency"] = (
                    "Currency must be exactly three characters."
                )

        if not isinstance(self.metadata, dict):
            errors["metadata"] = "Metadata must be a dictionary."

        if errors:
            raise ValidationError(errors)

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_calculated(self):
        return self.status == self.Status.CALCULATED

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def is_payable(self):
        return self.status == self.Status.PAYABLE

    @property
    def is_paid(self):
        return self.status == self.Status.PAID

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_reversed(self):
        return self.status == self.Status.REVERSED

    def __str__(self):
        return self.reference