"""
Canonical InvestmentOpportunity model for Univa.

An InvestmentOpportunity represents an investment opportunity that may
be made available to investors.

The model does not own:

    - investor commitments
    - investment transactions
    - distributions
    - settlements
    - payments
    - banking records
"""

from django.core.exceptions import ValidationError
from django.db import models


class InvestmentOpportunity(models.Model):
    """
    A canonical investment opportunity offered by Univa.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        PAUSED = "PAUSED", "Paused"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.BigAutoField(primary_key=True)

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

    currency = models.CharField(
        max_length=3,
        default="NGN",
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
        db_table = "investors_investment_opportunity"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="invopp_status_created_idx",
            ),
            models.Index(
                fields=["currency", "status"],
                name="invopp_currency_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.reference:
            raise ValidationError(
                {"reference": "Opportunity reference is required."}
            )

        if not self.name:
            raise ValidationError(
                {"name": "Opportunity name is required."}
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

        if self.minimum_amount is None:
            raise ValidationError(
                {"minimum_amount": "Minimum amount is required."}
            )

        if self.minimum_amount <= 0:
            raise ValidationError(
                {"minimum_amount": "Minimum amount must be greater than zero."}
            )

        if self.maximum_amount is not None:
            if self.maximum_amount <= 0:
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

        if self.metadata is None:
            self.metadata = {}

        if not isinstance(self.metadata, dict):
            raise ValidationError(
                {"metadata": "Opportunity metadata must be an object."}
            )

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

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