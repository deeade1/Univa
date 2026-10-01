# apps/backend/realestate/models/property_proximity.py

"""
Property proximity model for the real estate domain.

PropertyProximity stores the calculated distance between a listing and
a real-estate client's preferred/search location.

Ownership:

    accounts.User
        └── realestate.Client
                └── realestate.PropertyProximity

The real-estate domain references Client for buyer-specific relationships.
It does not depend on accounts.UserProfile.
"""

from django.core.validators import MinValueValidator
from django.db import models

from .client import Client


class PropertyProximity(models.Model):
    """
    Calculated proximity between a property and a real-estate client.
    """

    property = models.ForeignKey(
        "realestate.Listing",
        on_delete=models.CASCADE,
        related_name="proximities",
    )

    buyer = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="property_proximities",
    )

    distance_km = models.FloatField(
        validators=[
            MinValueValidator(0),
        ],
    )

    is_in_preferred_location = models.BooleanField(
        default=False,
    )

    calculated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-calculated_at"]

        
        constraints = [
            models.UniqueConstraint(
                fields=["property", "buyer"],
                name="unique_property_buyer_prox",
            ),
            models.CheckConstraint(
                condition=models.Q(distance_km__gte=0),
                name="prox_distance_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(distance_km__lte=1000),
                name="prox_distance_max_1000km",
            ),
        ]



        indexes = [
            models.Index(
                fields=[
                    "buyer",
                    "is_in_preferred_location",
                    "distance_km",
                ],
                name="prox_buyer_pref_distance_idx",
            ),
            models.Index(
                fields=["distance_km"],
                name="proximity_distance_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Proximity: {self.property} to {self.buyer} "
            f"- {self.distance_km:.2f}km"
        )
