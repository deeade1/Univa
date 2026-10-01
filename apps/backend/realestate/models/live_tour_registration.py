# apps/backend/realestate/models/live_tour_registration.py

"""
Live Tour Registration model for real estate.
"""

from django.conf import settings
from django.db import models


class LiveTourRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_tour_registration")
    tour = models.ForeignKey("LiveTourSchedule", on_delete=models.CASCADE, related_name="tour")
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    class Meta:
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["tour", "registered_at"], name="tour_reg_tour_registered_idx"),
            models.Index(fields=["user", "registered_at"], name="tour_reg_user_registered_idx"),
            models.Index(fields=["attended"], name="tour_reg_attended_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tour"], 
                name="unique_tour_registration"
            ),
        ]

    def __str__(self):
        return f"{self.user.first_name} - {self.tour.property.title} - {self.registered_at}"