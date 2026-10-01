
# apps/backend/realestate/models/listing_type.py

"""
Listing Type model for real estate.
"""

from django.db import models

from core.models.location import LocationModel
from .base import TimeStampedModel
from realestate.constants import PROPERTY_TYPES


class ListingType(TimeStampedModel, LocationModel):
    property_type = models.CharField(max_length=100, choices=PROPERTY_TYPES, unique=True)
    requires_land_details = models.BooleanField(default=False)
    requires_building_details = models.BooleanField(default=True)
    supports_plot_sales = models.BooleanField(default=False)

    class Meta:
        ordering = ["property_type"]
        indexes = [
            models.Index(fields=["requires_land_details"], name="listtype_land_details_idx"),
            models.Index(fields=["supports_plot_sales"], name="listtype_plot_sales_idx"),
        ]

    def __str__(self):
        return self.get_property_type_display()