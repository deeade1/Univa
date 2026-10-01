# apps/backend/notifications/events/emitter.py
"""
Notification event emitter.

This module is the public API used by Univa domain applications
to create NotificationEvent records.

Domain applications should normally use:

    from notifications.events import emit_notification_event

The emitter is intentionally independent of Celery and notification
processing internals.

Architecture
------------

    Domain Application
            │
            ▼
    emit_notification_event()
            │
            ▼
    NotificationEvent
            │
            ▼
    queue_event()
            │
            ▼
    transaction.on_commit()
            │
            ▼
    process_notification_event_task
            │
            ▼
    NotificationEventProcessor
            │
            ▼
    NotificationService
            │
            ▼
    NotificationPush
            │
            ▼
    notifications.tasks.push

Responsibilities
----------------

This module ONLY:

    - validates event input
    - validates event registration
    - normalizes event data
    - creates NotificationEvent records
    - delegates asynchronous queueing to notifications.tasks.queue

This module does NOT:

    - import Celery tasks
    - call Celery directly
    - process notification events
    - resolve recipients
    - evaluate notification preferences
    - create UserNotification records
    - create NotificationPush records
    - send push notifications
    - perform provider routing
    - contact Expo, FCM, APNs, or WebPush

The dependency direction is intentionally kept one-way:

    events.emitter
          │
          ▼
    tasks.queue
          │
          ▼
    tasks.event_tasks

This prevents circular dependencies and keeps the event subsystem
independent from Celery implementation details.
"""

from __future__ import annotations

from typing import Any, Mapping

from notifications.models.event import NotificationEvent
from notifications.tasks.queue import queue_event

from .registry import is_registered_event


# ============================================================================
# ERRORS
# ============================================================================


class NotificationEventError(Exception):
    """
    Raised when a notification event cannot be created.

    This exception represents an invalid event request rather than a
    Celery or provider delivery failure.
    """


# ============================================================================
# INTERNAL NORMALIZATION HELPERS
# ============================================================================


def _normalize_event_type(
    event_type: str,
) -> str:
    """
    Normalize and validate an event type.
    """

    normalized = str(event_type or "").strip()

    if not normalized:
        raise NotificationEventError(
            "event_type is required."
        )

    if not is_registered_event(normalized):
        raise NotificationEventError(
            f"Unregistered notification event: {normalized}"
        )

    return normalized


def _normalize_module(
    module: str,
) -> str:
    """
    Normalize and validate the originating domain module.
    """

    normalized = str(module or "").strip().lower()

    if not normalized:
        raise NotificationEventError(
            "module is required."
        )

    return normalized


