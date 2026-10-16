# apps/backend/realestate/models/commission.py

"""
Commission models for real estate.
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class CommissionPlan(models.Model):
    PLAN_TYPES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
        ("tiered", "Tiered"),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    base_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(
                fields=["plan_type", "is_active"],
                name="comm_plan_type_active",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(min_amount__isnull=True)
                    | Q(max_amount__isnull=True)
                    | Q(min_amount__lte=F("max_amount"))
                ),
                name="commission_plan_min_le_max",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"