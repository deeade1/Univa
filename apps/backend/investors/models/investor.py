"""
Canonical Investor model for Univa.

Investor represents a user's investor identity within Univa.

The model intentionally does not own:

    - money balances
    - payment records
    - banking accounts
    - settlements
    - earnings
    - distributions
    - investment calculations

Those concerns belong to their respective domains.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Investor(models.Model):
    """
    Canonical investor identity.

    One User may have at most one Investor profile.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        CLOSED = "CLOSED", "Closed"

    id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investor_profile",
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    display_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
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
        db_table = "investors_investor"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="investor_status_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.reference:
            raise ValidationError(
                {"reference": "Investor reference is required."}
            )

        if len(self.reference) > 50:
            raise ValidationError(
                {"reference": "Investor reference cannot exceed 50 characters."}
            )

        if self.status not in self.Status.values:
            raise ValidationError(
                {"status": "Invalid investor status."}
            )

        if self.metadata is None:
            self.metadata = {}

        if not isinstance(self.metadata, dict):
            raise ValidationError(
                {"metadata": "Investor metadata must be an object."}
            )

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_suspended(self):
        return self.status == self.Status.SUSPENDED

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    def __str__(self):
        return self.reference