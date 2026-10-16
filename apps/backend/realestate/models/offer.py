# apps/backend/realestate/models/offer.py

"""
Offer model for real estate.

An Offer represents a buyer's proposal against a real-estate listing.

Ownership:
    accounts.User
        └── realestate.Client
                └── realestate.Offer
"""

from decimal import Decimal
from django.db.models import F
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .client import Client


class Offer(models.Model):
    """
    Purchase offer submitted by a real-estate client.

    The buyer relationship intentionally points to Client rather than
    accounts.UserProfile. Client is the real-estate domain representation
    of the user's account.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("countered", "Countered"),
        ("withdrawn", "Withdrawn"),
        ("expired", "Expired"),
    ]

    property = models.ForeignKey(
        "Listing",
        on_delete=models.CASCADE,
        related_name="offers",
    )

    buyer = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="buyer_offers",
    )

    offer_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    message = models.TextField(
        blank=True,
    )

    expiration_date = models.DateTimeField()

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
                fields=["property", "status"],
                name="offer_property_status_idx",
            ),
            models.Index(
                fields=["buyer", "created_at"],
                name="offer_buyer_created_idx",
            ),
            models.Index(
                fields=["expiration_date"],
                name="offer_expiration_idx",
            ),
            models.Index(
                fields=["property", "created_at"],
                name="offer_property_created_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    expiration_date__gt=models.F("created_at")
                ),
                name="offer_expiration_after_creation",
            ),
        ]
    
    def __str__(self):
        property_title = self.property.title or "No Title"

        return (
            f"Offer {self.offer_price} "
            f"for {property_title} - {self.status}"
        )

    def is_expired(self):
        """
        Return True when the offer has passed its expiration date.
        """
        return timezone.now() > self.expiration_date
