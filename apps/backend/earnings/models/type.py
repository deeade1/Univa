"""
Canonical earning type definitions for Univa.

EarningType classifies an earning without owning the calculation
rules that produce the earning.

Examples:

    SERVICE
    COMMISSION
    TIP
    BONUS
    INCENTIVE
    REFERRAL
    FEE
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class EarningType(models.Model):
    """
    Canonical classification of an earning.
    """

    id = models.BigAutoField(primary_key=True)

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
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
        ordering = ["code"]
        indexes = [
            models.Index(
                fields=["is_active", "code"],
                name="earning_type_active_code_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"