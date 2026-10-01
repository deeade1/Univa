# apps/backend/realestate/models/search.py

"""
Search models for real estate.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import JSONField

from realestate.constants import NOTIFICATION_FREQUENCY
from .listing import Listing


class SearchProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_profiles")
    name = models.CharField(max_length=100)
    search_filters = JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    notification_frequency = models.CharField(max_length=20, choices=NOTIFICATION_FREQUENCY, default="instant")
    last_notified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["search_filters"], name="search_prof_filters_gin"),
            models.Index(fields=["user", "is_active"], name="search_profile_user_idx"),
            models.Index(fields=["is_active", "notification_frequency"], name="search_prof_notify_idx"),
            models.Index(fields=["last_notified"], name="search_prof_last_notif_idx"),
        ]

    def __str__(self):
        return f"Search: {self.name} - {self.user}"

    def execute_search(self):
        return Listing.objects.search(self.search_filters)