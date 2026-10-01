"""
Canonical earning adjustments for Univa.

Finalized earnings are not mutated to correct historical financial
facts. Corrections are represented explicitly as adjustments.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .earning import Earning


class EarningAdjustment(models.Model):
    """
    Immutable correction/reversal applied to an earning.
    """

    class AdjustmentType(models.TextChoices):
        CORRECTION = "correction", _("Correction")
        REVERSAL = "reversal", _("Reversal")
        OTHER = "other", _("Other")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    earning = models.ForeignKey(
        Earning,
        on_delete=models.PROTECT,
        related_name="adjustments",
    )

    adjustment_type = models.CharField(
        max_length=20,
        choices=AdjustmentType.choices,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    reason = models.TextField()

    source_type = models.CharField(
        max_length=50,
        blank=True,
    )

    source_id = models.CharField(
        max_length=100,
        blank=True,
    )

    source_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="earning_adjustments_created",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["earning", "created_at"],
                name="earning_adj_earn_created_idx",
            ),
            models.Index(
                fields=["adjustment_type", "created_at"],
                name="earning_adj_type_creat_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Earning adjustment {self.id} - "
            f"{self.amount} {self.earning.currency}"
        )

    def clean(self):
        super().clean()

        if self.amount == Decimal("0"):
            raise ValidationError(
                {
                    "amount": _(
                        "An earning adjustment cannot have a zero amount."
                    )
                }
            )