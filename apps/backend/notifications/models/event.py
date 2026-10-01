# apps/backend/notifications/models/event.py

"""
Notification event model for Univa.

A NotificationEvent stores a domain event that may result in one or
more notifications.

The model is intentionally module-agnostic so the same notification
infrastructure can be used by:

    - Accounts
    - Banking
    - Transport
    - E-commerce
    - Real Estate
    - Payments
    - Social
    - Chat
    - Blog
    - Community
    - System

Architecture:

    Domain Application
            |
            v
    NotificationEvent
            |
            v
    Event Processor
            |
            v
    NotificationService
            |
            +------------------+
            |                  |
            v                  v
    UserNotification    NotificationPush
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationEvent(models.Model):
    """
    Stores a domain event that may result in one or more notifications.

    NotificationEvent is the durable source event for the notification
    subsystem.

    It contains event identity, actor information, target information,
    payload data, and processing state.

    It does not:

        - create UserNotification records
        - send push notifications
        - call notification providers
        - dispatch Celery tasks
        - resolve provider-specific delivery
    """

    # ========================================================================
    # STATUS
    # ========================================================================

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    # ========================================================================
    # EVENT IDENTITY
    # ========================================================================

    event_type = models.CharField(
        max_length=150,
        db_index=True,
        help_text=(
            "Canonical event name, for example "
            "'REAL_ESTATE.OFFER_RECEIVED'."
        ),
    )

    module = models.CharField(
        max_length=50,
        db_index=True,
        help_text=(
            "Univa module that generated the event, "
            "for example 'realestate', 'banking', or 'transport'."
        ),
    )

    # ========================================================================
    # ACTOR
    # ========================================================================

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_events",
        help_text=(
            "User responsible for triggering the event, if applicable."
        ),
    )

    # ========================================================================
    # GENERIC EVENT TARGET
    # ========================================================================

    object_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Model/entity affected by the event.",
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary key of the affected object.",
    )

    # ========================================================================
    # EVENT PAYLOAD
    # ========================================================================

    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured event data consumed by the notification engine."
        ),
    )

    # ========================================================================
    # PROCESSING
    # ========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of processing attempts.",
    )

    error_message = models.TextField(
        blank=True,
        help_text="Most recent processing error.",
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ========================================================================
    # META
    # ========================================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "module",
                    "event_type",
                ],
                name="notif_evt_mod_type_idx",
            ),
            models.Index(
                fields=[
                    "status",
                    "created_at",
                ],
                name="notif_evt_status_idx",
            ),
            models.Index(
                fields=[
                    "actor",
                    "created_at",
                ],
                name="notif_evt_actor_idx",
            ),
            models.Index(
                fields=[
                    "object_type",
                    "object_id",
                ],
                name="notif_evt_object_idx",
            ),
            models.Index(
                fields=[
                    "created_at",
                ],
                name="notif_evt_created_idx",
            ),
        ]

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __str__(self) -> str:
        return (
            f"{self.module}:{self.event_type} "
            f"[{self.status}] #{self.pk}"
        )

    # ========================================================================
    # STATE PROPERTIES
    # ========================================================================

    @property
    def is_pending(self) -> bool:
        """
        Return True when the event is waiting to be processed.
        """
        return self.status == self.Status.PENDING

    @property
    def is_processing(self) -> bool:
        """
        Return True when the event is currently being processed.
        """
        return self.status == self.Status.PROCESSING

    @property
    def is_processed(self) -> bool:
        """
        Return True when the event has been successfully processed.
        """
        return self.status == self.Status.PROCESSED

    @property
    def has_failed(self) -> bool:
        """
        Return True when the event processing failed.
        """
        return self.status == self.Status.FAILED

    @property
    def is_cancelled(self) -> bool:
        """
        Return True when processing was intentionally cancelled.
        """
        return self.status == self.Status.CANCELLED

    @property
    def is_finished(self) -> bool:
        """
        Return True when the event should not normally be processed again.
        """
        return self.status in {
            self.Status.PROCESSED,
            self.Status.CANCELLED,
        }

    @property
    def can_retry(self) -> bool:
        """
        Return True when the event can be processed again.

        Retry scheduling belongs to the event-processing task layer.
        """
        return self.status == self.Status.FAILED

    # ========================================================================
    # PROCESSING STATE
    # ========================================================================

    def mark_processing(self) -> None:
        """
        Mark the event as currently being processed.
        """

        self.status = self.Status.PROCESSING
        self.attempts += 1
        self.error_message = ""

        self.save(
            update_fields=[
                "status",
                "attempts",
                "error_message",
                "updated_at",
            ]
        )

    def mark_processed(self) -> None:
        """
        Mark the event as successfully processed.
        """

        self.status = self.Status.PROCESSED
        self.processed_at = timezone.now()
        self.error_message = ""

        self.save(
            update_fields=[
                "status",
                "processed_at",
                "error_message",
                "updated_at",
            ]
        )

    def mark_failed(self, error: str) -> None:
        """
        Mark the event as failed.

        Retry scheduling is deliberately handled outside the model.
        """

        self.status = self.Status.FAILED
        self.error_message = str(error)[:5000]

        self.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

    def mark_cancelled(self, reason: str = "") -> None:
        """
        Mark the event as intentionally cancelled.
        """

        self.status = self.Status.CANCELLED
        self.error_message = str(reason)[:5000]

        self.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

    def reset_for_retry(self) -> None:
        """
        Reset a failed event to PENDING.

        Retry scheduling itself belongs to the task layer.
        """

        if self.status != self.Status.FAILED:
            return

        self.status = self.Status.PENDING
        self.error_message = ""
        self.processed_at = None

        self.save(
            update_fields=[
                "status",
                "error_message",
                "processed_at",
                "updated_at",
            ]
        )
