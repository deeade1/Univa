# apps/backend/realestate/models/message_thread.py

"""
Message Thread model for real estate.
"""

from django.conf import settings
from django.db import models
from django.contrib.postgres.indexes import GinIndex



class MessageThread(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, null=True, blank=True, related_name="threads")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="message_threads")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property", "-updated_at"], name="msg_thread_proty_upd_idx"),
            models.Index(fields=["created_at"], name="msg_thread_created_idx"),
        ]

    def __str__(self):
        return f"Thread for {self.property.title if self.property else 'General'} - {self.created_at}"
    

