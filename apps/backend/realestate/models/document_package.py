
# apps/backend/realestate/models/document_package.py

"""
Document Package model for real estate.
"""

from django.conf import settings
from django.db import models


class DocumentPackage(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="document_packages")
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,  related_name="created_document_packages")
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property'], name='doc_pkg_property_idx'),
            models.Index(fields=['created_by'], name='doc_pkg_creator_idx'),
            models.Index(fields=['is_completed'], name='doc_pkg_completed_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.property.title}"