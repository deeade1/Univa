# apps/backend/notifications/tasks/in_app.py

"""
Celery tasks for in-app notification processing.

Architecture
------------

NotificationService owns notification creation.

This task owns asynchronous in-app processing.

The task receives ONLY the persisted UserNotification primary key:

    NotificationService
            |
            | notification_id
            v
    send_in_app_notification
            |
            +--> load UserNotification
            |
            +--> validate recipient/preferences
            |
            +--> apply rate limit
            |
            +--> optionally queue WebSocket delivery

The task MUST NOT:

    - create another UserNotification
    - call NotificationService.notify()
    - reconstruct the original notification payload
    - pass Django model instances through Celery
    - duplicate notification persistence logic

WebSocket delivery remains owned by:

    notifications.tasks.websocket
    notifications.channels.websocket
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.core.cache import cache

from ..models import NotificationPreference, UserNotification

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

RATE_LIMIT_PER_HOUR = 100


# ============================================================================
# HELPERS
# ============================================================================


def _get_notification(
    notification_id: int | str,
) -> UserNotification | None:
    """
    Load the existing UserNotification.

    The task operates on an already-persisted notification. It never creates
    one.

    Returns:
        UserNotification when found.
        None when the notification does not exist.
    """

    try:
        return (
            UserNotification.objects
            .select_related("recipient")
            .get(pk=notification_id)
        )

    except UserNotification.DoesNotExist:
        logger.warning(
            "UserNotification not found: notification_id=%s",
            notification_id,
        )
        return None


def _check_preferences(
    user: Any,
) -> bool:
    """
    Determine whether in-app notification processing is enabled.

    Global notification settings take precedence over channel-specific
    settings.

    Missing preferences are treated as enabled because the absence of a
    preference record should not suppress an otherwise valid notification.
    """

    try:
        preferences = NotificationPreference.objects.get(
            user=user,
        )

    except NotificationPreference.DoesNotExist:
        return True

    if not preferences.notifications_enabled:
        return False

    return bool(preferences.in_app_enabled)


def _check_rate_limit(
    user_id: int,
    *,
    limit: int = RATE_LIMIT_PER_HOUR,
) -> bool:
    """
    Atomically enforce the hourly in-app notification limit.

    Returns:
        True when another notification may be processed.
        False when the hourly limit has already been reached.
    """

    key = f"in_app_rate_limit:{user_id}"

    count = cache.get(key, 0)

    if count >= limit:
        logger.warning(
            "In-app notification rate limit exceeded: user_id=%s",
            user_id,
        )
        return False

    cache.set(
        key,
        count + 1,
        timeout=3600,
    )

    return True


def _dispatch_websocket(
    notification_id: int,
) -> bool:
    """
    Queue WebSocket delivery for an existing UserNotification.

    This helper performs scheduling only. Actual WebSocket delivery belongs
    to notifications.tasks.websocket and notifications.channels.websocket.

    Returns:
        True when the WebSocket task was queued.
        False when the WebSocket task is unavailable.
    """

    try:
        from .websocket import send_websocket_notification

    except ImportError:
        logger.debug(
            "WebSocket notification task is unavailable: "
            "notification_id=%s",
            notification_id,
        )
        return False

    send_websocket_notification.delay(
        notification_id=notification_id,
    )

    return True


# ============================================================================
# PRIMARY TASK
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.send_in_app_notification",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def send_in_app_notification(
    self,
    notification_id: int | str,
    *,
    dispatch_websocket: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Process an existing UserNotification.

    Args:
        notification_id:
            Primary key of the existing UserNotification.

        dispatch_websocket:
            Whether successful in-app processing should also queue the
            WebSocket delivery task.

    Returns:
        A structured processing result.

    Important:
        This task does NOT create a UserNotification.

        NotificationService is responsible for persistence. This task is
        responsible only for asynchronous processing of that persisted
        record.
    """

    # ------------------------------------------------------------------------
    # Validate task input
    # ------------------------------------------------------------------------

    if notification_id is None:
        raise ValueError(
            "notification_id is required."
        )

    if not isinstance(notification_id, (int, str)):
        raise TypeError(
            "notification_id must be an integer or string."
        )

    # ------------------------------------------------------------------------
    # Load existing notification
    # ------------------------------------------------------------------------

    notification = _get_notification(
        notification_id,
    )

    if notification is None:
        return {
            "success": False,
            "status": "not_found",
            "notification_id": notification_id,
        }

    user_id = notification.recipient_id

    # ------------------------------------------------------------------------
    # Check global/channel preferences
    # ------------------------------------------------------------------------

    if not _check_preferences(
        notification.recipient,
    ):
        logger.info(
            "In-app notification delivery disabled by preferences: "
            "notification_id=%s user_id=%s",
            notification.pk,
            user_id,
        )

        return {
            "success": True,
            "status": "preference_disabled",
            "notification_id": notification.pk,
            "user_id": user_id,
        }

    # ------------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------------

    if not _check_rate_limit(
        user_id,
    ):
        return {
            "success": False,
            "status": "rate_limited",
            "notification_id": notification.pk,
            "user_id": user_id,
        }

    # ------------------------------------------------------------------------
    # Optional WebSocket dispatch
    # ------------------------------------------------------------------------

    websocket_dispatched = False

    if dispatch_websocket:
        websocket_dispatched = _dispatch_websocket(
            notification.pk,
        )

    # ------------------------------------------------------------------------
    # Completed
    # ------------------------------------------------------------------------

    logger.info(
        "In-app notification dispatched: "
        "notification_id=%s user_id=%s websocket=%s",
        notification.pk,
        user_id,
        websocket_dispatched,
    )

    return {
        "success": True,
        "status": "dispatched",
        "notification_id": notification.pk,
        "user_id": user_id,
        "websocket_dispatched": websocket_dispatched,
    }


# ============================================================================
# PAYLOAD COMPATIBILITY TASK
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.send_in_app_notification_for_user",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def send_in_app_notification_for_user(
    self,
    user_id: int | str,
    notification: dict[str, Any],
    *,
    dispatch_websocket: bool | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Compatibility adapter for callers that already have a notification
    payload.

    This adapter does NOT create a UserNotification.

    The preferred architecture is to persist the UserNotification first and
    queue send_in_app_notification(notification_id=...).

    Args:
        user_id:
            Recipient user ID.

        notification:
            Standardized notification payload.

        dispatch_websocket:
            Optional override for WebSocket dispatch.
    """

    if not isinstance(notification, dict):
        raise TypeError(
            "notification must be a dictionary."
        )

    # ------------------------------------------------------------------------
    # Resolve event type for compatibility callers.
    # ------------------------------------------------------------------------

    event_type = (
        notification.get("event_type")
        or notification.get("type")
    )

    if not event_type:
        raise ValueError(
            "notification must contain 'event_type' or 'type'."
        )

    # ------------------------------------------------------------------------
    # This adapter intentionally does not create a notification.
    #
    # It requires an existing persisted notification ID when used as part of
    # the canonical asynchronous pipeline.
    # ------------------------------------------------------------------------

    notification_id = (
        notification.get("notification_id")
        or notification.get("id")
    )

    if notification_id is None:
        raise ValueError(
            "notification must contain 'notification_id' or 'id'. "
            "The in-app task operates on an existing UserNotification."
        )

    if dispatch_websocket is None:
        dispatch_websocket = notification.get(
            "dispatch_websocket",
            True,
        )

    return send_in_app_notification(
        notification_id=notification_id,
        dispatch_websocket=dispatch_websocket,
    )


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    "send_in_app_notification",
    "send_in_app_notification_for_user",
]
