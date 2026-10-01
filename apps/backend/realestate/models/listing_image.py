
# apps/backend/realestate/models/listing_image.py

"""
Listing Image model for real estate.
"""

from django.db import models
from django_resized import ResizedImageField

from .base import TimeStampedModel, listing_dir_path


class ListingImage(TimeStampedModel):
    listing = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="images")
    image = ResizedImageField(size=[1200, 630], upload_to=listing_dir_path)
    short_description = models.TextField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=['listing'], name='listingimage_listing_idx')]

    def __str__(self):
        return f"{self.listing.title or 'No Title'} - {self.image.name}"