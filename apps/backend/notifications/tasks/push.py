"""
Celery tasks for notification push delivery.

Architecture
------------

UserNotification
        |
        v
NotificationPush
        |
        v
Celery task
        |
        v
NotificationService.claim_push_for_processing()
        |
        v
NotificationService.send_to_device()
        |
        v
notifications.channels.push.PushChannel
        |
        +---- Expo
        +---- FCM
        +---- APNs
        +---- WebPush


Responsibilities
----------------

This module owns Celery orchestration only.

It DOES:

    - load NotificationPush records
    - perform lightweight terminal-state checks
    - request an atomic delivery claim from NotificationService
    - schedule Celery retries
    - queue pending pushes
    - queue failed pushes for recovery
    - serialize task results

It does NOT:

    - create UserNotification records
    - create NotificationPush records
    - resolve recipients
    - validate notification devices
    - resolve providers
    - claim NotificationPush state directly
    - increment delivery attempts directly
    - implement NotificationPush state transitions
    - call providers directly
    - normalize provider responses
    - deactivate devices
    - perform provider-specific communication

Those responsibilities belong to:

    notifications.services.notification_service
    notifications.channels.push
    notifications.models.push

Celery retry and scheduling orchestration belongs here.

IMPORTANT
---------

The provider HTTP request MUST remain outside any database transaction.

The atomic PENDING -> PROCESSING claim is completed and committed
before NotificationService.send_to_device() performs provider delivery.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from ..models import NotificationPush
from ..services.notification_service import (
    NotificationService,
    reset_push_for_retry,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_PUSH_ATTEMPTS = 5

DEFAULT_RETRY_DELAY = 60
MAX_RETRY_DELAY = 300

DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000


# ============================================================================
# SINGLE PUSH DELIVERY
# ============================================================================


@shared_task(
    bind=True,
    name="notifications.tasks.deliver_push_notification",
    max_retries=MAX_PUSH_ATTEMPTS - 1,
    default_retry_delay=DEFAULT_RETRY_DELAY,
)
def deliver_push_notification(
    self,
    push_id: int,
) -> dict[str, Any]:
    """
    Deliver one NotificationPush.

    Celery owns:

        - loading the record
        - lightweight terminal-state checks
        - retry scheduling
        - task result serialization

    NotificationService owns:

        - atomic PENDING -> PROCESSING claim
        - delivery-attempt counting
        - device validation
        - provider resolution
        - provider delivery
        - response normalization
        - push state transitions
        - device failure handling

    Provider-specific communication must never happen here.

    IMPORTANT
    ---------

    The atomic delivery claim is completed before this task invokes
    NotificationService.send_to_device().

    Therefore no provider/API request occurs while the claim transaction
    is open.
    """

    # =========================================================================
    # LOAD
    # =========================================================================

    push = _get_push(push_id)

    if push is None:
        return _not_found_result(push_id)

    # =========================================================================
    # TERMINAL STATE
    # =========================================================================

    if _is_terminal(push):
        return _serialize_push_result(push)

    # =========================================================================
    # ATOMIC DELIVERY CLAIM
    # =========================================================================
    #
    # NotificationService is authoritative for:
    #
    #     PENDING -> PROCESSING
    #     attempts += 1
    #
    # The service must perform this operation atomically using:
    #
    #     transaction.atomic()
    #     SELECT ... FOR UPDATE
    #
    # The transaction is committed before this task calls
    # send_to_device().
    #
    # This prevents two Celery workers from simultaneously claiming
    # the same PENDING NotificationPush.
    # =========================================================================

    try:
        claim_result = (
            NotificationService.claim_push_for_processing(
                push_id=push_id,
            )
        )

    except NotificationPush.DoesNotExist:
        logger.warning(
            "NotificationPush disappeared while claiming: "
            "push_id=%s",
            push_id,
        )

        return _not_found_result(push_id)

    except Exception as exc:
        logger.exception(
            "Unable to claim notification push: "
            "push_id=%s",
            push_id,
        )

        return _handle_claim_failure(
            task=self,
            push_id=push_id,
            exception=exc,
        )

    # =========================================================================
    # CLAIM RESULT
    # =========================================================================
    #
    # claim_result is expected to be a NotificationPush instance.
    #
    # If another worker already claimed the push, the service should return
    # the current persisted state instead of allowing this task to proceed.
    # =========================================================================

    if claim_result is None:
        push = _refresh_push(push_id)

        if push is None:
            return _not_found_result(push_id)

        return _serialize_push_result(push)

    push = claim_result

    # -------------------------------------------------------------------------
    # Terminal state after claim
    # -------------------------------------------------------------------------

    if _is_terminal(push):
        return _serialize_push_result(push)

    # -------------------------------------------------------------------------
    # Only the PROCESSING owner may proceed to provider delivery.
    # -------------------------------------------------------------------------

    if push.status != NotificationPush.PushStatus.PROCESSING:

        logger.info(
            "NotificationPush was not claimed for processing: "
            "push_id=%s status=%s",
            push.pk,
            push.status,
        )

        return _serialize_push_result(push)

    # =========================================================================
    # SERVICE DELIVERY
    # =========================================================================
    #
    # At this point the claim transaction has already committed.
    #
    # Therefore provider HTTP communication occurs outside the database
    # transaction.
    #
    # NotificationService owns:
    #
    #     - device validation
    #     - provider selection
    #     - provider communication
    #     - response normalization
    #     - success/failure state transitions
    #     - device failure handling
    #
    # Celery only decides whether a failed delivery should be retried.
    # =========================================================================

    try:
        NotificationService.send_to_device(push)

    except Exception as exc:
        logger.exception(
            "Unexpected notification service failure: "
            "push_id=%s",
            push_id,
        )

        return _handle_unexpected_service_failure(
            task=self,
            push_id=push_id,
            exception=exc,
        )

    # =========================================================================
    # READ FINAL SERVICE STATE
    # =========================================================================

    push = _refresh_push(push_id)

    if push is None:
        return _not_found_result(push_id)

    response = _serialize_push_result(push)

    # =========================================================================
    # SUCCESS
    # =========================================================================

    if push.status == NotificationPush.PushStatus.SENT:

        logger.info(
            "Push notification delivered: "
            "push_id=%s provider=%s attempt=%s",
            push.pk,
            push.provider,
            push.attempts,
        )

        return response

    # =========================================================================
    # SKIPPED
    # =========================================================================

    if push.status == NotificationPush.PushStatus.SKIPPED:

        logger.info(
            "Push notification skipped: "
            "push_id=%s reason=%s",
            push.pk,
            push.error_message,
        )

        return response

    # =========================================================================
    # FAILED
    # =========================================================================

    if push.status == NotificationPush.PushStatus.FAILED:

        return _handle_failed_push(
            task=self,
            push=push,
            response=response,
        )

    # =========================================================================
    # PROCESSING
    # =========================================================================

    if push.status == NotificationPush.PushStatus.PROCESSING:

        logger.warning(
            "Push service returned while push remains processing: "
            "push_id=%s",
            push.pk,
        )

        return response

    # =========================================================================
    # PENDING
    # =========================================================================

    if push.status == NotificationPush.PushStatus.PENDING:

        logger.warning(
            "Push service returned without completing delivery: "
            "push_id=%s",
            push.pk,
        )

        return _retry_or_return(
            task=self,
            push=push,
            response=response,
            error="Push delivery did not reach a terminal state.",
        )

    # =========================================================================
    # UNEXPECTED STATE
    # =========================================================================

    logger.error(
        "Push ended in unexpected state: "
        "push_id=%s status=%s",
        push.pk,
        push.status,
    )

    return response


# ============================================================================
# CLAIM FAILURE HANDLING
# ============================================================================


def _handle_claim_failure(
    *,
    task: Any,
    push_id: int,
    exception: Exception,
) -> dict[str, Any]:
    """
    Handle an unexpected failure while attempting the atomic claim.

    Claim failures are infrastructure/database/service-boundary failures,
    not provider failures.

    They should therefore be retried by Celery rather than being converted
    into NotificationPush.FAILED by this task.
    """

    push = _refresh_push(push_id)

    if push is None:
        return _not_found_result(push_id)

    if _is_terminal(push):
        return _serialize_push_result(push)

    # -------------------------------------------------------------------------
    # If another worker has already claimed the push, do not interfere.
    # -------------------------------------------------------------------------

    if push.status == NotificationPush.PushStatus.PROCESSING:

        logger.info(
            "Push became processing while claim failed: "
            "push_id=%s",
            push_id,
        )

        return _serialize_push_result(push)

    # -------------------------------------------------------------------------
    # Attempts are controlled by the claim operation.
    #
    # We deliberately do NOT increment attempts here.
    # -------------------------------------------------------------------------

    if task.request.retries >= MAX_PUSH_ATTEMPTS - 1:

        logger.error(
            "Push claim failed and Celery retries are exhausted: "
            "push_id=%s retries=%s",
            push_id,
            task.request.retries,
        )

        raise exception

    raise task.retry(
        exc=exception,
        countdown=_retry_countdown(
            task.request.retries,
        ),
    )


# ============================================================================
# SERVICE FAILURE HANDLING
# ============================================================================


def _handle_unexpected_service_failure(
    *,
    task: Any,
    push_id: int,
    exception: Exception,
) -> dict[str, Any]:
    """
    Handle an unexpected exception escaping NotificationService.

    Expected provider failures should already have been persisted by the
    service.

    If an unexpected exception escapes the service boundary, this task
    provides a defensive persistence fallback before scheduling a retry.

    This fallback does not implement provider-specific failure semantics.
    """

    push = _refresh_push(push_id)

    if push is None:
        return _not_found_result(push_id)

    # -------------------------------------------------------------------------
    # Respect terminal state.
    # -------------------------------------------------------------------------

    if _is_terminal(push):
        return _serialize_push_result(push)

    # -------------------------------------------------------------------------
    # If service already persisted failure, use that state.
    # -------------------------------------------------------------------------

    if push.status == NotificationPush.PushStatus.FAILED:
        return _handle_failed_push(
            task=task,
            push=push,
            response=_serialize_push_result(push),
        )

    # -------------------------------------------------------------------------
    # Persist unexpected failure through authoritative service.
    # -------------------------------------------------------------------------

    try:
        NotificationService.mark_push_failed(
            push,
            str(exception),
            permanent=False,
        )

    except Exception:
        logger.exception(
            "Unable to persist unexpected push failure: "
            "push_id=%s",
            push_id,
        )

        # Do not silently report success if failure persistence itself
        # fails. Let Celery handle the exception.
        raise

    push = _refresh_push(push_id)

    if push is None:
        return _not_found_result(push_id)

    response = _serialize_push_result(push)

    if push.attempts >= MAX_PUSH_ATTEMPTS:
        logger.error(
            "Push exhausted attempts after unexpected service exception: "
            "push_id=%s attempts=%s",
            push.pk,
            push.attempts,
        )

        return response

    if _device_is_inactive(push):
        logger.warning(
            "Push will not be retried because device is inactive: "
            "push_id=%s device_id=%s",
            push.pk,
            push.device_id,
        )

        return response

    raise task.retry(
        exc=exception,
        countdown=_retry_countdown(
            task.request.retries,
        ),
    )


# ============================================================================
# FAILED PUSH HANDLING
# ============================================================================


def _handle_failed_push(
    *,
    task: Any,
    push: NotificationPush,
    response: dict[str, Any],
) -> dict[str, Any]:
    """
    Decide whether a service-persisted failure should be retried.

    NotificationService owns the failure state.

    Celery owns the retry decision.
    """

    error = (
        push.error_message
        or "Push delivery failed."
    )

    # -------------------------------------------------------------------------
    # Attempt limit.
    # -------------------------------------------------------------------------

    if push.attempts >= MAX_PUSH_ATTEMPTS:

        logger.error(
            "Push retry limit reached: "
            "push_id=%s attempts=%s error=%s",
            push.pk,
            push.attempts,
            error,
        )

        return response

    # -------------------------------------------------------------------------
    # Inactive device.
    # -------------------------------------------------------------------------

    if _device_is_inactive(push):

        logger.warning(
            "Push failure will not be retried because device is inactive: "
            "push_id=%s device_id=%s error=%s",
            push.pk,
            push.device_id,
            error,
        )

        return response

    # -------------------------------------------------------------------------
    # Retry transient failure.
    #
    # The push is reset to PENDING before Celery retries.
    # The next task invocation must atomically claim it.
    # -------------------------------------------------------------------------

    try:
        reset_push_for_retry(push)

    except Exception:
        logger.exception(
            "Unable to reset failed push for retry: "
            "push_id=%s",
            push.pk,
        )
        raise

    logger.warning(
        "Retrying failed push: "
        "push_id=%s attempt=%s retry=%s error=%s",
        push.pk,
        push.attempts,
        task.request.retries,
        error,
    )

    raise task.retry(
        exc=RuntimeError(error),
        countdown=_retry_countdown(
            task.request.retries,
        ),
    )


# ============================================================================
# NON-TERMINAL RECOVERY
# ============================================================================


def _retry_or_return(
    *,
    task: Any,
    push: NotificationPush,
    response: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    """
    Retry a non-terminal push when attempts remain.

    This is a defensive recovery path for a service result that did not
    reach SENT, SKIPPED, or FAILED.
    """

    if push.attempts >= MAX_PUSH_ATTEMPTS:

        logger.error(
            "Push cannot be retried because maximum attempts were reached: "
            "push_id=%s attempts=%s",
            push.pk,
            push.attempts,
        )

        return response

    if _device_is_inactive(push):

        logger.warning(
            "Push will not be retried because device is inactive: "
            "push_id=%s device_id=%s",
            push.pk,
            push.device_id,
        )

        return response

    # -------------------------------------------------------------------------
    # The push should not remain PROCESSING indefinitely.
    #
    # Reset it through the authoritative service before retrying.
    # -------------------------------------------------------------------------

    try:
        reset_push_for_retry(push)

    except Exception:
        logger.exception(
            "Unable to reset non-terminal push for retry: "
            "push_id=%s",
            push.pk,
        )
        raise

    logger.warning(
        "Retrying non-terminal push: "
        "push_id=%s attempt=%s error=%s",
        push.pk,
        push.attempts,
        error,
    )

    raise task.retry(
        exc=RuntimeError(error),
        countdown=_retry_countdown(
            task.request.retries,
        ),
    )


# ============================================================================
# PUSH LOOKUP HELPERS
# ============================================================================


def _get_push(
    push_id: int,
) -> NotificationPush | None:
    """
    Load a NotificationPush with relationships required by delivery
    and serialization.

    This is read-only preparation.
    """

    try:
        return (
            NotificationPush.objects
            .select_related(
                "notification",
                "notification__recipient",
                "notification__event",
                "device",
                "device__user",
            )
            .get(pk=push_id)
        )

    except NotificationPush.DoesNotExist:
        logger.warning(
            "NotificationPush does not exist: push_id=%s",
            push_id,
        )

        return None


def _refresh_push(
    push_id: int,
) -> NotificationPush | None:
    """
    Reload a push from the database after service execution.
    """

    try:
        return (
            NotificationPush.objects
            .select_related(
                "notification",
                "notification__recipient",
                "notification__event",
                "device",
                "device__user",
            )
            .get(pk=push_id)
        )

    except NotificationPush.DoesNotExist:
        logger.warning(
            "NotificationPush no longer exists: push_id=%s",
            push_id,
        )

        return None


# ============================================================================
# STATE HELPERS
# ============================================================================


def _is_terminal(
    push: NotificationPush,
) -> bool:
    """
    Return True when no further delivery work is required.
    """

    return push.status in {
        NotificationPush.PushStatus.SENT,
        NotificationPush.PushStatus.SKIPPED,
    }


def _device_is_inactive(
    push: NotificationPush,
) -> bool:
    """
    Return True when the associated device exists but is inactive.

    Missing devices are intentionally not treated as inactive here.

    Device validity belongs to NotificationService.
    """

    try:
        device = push.device

    except Exception:
        return False

    if device is None:
        return False

    return not bool(
        getattr(
            device,
            "is_active",
            False,
        )
    )


# ============================================================================
# RETRY HELPERS
# ============================================================================


def _retry_countdown(
    retry_number: int,
) -> int:
    """
    Calculate bounded exponential retry delay.

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
# SERIALIZATION
# ============================================================================


