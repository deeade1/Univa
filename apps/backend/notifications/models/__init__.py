"""
Notification models for the Univa notification subsystem.

The notification system is built around five core models:

    NotificationEvent
        Domain event that triggers notification processing.

    UserNotification
        Persistent in-app notification delivered to a user.

    NotificationDevice
        Registered device capable of receiving push notifications.

    NotificationPreference
        Per-user notification preferences.

    NotificationPush
        Delivery record connecting a notification to a device.

The models intentionally remain independent of:

    - notification providers
    - Celery tasks
    - event processing
    - push delivery services
    - GraphQL presentation
"""

from .device import NotificationDevice
from .event import NotificationEvent
from .notification import UserNotification
from .preference import NotificationPreference
from .push import NotificationPush


__all__ = [
    "NotificationDevice",
    "NotificationEvent",
    "UserNotification",
    "NotificationPreference",
    "NotificationPush",
]