"""
Canonical InvestmentPlan model for Univa.

An InvestmentPlan defines the investment terms offered under an
InvestmentOpportunity.

The model intentionally does not own:

    - investor commitments
    - investor balances
    - payments
    - settlements
    - distributions
    - investment returns
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .opportunity import InvestmentOpportunity


class InvestmentPlan(models.Model):
    """
    Defines the terms under which an investment opportunity may be
    subscribed to.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.BigAutoField(primary_key=True)

    opportunity = models.ForeignKey(
        InvestmentOpportunity,
        on_delete=models.PROTECT,
        related_name="plans",
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    minimum_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    maximum_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    expected_return_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        blank=True,
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "investors_investment_plan"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["opportunity", "status"],
                name="invplan_opp_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="invplan_status_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.opportunity_id is None:
            raise ValidationError(
                {"opportunity": "Investment opportunity is required."}
            )

        if not self.reference:
            raise ValidationError(
                {"reference": "Investment plan reference is required."}
            )

        if not self.name:
            raise ValidationError(
                {"name": "Investment plan name is required."}
            )

        if self.minimum_amount is None:
            raise ValidationError(
                {"minimum_amount": "Minimum amount is required."}
            )

        if self.minimum_amount <= Decimal("0"):
            raise ValidationError(
                {
                    "minimum_amount":
                    "Minimum amount must be greater than zero."
                }
            )

        if self.maximum_amount is not None:
            if self.maximum_amount <= Decimal("0"):
                raise ValidationError(
                    {
                        "maximum_amount":
                        "Maximum amount must be greater than zero."
                    }
                )

            if self.maximum_amount < self.minimum_amount:
                raise ValidationError(
                    {
                        "maximum_amount":
                        "Maximum amount cannot be less than minimum amount."
                    }
                )

        if self.duration_days is not None and self.duration_days <= 0:
            raise ValidationError(
                {
                    "duration_days":
                    "Duration must be greater than zero."
                }
            )

        if self.expected_return_rate is not None:
            if self.expected_return_rate < Decimal("0"):
                raise ValidationError(
                    {
                        "expected_return_rate":
                        "Expected return rate cannot be negative."
                    }
                )

        if self.metadata is None:
            self.metadata = {}

        if not isinstance(self.metadata, dict):
            raise ValidationError(
                {"metadata": "Investment plan metadata must be an object."}
            )

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_paused(self):
        return self.status == self.Status.PAUSED

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def __str__(self):
        return self.reference