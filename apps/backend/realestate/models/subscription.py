# apps/backend/realestate/models/subscription.py

"""
Property subscription model for real estate.

A PropertySubscription belongs directly to the central account user.

Relationship:

    accounts.User
        └── realestate.PropertySubscription

The subscription stores real-estate-specific search and notification
preferences. It does not depend on accounts.UserProfile.
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.measure import D
from django.db import models

from realestate.constants import NOTIFICATION_FREQUENCY
from .listing import Listing


class PropertySubscription(models.Model):
    """
    Saved real-estate property subscription for a user.

    A subscription defines the type of property, geographic search
    area, radius, and notification frequency that the user wants
    to receive updates for.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_subscriptions",
    )

    property_type = models.CharField(
        max_length=50,
        blank=True,
    )

    location_point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
    )

    radius_km = models.PositiveIntegerField(
        default=10,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notification_frequency = models.CharField(
        max_length=20,
        choices=NOTIFICATION_FREQUENCY,
        default="instant",
    )

    last_notified = models.DateTimeField(
        null=True,
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
                fields=["user", "is_active"],
                name="sub_user_active_idx",
            ),
            models.Index(
                fields=["property_type", "is_active"],
                name="sub_prop_active_idx",
            ),
            models.Index(
                fields=["notification_frequency", "is_active"],
                name="sub_notify_active_idx",
            ),
            models.Index(
                fields=["last_notified"],
                name="sub_last_notified_idx",
            ),
            gis_models.Index(
                fields=["location_point"],
                name="sub_location_point_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Subscription for {self.user} - "
            f"{self.property_type or 'All'}"
        )

    def get_properties_in_radius(self):
        """
        Return published listings within the subscription's
        configured geographic radius.

        Results are ordered by distance from the subscription
        location.
        """
        if not self.location_point:
            return Listing.objects.none()

        queryset = (
            Listing.objects.filter(
                location_point__distance_lte=(
                    self.location_point,
                    D(km=self.radius_km),
                )
            )
            .filter(is_published=True)
            .annotate(
                distance=gis_models.Distance(
                    "location_point",
                    self.location_point,
                )
            )
            .order_by("distance")
        )

        if self.property_type:
            queryset = queryset.filter(
                listing_type__property_type=self.property_type
            )

        return queryset
