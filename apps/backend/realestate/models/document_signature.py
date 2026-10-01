# apps/backend/realestate/models/document_signature.py

"""
Document Signature model for real estate.
"""

from django.conf import settings
from django.db import models


class DocumentSignature(models.Model):
    document = models.ForeignKey("Document", on_delete=models.CASCADE, related_name="signatures")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="user" )
    signed_at = models.DateTimeField(auto_now_add=True)
    signature_image = models.ImageField(upload_to='signatures/')
    ip_address = models.GenericIPAddressField()

    class Meta:
        ordering = ["-signed_at"]
        indexes = [
            models.Index(fields=["document", "signed_at"], name="doc_sig_document_signed_idx"),
            models.Index(fields=["user", "signed_at"], name="doc_sig_user_signed_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "user"], 
                name="unique_document_signature"
            ),
        ]

    def __str__(self):
        return f"Signature by {self.user} on {self.document.title} at {self.signed_at}"