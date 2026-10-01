# apps/backend/loyalty/models/tier.py

from django.db import models


class LoyaltyRewardTier(models.Model):
    """
    Defines a loyalty reward tier.

    Tiers are global loyalty configuration and are not owned
    by an individual user.
    """

    points_needed = models.PositiveIntegerField()
    reward = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["points_needed"]
        indexes = [
            models.Index(
                fields=["active", "points_needed"],
                name="loyalty_tier_active_points_idx",
            ),
        ]

    def __str__(self):
        return f"{self.points_needed} pts - {self.reward}"