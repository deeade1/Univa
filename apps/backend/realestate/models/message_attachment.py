# apps/backend/realestate/models/message_attachment.py

"""
Message Attachment model for real estate.
"""

from django.db import models


class MessageAttachment(models.Model):
    message = models.ForeignKey("Message", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to='message_attachments/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['message'], name='msg_attach_message_idx'),
            models.Index(fields=['file_type'], name='msg_attach_type_idx'),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.file_type})"