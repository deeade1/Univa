# apps/backend/realestate/models/agent_rating.py

"""
Agent Rating model for real estate.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AgentRating(models.Model):
    agent = models.ForeignKey("realestate.Agent", on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_ratings")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "user"], 
                name="unique_agent_user_rating"
            ),
        ]
        indexes = [
            models.Index(fields=["agent", "rating"], name="agent_rating_agent_rating_idx"),
            models.Index(fields=["agent", "created_at"], name="agent_rating_agent_created_idx"),
        ]

    def __str__(self):
        return f"Rating {self.rating} for {self.agent} by {self.user}"