# apps/backend/notifications/services/__init__.py

"""
Notification service package.

The service layer owns notification creation, recipient resolution,
preferences, and notification state operations.
"""

from .notification_service import (
    InvalidNotificationChannel,
    InvalidNotificationType,
    NotificationRecipientError,
    NotificationService,
    NotificationServiceError,
    mark_push_failed,
    reset_push_for_retry,
)


__all__ = [
    "NotificationService",
    "NotificationServiceError",
    "InvalidNotificationChannel",
    "InvalidNotificationType",
    "NotificationRecipientError",
    "mark_push_failed",
    "reset_push_for_retry",
]