def _serialize_push_result(
    push: NotificationPush,
) -> dict[str, Any]:
    """
    Convert NotificationPush into a Celery-safe dictionary.

    Only SENT represents successful delivery.

    SKIPPED is intentionally not considered successful delivery.
    """

    return {
        "success": (
            push.status
            == NotificationPush.PushStatus.SENT
        ),
        "push_id": push.pk,
        "notification_id": push.notification_id,
        "device_id": push.device_id,
        "provider": push.provider,
        "provider_message_id": push.provider_message_id,
        "status": push.status,
        "attempts": push.attempts,
        "error_message": push.error_message,
    }


def _not_found_result(
    push_id: int,
) -> dict[str, Any]:
    """
    Return a stable result for a missing NotificationPush.
    """

    return {
        "success": False,
        "push_id": push_id,
        "status": "not_found",
    }


# ============================================================================
# QUEUE PENDING PUSHES
# ============================================================================


@shared_task(
    name="notifications.tasks.deliver_pending_push_notifications",
)
def deliver_pending_push_notifications(
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Queue pending NotificationPush records.

    This task only schedules delivery tasks.

    It does not perform provider delivery.

    Multiple workers may observe the same pending record. That is safe
    because deliver_push_notification() delegates the actual atomic claim
    to NotificationService.
    """

    batch_size = _normalize_batch_size(batch_size)

    push_ids = list(
        NotificationPush.objects
        .filter(
            status=NotificationPush.PushStatus.PENDING,
            attempts__lt=MAX_PUSH_ATTEMPTS,
        )
        .order_by(
            "created_at",
            "pk",
        )
        .values_list(
            "pk",
            flat=True,
        )[:batch_size]
    )

    queued = 0

    for push_id in push_ids:

        try:
            deliver_push_notification.delay(push_id)
            queued += 1

        except Exception:
            logger.exception(
                "Failed to queue pending push: push_id=%s",
                push_id,
            )

    logger.info(
        "Queued pending notification pushes: "
        "count=%s batch_size=%s",
        queued,
        batch_size,
    )

    return {
        "success": True,
        "queued": queued,
        "batch_size": batch_size,
    }


# ============================================================================
# RETRY FAILED PUSHES
# ============================================================================


@shared_task(
    name="notifications.tasks.retry_failed_push_notifications",
)
def retry_failed_push_notifications(
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Requeue failed NotificationPush records.

    This is intended for scheduled/manual recovery.

    Normal transient failures are normally retried directly by
    deliver_push_notification().

    Only failed pushes belonging to active devices with remaining
    attempts are recovered.

    The FAILED -> PENDING transition is delegated to
    NotificationService.reset_push_for_retry().

    The subsequent PENDING -> PROCESSING transition is delegated to
    NotificationService.claim_push_for_processing().
    """

    batch_size = _normalize_batch_size(batch_size)

    push_ids = list(
        NotificationPush.objects
        .filter(
            status=NotificationPush.PushStatus.FAILED,
            attempts__lt=MAX_PUSH_ATTEMPTS,
            device__is_active=True,
        )
        .order_by(
            "updated_at",
            "pk",
        )
        .values_list(
            "pk",
            flat=True,
        )[:batch_size]
    )

    queued = 0

    for push_id in push_ids:

        try:
            push = _refresh_push(push_id)

            if push is None:
                continue

            if push.status != NotificationPush.PushStatus.FAILED:
                continue

            if push.attempts >= MAX_PUSH_ATTEMPTS:
                continue

            if _device_is_inactive(push):
                continue

            reset_push_for_retry(push)

            deliver_push_notification.delay(push_id)
            queued += 1

        except Exception:
            logger.exception(
                "Failed to recover failed push: push_id=%s",
                push_id,
            )

    logger.info(
        "Retried failed notification pushes: "
        "count=%s batch_size=%s",
        queued,
        batch_size,
    )

    return {
        "success": True,
        "queued": queued,
        "batch_size": batch_size,
    }


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================


@shared_task(
    name="notifications.tasks.deliver_notification",
)
def deliver_notification(
    notification_id: int,
) -> dict[str, Any]:
    """
    Compatibility task for older callers.

    Older code may call:

        deliver_notification(notification_id)

    New code should queue NotificationPush IDs directly.

    This compatibility task only discovers pending pushes and delegates
    actual delivery to deliver_push_notification().
    """

    push_ids = list(
        NotificationPush.objects
        .filter(
            notification_id=notification_id,
            status=NotificationPush.PushStatus.PENDING,
            attempts__lt=MAX_PUSH_ATTEMPTS,
        )
        .order_by(
            "created_at",
            "pk",
        )
        .values_list(
            "pk",
            flat=True,
        )
    )

    queued = 0

    for push_id in push_ids:

        try:
            deliver_push_notification.delay(push_id)
            queued += 1

        except Exception:
            logger.exception(
                "Failed to queue compatibility push: "
                "notification_id=%s push_id=%s",
                notification_id,
                push_id,
            )

    logger.info(
        "Queued notification pushes through compatibility task: "
        "notification_id=%s count=%s",
        notification_id,
        queued,
    )

    return {
        "success": True,
        "notification_id": notification_id,
        "queued": queued,
    }


# ============================================================================
# HELPERS
# ============================================================================


def _normalize_batch_size(
    batch_size: int,
) -> int:
    """
    Normalize a requested batch size to a safe range.
    """

    try:
        batch_size = int(batch_size)

    except (TypeError, ValueError):
        batch_size = DEFAULT_BATCH_SIZE

    return max(
        1,
        min(
            batch_size,
            MAX_BATCH_SIZE,
        ),
    )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "deliver_push_notification",
    "deliver_pending_push_notifications",
    "retry_failed_push_notifications",
    "deliver_notification",
]