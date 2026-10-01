# apps/backend/realestate/models/property_update_log.py

"""
Property Update Log model for real estate.

Records changes made to real-estate listings.

The account responsible for the change belongs to the central
accounts.User model.
"""

import json

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class PropertyUpdateLog(models.Model):
    """
    Immutable audit record for changes made to a Listing.

    Ownership:

        Listing
            │
            └── PropertyUpdateLog
                    └── updated_by → accounts.User
    """

    property = models.ForeignKey(
        "Listing",
        on_delete=models.CASCADE,
        related_name="update_logs",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="realestate_property_update_logs",
    )

    changed_fields = models.JSONField(
        default=dict,
        blank=True,
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-timestamp"]

        indexes = [
            models.Index(
                fields=["property", "timestamp"],
                name="update_log_pro_timestamp_idx",
            ),
            GinIndex(
                fields=["changed_fields"],
                name="update_log_changed_fields_gin",
            ),
            models.Index(
                fields=["updated_by"],
                name="update_log_updated_by_idx",
            ),
        ]

    def __str__(self):
        property_title = (
            self.property.title
            if self.property and self.property.title
            else "No Title"
        )

        updater = (
            self.updated_by.email
            if self.updated_by
            else "Unknown User"
        )

        return (
            f"Update on {property_title} "
            f"by {updater} at {self.timestamp}"
        )

    def get_changed_fields(self):
        """
        Return the names of fields that were changed.
        """
        return list(self.changed_fields.keys())

    def get_change_summary_as_dict(self):
        """
        Return changed fields excluding values that are None.
        """
        return {
            field: value
            for field, value in self.changed_fields.items()
            if value is not None
        }

    def get_change_summary(self):
        """
        Return a human-readable summary of the changes.
        """
        changes = self.get_change_summary_as_dict()

        if not changes:
            return "No changes made"

        return ", ".join(
            f"{field}: {value}"
            for field, value in changes.items()
        )

    def get_change_summary_as_json(self):
        """
        Return the change summary as JSON.
        """
        return json.dumps(
            self.get_change_summary_as_dict()
            or {"message": "No changes made"}
        )
