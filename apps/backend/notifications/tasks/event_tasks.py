"""
Celery tasks responsible for processing NotificationEvent records.

Architecture
------------

    NotificationEvent
           │
           ▼
    process_notification_event_task
           │
           ▼
    notifications.events.processor
           │
           ├── locking
           ├── state transitions
           ├── recipient resolution
           └── notification creation
                       │
                       ▼
              NotificationService
                       │
                       ├── UserNotification
                       └── NotificationPush
                                      │
                                      ▼
                              notifications.tasks.push


Responsibilities
----------------

This module owns Celery orchestration only.

It does NOT:

    - implement notification business logic
    - resolve recipients
    - evaluate notification preferences
    - create UserNotification records
    - create NotificationPush records
    - send push notifications
    - contact Expo
    - contact FCM
    - contact APNs
    - contact WebPush
    - implement provider routing
    - persist event failure state as business logic

Those responsibilities belong to:

    notifications.events.processor
    notifications.services.notification_service
    notifications.channels.push
    notifications.channels.*

The processor is authoritative for:

    - event locking
    - event state transitions
    - recipient resolution
    - notification creation
    - event failure persistence

Celery is authoritative for:

    - asynchronous execution
    - retry scheduling
    - retry backoff
    - operational recovery orchestration

Public tasks
------------

    process_notification_event_task
    recover_stale_notification_events
    retry_failed_notification_events
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from notifications.events.processor import (
    process_notification_event,
)
from notifications.models.event import NotificationEvent


logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

EVENT_MAX_RETRIES = 5

DEFAULT_RETRY_DELAY = 60
MAX_RETRY_DELAY = 300

DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000

DEFAULT_STALE_TIMEOUT = 15 * 60


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def _normalize_event_id(event_id: Any) -> int:
    """
    Normalize and validate a NotificationEvent primary key.

    Celery task boundaries should receive primitive values rather than
    Django model instances.
    """

    if event_id is None:
        raise ValueError(
            "event_id is required."
        )

    try:
        value = int(event_id)

    except (TypeError, ValueError) as exc:
        raise ValueError(
            "event_id must be a valid integer."
        ) from exc

    if value <= 0:
        raise ValueError(
            "event_id must be greater than zero."
        )

    return value


def _normalize_batch_size(
    batch_size: int,
) -> int:
    """
    Normalize a requested batch size to a safe range.
    """

    try:
        value = int(batch_size)

    except (TypeError, ValueError):
        value = DEFAULT_BATCH_SIZE

    return max(
        1,
        min(
            value,
            MAX_BATCH_SIZE,
        ),
    )


def _normalize_timeout(
    timeout_seconds: int,
) -> int:
    """
    Normalize a stale-event timeout.

    A timeout of zero or a negative value is unsafe because it could
    immediately classify active processing as stale.
    """

    try:
        value = int(timeout_seconds)

    except (TypeError, ValueError):
        value = DEFAULT_STALE_TIMEOUT

    return max(
        1,
        value,
    )


# ============================================================================
# RETRY HELPERS
# ============================================================================


def _retry_countdown(
    retry_number: int,
) -> int:
    """
    Calculate a bounded exponential retry delay.

    Retry 0 -> 60 seconds
    Retry 1 -> 120 seconds
    Retry 2 -> 240 seconds
    Retry 3 -> 300 seconds
    Retry 4 -> 300 seconds
    """

    try:
        retry_number = max(
            0,
            int(retry_number),
        )

    except (TypeError, ValueError):
        retry_number = 0

    return min(
        DEFAULT_RETRY_DELAY * (2 ** retry_number),
        MAX_RETRY_DELAY,
    )


# ============================================================================
# PROCESS SINGLE EVENT
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.process_notification_event",
    max_retries=EVENT_MAX_RETRIES,
    default_retry_delay=DEFAULT_RETRY_DELAY,
)
def process_notification_event_task(
    self,
    event_id: int,
) -> dict[str, Any]:
    """
    Process one NotificationEvent.

    This task is intentionally thin.

    Celery owns:

        - task execution
        - retry scheduling
        - retry backoff

    NotificationEventProcessor owns:

        - event locking
        - event state transitions
        - recipient resolution
        - notification creation
        - failure persistence

    Push delivery is NOT performed here.
    """

    event_id = _normalize_event_id(
        event_id,
    )

    logger.info(
        "Processing notification event: event_id=%s",
        event_id,
    )

    # =========================================================================
    # LOAD EVENT
    # =========================================================================

    try:
        event = (
            NotificationEvent.objects
            .select_related("actor")
            .get(
                pk=event_id,
            )
        )

    except NotificationEvent.DoesNotExist:
        logger.warning(
            "Notification event does not exist: event_id=%s",
            event_id,
        )

        return {
            "success": False,
            "event_id": event_id,
            "status": "not_found",
            "notifications_created": 0,
            "notification_ids": [],
        }

    # =========================================================================
    # TERMINAL STATES
    # =========================================================================

    if event.status == NotificationEvent.Status.PROCESSED:
        logger.info(
            "Notification event already processed: event_id=%s",
            event_id,
        )

        return {
            "success": True,
            "event_id": event_id,
            "status": "already_processed",
            "notifications_created": 0,
            "notification_ids": [],
        }

    if event.status == NotificationEvent.Status.CANCELLED:
        logger.info(
            "Notification event is cancelled: event_id=%s",
            event_id,
        )

        return {
            "success": True,
            "event_id": event_id,
            "status": "cancelled",
            "notifications_created": 0,
            "notification_ids": [],
        }

    # =========================================================================
    # PROCESS THROUGH AUTHORITATIVE PROCESSOR
    # =========================================================================

    try:
        notifications = process_notification_event(
            event,
        )

    except NotificationEvent.DoesNotExist:
        logger.warning(
            "Notification event disappeared during processing: "
            "event_id=%s",
            event_id,
        )

        return {
            "success": False,
            "event_id": event_id,
            "status": "not_found",
            "notifications_created": 0,
            "notification_ids": [],
        }

    except Exception as exc:
        logger.exception(
            "Notification event processing failed: event_id=%s",
            event_id,
        )

        # ---------------------------------------------------------------------
        # IMPORTANT ARCHITECTURAL BOUNDARY
        #
        # The processor is responsible for persisting FAILED state.
        #
        # This task must NOT:
        #
        #     - call mark_event_failed()
        #     - modify event.status
        #     - increment event.attempts
        #     - perform notification creation
        #
        # Celery only decides whether another execution should occur.
        # ---------------------------------------------------------------------

        try:
            event.refresh_from_db()

        except NotificationEvent.DoesNotExist:
            logger.warning(
                "Notification event disappeared after processing failure: "
                "event_id=%s",
                event_id,
            )

            return {
                "success": False,
                "event_id": event_id,
                "status": "not_found",
                "notifications_created": 0,
                "notification_ids": [],
            }

        # ---------------------------------------------------------------------
        # Cancellation is terminal.
        # ---------------------------------------------------------------------

        if event.status == NotificationEvent.Status.CANCELLED:
            logger.info(
                "Notification event was cancelled after failure: "
                "event_id=%s",
                event_id,
            )

            return {
                "success": True,
                "event_id": event_id,
                "status": event.status,
                "notifications_created": 0,
                "notification_ids": [],
            }

        # ---------------------------------------------------------------------
        # Celery retry policy.
        #
        # self.request.retries represents retries already performed.
        #
        # With max_retries=5, retry attempts are:
        #
        #     retry 0
        #     retry 1
        #     retry 2
        #     retry 3
        #     retry 4
        #
        # Once the retry limit is reached, allow Celery to raise the
        # terminal MaxRetriesExceededError rather than manufacturing another
        # application-level state.
        # ---------------------------------------------------------------------

        if self.request.retries >= EVENT_MAX_RETRIES:
            logger.error(
                "Notification event retry limit reached: "
                "event_id=%s retries=%s status=%s error=%s",
                event_id,
                self.request.retries,
                event.status,
                event.error_message or str(exc),
            )

            return {
                "success": False,
                "event_id": event_id,
                "status": event.status,
                "notifications_created": 0,
                "notification_ids": [],
                "error_message": (
                    event.error_message or str(exc)
                ),
            }

        logger.warning(
            "Retrying notification event: "
            "event_id=%s retry=%s status=%s error=%s",
            event_id,
            self.request.retries,
            event.status,
            event.error_message or str(exc),
        )

        raise self.retry(
            exc=exc,
            countdown=_retry_countdown(
                self.request.retries,
            ),
        )

    # =========================================================================
    # REFRESH AUTHORITATIVE EVENT STATE
    # =========================================================================

    try:
        event.refresh_from_db()

    except NotificationEvent.DoesNotExist:
        logger.warning(
            "Notification event disappeared after successful processing: "
            "event_id=%s",
            event_id,
        )

        notification_ids = [
            notification.pk
            for notification in notifications
            if getattr(notification, "pk", None)
        ]

        return {
            "success": False,
            "event_id": event_id,
            "status": "not_found",
            "notifications_created": len(
                notification_ids,
            ),
            "notification_ids": notification_ids,
        }

    # =========================================================================
    # BUILD RESULT
    # =========================================================================

    notification_ids = [
        notification.pk
        for notification in notifications
        if getattr(notification, "pk", None)
    ]

    success = (
        event.status
        == NotificationEvent.Status.PROCESSED
    )

    logger.info(
        "Notification event processing completed: "
        "event_id=%s status=%s notifications=%s",
        event_id,
        event.status,
        len(notification_ids),
    )

    return {
        "success": success,
        "event_id": event_id,
        "status": event.status,
        "notifications_created": len(notification_ids),
        "notification_ids": notification_ids,
        "error_message": event.error_message or "",
    }


# ============================================================================
# RECOVER STALE PROCESSING EVENTS
# ============================================================================


@shared_task(
    name="notifications.tasks.recover_stale_notification_events",
)
def recover_stale_notification_events(
    timeout_seconds: int = DEFAULT_STALE_TIMEOUT,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Recover NotificationEvent records that have remained in PROCESSING.

    A worker can terminate after the processor marks an event PROCESSING but
    before the transaction completes. Without recovery, the event could
    remain stuck indefinitely.

    Recovery does not perform event processing itself.

    The event is returned to PENDING and a new Celery processing task is
    scheduled after the database transaction commits.
    """

    timeout_seconds = _normalize_timeout(
        timeout_seconds,
    )

    batch_size = _normalize_batch_size(
        batch_size,
    )

    cutoff = (
        timezone.now()
        - timedelta(
            seconds=timeout_seconds,
        )
    )

    event_ids = list(
        NotificationEvent.objects
        .filter(
            status=NotificationEvent.Status.PROCESSING,
            updated_at__lt=cutoff,
        )
        .order_by(
            "updated_at",
        )
        .values_list(
            "pk",
            flat=True,
        )[:batch_size]
    )

    recovered = 0
    queued = 0

    for event_id in event_ids:

        try:
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

                event.status = (
                    NotificationEvent.Status.PENDING
                )

                event.processed_at = None

                event.error_message = (
                    "Notification event recovered after "
                    "remaining in processing state."
                )

                event.save(
                    update_fields=[
                        "status",
                        "processed_at",
                        "error_message",
                        "updated_at",
                    ]
                )

                recovered += 1

                # -------------------------------------------------------------
                # Queue only after this transaction commits.
                # -------------------------------------------------------------

                transaction.on_commit(
                    lambda event_id=event_id: (
                        process_notification_event_task.delay(
                            event_id,
                        )
                    )
                )

                queued += 1

        except Exception:
            logger.exception(
                "Failed to recover stale notification event: "
                "event_id=%s",
                event_id,
            )

    if recovered:
        logger.warning(
            "Recovered stale notification events: "
            "recovered=%s queued=%s",
            recovered,
            queued,
        )

    return {
        "success": True,
        "recovered": recovered,
        "queued": queued,
        "timeout_seconds": timeout_seconds,
        "batch_size": batch_size,
    }


