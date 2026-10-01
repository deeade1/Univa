# apps/backend/biometrics/models/verification.py

"""
Face verification state model.

One row per user. Tracks verification status, attempt counts,
lockout state, and policy thresholds.

Architecture
------------

The model owns:

    - per-user verification state
    - attempt counting
    - lockout timestamps
    - policy thresholds (confidence, liveness)

The model does NOT own:

    - embedding matching
    - face detection
    - JWT issuance
    - GraphQL

Those belong to biometrics.services.verification and univa_jwt.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_MAX_ATTEMPTS = 3

DEFAULT_LOCKOUT_MINUTES = 30

DEFAULT_CONFIDENCE_THRESHOLD = 0.6

DEFAULT_LIVENESS_THRESHOLD = 0.8


# ============================================================================
# FACE VERIFICATION
# ============================================================================


class FaceVerification(models.Model):
    """
    Per-user biometric verification state.

    Verification requires face matching against the user's active
    encodings. This model stores the resulting state and the policy
    that the matching service enforces.
    """

    VERIFICATION_METHODS = [
        ("face", "Face"),
        ("deepface", "DeepFace"),
        ("custom", "Custom Algorithm"),
    ]

    VERIFICATION_CHANNELS = [
        ("photo", "Static Photo"),
        ("video", "Video Capture"),
        ("liveness", "Liveness Check"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="face_verification",
    )

    is_verified = models.BooleanField(default=False)

    verification_method = models.CharField(
        max_length=20,
        choices=VERIFICATION_METHODS,
        default="face",
    )

    verification_channel = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHANNELS,
        default="photo",
    )

    device_id = models.CharField(max_length=255, blank=True)

    last_verified_at = models.DateTimeField(null=True, blank=True)

    verification_attempts = models.PositiveIntegerField(default=0)

    locked_until = models.DateTimeField(null=True, blank=True)

    confidence_threshold = models.FloatField(
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help_text=_(
            "Minimum confidence score for verification (0-1)."
        ),
    )

    liveness_threshold = models.FloatField(
        default=DEFAULT_LIVENESS_THRESHOLD,
        help_text=_("Minimum liveness score (0-1)."),
    )

    class Meta:
        verbose_name = _("Face Verification")
        verbose_name_plural = _("Face Verifications")
        ordering = ["-last_verified_at"]
        indexes = [
            models.Index(
                fields=["is_verified", "last_verified_at"],
                name="face_verif_state_idx",
            ),
            models.Index(
                fields=["user", "locked_until"],
                name="face_verif_lock_idx",
            ),
            models.Index(
                fields=["device_id"],
                name="face_verif_device_idx",
            ),
        ]

    def __str__(self):
        return f"Face Verification for {self.user.email}"

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def clean(self):
        super().clean()

        if self.confidence_threshold is not None:
            if not 0.0 <= float(self.confidence_threshold) <= 1.0:
                raise ValidationError(
                    {
                        "confidence_threshold": _(
                            "Confidence threshold must be between 0 and 1."
                        )
                    }
                )

        if self.liveness_threshold is not None:
            if not 0.0 <= float(self.liveness_threshold) <= 1.0:
                raise ValidationError(
                    {
                        "liveness_threshold": _(
                            "Liveness threshold must be between 0 and 1."
                        )
                    }
                )

    # ==================================================================
    # POLICY ACCESSORS
    # ==================================================================

    @property
    def max_attempts(self) -> int:
        return int(
            getattr(
                settings,
                "FACE_VERIFICATION_MAX_ATTEMPTS",
                DEFAULT_MAX_ATTEMPTS,
            )
        )

    @property
    def lockout_minutes(self) -> int:
        return int(
            getattr(
                settings,
                "FACE_VERIFICATION_LOCKOUT_MINUTES",
                DEFAULT_LOCKOUT_MINUTES,
            )
        )

    # ==================================================================
    # LOCKOUT
    # ==================================================================

    def is_locked(self) -> bool:
        return bool(
            self.locked_until
            and self.locked_until > timezone.now()
        )

    def check_lockout(self):
        """Raise ValueError if the account is currently locked."""
        if self.is_locked():
            raise ValueError(
                "Account temporarily locked due to too many attempts."
            )

    def increment_attempts(self):
        """
        Increment failed attempts; lock the account if the limit is hit.
        Only the changed fields are written.
        """

        self.verification_attempts += 1

        update_fields = ["verification_attempts"]

        if self.verification_attempts >= self.max_attempts:
            self.locked_until = (
                timezone.now()
                + timedelta(minutes=self.lockout_minutes)
            )
            update_fields.append("locked_until")

        self.save(update_fields=update_fields)

    def reset_attempts(self):
        """Clear failed attempts and any lockout."""
        if (
            self.verification_attempts == 0
            and self.locked_until is None
        ):
            return

        self.verification_attempts = 0
        self.locked_until = None
        self.save(
            update_fields=["verification_attempts", "locked_until"]
        )

    # ==================================================================
    # ALERTS
    # ==================================================================

    def trigger_alert(self):
        """
        Emit a notification event for repeated biometric verification
        failures.

        Delivery is owned by the notification system. This method only
        emits the canonical event.
        """

        from notifications.events.emitter import (
            emit_and_queue_notification_event,
        )
        from notifications.events.constants import (
            BIOMETRIC_VERIFICATION_FAILED,
        )

        try:
            emit_and_queue_notification_event(
                event_type=BIOMETRIC_VERIFICATION_FAILED,
                module="biometrics",
                actor=self.user,
                object_type="FaceVerification",
                object_id=self.pk,
                payload={
                    "user_id": self.user.pk,
                    "user_email": self.user.email,
                    "attempts": self.verification_attempts,
                    "max_attempts": self.max_attempts,
                    "locked_until": (
                        self.locked_until.isoformat()
                        if self.locked_until else None
                    ),
                    "device_id": self.device_id or None,
                    "at": timezone.now().isoformat(),
                },
            )
        except Exception:
            logger.exception(
                "Failed to emit biometric verification alert "
                "for user %s.",
                self.user_id,
            )