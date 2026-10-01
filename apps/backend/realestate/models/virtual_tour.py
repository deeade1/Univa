# apps/backend/realestate/models/virtual_tour.py

"""
Virtual Tour model for real estate.
"""

from django.db import models


class VirtualTour(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="virtual_tours")
    tour_url = models.URLField()
    thumbnail = models.ImageField(upload_to='virtual_tours/')
    created_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "created_at"]
        indexes = [models.Index(fields=["property"], name="virtual_tour_property_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["property"], 
                condition=models.Q(is_primary=True), 
                name="unique_primary_virtual_tour"
            )
        ]

    def __str__(self):
        return f"Virtual Tour for {self.property.title or 'No Title'}"