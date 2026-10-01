"""
Canonical commission plans for Univa.

A CommissionPlan defines the rule used to calculate a commission.

The plan is domain-neutral and may be used by:

    - Real Estate
    - Transport
    - Logistics
    - E-commerce
    - Referrals
    - Affiliates
    - Other Univa domains

A CommissionPlan defines HOW a commission is calculated.

A Commission records WHAT was actually earned.
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class CommissionPlan(models.Model):
    """
    Defines a reusable commission calculation policy.

    Historical commission records must retain the calculation result
    that was produced from the applicable plan at the time of calculation.
    """

    class PlanType(models.TextChoices):
        PERCENTAGE = "percentage", _("Percentage")
        FIXED = "fixed", _("Fixed Amount")
        TIERED = "tiered", _("Tiered")

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    code = models.CharField(
        max_length=80,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
    )

    percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )

    fixed_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    effective_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
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
                fields=["plan_type", "is_active"],
                name="comm_plan_type_active_idx",
            ),
            models.Index(
                fields=["effective_from", "effective_until"],
                name="comm_plan_effective_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_percentage(self):
        return self.plan_type == self.PlanType.PERCENTAGE

    @property
    def is_fixed(self):
        return self.plan_type == self.PlanType.FIXED

    @property
    def is_tiered(self):
        return self.plan_type == self.PlanType.TIERED