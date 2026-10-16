"""
Notification preference model for Univa.

Controls how a user receives notifications across the Univa platform.

Preferences are intentionally independent from notification delivery.

This model does NOT:

    - create notifications
    - resolve notification recipients
    - send push notifications
    - call Expo
    - call FCM
    - call APNs
    - call WebPush
    - dispatch Celery tasks

Delivery orchestration belongs to:

    notifications.services.notification_service
    notifications.events.processor
    notifications.tasks.*

Provider delivery belongs to:

    notifications.channels.*
"""

from __future__ import annotations

from datetime import time

from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    """
    Stores notification preferences for one Univa user.

    A user has exactly one preference record.

    Example:

        User
          │
          └── NotificationPreference
                  ├── channels
                  ├── frequency
                  ├── quiet hours
                  └── category preferences
    """

    # ======================================================================
    # ENUMS
    # ======================================================================

    class Frequency(models.TextChoices):
        INSTANT = "instant", "Instant"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    # ======================================================================
    # USER
    # ======================================================================

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        db_index=True,
        help_text="User whose notification preferences are stored.",
    )

    # ======================================================================
    # GLOBAL NOTIFICATION SWITCH
    # ======================================================================

    notifications_enabled = models.BooleanField(
        default=True,
        help_text=(
            "Master switch controlling all non-critical notifications."
        ),
    )

    # ======================================================================
    # DELIVERY CHANNELS
    # ======================================================================

    in_app_enabled = models.BooleanField(
        default=True,
    )

    push_enabled = models.BooleanField(
        default=True,
    )

    email_enabled = models.BooleanField(
        default=True,
    )

    # ======================================================================
    # DELIVERY FREQUENCY
    # ======================================================================

    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.INSTANT,
        db_index=True,
    )

    # ======================================================================
    # QUIET HOURS
    # ======================================================================

    quiet_hours_enabled = models.BooleanField(
        default=False,
    )

    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
    )

    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
    )

    # ======================================================================
    # NOTIFICATION CATEGORIES
    # ======================================================================

    marketing_enabled = models.BooleanField(
        default=True,
    )

    transactional_enabled = models.BooleanField(
        default=True,
    )

    security_enabled = models.BooleanField(
        default=True,
    )

    social_enabled = models.BooleanField(
        default=True,
    )

    # ======================================================================
    # TIMESTAMPS
    # ======================================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ======================================================================
    # META
    # ======================================================================

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            models.Index(
                fields=[
                    "notifications_enabled",
                ],
                name="notif_pref_enabled_idx",
            ),
            models.Index(
                fields=[
                    "frequency",
                ],
                name="notif_pref_freq_idx",
            ),
        ]

    # ======================================================================
    # STRING REPRESENTATION
    # ======================================================================

    def __str__(self) -> str:
        return (
            f"Notification preferences: "
            f"{self.user}"
        )

    # ======================================================================
    # CHANNEL PERMISSIONS
    # ======================================================================

    def allows_channel(
        self,
        channel: str,
    ) -> bool:
        """
        Determine whether a notification channel is enabled.

        Supported channels:

            in_app
            push
            email
            sms

        SMS is intentionally unsupported by the current preference
        model and therefore returns False.
        """

        if not self.notifications_enabled:
            return False

        if not channel:
            return False

        channel = str(channel).strip().lower()

        if channel == "in_app":
            return self.in_app_enabled

        if channel == "push":
            return self.push_enabled

        if channel == "email":
            return self.email_enabled

        if channel == "sms":
            return False

        return False

    # ======================================================================
    # CATEGORY PERMISSIONS
    # ======================================================================

    def allows_category(
        self,
        category: str,
    ) -> bool:
        """
        Determine whether a notification category is enabled.

        Registry categories such as:

            account
            order
            payment
            banking
            transport
            chat
            social
            realestate
            product
            system
            invoice

        are mapped to the preference groups:

            security
            transactional
            social
            marketing

        Unknown categories default to transactional behavior.
        """

        if not self.notifications_enabled:
            return False

        if not category:
            return True

        category = str(category).strip().lower()

        # --------------------------------------------------------------
        # Security
        # --------------------------------------------------------------

        security_categories = {
            "security",
            "account",
        }

        if category in security_categories:
            return self.security_enabled

        # --------------------------------------------------------------
        # Social
        # --------------------------------------------------------------

        social_categories = {
            "social",
            "chat",
        }

        if category in social_categories:
            return self.social_enabled

        # --------------------------------------------------------------
        # Marketing
        # --------------------------------------------------------------

        marketing_categories = {
            "marketing",
        }

        if category in marketing_categories:
            return self.marketing_enabled

        # --------------------------------------------------------------
        # Transactional
        # --------------------------------------------------------------

        transactional_categories = {
            "transactional",
            "order",
            "payment",
            "banking",
            "transport",
            "realestate",
            "product",
            "system",
            "invoice",
        }

        if category in transactional_categories:
            return self.transactional_enabled

        # --------------------------------------------------------------
        # Unknown category
        # --------------------------------------------------------------

        # Unknown categories are treated as transactional rather than
        # silently disabling potentially important notifications.
        return self.transactional_enabled

    # ======================================================================
    # FREQUENCY
    # ======================================================================

    def should_send_instantly(self) -> bool:
        """
        Return True when notifications should be delivered immediately.
        """

        return (
            self.frequency == self.Frequency.INSTANT
        )

    def should_batch_daily(self) -> bool:
        """
        Return True when notifications should be accumulated
        for daily delivery.
        """

        return (
            self.frequency == self.Frequency.DAILY
        )

    def should_batch_weekly(self) -> bool:
        """
        Return True when notifications should be accumulated
        for weekly delivery.
        """

        return (
            self.frequency == self.Frequency.WEEKLY
        )

    # ======================================================================
    # QUIET HOURS
    # ======================================================================

    def is_quiet_hours_configured(self) -> bool:
        """
        Return True when quiet hours have a valid start/end range.
        """

        return bool(
            self.quiet_hours_enabled
            and self.quiet_hours_start is not None
            and self.quiet_hours_end is not None
        )

    def is_within_quiet_hours(
        self,
        current_time: time | None = None,
    ) -> bool:
        """
        Determine whether a supplied/current local time falls
        within the configured quiet-hours period.

        Supports both normal and overnight ranges.

        Examples:

            22:00 -> 07:00
            08:00 -> 17:00
        """

        if not self.is_quiet_hours_configured():
            return False

        if current_time is None:
            from django.utils import timezone

            current_time = timezone.localtime().time()

        start = self.quiet_hours_start
        end = self.quiet_hours_end

        if start == end:
            return True

        # Normal range:
        #
        # 08:00 -> 17:00
        if start < end:
            return start <= current_time < end

        # Overnight range:
        #
        # 22:00 -> 07:00
        return (
            current_time >= start
            or current_time < end
        )

    # ======================================================================
    # IMMEDIATE DELIVERY
    # ======================================================================

    def can_deliver_immediately(
        self,
        *,
        channel: str = "push",
        category: str | None = None,
        current_time: time | None = None,
    ) -> bool:
        """
        Determine whether a notification can currently be delivered
        immediately through the specified channel.

        This is intentionally a preference-level decision.

        It does not inspect devices or providers.
        """

        if not self.notifications_enabled:
            return False

        if category and not self.allows_category(category):
            return False

        if not self.allows_channel(channel):
            return False

        if not self.should_send_instantly():
            return False

        if self.is_within_quiet_hours(current_time=current_time):
            return False

        return True

    # ======================================================================
    # ENABLE / DISABLE ALL
    # ======================================================================

    def disable_all(self) -> None:
        """
        Disable all notification channels.

        Preferences remain stored and can later be restored.
        """

        self.notifications_enabled = False

        self.save(
            update_fields=[
                "notifications_enabled",
                "updated_at",
            ]
        )

    def enable_all(self) -> None:
        """
        Enable global notifications.
        """

        self.notifications_enabled = True

        self.save(
            update_fields=[
                "notifications_enabled",
                "updated_at",
            ]
        )

    # ======================================================================
    # CHANNEL HELPERS
    # ======================================================================

    def disable_push(self) -> None:
        """
        Disable push notifications.
        """

        self.push_enabled = False

        self.save(
            update_fields=[
                "push_enabled",
                "updated_at",
            ]
        )

    def enable_push(self) -> None:
        """
        Enable push notifications.
        """

        self.push_enabled = True
        self.notifications_enabled = True

        self.save(
            update_fields=[
                "push_enabled",
                "notifications_enabled",
                "updated_at",
            ]
        )

    def disable_in_app(self) -> None:
        """
        Disable in-app notifications.
        """

        self.in_app_enabled = False

        self.save(
            update_fields=[
                "in_app_enabled",
                "updated_at",
            ]
        )

    def enable_in_app(self) -> None:
        """
        Enable in-app notifications.
        """

        self.in_app_enabled = True
        self.notifications_enabled = True

        self.save(
            update_fields=[
                "in_app_enabled",
                "notifications_enabled",
                "updated_at",
            ]
        )

    def disable_email(self) -> None:
        """
        Disable email notifications.
        """

        self.email_enabled = False

        self.save(
            update_fields=[
                "email_enabled",
                "updated_at",
            ]
        )

    def enable_email(self) -> None:
        """
        Enable email notifications.
        """

        self.email_enabled = True
        self.notifications_enabled = True

        self.save(
            update_fields=[
                "email_enabled",
                "notifications_enabled",
                "updated_at",
            ]
        )


__all__ = [
    "NotificationPreference",
]