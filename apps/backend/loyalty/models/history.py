# apps/backend/loyalty/models/history.py

from django.conf import settings
from django.db import models


class LoyaltyHistory(models.Model):
    """
    Records loyalty activity for a user account.

    Ownership:
        accounts.User -> LoyaltyHistory
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_history",
    )
    reward = models.CharField(max_length=100)
    date_redeemed = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_redeemed"]
        indexes = [
            models.Index(
                fields=["user", "date_redeemed"],
                name="loyalty_history_user_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} redeemed "
            f"{self.reward} on {self.date_redeemed}"
        )