# apps/backend/realestate/models/location_preference.py

"""
Location Preference model for real estate.

A LocationPreference belongs directly to the central account User.
It contains only real-estate-specific geographic search preferences.
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class LocationPreference(models.Model):
    """
    Geographic preference used by a real-estate user when searching
    for properties.

    Ownership:

        accounts.User
            └── realestate.LocationPreference
    """

    name = models.CharField(
        max_length=100,
    )

    location_point = gis_models.PointField(
        srid=4326,
    )

    radius_km = models.PositiveIntegerField(
        default=5,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_preferences",
    )

    class Meta:
        ordering = ["-id"]

        indexes = [
            gis_models.Index(
                fields=["location_point"],
                name="loc_pref_point_idx",
            ),
            models.Index(
                fields=["user"],
                name="loc_pref_user_idx",
            ),
            models.Index(
                fields=["name"],
                name="loc_pref_name_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.first_name}"

    @property
    def latitude(self):
        return (
            self.location_point.y
            if self.location_point
            else None
        )

    @property
    def longitude(self):
        return (
            self.location_point.x
            if self.location_point
            else None
        )

