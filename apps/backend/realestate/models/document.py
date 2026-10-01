# apps/backend/realestate/models/document.py

"""
Document model for real estate.
"""

from django.db import models


class Document(models.Model):
    package = models.ForeignKey("DocumentPackage", on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to='property_documents/')
    title = models.CharField(max_length=200)
    requires_signature = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["package", "order"], name="doc_package_order_idx")]

    def __str__(self):
        return f"{self.title} - {self.package.title}"