from django.db import models
from django.utils import timezone


class EmergencyContactMixin(models.Model):
    """Mixin for emergency contact information"""
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True, null=True)
    
    class Meta:
        abstract = True

class TimestampMixin(models.Model):
    """Mixin for created and updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True