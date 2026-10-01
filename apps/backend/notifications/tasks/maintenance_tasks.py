"""
Maintenance Celery tasks for the notification subsystem.

Responsibilities:

    - Deactivate stale notification devices.
    - Recover stale NotificationEvent records.
    - Recover stale NotificationPush records.
    - Remove old archived notifications.
    - Remove old processed notification events.
    - Remove old completed push-delivery records.

Maintenance tasks do not perform provider delivery.

Provider delivery remains in:

    notifications.tasks.delivery_tasks
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from notifications.models.device import NotificationDevice
from notifications.models.event import NotificationEvent
from notifications.models.notification import UserNotification
from notifications.models.push import NotificationPush

logger = logging.getLogger(__name__)


# ============================================================================
# DEVICE MAINTENANCE
# ============================================================================


@shared_task(
    name="notifications.tasks.cleanup_stale_devices",
)
def cleanup_stale_devices(
    days: int = 90,
):
    """
    Deactivate notification devices that have not been used recently.

    Devices are deactivated rather than deleted so registration history
    remains available.

    Devices without last_used_at are intentionally preserved because
    there is not enough information to determine whether they are stale.
    """

    days = max(1, int(days))

    cutoff = timezone.now() - timedelta(days=days)

    queryset = NotificationDevice.objects.filter(
        is_active=True,
        last_used_at__isnull=False,
        last_used_at__lt=cutoff,
    )

    count = queryset.update(
        is_active=False,
        updated_at=timezone.now(),
    )

    logger.info(
        "Deactivated stale notification devices: count=%s days=%s",
        count,
        days,
    )

    return {
        "success": True,
        "deactivated": count,
        "days": days,
    }


# ============================================================================
# EVENT MAINTENANCE
# ============================================================================


@shared_task(
    name="notifications.tasks.recover_stale_notification_events",
)
def recover_stale_notification_events(
    timeout_minutes: int = 15,
    batch_size: int = 100,
):
    """
    Recover NotificationEvent records stuck in PROCESSING.

    This protects against workers terminating after an event has been
    claimed but before processing completes.

    Recovered events are returned to PENDING so the normal event queue
    can process them again.
    """

    timeout_minutes = max(1, int(timeout_minutes))
    batch_size = max(1, min(int(batch_size), 1000))

    cutoff = timezone.now() - timedelta(
        minutes=timeout_minutes,
    )

    event_ids = list(
        NotificationEvent.objects
        .filter(
            status=NotificationEvent.Status.PROCESSING,
            updated_at__lt=cutoff,
        )
        .order_by("updated_at")
        .values_list("id", flat=True)[:batch_size]
    )

    recovered = 0

    for event_id in event_ids:
        with transaction.atomic():
            event = (
                NotificationEvent.objects
                .select_for_update()
                .filter(
                    pk=event_id,
                    status=NotificationEvent.Status.PROCESSING,
                    updated_at__lt=cutoff,
                )
                .first()
            )

            if event is None:
                continue

            event.status = NotificationEvent.Status.PENDING
            event.error_message = (
                "Event recovered after remaining in "
                "processing state."
            )

            event.save(
                update_fields=[
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )

            recovered += 1

    logger.info(
        "Recovered stale notification events: count=%s",
        recovered,
    )

    return {
        "success": True,
        "recovered": recovered,
        "timeout_minutes": timeout_minutes,
    }


# ============================================================================
# PUSH MAINTENANCE
# ============================================================================


@shared_task(
    name="notifications.tasks.recover_stale_notification_pushes",
)
def recover_stale_notification_pushes(
    timeout_minutes: int = 15,
    batch_size: int = 100,
):
    """
    Recover NotificationPush records stuck in PROCESSING.

    A worker can terminate while a provider request is in progress.
    Such records must not remain permanently PROCESSING.

    Recovered records are returned to PENDING.
    """

    timeout_minutes = max(1, int(timeout_minutes))
    batch_size = max(1, min(int(batch_size), 1000))

    cutoff = timezone.now() - timedelta(
        minutes=timeout_minutes,
    )

    push_ids = list(
        NotificationPush.objects
        .filter(
            status=NotificationPush.PushStatus.PROCESSING,
            processing_started_at__isnull=False,
            processing_started_at__lt=cutoff,
        )
        .order_by("processing_started_at")
        .values_list("id", flat=True)[:batch_size]
    )

    recovered = 0

    for push_id in push_ids:
        with transaction.atomic():
            push = (
                NotificationPush.objects
                .select_for_update()
                .filter(
                    pk=push_id,
                    status=NotificationPush.PushStatus.PROCESSING,
                    processing_started_at__isnull=False,
                    processing_started_at__lt=cutoff,
                )
                .first()
            )

            if push is None:
                continue

            push.status = NotificationPush.PushStatus.PENDING
            push.error_message = (
                "Push delivery recovered after remaining "
                "in processing state."
            )
            push.processing_started_at = None

            push.save(
                update_fields=[
                    "status",
                    "error_message",
                    "processing_started_at",
                    "updated_at",
                ]
            )

            recovered += 1

    logger.info(
        "Recovered stale notification pushes: count=%s",
        recovered,
    )

    return {
        "success": True,
        "recovered": recovered,
        "timeout_minutes": timeout_minutes,
    }


# ============================================================================
# NOTIFICATION CLEANUP
# ============================================================================


@shared_task(
    name="notifications.tasks.cleanup_old_notifications",
)
def cleanup_old_notifications(
    days: int = 180,
    batch_size: int = 1000,
):
    """
    Delete old archived notifications.

    Unread notifications are deliberately preserved.

    Only archived notifications older than the retention period
    are eligible for deletion.
    """

    days = max(1, int(days))
    batch_size = max(1, min(int(batch_size), 5000))

    cutoff = timezone.now() - timedelta(days=days)

    notification_ids = list(
        UserNotification.objects
        .filter(
            is_archived=True,
            created_at__lt=cutoff,
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    if not notification_ids:
        return {
            "success": True,
            "deleted": 0,
            "days": days,
        }

    deleted, _ = (
        UserNotification.objects
        .filter(pk__in=notification_ids)
        .delete()
    )

    logger.info(
        "Deleted old archived notifications: deleted=%s days=%s",
        deleted,
        days,
    )

    return {
        "success": True,
        "deleted": deleted,
        "days": days,
    }


# ============================================================================
# PUSH DELIVERY CLEANUP
# ============================================================================


@shared_task(
    name="notifications.tasks.cleanup_old_push_deliveries",
)
def cleanup_old_push_deliveries(
    days: int = 90,
    batch_size: int = 2000,
):
    """
    Delete old completed NotificationPush records.

    SENT and SKIPPED records are historical delivery records and can
    eventually be removed once they pass the retention period.

    FAILED and PENDING records are preserved.
    """

    days = max(1, int(days))
    batch_size = max(1, min(int(batch_size), 5000))

    cutoff = timezone.now() - timedelta(days=days)

    push_ids = list(
        NotificationPush.objects
        .filter(
            status__in=[
                NotificationPush.PushStatus.SENT,
                NotificationPush.PushStatus.SKIPPED,
            ],
            created_at__lt=cutoff,
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    if not push_ids:
        return {
            "success": True,
            "deleted": 0,
            "days": days,
        }

    deleted, _ = (
        NotificationPush.objects
        .filter(pk__in=push_ids)
        .delete()
    )

    logger.info(
        "Deleted old push delivery records: deleted=%s days=%s",
        deleted,
        days,
    )

    return {
        "success": True,
        "deleted": deleted,
        "days": days,
    }


# ============================================================================
# EVENT CLEANUP
# ============================================================================


@shared_task(
    name="notifications.tasks.cleanup_old_events",
)
def cleanup_old_events(
    days: int = 90,
    batch_size: int = 1000,
):
    """
    Delete old successfully processed NotificationEvent records.

    Failed, pending, processing, and cancelled events are preserved.

    The related UserNotification.event foreign key uses SET_NULL,
    so deleting the event does not delete the user's notification.
    """

    days = max(1, int(days))
    batch_size = max(1, min(int(batch_size), 5000))

    cutoff = timezone.now() - timedelta(days=days)

    event_ids = list(
        NotificationEvent.objects
        .filter(
            status=NotificationEvent.Status.PROCESSED,
            processed_at__isnull=False,
            processed_at__lt=cutoff,
        )
        .order_by("processed_at")
        .values_list("id", flat=True)[:batch_size]
    )

    if not event_ids:
        return {
            "success": True,
            "deleted": 0,
            "days": days,
        }

    deleted, _ = (
        NotificationEvent.objects
        .filter(pk__in=event_ids)
        .delete()
    )

    logger.info(
        "Deleted old notification events: deleted=%s days=%s",
        deleted,
        days,
    )

    return {
        "success": True,
        "deleted": deleted,
        "days": days,
    }


# ============================================================================
# COMBINED MAINTENANCE
# ============================================================================


@shared_task(
    name="notifications.tasks.run_notification_maintenance",
)
def run_notification_maintenance():
    """
    Run the standard notification maintenance cycle.

    This task is a Celery orchestration boundary only.

    Individual maintenance tasks remain independently callable.

    The returned structure intentionally exposes each maintenance result
    directly at the top level so callers, monitoring, and tests can consume
    the result without an additional ``results`` nesting layer.
    """

    stale_devices = cleanup_stale_devices()
    stale_events = recover_stale_notification_events()
    stale_pushes = recover_stale_notification_pushes()
    old_notifications = cleanup_old_notifications()
    old_push_deliveries = cleanup_old_push_deliveries()
    old_events = cleanup_old_events()

    result = {
        "success": True,
        "stale_devices": stale_devices,
        "stale_events": stale_events,
        "stale_pushes": stale_pushes,
        "old_notifications": old_notifications,
        "old_pushes": old_push_deliveries,
        "old_events": old_events,
    }

    logger.info(
        "Notification maintenance completed: %s",
        result,
    )

    return result