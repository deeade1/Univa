# apps/backend/notifications/tasks/queue.py

"""
Notification task queue compatibility layer.

ARCHITECTURE
------------

Canonical implementations live in:

    notifications.tasks.event_tasks
    notifications.tasks.process_notification_queue
    notifications.tasks.push

This module is a compatibility facade.

Dependency direction:

    domain
        ↓
    notifications.events.emitter
        ↓
    notifications.tasks.queue
        ↓
    canonical task modules

Canonical modules MUST NOT delegate back into this compatibility facade
for their actual processing logic.

This module does NOT:

    - implement provider delivery
    - perform provider HTTP requests
    - create NotificationPush records
    - implement notification business logic
    - duplicate event processing
    - duplicate push delivery
    - own notification state transitions
"""

from __future__ import annotations

from typing import Any

from celery import shared_task


# ============================================================================
# EVENT QUEUE COMPATIBILITY API
# ============================================================================
def queue_event(
    event,
    *args: Any,
    **kwargs: Any,
) -> Any:
    from notifications.tasks.event_tasks import (
        process_notification_event_task,
    )

    event_id = event.pk if hasattr(event, "pk") else event

    return process_notification_event_task.delay(
        event_id,
        *args,
        **kwargs,
    )
# ============================================================================
# CANONICAL TASK RESOLUTION
# ============================================================================


def _get_process_notification_queue_task():
    """
    Lazily resolve the canonical notification queue task.
    """

    from notifications.tasks.process_notification_queue import (
        process_notification_queue as task,
    )

    return task


def _get_process_notification_push_task():
    """
    Lazily resolve the canonical single-push processing task.
    """

    from notifications.tasks.process_notification_queue import (
        process_notification_push as task,
    )

    return task


def _get_enqueue_pending_notification_pushes_task():
    """
    Lazily resolve the canonical pending-push processing task.
    """

    from notifications.tasks.process_notification_queue import (
        enqueue_pending_notification_pushes as task,
    )

    return task


def _get_deliver_push_notification_task():
    """
    Lazily resolve the canonical push-delivery task.
    """

    from notifications.tasks.push import (
        deliver_push_notification as task,
    )

    return task


# ============================================================================
# QUEUE COMPATIBILITY TASKS
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.queue.process_notification_queue",
)
def process_notification_queue(
    self,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Compatibility wrapper for the canonical notification queue task.

    Delegates to:

        notifications.tasks.process_notification_queue
    """

    task = _get_process_notification_queue_task()

    return task.run(
        batch_size=batch_size,
    )


@shared_task(
    bind=True,
    name="notifications.tasks.queue.process_notification_push",
)
def process_notification_push(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Compatibility wrapper for canonical single-push processing.

    Delegates to:

        notifications.tasks.process_notification_queue
        .process_notification_push

    This wrapper MUST NOT be called by the canonical processor.
    """

    task = _get_process_notification_push_task()

    return task.run(
        push_id,
    )


# ============================================================================
# PENDING-PUSH COMPATIBILITY TASK
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.queue.enqueue_pending_notification_pushes",
)
def enqueue_pending_notification_pushes(
    self,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Compatibility wrapper for pending notification push processing.
    """

    task = _get_enqueue_pending_notification_pushes_task()

    return task.run(
        batch_size=batch_size,
    )


# ============================================================================
# SINGLE-PUSH LEGACY COMPATIBILITY NAME
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.queue.process_single_push",
)
def process_single_push(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Backwards-compatible single-push processor.

    Delegates to the canonical single-push processing task.

    Dependency direction:

        process_single_push
            ↓
        canonical process_notification_push
            ↓
        canonical deliver_push_notification

    The canonical task MUST NOT delegate back here.
    """

    task = _get_process_notification_push_task()

    return task.run(
        push_id,
    )


# ============================================================================
# PUSH DELIVERY COMPATIBILITY
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.queue.deliver_push_notification",
)
def deliver_push_notification(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Compatibility wrapper for canonical push delivery.

    Provider delivery remains exclusively owned by:

        notifications.tasks.push.deliver_push_notification
    """

    task = _get_deliver_push_notification_task()

    return task.run(
        push_id,
    )


@shared_task(
    bind=True,
    name="notifications.tasks.queue.deliver_notification_push",
)
def deliver_notification_push(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Legacy compatibility wrapper for push delivery.
    """

    task = _get_deliver_push_notification_task()

    return task.run(
        push_id,
    )


# ============================================================================
# CANONICAL TASK ACCESSORS
# ============================================================================


def get_canonical_process_notification_queue():
    """
    Return the canonical notification queue task.
    """

    return _get_process_notification_queue_task()


def get_canonical_process_notification_push():
    """
    Return the canonical single-push processing task.
    """

    return _get_process_notification_push_task()


def get_canonical_enqueue_pending_notification_pushes():
    """
    Return the canonical pending-push processing task.
    """

    return _get_enqueue_pending_notification_pushes_task()


def get_canonical_deliver_push_notification():
    """
    Return the canonical push-delivery task.
    """

    return _get_deliver_push_notification_task()


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Event queue API
    "queue_event",

    # Queue compatibility tasks
    "process_notification_queue",
    "process_notification_push",
    "process_single_push",
    "enqueue_pending_notification_pushes",

    # Push compatibility tasks
    "deliver_push_notification",
    "deliver_notification_push",

    # Canonical task accessors
    "get_canonical_process_notification_queue",
    "get_canonical_process_notification_push",
    "get_canonical_enqueue_pending_notification_pushes",
    "get_canonical_deliver_push_notification",
]