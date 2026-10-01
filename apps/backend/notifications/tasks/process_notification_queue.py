# apps/backend/notifications/tasks/process_notification_queue.py

"""
Notification push queue orchestration.

ARCHITECTURE
------------

Canonical queue orchestration:

    notifications.tasks.process_notification_queue

Canonical individual push processing:

    notifications.tasks.process_notification_queue.process_notification_push

Canonical provider delivery:

    notifications.tasks.push.deliver_push_notification

Compatibility/public task facade:

    notifications.tasks.queue

Responsibilities
----------------

This module owns:

    - finding pending NotificationPush records
    - recovering stale PROCESSING pushes
    - processing pending pushes
    - processing one push
    - compatibility entry points required by existing callers

This module does NOT:

    - contact Expo
    - contact FCM
    - contact APNs
    - implement provider-specific delivery
    - implement provider routing
    - duplicate NotificationService business logic

Provider delivery belongs to:

    notifications.channels.push

Notification-domain state management belongs to:

    notifications.services.notification_service

IMPORTANT
---------

The canonical single-push processor MUST NOT delegate back to
notifications.tasks.queue.process_single_push.

That would create a recursive cycle:

    process_notification_push
        -> queue.process_single_push
        -> process_notification_push
        -> ...

Instead:

    process_notification_push
        -> deliver_push_notification

The queue compatibility facade may delegate into this module, but this
module must never delegate back into the compatibility facade for its
canonical processing path.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

from notifications.models.push import NotificationPush


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000

PROCESSING_TIMEOUT_MINUTES = 10


# ============================================================================
# INTERNAL CANONICAL TASK RESOLUTION
# ============================================================================


def _get_delivery_task():
    """
    Resolve the canonical push-delivery task lazily.

    Provider delivery remains owned by:

        notifications.tasks.push.deliver_push_notification

    The import is intentionally lazy to avoid task-module import cycles.
    """

    from notifications.tasks.push import deliver_push_notification

    return deliver_push_notification


# ============================================================================
# MAIN QUEUE TASK
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.process_notification_queue",
    max_retries=3,
    default_retry_delay=30,
)
def process_notification_queue(
    self,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Process a batch of pending NotificationPush records.

    This is the canonical queue orchestration boundary.

    Flow:

        1. normalize batch size
        2. recover stale PROCESSING pushes
        3. obtain pending push IDs
        4. process each push synchronously through the canonical
           process_notification_push task

    No nested .delay() calls are created here.
    """

    batch_size = _normalize_batch_size(batch_size)

    logger.info(
        "Starting notification push queue: batch_size=%s",
        batch_size,
    )

    recovered = recover_stale_processing_pushes()

    push_ids = get_pending_push_ids(
        limit=batch_size,
    )

    if not push_ids:
        result = {
            "success": True,
            "status": "empty",
            "processed": 0,
            "queued": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "recovered": recovered,
            "push_ids": [],
        }

        logger.debug(
            "Notification push queue is empty: %s",
            result,
        )

        return result

    processed = 0
    sent = 0
    failed = 0
    skipped = 0

    for push_id in push_ids:
        try:
            result = process_notification_push.run(
                push_id,
            )

            processed += 1

            if not isinstance(result, dict):
                continue

            status = result.get("status")

            if status == NotificationPush.PushStatus.SENT:
                sent += 1

            elif status == NotificationPush.PushStatus.FAILED:
                failed += 1

            elif status == NotificationPush.PushStatus.SKIPPED:
                skipped += 1

        except Exception as exc:
            failed += 1

            logger.exception(
                "Unable to process notification push: push_id=%s",
                push_id,
            )

            logger.error(
                "Notification push processing failed: "
                "push_id=%s error=%s",
                push_id,
                exc,
            )

    result = {
        "success": True,
        "status": "completed",
        "processed": processed,
        "queued": processed,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "recovered": recovered,
        "push_ids": push_ids,
    }

    logger.info(
        "Notification push queue completed: %s",
        result,
    )

    return result


# ============================================================================
# FETCH PENDING PUSH IDS
# ============================================================================


