# apps/backend/biometrics/models/device.py

"""
Biometric device model.

A biometric device belongs directly to the authenticated system user.

Architecture:

    User
      │
      └── biometric_devices
              │
              └── BiometricDevice

Biometrics is an authentication/security domain and therefore must not
depend on UserProfile.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class BiometricDevice(models.Model):
    """
    Trusted device registered for biometric authentication.

    The device belongs directly to the system User rather than
    UserProfile. UserProfile is a presentation/profile extension and
    should not be used as the ownership boundary for application domains.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="biometric_devices",
    )

    device_id = models.CharField(
        max_length=100,
        unique=True,
        help_text=(
            "Globally unique device identifier supplied by the client. "
            "Must be stable across sessions for a given physical device."
        ),
    )

    public_key = models.TextField(
        blank=True,
        null=True,
        help_text="Public key used for biometric/device verification.",
    )

    trusted = models.BooleanField(
        default=False,
        help_text="Whether this device is trusted for biometric authentication.",
    )

    device_info = models.TextField(
        blank=True,
        help_text="Device information such as model, OS, and platform.",
    )

    biometric_hash = models.TextField(
        blank=True,
        help_text=(
            "Optional hash associated with the registered biometric credential."
        ),
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this device was last used for biometric authentication.",
    )

    registered_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this device was registered.",
    )

    class Meta:
        ordering = ["-registered_at"]

        verbose_name = "Biometric Device"
        verbose_name_plural = "Biometric Devices"

        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_id"],
                name="unique_user_biometric_device",
                violation_error_message=(
                    "This device is already registered for this user."
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "trusted"],
                name="biometric_user_trusted_idx",
            ),
            models.Index(
                fields=["device_id"],
                name="biometric_device_id_idx",
            ),
            models.Index(
                fields=["last_used_at"],
                name="biometric_last_used_idx",
            ),
            models.Index(
                fields=["registered_at"],
                name="biometric_registered_idx",
            ),
        ]

    def __str__(self):
        return f"Biometric Device {self.device_id} for {self.user.email}"

    def mark_used(self):
        """Update the last-used timestamp only."""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def trust(self):
        """Mark this device as trusted."""
        if not self.trusted:
            self.trusted = True
            self.save(update_fields=["trusted"])

    def revoke(self):
        """Revoke trust for this device."""
        if self.trusted:
            self.trusted = False
            self.save(update_fields=["trusted"])