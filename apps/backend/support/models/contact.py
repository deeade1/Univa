from django.conf import settings
from django.db import  models
import uuid

class ContactUs(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Reply info
    replied = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)
    reply_message = models.TextField(null=True, blank=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contact_replies",
    )
    
    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.name} <{self.email}>"