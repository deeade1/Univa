"""
Notification event processor.

Architecture
------------

    NotificationEvent
            │
            ▼
    NotificationEventProcessor
            │
            ├── acquire row lock
            ├── validate state
            ├── mark PROCESSING
            ├── resolve recipients
            └── create notifications
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

This module is the authoritative coordinator for NotificationEvent
processing.

It owns:

    - loading the authoritative NotificationEvent record
    - row-level locking
    - event processing-state transitions
    - recipient-resolution coordination
    - notification-creation coordination
    - atomic event processing
    - failure-state persistence after rollback
    - terminal-state idempotency
    - protection against concurrent event processing

It does NOT:

    - send push notifications
    - contact Expo
    - contact FCM
    - contact APNs
    - contact WebPush
    - implement provider routing
    - create NotificationPush records directly
    - implement push delivery state transitions
    - schedule Celery push delivery
    - implement notification preferences
    - contain provider-specific logic

Those responsibilities belong to:

    notifications.services.notification_service
    notifications.channels.push
    notifications.channels.*
    notifications.tasks.push

Celery orchestration belongs to:

    notifications.tasks.event_tasks

Transaction-safe task enqueueing belongs to:

    notifications.tasks.queue


Processing contract
-------------------

Normal event lifecycle:

    PENDING
       │
       ▼
    PROCESSING
       │
       ├── success ──► PROCESSED
       │
       └── failure ──► FAILED

Recovery lifecycle:

    FAILED
       │
       ▼
    PENDING
       │
       ▼
    PROCESSING
       │
       ▼
    PROCESSED

Stale lifecycle:

    PROCESSING
       │
       │ stale timeout
       ▼
    PENDING
       │
       ▼
    PROCESSING

Terminal states:

    PROCESSED
    CANCELLED

are never processed again.

Public API
----------

    process_notification_event(event)

or:

    NotificationEventProcessor.process(event)
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from notifications.models.event import NotificationEvent
from notifications.services.notification_service import (
    create_user_notification,
    resolve_recipients,
)


logger = logging.getLogger(__name__)


# ============================================================================
# PROCESSOR
# ============================================================================


class NotificationEventProcessor:
    """
    Authoritative coordinator for processing one NotificationEvent.

    The processor is intentionally responsible for orchestration and event
    state. Business-specific recipient rules and notification construction
    remain delegated to the notification service.

    Processing is atomic:

        lock event
            │
            ▼
        PROCESSING
            │
            ▼
        resolve recipients
            │
            ▼
        create notifications
            │
            ▼
        PROCESSED
            │
            ▼
        commit

    If any operation fails before commit, the transaction is rolled back.
    The event is then freshly loaded and marked FAILED outside the rolled-back
    transaction.
    """

    @classmethod
    def process(
        cls,
        event: NotificationEvent,
    ) -> list[Any]:
        """
        Process one NotificationEvent.

        The supplied model instance is used only to obtain its primary key.
        The authoritative database state is always loaded again under a
        row-level lock.

        Processing rules:

            PROCESSED  -> idempotent no-op
            CANCELLED  -> idempotent no-op
            PROCESSING -> no-op
            PENDING     -> process
            FAILED      -> no-op

        FAILED events must first be deliberately returned to PENDING by the
        recovery/retry layer.

        Any processing exception is persisted as FAILED after the processing
        transaction rolls back, then the original exception is re-raised so
        Celery can apply its retry policy.
        """

        # ====================================================================
        # VALIDATION
        # ====================================================================

        if not isinstance(event, NotificationEvent):
            raise ValueError(
                "NotificationEventProcessor.process requires "
                "a NotificationEvent instance."
            )

        if not event.pk:
            raise ValueError(
                "NotificationEvent must be saved before processing."
            )

        event_id = event.pk

        logger.debug(
            "Starting notification event processing: event_id=%s",
            event_id,
        )

        # ====================================================================
        # ATOMIC PROCESSING
        # ====================================================================

        try:
            with transaction.atomic():

                # ------------------------------------------------------------
                # AUTHORITATIVE LOAD + ROW LOCK
                # ------------------------------------------------------------

                locked_event = (
                    NotificationEvent.objects
                    .select_for_update()
                    .get(
                        pk=event_id,
                    )
                )

                # ------------------------------------------------------------
                # TERMINAL: PROCESSED
                # ------------------------------------------------------------

                if (
                    locked_event.status
                    == NotificationEvent.Status.PROCESSED
                ):
                    logger.info(
                        "Notification event already processed: "
                        "event_id=%s",
                        event_id,
                    )

                    return []

                # ------------------------------------------------------------
                # TERMINAL: CANCELLED
                # ------------------------------------------------------------

                if (
                    locked_event.status
                    == NotificationEvent.Status.CANCELLED
                ):
                    logger.info(
                        "Notification event is cancelled: "
                        "event_id=%s",
                        event_id,
                    )

                    return []

                # ------------------------------------------------------------
                # CONCURRENT PROCESSING
                # ------------------------------------------------------------

                if (
                    locked_event.status
                    == NotificationEvent.Status.PROCESSING
                ):
                    logger.info(
                        "Notification event is already being processed: "
                        "event_id=%s",
                        event_id,
                    )

                    return []

                # ------------------------------------------------------------
                # FAILED EVENTS ARE NOT DIRECTLY PROCESSABLE
                # ------------------------------------------------------------
                #
                # A FAILED event must be explicitly reset by the recovery
                # layer before it can be processed again.
                #
                # This keeps retry policy outside the processor.
                # ------------------------------------------------------------

                if (
                    locked_event.status
                    == NotificationEvent.Status.FAILED
                ):
                    logger.info(
                        "Notification event is FAILED and requires "
                        "explicit recovery before processing: "
                        "event_id=%s",
                        event_id,
                    )

                    return []

                # ------------------------------------------------------------
                # ONLY PENDING EVENTS MAY BE CLAIMED
                # ------------------------------------------------------------

                if (
                    locked_event.status
                    != NotificationEvent.Status.PENDING
                ):
                    logger.warning(
                        "Notification event is not processable: "
                        "event_id=%s status=%s",
                        event_id,
                        locked_event.status,
                    )

                    return []

                # ------------------------------------------------------------
                # CLAIM EVENT
                # ------------------------------------------------------------

                locked_event.mark_processing()

                logger.debug(
                    "Notification event marked PROCESSING: "
                    "event_id=%s attempt=%s",
                    event_id,
                    locked_event.attempts,
                )

                # ------------------------------------------------------------
                # RESOLVE RECIPIENTS
                # ------------------------------------------------------------
                #
                # Recipient-selection rules remain outside this processor.
                #
                # The processor coordinates the operation but does not know
                # domain-specific recipient rules or notification preferences.
                # ------------------------------------------------------------

                recipients = resolve_recipients(
                    locked_event,
                )

                if not recipients:
                    logger.info(
                        "No recipients resolved for notification event: "
                        "event_id=%s",
                        event_id,
                    )

                    # No recipients is a successful event-processing outcome.
                    locked_event.mark_processed()

                    return []

                # ------------------------------------------------------------
                # CREATE USER NOTIFICATIONS
                # ------------------------------------------------------------
                #
                # NotificationService owns notification construction.
                #
                # This processor does NOT:
                #
                #     - create UserNotification directly
                #     - create NotificationPush directly
                #     - resolve providers
                #     - send push notifications
                #
                # The service may create NotificationPush records and enqueue
                # delivery through the appropriate transaction-safe boundary.
                # ------------------------------------------------------------

                notifications: list[Any] = []

                for recipient in recipients:

                    notification = create_user_notification(
                        event=locked_event,
                        recipient=recipient,
                    )

                    if notification is None:
                        continue

                    notifications.append(
                        notification
                    )

                # ------------------------------------------------------------
                # MARK EVENT PROCESSED
                # ------------------------------------------------------------
                #
                # This occurs inside the same transaction as notification
                # creation.
                #
                # Therefore:
                #
                #     notification creation succeeds
                #             +
                #     event becomes PROCESSED
                #             +
                #     transaction commits
                #
                # or:
                #
                #     everything rolls back.
                # ------------------------------------------------------------

                locked_event.mark_processed()

                logger.info(
                    "Notification event processed successfully: "
                    "event_id=%s notifications=%s",
                    event_id,
                    len(notifications),
                )

                return notifications

        # ====================================================================
        # EVENT DISAPPEARED
        # ====================================================================

        except NotificationEvent.DoesNotExist:
            logger.warning(
                "Notification event does not exist: "
                "event_id=%s",
                event_id,
            )

            return []

        # ====================================================================
        # PROCESSING FAILURE
        # ====================================================================

        except Exception as exc:
            logger.exception(
                "Notification event processing failed: "
                "event_id=%s",
                event_id,
            )

            # ---------------------------------------------------------------
            # TRANSACTION BOUNDARY
            # ---------------------------------------------------------------
            #
            # The transaction.atomic() block has now rolled back.
            #
            # Consequently:
            #
            #     - PROCESSING state has rolled back
            #     - notification records created inside the transaction
            #       have rolled back
            #     - any NotificationPush records created inside the
            #       transaction have rolled back
            #
            # Failure state must therefore be persisted using a fresh
            # database operation.
            # ---------------------------------------------------------------

            try:
                mark_event_failed_by_id(
                    event_id=event_id,
                    error=str(exc),
                )

            except Exception:
                # -----------------------------------------------------------
                # Never hide the original processing exception because failure
                # persistence itself failed.
                # -----------------------------------------------------------

                logger.exception(
                    "Unable to persist FAILED state for notification event: "
                    "event_id=%s",
                    event_id,
                )

            # ---------------------------------------------------------------
            # Celery owns retry scheduling.
            #
            # Re-raise the original exception.
            # ---------------------------------------------------------------

            raise


# ============================================================================
# FAILURE PERSISTENCE
# ============================================================================


def mark_event_failed_by_id(
    event_id: int,
    error: str,
) -> None:
    """
    Persist FAILED state for a NotificationEvent.

    This function runs after the processing transaction has rolled back.

    Event failure persistence belongs to the processor boundary.

    Retry scheduling does NOT belong here.
    """

    # ========================================================================
    # VALIDATE ID
    # ========================================================================

    if event_id is None:
        raise ValueError(
            "event_id is required."
        )

    try:
        normalized_event_id = int(
            event_id,
        )

    except (TypeError, ValueError) as exc:
        raise ValueError(
            "event_id must be a valid integer."
        ) from exc

    if normalized_event_id <= 0:
        raise ValueError(
            "event_id must be greater than zero."
        )

    # ========================================================================
    # FRESH DATABASE LOOKUP
    # ========================================================================

    event = (
        NotificationEvent.objects
        .filter(
            pk=normalized_event_id,
        )
        .first()
    )

    if event is None:
        logger.warning(
            "Cannot mark missing notification event as failed: "
            "event_id=%s",
            normalized_event_id,
        )

        return

    # ========================================================================
    # PROTECT TERMINAL STATES
    # ========================================================================

    if (
        event.status
        == NotificationEvent.Status.CANCELLED
    ):
        logger.info(
            "Notification event was cancelled before failure "
            "persistence: event_id=%s",
            normalized_event_id,
        )

        return

    if (
        event.status
        == NotificationEvent.Status.PROCESSED
    ):
        logger.info(
            "Notification event was processed before failure "
            "persistence: event_id=%s",
            normalized_event_id,
        )

        return

    # ========================================================================
    # PERSIST FAILURE
    # ========================================================================

    event.mark_failed(
        error,
    )

    logger.warning(
        "Notification event marked FAILED: "
        "event_id=%s",
        normalized_event_id,
    )


# ============================================================================
# PUBLIC FUNCTION API
# ============================================================================


def process_notification_event(
    event: NotificationEvent,
) -> list[Any]:
    """
    Public function-based API for processing a NotificationEvent.

    This is the canonical function entry point for:

        notifications.tasks.event_tasks

    and compatibility callers.

    All processing remains centralized in NotificationEventProcessor.
    """

    return NotificationEventProcessor.process(
        event,
    )


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    "NotificationEventProcessor",
    "process_notification_event",
]
