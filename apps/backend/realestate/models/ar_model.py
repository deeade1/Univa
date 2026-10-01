# apps/backend/realestate/models/ar_model.py

"""
AR Model for real estate.
"""

from django.core.validators import MinValueValidator
from django.db import models

from realestate.constants import ANCHOR_TYPES


class ARModel(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="ar_models")
    model_url = models.URLField()
    scale = models.FloatField(default=1.0, validators=[MinValueValidator(0.001)])
    anchor_type = models.CharField(max_length=20, choices=ANCHOR_TYPES)
    preview_image = models.ImageField(upload_to="ar_previews/")

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["property"], name="armodel_property_idx"),
            models.Index(fields=["anchor_type"], name="armodel_anchor_type_idx"),
        ]

    def __str__(self):
        return f"AR Model for {self.property.title or 'No Title'} - Scale: {self.scale}"