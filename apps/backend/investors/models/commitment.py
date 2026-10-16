"""
Canonical InvestmentCommitment model for Univa.

An InvestmentCommitment represents an investor's commitment to invest
under an InvestmentPlan.

The model intentionally does not own:

    - payment execution
    - settlement
    - banking transactions
    - investment returns
    - distributions
    - earnings
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .opportunity import InvestmentOpportunity
from .plan import InvestmentPlan


class InvestmentCommitment(models.Model):
    """
    An investor's commitment under a specific investment plan.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FUNDED = "FUNDED", "Funded"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        REJECTED = "REJECTED", "Rejected"

    id = models.BigAutoField(primary_key=True)

    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investment_commitments",
    )

    opportunity = models.ForeignKey(
        InvestmentOpportunity,
        on_delete=models.PROTECT,
        related_name="commitments",
    )

    plan = models.ForeignKey(
        InvestmentPlan,
        on_delete=models.PROTECT,
        related_name="commitments",
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

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    funded_at = models.DateTimeField(
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
        db_table = "investors_investment_commitment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["investor", "status"],
                name="invcommit_investor_status_idx",
            ),
            models.Index(
                fields=["opportunity", "status"],
                name="invcommit_opp_status_idx",
            ),
            models.Index(
                fields=["plan", "status"],
                name="invcommit_plan_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="invcommit_status_created_idx",
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

        if not self.reference:
            raise ValidationError(
                {"reference": "Commitment reference is required."}
            )

        if self.amount is None:
            raise ValidationError(
                {"amount": "Commitment amount is required."}
            )

        if self.amount <= Decimal("0"):
            raise ValidationError(
                {"amount": "Commitment amount must be greater than zero."}
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
                {"metadata": "Commitment metadata must be an object."}
            )

        if self.plan_id:
            if self.plan.opportunity_id != self.opportunity_id:
                raise ValidationError(
                    {
                        "plan":
                        "Investment plan must belong to the selected "
                        "investment opportunity."
                    }
                )

            if self.amount < self.plan.minimum_amount:
                raise ValidationError(
                    {
                        "amount":
                        "Commitment amount cannot be below the plan "
                        "minimum amount."
                    }
                )

            if (
                self.plan.maximum_amount is not None
                and self.amount > self.plan.maximum_amount
            ):
                raise ValidationError(
                    {
                        "amount":
                        "Commitment amount cannot exceed the plan "
                        "maximum amount."
                    }
                )

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    @property
    def is_funded(self):
        return self.status == self.Status.FUNDED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_expired(self):
        return self.status == self.Status.EXPIRED

    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED

    def __str__(self):
        return self.reference