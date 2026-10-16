# apps/backend/realestate/models/agent_commission.py

"""
AgentCommission model for real estate.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from .commission import CommissionPlan


class AgentCommission(models.Model):
    agent = models.ForeignKey(
        "Agent",
        on_delete=models.PROTECT,
        related_name="commissions",
    )
    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.PROTECT,
        related_name="commissions_transaction",
    )
    commission_plan = models.ForeignKey(
        CommissionPlan,
        on_delete=models.PROTECT,
        related_name="agent_commissions",
    )

    calculated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(
                fields=["agent", "paid_date"],
                name="commission_agent_paid_idx",
            ),
            models.Index(
                fields=["transaction"],
                name="commission_transaction_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(calculated_amount__gte=0),
                name="commission_calculated_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__gte=0),
                name="commission_paid_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__lte=F("calculated_amount")),
                name="commission_paid_lte_calculated",
            ),
        ]

    def __str__(self):
        return (
            f"Commission: {self.agent} - "
            f"{self.calculated_amount}"
        )