def get_pending_push_ids(
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> list[int]:
    """
    Return IDs of pending NotificationPush records.

    Only primary keys cross the queue orchestration boundary.
    """

    limit = _normalize_batch_size(limit)

    return list(
        NotificationPush.objects
        .filter(
            status=NotificationPush.PushStatus.PENDING,
        )
        .order_by(
            "created_at",
            "pk",
        )
        .values_list(
            "pk",
            flat=True,
        )[:limit]
    )


# ============================================================================
# SINGLE-PUSH PROCESSING TASK
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.process_notification_push",
    max_retries=3,
    default_retry_delay=30,
)
def process_notification_push(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Process one NotificationPush.

    This is the canonical single-push processing boundary.

    IMPORTANT
    ---------

    This function MUST NOT call:

        notifications.tasks.queue.process_single_push

    That compatibility task delegates back to this function and would
    therefore create infinite recursion.

    Instead, this canonical processor delegates directly to the canonical
    delivery task:

        notifications.tasks.push.deliver_push_notification
    """

    try:
        push = (
            NotificationPush.objects
            .filter(pk=push_id)
            .first()
        )

    except Exception as exc:
        logger.exception(
            "Unable to load notification push: push_id=%s",
            push_id,
        )

        raise self.retry(
            exc=exc,
            countdown=30,
        )

    if push is None:
        logger.warning(
            "NotificationPush does not exist: push_id=%s",
            push_id,
        )

        return {
            "success": False,
            "status": "not_found",
            "push_id": push_id,
        }

    # ------------------------------------------------------------------------
    # IDEMPOTENCY
    # ------------------------------------------------------------------------

    if push.status == NotificationPush.PushStatus.SENT:
        return {
            "success": True,
            "status": NotificationPush.PushStatus.SENT,
            "push_id": push.pk,
        }

    if push.status == NotificationPush.PushStatus.SKIPPED:
        return {
            "success": True,
            "status": NotificationPush.PushStatus.SKIPPED,
            "push_id": push.pk,
        }

    # ------------------------------------------------------------------------
    # CANONICAL DELIVERY
    # ------------------------------------------------------------------------
    #
    # IMPORTANT:
    #
    # Do NOT resolve queue.process_single_push here.
    #
    # queue.process_single_push -> this task.
    #
    # Calling it here would produce:
    #
    #     this task
    #         -> queue.process_single_push
    #         -> this task
    #         -> ...
    #
    # Instead, go directly to the canonical delivery task.
    # ------------------------------------------------------------------------

    try:
        delivery_task = _get_delivery_task()

        result = delivery_task.run(
            push.pk,
        )

        if isinstance(result, dict):
            return result

        return {
            "success": True,
            "status": "processed",
            "push_id": push.pk,
            "result": result,
        }

    except Exception as exc:
        logger.exception(
            "Unable to deliver notification push: push_id=%s",
            push_id,
        )

        raise self.retry(
            exc=exc,
            countdown=30,
        )


# ============================================================================
# ENQUEUE PENDING PUSHES
# ============================================================================


@shared_task(
    name="notifications.tasks.enqueue_pending_notification_pushes",
)
def enqueue_pending_notification_pushes(
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Process pending pushes through the canonical queue processor.

    This remains a compatibility-oriented entry point.

    Processing is intentionally synchronous once this task has started.
    """

    batch_size = _normalize_batch_size(batch_size)

    push_ids = get_pending_push_ids(
        limit=batch_size,
    )

    queued = 0
    failed = 0

    for push_id in push_ids:
        try:
            process_notification_push.run(
                push_id,
            )

            queued += 1

        except Exception:
            failed += 1

            logger.exception(
                "Unable to process pending push: push_id=%s",
                push_id,
            )

    result = {
        "success": failed == 0,
        "status": "completed",
        "queued": queued,
        "failed": failed,
        "push_ids": push_ids,
        "batch_size": batch_size,
    }

    logger.info(
        "Processed pending notification pushes: queued=%s failed=%s",
        queued,
        failed,
    )

    return result


# ============================================================================
# STALE PROCESSING RECOVERY
# ============================================================================


def recover_stale_processing_pushes() -> int:
    """
    Return stale PROCESSING pushes to PENDING.

    A push is stale when it has remained in PROCESSING longer than
    PROCESSING_TIMEOUT_MINUTES.
    """

    cutoff = (
        timezone.now()
        - timedelta(
            minutes=PROCESSING_TIMEOUT_MINUTES,
        )
    )

    now = timezone.now()

    stale_pushes = (
        NotificationPush.objects
        .filter(
            status=NotificationPush.PushStatus.PROCESSING,
            processing_started_at__lt=cutoff,
        )
    )

    count = stale_pushes.update(
        status=NotificationPush.PushStatus.PENDING,
        error_message="",
        processing_started_at=None,
        updated_at=now,
    )

    if count:
        logger.warning(
            "Recovered stale notification pushes: count=%s",
            count,
        )

    return count


# ============================================================================
# LEGACY COMPATIBILITY ALIAS
# ============================================================================


def deliver_notification_push(
    push_id: int,
) -> dict[str, Any]:
    """
    Compatibility function for legacy callers.

    Delegates directly to the canonical provider-delivery task.

    This function does not implement provider delivery itself.
    """

    delivery_task = _get_delivery_task()

    return delivery_task.run(
        push_id,
    )


# ============================================================================
# NORMALIZATION
# ============================================================================


def _normalize_batch_size(
    batch_size: int,
) -> int:
    """
    Normalize batch size to the supported range.
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


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    "process_notification_queue",
    "process_notification_push",
    "enqueue_pending_notification_pushes",
    "deliver_notification_push",
    "get_pending_push_ids",
    "recover_stale_processing_pushes",
]