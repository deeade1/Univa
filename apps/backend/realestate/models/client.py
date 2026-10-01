# apps/backend/realestate/models/client.py

"""
Client model for the real estate domain.

A Client is a real-estate-specific representation of an account.
The core account belongs to Django's AUTH_USER_MODEL.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from core.models.location import LocationModel

from .base import TimeStampedModel
from realestate.constants import NOTIFICATION_FREQUENCY
from .listing import Listing


class Client(LocationModel, TimeStampedModel):
    """
    Real-estate client preferences and search configuration.

    The account identity belongs directly to the central User model.
    Client contains only real-estate-specific information.
    """

    VERIFY_ADDRESS = True

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="realestate_client",
    )

    search_radius_km = models.PositiveIntegerField(
        default=10,
        validators=[
            MaxValueValidator(100),
        ],
    )

    price_range_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    price_range_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    preferred_property_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of property type codes",
    )

    notification_frequency = models.CharField(
        max_length=20,
        choices=NOTIFICATION_FREQUENCY,
        default="instant",
    )

    class Meta:
        ordering = ["-created"]

        indexes = [
            models.Index(
                fields=["search_radius_km"],
                name="client_search_radius_idx",
            ),
            GinIndex(
                fields=["preferred_property_types"],
                name="client_prop_types_gin",
                opclasses=["jsonb_ops"],
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(price_range_min__isnull=True)
                    | Q(price_range_max__isnull=True)
                    | Q(price_range_min__lte=F("price_range_max"))
                ),
                name="client_price_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(search_radius_km__lte=100),
                name="client_radius_max_100km",
            ),
        ]

    def __str__(self):
        return f"Real Estate Client: {self.user}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.price_range_min is not None
            and self.price_range_max is not None
            and self.price_range_min > self.price_range_max
        ):
            raise ValidationError(
                {
                    "price_range_max": (
                        "Maximum price must be greater than minimum price."
                    )
                }
            )

    def find_nearby_properties(self, max_results=20):
        if not self.location_point:
            return Listing.objects.none()

        return (
            Listing.objects
            .nearby(
                self.location_point,
                self.search_radius_km,
            )
            .published()
            .with_price_range(
                self.price_range_min,
                self.price_range_max,
            )
            .by_property_type(
                self.preferred_property_types,
            )[:max_results]
        )

    def get_personalized_recommendations(self, max_results=10):
        return self.find_nearby_properties(max_results)