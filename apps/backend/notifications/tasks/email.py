# apps/backend/notifications/tasks/email.py

"""
Celery task for email notification delivery.

Architecture
------------

    UserNotification
            |
            v
    send_email_notification
            |
            v
      Django email backend
            |
            +----> SMTP
            +----> SendGrid
            +----> Amazon SES
            +----> Mailgun
            +----> Other configured backend

This module owns email-delivery orchestration only.

It does NOT:

    - create UserNotification records
    - resolve notification recipients
    - resolve notification preferences
    - create notification events
    - implement SMTP
    - call an email provider directly
    - contain provider-specific email logic
    - schedule itself
    - manage notification-event processing

Notification creation belongs to:

    notifications.services.notification_service

Notification event processing belongs to:

    notifications.events.processor

Email infrastructure belongs to:

    Django's configured email backend
"""

from __future__ import annotations

import logging
from html import escape
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from ..models import UserNotification


logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class EmailNotificationTaskError(Exception):
    """Base exception for email notification task failures."""


# ============================================================================
# PUBLIC TASK
# ============================================================================


@shared_task(
    bind=True,
    autoretry_for=(EmailNotificationTaskError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def send_email_notification(
    self,
    notification_id: int,
) -> dict[str, Any]:
    """
    Deliver one UserNotification through Django's configured email backend.

    Celery receives only the notification primary key.

    Retry policy belongs to Celery. Email delivery itself belongs to this
    task and Django's configured email backend.

    Parameters
    ----------
    notification_id:
        Primary key of the UserNotification to deliver.

    Returns
    -------
    dict
        Delivery result.
    """

    # ========================================================================
    # VALIDATE ID
    # ========================================================================

    if notification_id is None:
        raise EmailNotificationTaskError(
            "notification_id is required."
        )

    try:
        notification_id = int(notification_id)

    except (TypeError, ValueError) as exc:
        raise EmailNotificationTaskError(
            "notification_id must be a valid integer."
        ) from exc

    if notification_id <= 0:
        raise EmailNotificationTaskError(
            "notification_id must be greater than zero."
        )

    # ========================================================================
    # LOAD NOTIFICATION
    # ========================================================================

    try:
        notification = (
            UserNotification.objects
            .select_related("recipient")
            .get(pk=notification_id)
        )

    except UserNotification.DoesNotExist:
        logger.warning(
            "Email notification does not exist: notification=%s",
            notification_id,
        )

        # A missing notification is not a transient delivery failure.
        # Retrying cannot recreate the notification.
        return {
            "success": False,
            "notification_id": notification_id,
            "status": "not_found",
        }

    # ========================================================================
    # VALIDATE RECIPIENT
    # ========================================================================

    recipient = notification.recipient

    recipient_email = getattr(
        recipient,
        "email",
        None,
    )

    if recipient_email is None:
        logger.info(
            "Email notification skipped because recipient has no email: "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": "no_email",
        }

    recipient_email = str(
        recipient_email
    ).strip()

    if not recipient_email:
        logger.info(
            "Email notification skipped because recipient email is empty: "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        return {
            "success": True,
            "notification_id": notification.pk,
            "recipient_id": notification.recipient_id,
            "status": "no_email",
        }

    # ========================================================================
    # DELIVER
    # ========================================================================

    try:
        result = _send_email(
            notification=notification,
            recipient_email=recipient_email,
        )

    except EmailNotificationTaskError:
        logger.exception(
            "Email notification delivery failed: "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        raise

    except Exception as exc:
        logger.exception(
            "Unexpected email notification delivery failure: "
            "notification=%s recipient=%s",
            notification.pk,
            notification.recipient_id,
        )

        raise EmailNotificationTaskError(
            str(exc)
            or "Unexpected email notification delivery failure."
        ) from exc

    logger.info(
        "Email notification delivered: "
        "notification=%s recipient=%s",
        notification.pk,
        notification.recipient_id,
    )

    return result


# ============================================================================
# EMAIL DELIVERY
# ============================================================================


def _send_email(
    *,
    notification: UserNotification,
    recipient_email: str,
) -> dict[str, Any]:
    """
    Send one notification using Django's configured email backend.

    This function deliberately knows nothing about SMTP, SES, SendGrid,
    Mailgun, or any other provider.
    """

    # ========================================================================
    # FROM ADDRESS
    # ========================================================================

    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        None,
    )

    if not from_email:
        raise EmailNotificationTaskError(
            "DEFAULT_FROM_EMAIL is not configured."
        )

    # ========================================================================
    # CONTENT
    # ========================================================================

    subject = (
        str(notification.title or "").strip()
        or "Notification"
    )

    text_body = _build_text_body(
        notification=notification,
    )

    html_body = _build_html_body(
        notification=notification,
    )

    # ========================================================================
    # MESSAGE
    # ========================================================================

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient_email],
    )

    email.attach_alternative(
        html_body,
        "text/html",
    )

    # ========================================================================
    # SEND
    # ========================================================================

    sent = email.send(
        fail_silently=False,
    )

    if sent != 1:
        raise EmailNotificationTaskError(
            "Django email backend did not report successful delivery."
        )

    return {
        "success": True,
        "notification_id": notification.pk,
        "recipient_id": notification.recipient_id,
        "email": recipient_email,
        "status": "sent",
        "sent_at": timezone.now().isoformat(),
    }


# ============================================================================
# PLAIN-TEXT EMAIL
# ============================================================================


def _build_text_body(
    *,
    notification: UserNotification,
) -> str:
    """
    Build the plain-text representation of a notification.
    """

    lines = [
        notification.title,
        "",
        notification.message,
    ]

    if notification.action_url:
        lines.extend(
            [
                "",
                f"Open notification: {notification.action_url}",
            ]
        )

    lines.extend(
        [
            "",
            f"Module: {notification.module}",
            f"Type: {notification.notification_type}",
            f"Priority: {notification.priority}",
        ]
    )

    return "\n".join(lines)


# ============================================================================
# HTML EMAIL
# ============================================================================


def _build_html_body(
    *,
    notification: UserNotification,
) -> str:
    """
    Build the HTML representation of a notification.

    All notification-controlled content is HTML escaped.
    """

    title = escape(
        notification.title or ""
    )

    message = escape(
        notification.message or ""
    ).replace(
        "\n",
        "<br>",
    )

    module = escape(
        notification.module or ""
    )

    notification_type = escape(
        notification.notification_type or ""
    )

    priority = escape(
        notification.priority or ""
    )

    action_html = ""

    if notification.action_url:
        action_url = escape(
            notification.action_url,
            quote=True,
        )

        action_html = f"""
        <p>
            <a href="{action_url}">
                Open notification
            </a>
        </p>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>

<body>
    <div>
        <h2>{title}</h2>

        <p>
            {message}
        </p>

        {action_html}

        <hr>

        <p>
            <strong>Module:</strong> {module}<br>
            <strong>Type:</strong> {notification_type}<br>
            <strong>Priority:</strong> {priority}
        </p>
    </div>
</body>
</html>
""".strip()


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    "EmailNotificationTaskError",
    "send_email_notification",
]