# apps/backend/notifications/tasks/delivery_tasks.py

"""
Compatibility exports for notification delivery tasks.

Canonical push delivery implementation:

    notifications.tasks.push

This module intentionally contains no provider-delivery logic.

It exists to preserve compatibility with older imports and task names
used by the notification system and existing callers.
"""

from __future__ import annotations

from notifications.services.notification_service import (
    reset_push_for_retry,
)

from .push import (
    deliver_notification,
    deliver_pending_push_notifications,
    deliver_push_notification,
    retry_failed_push_notifications,
)


# ============================================================================
# LEGACY TASK COMPATIBILITY
# ============================================================================

# Older notification code refers to the task as:
#
#     deliver_notification_push
#
# The canonical task is:
#
#     deliver_push_notification
#
# Keep the canonical implementation in push.py while exposing the legacy
# name from this compatibility module.

deliver_notification_push = deliver_push_notification


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "deliver_push_notification",
    "deliver_notification_push",
    "deliver_pending_push_notifications",
    "retry_failed_push_notifications",
    "deliver_notification",
    "reset_push_for_retry",
]
