# apps/backend/loyalty/models/reward.py

from django.conf import settings
from django.db import models


class LoyaltyReward(models.Model):
    """
    Loyalty reward assigned directly to a user account.

    Ownership:
        accounts.User -> LoyaltyReward
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_rewards",
    )
    reward_type = models.CharField(max_length=20)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    expires = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "expires"],
                name="loyalty_reward_user_exp_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Loyalty reward for "
            f"{self.user.email} - {self.reward_type}"
        )