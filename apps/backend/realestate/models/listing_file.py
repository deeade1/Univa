
# apps/backend/realestate/models/listing_file.py
"""
Listing File model for real estate.
"""

from django.db import models

from .base import TimeStampedModel
from django.conf import settings



class ListingFile(TimeStampedModel):
    listing = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="files")
    name = models.CharField(max_length=255)
    short_description = models.TextField(blank=True)
    file = models.FileField(upload_to="listings/files/", null=True, blank=True)
    for_customer = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=['listing'], name='listingfile_listing_idx'),
            models.Index(fields=['for_customer'], name='listingfile_customer_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.listing.title or 'No Title'})"
    
    