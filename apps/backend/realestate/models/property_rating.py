# apps/backend/realestate/models/property_rating.py

"""
Property Rating model for real estate.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PropertyRating(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="property_ratings")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "user"], 
                name="unique_property_user_rating"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), 
                name="property_rating_1_to_5"
            ),
        ]
        indexes = [
            models.Index(fields=["property", "rating"], name="rating_property_rating_idx"),
            models.Index(fields=["user", "created_at"], name="rating_user_created_idx"),
            models.Index(fields=["property", "created_at"], name="rating_property_created_idx"),
        ]

    def __str__(self):
        return f"Rating {self.rating} for {self.property.title} by {self.user}"

    def clean(self):
        if self.review and len(self.review) > 2000:
            raise ValidationError({"review": "Review cannot exceed 2000 characters."})
        if self.property.owner and self.property.owner.user == self.user:
            raise ValidationError({"user": "You cannot rate your own property."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)