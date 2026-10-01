# apps/backend/notifications/models/push.py

"""
Notification push delivery model for Univa.

A NotificationPush represents one delivery of a UserNotification
to one registered notification device.

Architecture:

    UserNotification
            |
            v
    NotificationPush
            |
            v
    Celery delivery task
            |
            v
    notifications.channels.*

This model contains delivery state only.

It does NOT:

    - send notifications
    - call Expo
    - call FCM
    - call APNs
    - call WebPush
    - dispatch Celery tasks
    - contain provider-specific logic

Provider delivery belongs to:

    notifications.channels.*

Task orchestration belongs to:

    notifications.tasks.*
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class NotificationPush(models.Model):
    """
    Tracks delivery of a UserNotification to a specific device.

    One UserNotification can have multiple NotificationPush records,
    normally one for each eligible device belonging to the recipient.

    Example:

        UserNotification
            ├── Android device → SENT
            ├── iPhone device  → FAILED
            └── Web device     → SKIPPED
    """

    # ========================================================================
    # STATUS
    # ========================================================================

    class PushStatus(models.TextChoices):
        """Lifecycle states for push delivery."""

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    # ========================================================================
    # NOTIFICATION
    # ========================================================================

    notification = models.ForeignKey(
        "notifications.UserNotification",
        on_delete=models.CASCADE,
        related_name="push_deliveries",
        help_text="User notification being delivered.",
    )

    # ========================================================================
    # TARGET DEVICE
    # ========================================================================

    device = models.ForeignKey(
        "notifications.NotificationDevice",
        on_delete=models.CASCADE,
        related_name="push_deliveries",
        help_text="Notification device receiving the push.",
    )

    # ========================================================================
    # PROVIDER
    # ========================================================================

    provider = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text=(
            "Push provider used for delivery, such as "
            "expo, fcm, apns, or webpush."
        ),
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Message, ticket, or receipt identifier returned "
            "by the push provider."
        ),
    )

    # ========================================================================
    # DELIVERY STATE
    # ========================================================================

    status = models.CharField(
        max_length=20,
        choices=PushStatus.choices,
        default=PushStatus.PENDING,
        db_index=True,
    )

    attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of delivery attempts made.",
    )

    # ========================================================================
    # ERROR INFORMATION
    # ========================================================================

    error_message = models.TextField(
        blank=True,
        help_text="Most recent delivery error.",
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ========================================================================
    # META
    # ========================================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "status",
                    "created_at",
                ],
                name="notif_push_status_idx",
            ),
            models.Index(
                fields=[
                    "notification",
                    "status",
                ],
                name="notif_push_notif_status_idx",
            ),
            models.Index(
                fields=[
                    "device",
                    "status",
                ],
                name="notif_push_device_status_idx",
            ),
            models.Index(
                fields=[
                    "provider",
                    "status",
                ],
                name="notif_push_provider_status_idx",
            ),
            models.Index(
                fields=[
                    "created_at",
                ],
                name="notif_push_created_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "notification",
                    "device",
                ],
                name="unique_notification_device_push",
            ),
        ]

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __str__(self) -> str:
        return (
            f"Push #{self.pk} | "
            f"notification={self.notification_id} | "
            f"device={self.device_id} | "
            f"{self.status}"
        )

    # ========================================================================
    # STATE PROPERTIES
    # ========================================================================

    @property
    def is_pending(self) -> bool:
        """Return True when delivery is waiting to be processed."""

        return self.status == self.PushStatus.PENDING

    @property
    def is_processing(self) -> bool:
        """Return True when a delivery worker is processing this record."""

        return self.status == self.PushStatus.PROCESSING

    @property
    def is_sent(self) -> bool:
        """Return True when delivery succeeded."""

        return self.status == self.PushStatus.SENT

    @property
    def is_failed(self) -> bool:
        """Return True when the most recent delivery attempt failed."""

        return self.status == self.PushStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        """Return True when delivery was intentionally skipped."""

        return self.status == self.PushStatus.SKIPPED

    @property
    def is_finished(self) -> bool:
        """
        Return True when no further delivery should normally occur.

        FAILED is deliberately excluded because failed deliveries
        remain eligible for retry.
        """

        return self.status in {
            self.PushStatus.SENT,
            self.PushStatus.SKIPPED,
        }

    @property
    def can_retry(self) -> bool:
        """
        Return True when this delivery is eligible for retry.

        Retry scheduling belongs to the Celery task layer.
        """

        return self.status == self.PushStatus.FAILED

    @property
    def has_provider(self) -> bool:
        """Return True when a provider has been assigned."""

        return bool(
            self.provider
            and self.provider.strip()
        )

    @property
    def has_provider_message_id(self) -> bool:
        """Return True when the provider returned a delivery identifier."""

        return bool(
            self.provider_message_id
            and self.provider_message_id.strip()
        )

    # ========================================================================
    # STATE TRANSITIONS
    # ========================================================================

    def mark_processing(self) -> None:
        """
        Mark this delivery as currently being processed.
        """

        self.status = self.PushStatus.PROCESSING
        self.processing_started_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "processing_started_at",
                "updated_at",
            ]
        )

    def mark_sent(
        self,
        *,
        provider: str | None = None,
        provider_message_id: str | None = None,
    ) -> None:
        """
        Mark delivery as successfully sent.

        Provider-specific response information may optionally be stored.
        """

        self.status = self.PushStatus.SENT
        self.sent_at = timezone.now()
        self.error_message = ""

        if provider is not None:
            self.provider = provider

        if provider_message_id is not None:
            self.provider_message_id = provider_message_id

        self.save(
            update_fields=[
                "status",
                "sent_at",
                "error_message",
                "provider",
                "provider_message_id",
                "updated_at",
            ]
        )

    def mark_failed(
        self,
        error_message: str,
    ) -> None:
        """
        Mark delivery as failed.

        The Celery task layer decides whether and when to retry.
        """

        self.status = self.PushStatus.FAILED
        self.error_message = str(error_message)

        self.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

    def mark_skipped(
        self,
        reason: str = "",
    ) -> None:
        """
        Mark delivery as intentionally skipped.
        """

        self.status = self.PushStatus.SKIPPED
        self.error_message = reason

        self.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

    def increment_attempts(self) -> None:
        """
        Increment the delivery attempt counter.

        This is normally called by the Celery delivery task immediately
        before attempting provider delivery.
        """

        self.attempts += 1

        self.save(
            update_fields=[
                "attempts",
                "updated_at",
            ]
        )