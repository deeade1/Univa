# apps/backend/realestate/models/message.py

"""
Message model for real estate.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Message(models.Model):
    thread = models.ForeignKey("MessageThread", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sender")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['thread', 'timestamp', 'sender'], name='msg_thread_ts_sender_idx'),
            GinIndex(fields=['content'], name='msg_content_gin', opclasses=['gin_trgm_ops']),
            models.Index(fields=['thread', 'read'], name='msg_thread_read_idx'),
            models.Index(fields=['sender'], name='msg_sender_idx'),
            models.Index(fields=['timestamp'], name='msg_timestamp_idx'),
        ]

    def __str__(self):
        return f"Message from {self.sender} in thread {self.thread.id} at {self.timestamp}"