# ============================================================================
# RETRY FAILED EVENTS
# ============================================================================


@shared_task(
    name="notifications.tasks.retry_failed_notification_events",
)
def retry_failed_notification_events(
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Return failed NotificationEvent records to PENDING and enqueue them.

    This task is intended for operational recovery/manual retry workflows.

    It does not process events directly.

    Actual event processing is always performed by:

        process_notification_event_task
    """

    batch_size = _normalize_batch_size(
        batch_size,
    )

    event_ids = list(
        NotificationEvent.objects
        .filter(
            status=NotificationEvent.Status.FAILED,
        )
        .order_by(
            "updated_at",
        )
        .values_list(
            "pk",
            flat=True,
        )[:batch_size]
    )

    reset = 0
    queued = 0

    for event_id in event_ids:

        try:
            with transaction.atomic():

                event = (
                    NotificationEvent.objects
                    .select_for_update()
                    .filter(
                        pk=event_id,
                        status=NotificationEvent.Status.FAILED,
                    )
                    .first()
                )

                if event is None:
                    continue

                event.status = (
                    NotificationEvent.Status.PENDING
                )

                event.error_message = ""
                event.processed_at = None

                event.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "processed_at",
                        "updated_at",
                    ]
                )

                reset += 1

                # -------------------------------------------------------------
                # Queue only after the reset transaction commits.
                # -------------------------------------------------------------

                transaction.on_commit(
                    lambda event_id=event_id: (
                        process_notification_event_task.delay(
                            event_id,
                        )
                    )
                )

                queued += 1

        except Exception:
            logger.exception(
                "Failed to reset notification event: "
                "event_id=%s",
                event_id,
            )

    logger.info(
        "Reset failed notification events: "
        "reset=%s queued=%s",
        reset,
        queued,
    )

    return {
        "success": True,
        "reset": reset,
        "queued": queued,
        "batch_size": batch_size,
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "process_notification_event_task",
    "recover_stale_notification_events",
    "retry_failed_notification_events",
]
