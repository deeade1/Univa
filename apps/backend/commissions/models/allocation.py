"""
Commission allocation model for Univa.

A Commission represents the total commission entitlement generated
by a business event.

A CommissionAllocation represents how that commission is allocated
among one or more beneficiaries.

Example:

    Property sale commission = ₦10,000,000

        Agent A   → ₦7,000,000
        Agent B   → ₦2,000,000
        Univa     → ₦1,000,000

The Commission remains the canonical commission record.

Allocations describe the distribution of that commission.

Settlement and payment are separate concerns.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .commission import Commission


class CommissionAllocation(models.Model):
    """
    Represents one beneficiary's share of a Commission.

    Allocation does not represent payment.

    The aggregate allocation rule:

        sum(allocation.amount) == commission.calculated_amount

    is enforced by the commission service when allocations are
    finalized rather than by this individual model.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    commission = models.ForeignKey(
        Commission,
        on_delete=models.PROTECT,
        related_name="allocations",
    )

    beneficiary = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="commission_allocations",
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    allocation_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
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
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["commission", "beneficiary"],
                name="commission_alloc_comm_ben_idx",
            ),
            models.Index(
                fields=["beneficiary", "created_at"],
                name="comm_alloc_ben_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Allocation {self.id} - "
            f"{self.beneficiary} - "
            f"{self.amount} {self.commission.currency}"
        )

    def clean(self):
        super().clean()

        if self.amount < 0:
            raise ValidationError(
                {
                    "amount": _(
                        "Allocation amount cannot be negative."
                    )
                }
            )

        if self.allocation_percentage is not None:
            if not (
                Decimal("0")
                <= self.allocation_percentage
                <= Decimal("100")
            ):
                raise ValidationError(
                    {
                        "allocation_percentage": _(
                            "Allocation percentage must be "
                            "between 0 and 100."
                        )
                    }
                )

        if self.commission_id:
            if self.amount > self.commission.calculated_amount:
                raise ValidationError(
                    {
                        "amount": _(
                            "Allocation cannot exceed "
                            "the commission amount."
                        )
                    }
                )

    @property
    def currency(self):
        return self.commission.currency