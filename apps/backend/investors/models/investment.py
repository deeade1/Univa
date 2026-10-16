"""
Canonical Investment model for Univa.

An Investment represents an actual investment position created from an
InvestmentCommitment.

The model intentionally does not own:

    - investment return calculations
    - distributions
    - settlements
    - payments
    - banking transactions
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .commitment import InvestmentCommitment
from .opportunity import InvestmentOpportunity
from .plan import InvestmentPlan


class Investment(models.Model):
    """
    An actual investment position created from an investment commitment.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        MATURED = "MATURED", "Matured"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.BigAutoField(primary_key=True)

    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investor_investments",
    )

    opportunity = models.ForeignKey(
        InvestmentOpportunity,
        on_delete=models.PROTECT,
        related_name="investments",
    )

    plan = models.ForeignKey(
        InvestmentPlan,
        on_delete=models.PROTECT,
        related_name="investments",
    )

    commitment = models.OneToOneField(
        InvestmentCommitment,
        on_delete=models.PROTECT,
        related_name="investment",
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
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
        db_index=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    matured_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
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
        db_table = "investors_investment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["investor", "status"],
                name="investment_investor_status_idx",
            ),
            models.Index(
                fields=["opportunity", "status"],
                name="investment_opp_status_idx",
            ),
            models.Index(
                fields=["plan", "status"],
                name="investment_plan_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="investment_status_created_idx",
            ),
        ]

    
    def clean(self):
        super().clean()

        if self.investor_id is None:
            raise ValidationError(
                {"investor": "Investor is required."}
            )

        if self.opportunity_id is None:
            raise ValidationError(
                {"opportunity": "Investment opportunity is required."}
            )

        if self.plan_id is None:
            raise ValidationError(
                {"plan": "Investment plan is required."}
            )

        if self.commitment_id is None:
            raise ValidationError(
                {"commitment": "Investment commitment is required."}
            )

        if not self.reference:
            raise ValidationError(
                {"reference": "Investment reference is required."}
            )

        if self.amount is None:
            raise ValidationError(
                {"amount": "Investment amount is required."}
            )

        if self.amount <= Decimal("0"):
            raise ValidationError(
                {"amount": "Investment amount must be greater than zero."}
            )

        if not self.currency:
            raise ValidationError(
                {"currency": "Currency is required."}
            )

        self.currency = self.currency.upper()

        if len(self.currency) != 3:
            raise ValidationError(
                {"currency": "Currency must be exactly 3 characters."}
            )

        if self.metadata is None:
            self.metadata = {}

        if not isinstance(self.metadata, dict):
            raise ValidationError(
                {"metadata": "Investment metadata must be an object."}
            )

        commitment = self.commitment

        if commitment.investor_id != self.investor_id:
            raise ValidationError({
                "investor": (
                    "Investment investor must match the commitment investor."
                )
            })

        if commitment.opportunity_id != self.opportunity_id:
            raise ValidationError({
                "opportunity": (
                    "Investment opportunity must match the commitment "
                    "opportunity."
                )
            })

        if commitment.plan_id != self.plan_id:
            raise ValidationError({
                "plan": "Investment plan must match the commitment plan."
            })

        if commitment.amount != self.amount:
            raise ValidationError({
                "amount": "Investment amount must match the commitment amount."
            })

        if commitment.currency.upper() != self.currency:
            raise ValidationError({
                "currency": (
                    "Investment currency must match the commitment currency."
                )
            })

        if commitment.status != InvestmentCommitment.Status.FUNDED:
            raise ValidationError({
                "commitment": (
                    "An investment can only be created from a funded commitment."
                )
            })


    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_matured(self):
        return self.status == self.Status.MATURED

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def __str__(self):
        return self.reference