# apps/backend/notifications/tasks/websocket.py

"""
Celery tasks for WebSocket notification delivery.

This module is responsible for orchestration only.

Architecture:

    UserNotification
            |
            v
    send_websocket_notification
            |
            v
       WebSocketChannel
            |
            +----> Django Channels
            +----> Redis channel layer
            +----> Connected client

This module does NOT:

    - manage WebSocket connections
    - access Redis directly
    - create WebSocket consumers
    - serialize WebSocket protocol messages
    - resolve notification events
    - create UserNotification records
    - contain frontend-specific WebSocket logic

WebSocket delivery belongs to:

    notifications.channels.websocket

Task orchestration belongs to:

    notifications.tasks.*
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from ..models import UserNotification

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class WebSocketNotificationTaskError(Exception):
    """Base exception for WebSocket notification task failures."""


class WebSocketChannelNotConfigured(
    WebSocketNotificationTaskError
):
    """
    Raised when the WebSocket notification channel is unavailable.
    """


# ============================================================================
# Public task
# ============================================================================


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def send_websocket_notification(
    self,
    notification_id: int,
) -> dict[str, Any]:
    """
    Deliver a UserNotification through the WebSocket channel.

    Args:
        notification_id:
            Primary key of the UserNotification to deliver.

    Returns:
        Dictionary containing delivery information.

    The Celery task receives only the notification ID rather than
    passing a Django model instance through the queue.
    """

    # ------------------------------------------------------------------------
    # Load notification
    # ------------------------------------------------------------------------

    try:
        notification = (
            UserNotification.objects
            .select_related("recipient")
            .get(pk=notification_id)
        )

    except UserNotification.DoesNotExist:
        logger.warning(
            "WebSocket notification skipped: UserNotification %s does not exist.",
            notification_id,
        )

        return {
            "success": False,
            "notification_id": notification_id,
            "status": "not_found",
        }

    # ------------------------------------------------------------------------
    # Delegate delivery
    # ------------------------------------------------------------------------

    try:
        result = _send_websocket_notification(
            notification=notification,
        )

    except WebSocketChannelNotConfigured as exc:
        logger.info(
            "WebSocket notification skipped because the WebSocket channel is not configured. "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": "channel_not_configured",
            "error": str(exc),
        }

    except Exception as exc:
        logger.exception(
            "WebSocket notification failed notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        raise WebSocketNotificationTaskError(str(exc)) from exc

    logger.info(
        "WebSocket notification completed notification=%s recipient=%s status=%s",
        notification.pk,
        notification.recipient_id,
        result.get("status"),
    )

    return result


# ============================================================================
# WebSocket delivery
# ============================================================================


def _send_websocket_notification(
    *,
    notification: UserNotification,
) -> dict[str, Any]:
    """
    Delegate notification delivery to the WebSocket channel.

    Provider/channel-specific implementation must remain outside
    this Celery task.

    Expected channel interface:

        WebSocketChannel().send_notification(
            notification=notification,
        )

    The channel may return:

        {
            "success": True,
            "status": "sent",
        }

    or:

        {
            "success": False,
            "status": "no_connection",
        }

    or:

        {
            "success": False,
            "error": "...",
        }
    """

    try:
        from ..channels.websocket import WebSocketChannel

    except ImportError as exc:
        raise WebSocketChannelNotConfigured(
            "WebSocket notification channel is not implemented. "
            "Create notifications.channels.websocket before enabling "
            "WebSocket notification delivery."
        ) from exc

    channel = WebSocketChannel()

    response = channel.send_notification(
        notification=notification,
    )

    if not isinstance(response, dict):
        response = {
            "success": bool(response),
        }

    # ------------------------------------------------------------------------
    # Successful delivery
    # ------------------------------------------------------------------------

    if response.get("success"):
        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": response.get("status", "sent"),
            "channel": "websocket",
        }

    # ------------------------------------------------------------------------
    # Unsuccessful delivery
    # ------------------------------------------------------------------------

    error_message = (
        response.get("error")
        or response.get("error_message")
        or "WebSocket channel returned an unsuccessful response."
    )

    # ``no_connection`` is not necessarily an infrastructure failure.
    # A user may simply have no active WebSocket session.
    status = response.get("status", "failed")

    if status == "no_connection":
        logger.debug(
            "No active WebSocket connection for notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": "no_connection",
            "channel": "websocket",
        }

    raise WebSocketNotificationTaskError(str(error_message))


# ============================================================================
# Notification payload
# ============================================================================


def build_websocket_payload(
    notification: UserNotification,
) -> dict[str, Any]:
    """
    Build the canonical notification payload for WebSocket delivery.

    The channel layer may use this helper when constructing the
    message sent to the connected client.

    The payload intentionally mirrors the fields available on
    UserNotification without exposing the Django model instance.
    """

    return {
        "id": notification.pk,
        "type": "notification",
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "module": notification.module,
        "title": notification.title,
        "message": notification.message,
        "action_url": notification.action_url,
        "metadata": dict(notification.metadata or {}),
        "is_read": notification.is_read,
        "is_archived": notification.is_archived,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at
            else None
        ),
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "send_websocket_notification",
    "build_websocket_payload",
]