def _normalize_payload(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Normalize notification event payload.

    Payloads are copied into a new dictionary so callers cannot mutate
    the event payload through the original mapping after the event has
    been created.
    """

    if payload is None:
        return {}

    if not isinstance(payload, Mapping):
        raise NotificationEventError(
            "payload must be a mapping/dictionary."
        )

    return dict(payload)


def _normalize_object_id(
    object_id: str | int | None,
) -> str:
    """
    Normalize the related domain object's primary key.

    None represents an absent object ID.

    Zero is preserved intentionally because it is a legitimate primitive
    value and should never be silently converted into an empty string.
    """

    if object_id is None:
        return ""

    return str(object_id)


def _normalize_object_type(
    object_type: str | None,
) -> str:
    """
    Normalize the related domain object's type.
    """

    return str(object_type or "").strip()


# ============================================================================
# EVENT EMISSION
# ============================================================================


def emit_notification_event(
    *,
    event_type: str,
    module: str,
    actor=None,
    object_type: str = "",
    object_id: str | int = "",
    payload: Mapping[str, Any] | None = None,
    enqueue: bool = True,
) -> NotificationEvent:
    """
    Create and optionally queue a NotificationEvent.

    Parameters
    ----------
    event_type:
        Canonical registered notification event identifier.

        Example:

            "ORDER.CREATED"

    module:
        Domain module that generated the event.

        Example:

            "order"

    actor:
        User responsible for generating the event, when applicable.

    object_type:
        Type of domain object associated with the event.

        Example:

            "Order"

    object_id:
        Primary key of the associated domain object.

    payload:
        Structured event data consumed by the notification subsystem.

        Example:

            {
                "recipient_id": 123,
            }

    enqueue:
        When True, delegate queueing to notifications.tasks.queue.
        The queue layer is responsible for transaction-safe Celery
        publication.

    Returns
    -------
    NotificationEvent
        The newly-created notification event.

    Raises
    ------
    NotificationEventError
        If the event data is invalid or the event type is not registered.

    Notes
    -----
    This function deliberately does not import or invoke Celery tasks.
    """

    # ------------------------------------------------------------------------
    # Normalize and validate event data
    # ------------------------------------------------------------------------

    normalized_event_type = _normalize_event_type(event_type)
    normalized_module = _normalize_module(module)
    normalized_payload = _normalize_payload(payload)
    normalized_object_type = _normalize_object_type(object_type)
    normalized_object_id = _normalize_object_id(object_id)

    # ------------------------------------------------------------------------
    # Create event
    # ------------------------------------------------------------------------

    try:
        event = NotificationEvent.objects.create(
            event_type=normalized_event_type,
            module=normalized_module,
            actor=actor,
            object_type=normalized_object_type,
            object_id=normalized_object_id,
            payload=normalized_payload,
            status=NotificationEvent.Status.PENDING,
        )

    except Exception as exc:
        raise NotificationEventError(
            "Unable to create notification event."
        ) from exc

    # ------------------------------------------------------------------------
    # Queue after creation
    # ------------------------------------------------------------------------
    #
    # queue_event() owns transaction.on_commit().
    #
    # emitter.py therefore remains independent of:
    #
    #     - Celery
    #     - task names
    #     - task implementation
    #     - delivery workers
    #
    # This is important for a clean production architecture.
    # ------------------------------------------------------------------------

    if enqueue:
        try:
            queue_event(event)

        except Exception as exc:
            raise NotificationEventError(
                f"Notification event {event.pk} was created but "
                "could not be queued."
            ) from exc

    return event


# ============================================================================
# CONVENIENCE API
# ============================================================================


def emit_and_queue_notification_event(
    *,
    event_type: str,
    module: str,
    actor=None,
    object_type: str = "",
    object_id: str | int = "",
    payload: Mapping[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create and queue a NotificationEvent.

    This is the preferred API for normal domain application usage.

    Example
    -------

        emit_and_queue_notification_event(
            event_type=ORDER_CREATED,
            module="order",
            actor=user,
            object_type="Order",
            object_id=order.pk,
            payload={
                "recipient_id": user.pk,
            },
        )
    """

    return emit_notification_event(
        event_type=event_type,
        module=module,
        actor=actor,
        object_type=object_type,
        object_id=object_id,
        payload=payload,
        enqueue=True,
    )


def create_notification_event(
    *,
    event_type: str,
    module: str,
    actor=None,
    object_type: str = "",
    object_id: str | int = "",
    payload: Mapping[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a NotificationEvent without queueing it.

    Useful for:

        - administrative workflows
        - tests
        - imports
        - migrations
        - workflows that control processing manually

    The returned event remains in PENDING status until another part of
    the application explicitly queues it.
    """

    return emit_notification_event(
        event_type=event_type,
        module=module,
        actor=actor,
        object_type=object_type,
        object_id=object_id,
        payload=payload,
        enqueue=False,
    )



def queue_event_by_id(event_id: int) -> None:
    """
    Queue an existing event by its ID.
    
    This is used by the event system to queue events that were created
    without automatic queueing.
    """
    from notifications.tasks.queue import queue_event
    
    try:
        event = NotificationEvent.objects.get(pk=event_id)
        queue_event(event)
    except NotificationEvent.DoesNotExist:
        raise NotificationEventError(f"Event {event_id} does not exist.")
# ============================================================================
# PUBLIC API
# ============================================================================


__all__ = [
    "NotificationEventError",
    "emit_notification_event",
    "emit_and_queue_notification_event",
    "create_notification_event",
    "queue_event_by_id",
]
