# apps/backend/notifications/tasks/sms.py

"""
Celery tasks for SMS notification delivery.

This module is responsible for SMS delivery orchestration only.

Architecture:

    UserNotification
            |
            v
    send_sms_notification
            |
            v
       SMS gateway
            |
            +----> Twilio
            +----> Africa's Talking
            +----> Termii
            +----> Vonage
            +----> Future provider

This module does NOT:

    - implement an SMS provider
    - call Twilio directly
    - call Termii directly
    - call Africa's Talking directly
    - call Vonage directly
    - create UserNotification records
    - resolve notification events
    - dispatch notification creation

Notification creation belongs to:

    notifications.services.notification_service

Provider-specific SMS delivery belongs to:

    notifications.channels.*

Task orchestration belongs to:

    notifications.tasks.*
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.conf import settings

from ..models import UserNotification

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

MAX_SMS_ATTEMPTS = 3


# ============================================================================
# Exceptions
# ============================================================================


class SMSNotificationTaskError(Exception):
    """Base exception for SMS notification task failures."""


class SMSRecipientError(SMSNotificationTaskError):
    """Raised when a notification recipient has no usable phone number."""


class SMSProviderNotConfigured(SMSNotificationTaskError):
    """
    Raised when SMS delivery has been requested but no SMS provider
    has been configured.
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
def send_sms_notification(
    self,
    notification_id: int,
) -> dict[str, Any]:
    """
    Send one UserNotification through the configured SMS channel.

    Args:
        notification_id:
            Primary key of the UserNotification to deliver.

    Returns:
        Dictionary containing delivery information.

    The task receives only the notification ID rather than passing
    a Django model instance through Celery.
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
            "SMS notification skipped: UserNotification %s does not exist.",
            notification_id,
        )

        return {
            "success": False,
            "notification_id": notification_id,
            "status": "not_found",
        }

    # ------------------------------------------------------------------------
    # Resolve recipient phone number
    # ------------------------------------------------------------------------

    phone_number = _get_recipient_phone(notification)

    if not phone_number:
        logger.info(
            "SMS notification skipped: user=%s has no usable phone number.",
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": "no_phone",
        }

    # ------------------------------------------------------------------------
    # Provider availability
    # ------------------------------------------------------------------------

    if not _sms_provider_configured():
        logger.info(
            "SMS notification skipped: no SMS provider is currently configured. "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "phone_number": phone_number,
            "status": "provider_not_configured",
        }

    # ------------------------------------------------------------------------
    # Send SMS
    # ------------------------------------------------------------------------

    try:
        result = _send_sms(
            notification=notification,
            phone_number=phone_number,
        )

    except Exception as exc:
        logger.exception(
            "SMS notification failed notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        raise SMSNotificationTaskError(str(exc)) from exc

    logger.info(
        "SMS notification completed notification=%s recipient=%s",
        notification.pk,
        notification.recipient_id,
    )

    return result


# ============================================================================
# Recipient resolution
# ============================================================================


def _get_recipient_phone(
    notification: UserNotification,
) -> str:
    """
    Resolve the recipient's phone number.

    The current Univa User model uses ``phone_number`` as its
    phone field.

    No phone number is persisted or modified by this task.
    """

    recipient = notification.recipient

    phone_number = getattr(
        recipient,
        "phone_number",
        None,
    )

    if phone_number is None:
        return ""

    return str(phone_number).strip()


# ============================================================================
# Provider configuration
# ============================================================================


def _sms_provider_configured() -> bool:
    """
    Determine whether an SMS provider has been configured.

    The notification system does not assume a particular SMS provider.

    Supported configuration convention:

        SMS_PROVIDER

    Example:

        SMS_PROVIDER = "termii"

    or:

        SMS_PROVIDER = "twilio"

    The actual provider implementation belongs in:

        notifications.channels.*
    """

    provider = getattr(settings, "SMS_PROVIDER", "")

    return bool(provider and str(provider).strip())


# ============================================================================
# SMS delivery
# ============================================================================


def _send_sms(
    *,
    notification: UserNotification,
    phone_number: str,
) -> dict[str, Any]:
    """
    Delegate SMS delivery to the notification channel layer.

    Provider-specific logic must NOT live in this Celery task.

    The expected channel interface is:

        SMSChannel().send_to_recipient(
            notification=notification,
            phone_number=phone_number,
        )

    The channel should return a dictionary such as:

        {
            "success": True,
            "provider": "termii",
            "message_id": "...",
        }

    or:

        {
            "success": False,
            "error": "...",
            "permanent": False,
        }
    """

    try:
        from ..channels.sms import SMSChannel
    except ImportError as exc:
        raise SMSProviderNotConfigured(
            "SMS channel is not implemented. "
            "Create notifications.channels.sms before enabling SMS delivery."
        ) from exc

    channel = SMSChannel()

    response = channel.send_to_recipient(
        notification=notification,
        phone_number=phone_number,
    )

    if not isinstance(response, dict):
        response = {
            "success": bool(response),
        }

    if response.get("success"):
        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "phone_number": phone_number,
            "status": "sent",
            "provider": response.get("provider", ""),
            "message_id": (
                response.get("message_id")
                or response.get("provider_message_id")
                or ""
            ),
        }

    error_message = (
        response.get("error")
        or response.get("error_message")
        or "SMS provider returned an unsuccessful response."
    )

    permanent = bool(response.get("permanent"))

    if permanent:
        logger.warning(
            "Permanent SMS delivery failure notification=%s recipient=%s error=%s",
            notification.pk,
            notification.recipient_id,
            error_message,
        )

    raise SMSNotificationTaskError(str(error_message))


# ============================================================================
# Message construction
# ============================================================================


def build_sms_message(
    notification: UserNotification,
) -> str:
    """
    Build the SMS message from a UserNotification.

    This helper intentionally keeps the message compact because
    SMS messages have limited payload sizes.

    The notification title and message are combined.

    If an action URL exists, it is appended.
    """

    title = (notification.title or "").strip()
    message = (notification.message or "").strip()

    parts = []

    if title:
        parts.append(title)

    if message:
        parts.append(message)

    if notification.action_url:
        parts.append(str(notification.action_url).strip())

    return "\n\n".join(part for part in parts if part)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "send_sms_notification",
    "build_sms_message",
]