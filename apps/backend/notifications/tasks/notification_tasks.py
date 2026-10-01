"""
Celery tasks for notification processing.

This module contains task entry points for UserNotification-related
background work.

Notification creation belongs to:

    notifications.services.notification_service

NotificationEvent processing belongs to:

    notifications.tasks.event_tasks

Push delivery belongs to:

    notifications.tasks.delivery_tasks

Provider-specific delivery belongs to:

    notifications.channels.*
"""

from __future__ import annotations

import logging

from celery import shared_task

from notifications.models.notification import UserNotification
from notifications.services.notification_service import (
    create_push_deliveries,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="notifications.tasks.prepare_notification_delivery",
)
def prepare_notification_delivery(
    notification_id: int,
) -> dict:
    """
    Prepare push delivery records for a UserNotification.

    This task does not send anything.

    It ensures eligible NotificationPush records exist for the
    notification's recipient. Actual provider delivery is handled
    by delivery_tasks.py.
    """

    try:
        notification = (
            UserNotification.objects
            .select_related("recipient", "event")
            .get(pk=notification_id)
        )

    except UserNotification.DoesNotExist:
        logger.warning(
            "UserNotification does not exist: notification_id=%s",
            notification_id,
        )

        return {
            "success": False,
            "notification_id": notification_id,
            "status": "not_found",
            "push_records": 0,
        }

    push_records = create_push_deliveries(
        notification,
    )

    logger.info(
        "Notification delivery prepared: "
        "notification_id=%s push_records=%s",
        notification_id,
        len(push_records),
    )

    return {
        "success": True,
        "notification_id": notification_id,
        "push_records": len(push_records),
        "status": "prepared",
    }


__all__ = [
    "prepare_notification_delivery",
]
