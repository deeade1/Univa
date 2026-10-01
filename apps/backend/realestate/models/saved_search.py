# apps/backend/realestate/models/saved_search.py

"""
Saved Search model for real estate.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import JSONField


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=100)
    search_parameters = JSONField()
    is_active = models.BooleanField(default=True)
    last_notified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=['search_parameters'], name='saved_params_gin'),
            models.Index(fields=['user'], name='saved_search_idx'),
            models.Index(fields=['is_active'], name='saved_active_idx'),
            models.Index(fields=['last_notified'], name='saved_sea_noti_idx'),
        ]

    def __str__(self):
        return f"Saved Search: {self.name} - User: {self.user.first_name}"