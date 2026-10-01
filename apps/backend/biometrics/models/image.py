# apps/backend/biometrics/models/image.py

"""
Face verification image model.

Stores images used for biometric verification and enrollment.
Biometric image processing belongs to the biometrics domain.
"""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_resized import ResizedImageField


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# ============================================================================
# FACE VERIFICATION IMAGE
# ============================================================================


class FaceVerificationImage(models.Model):
    """
    Stores images used for biometric/face verification.

    The model is the persistence boundary; the GraphQL and service
    layers are responsible for the actual verification workflow.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="face_verification_images",
    )

    image = ResizedImageField(
        size=[1200, 1200],
        upload_to="face_verification/",
        quality=90,
    )

    thumbnail = ResizedImageField(
        size=[300, 300],
        upload_to="face_verification/thumbnails/",
        quality=85,
        null=True,
        blank=True,
    )

    is_verified = models.BooleanField(default=False)

    verification_score = models.FloatField(
        null=True,
        blank=True,
    )

    face_detected = models.BooleanField(default=False)

    face_count = models.PositiveIntegerField(default=0)

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Face Verification Image")
        verbose_name_plural = _("Face Verification Images")
        indexes = [
            models.Index(
                fields=["user", "is_verified"],
                name="face_img_user_verified_idx",
            ),
            models.Index(
                fields=["face_detected"],
                name="face_img_detected_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="face_img_created_idx",
            ),
        ]

    def __str__(self):
        return f"Face Verification Image for {self.user.email}"

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        if self.image and hasattr(self.image, "size"):
            # ResizedImageField wraps an underlying field whose `.size`
            # may be a file-size in bytes after upload.
            try:
                if self.image.size and self.image.size > MAX_IMAGE_SIZE:
                    raise ValidationError(
                        {
                            "image": _(
                                "Image file too large. Maximum size is 10 MB."
                            )
                        }
                    )
            except (TypeError, ValueError):
                # Some upload handlers don't expose `.size` until save;
                # skip the check in that case.
                pass

            _, ext = os.path.splitext(self.image.name or "")
            if ext.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError(
                    {
                        "image": _(
                            "Only JPEG and PNG images are allowed."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)