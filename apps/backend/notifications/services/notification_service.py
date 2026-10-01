# apps/backend/notifications/services/notification_service.py

"""
Central Notification Service for Univa.

Architecture
------------

This module is the authoritative service layer for:

    - notification persistence
    - notification preference resolution
    - push-record creation
    - atomic push-delivery claiming
    - push delivery orchestration
    - push delivery state transitions
    - notification channel dispatch scheduling

Event processing is NOT owned by this service.

Authoritative event processing belongs to:

    notifications.events.processor

Celery orchestration belongs to:

    notifications.tasks.*

Provider routing belongs to:

    notifications.channels.push

Provider implementations belong to:

    notifications.channels.expo
    notifications.channels.fcm
    notifications.channels.apns
    notifications.channels.webpush


Dependency direction
--------------------

    Domain
        │
        ▼
    notifications.events.emitter
        │
        ▼
    notifications.tasks.event_tasks
        │
        ▼
    notifications.events.processor
        │
        ├── recipient resolution
        │
        ▼
    NotificationService
        │
        ├── UserNotification
        └── NotificationPush
                    │
                    ▼
            notifications.tasks.push
                    │
                    ▼
            notifications.channels.push
                    │
                    ▼
                providers


This module MUST NOT import:

    notifications.events.processor

The event processor may depend on this service, but this service must
never depend on the event processor.


Responsibilities
----------------

NotificationService owns:

    - notification validation
    - notification persistence
    - notification preference resolution
    - eligible-device resolution
    - NotificationPush creation
    - atomic PENDING -> PROCESSING claim
    - provider delivery orchestration
    - push SENT / FAILED / retry state transitions
    - transaction-safe channel dispatch scheduling

This module does NOT own:

    - NotificationEvent processing
    - NotificationEvent recipient business rules
    - NotificationEvent state transitions
    - Celery retry policy
    - provider-specific HTTP communication


Transaction boundary
--------------------

Database state transitions occur inside short transactions.

Provider HTTP requests MUST occur outside database transactions.

For push delivery:

    PENDING
        │
        │ atomic database claim
        ▼
    PROCESSING
        │
        │ transaction commits
        ▼
    provider HTTP request
        │
        ├── success ──► SENT
        │
        └── failure ──► FAILED


Compatibility
-------------

A small number of module-level functions are retained for existing callers.

Compatibility functions delegate only toward the canonical service
implementation.

They must never become dependencies of the canonical implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping

from django.db import transaction
from django.utils import timezone

from ..models import (
    NotificationDevice,
    NotificationEvent,
    NotificationPreference,
    NotificationPush,
    UserNotification,
)
from notifications.events.registry import get_event_definition

logger = logging.getLogger(__name__)


# ============================================================================
# CHANNELS
# ============================================================================

CHANNEL_IN_APP = "in_app"
CHANNEL_PUSH = "push"
CHANNEL_EMAIL = "email"
CHANNEL_SMS = "sms"
CHANNEL_WEBSOCKET = "websocket"

SUPPORTED_CHANNELS = frozenset(
    {
        CHANNEL_IN_APP,
        CHANNEL_PUSH,
        CHANNEL_EMAIL,
        CHANNEL_SMS,
        CHANNEL_WEBSOCKET,
    }
)

DEFAULT_CHANNELS = (
    CHANNEL_IN_APP,
    CHANNEL_PUSH,
)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class NotificationServiceError(Exception):
    """Base exception for notification-service failures."""


class InvalidNotificationChannel(NotificationServiceError):
    """Raised when an unsupported notification channel is requested."""


class InvalidNotificationType(NotificationServiceError):
    """Raised when an unsupported notification type is requested."""


class NotificationRecipientError(NotificationServiceError):
    """Raised when a notification recipient cannot be resolved."""


# ============================================================================
# NOTIFICATION SERVICE
# ============================================================================


class NotificationService:
    """
    Authoritative notification and push-delivery service.

    Event processing itself belongs to:

        notifications.events.processor.NotificationEventProcessor

    This service may be called by the event processor, but it never calls
    the event processor.
    """

    # ========================================================================
    # PUBLIC NOTIFICATION API
    # ========================================================================

    @classmethod
    def notify(
        cls,
        *,
        user: Any,
        module: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Mapping[str, Any] | None = None,
        action_url: str = "",
        channels: Iterable[str] | None = None,
        priority: str = UserNotification.Priority.NORMAL,
        event: Any = None,
        dispatch: bool = True,
    ) -> UserNotification:
        """
        Create a UserNotification and prepare requested delivery channels.

        All notification and push records are persisted before asynchronous
        channel dispatch is scheduled.

        Celery work is registered using transaction.on_commit() so a worker
        cannot observe records from a transaction that later rolls back.
        """

        cls._validate_user(user)
        cls._validate_module(module)
        cls._validate_notification_type(notification_type)
        cls._validate_content(title, message)
        cls._validate_priority(priority)

        normalized_metadata = dict(metadata or {})

        selected_channels = cls.resolve_channels(
            user=user,
            requested_channels=channels,
            module=module,
            notification_type=notification_type,
            priority=priority,
        )

        with transaction.atomic():

            notification = cls._create_notification(
                user=user,
                module=module,
                notification_type=notification_type,
                title=title,
                message=message,
                metadata=normalized_metadata,
                action_url=action_url,
                priority=priority,
                event=event,
            )

            push_deliveries: list[NotificationPush] = []

            if CHANNEL_PUSH in selected_channels:
                push_deliveries = cls.create_push_deliveries(
                    notification
                )

            if not selected_channels:
                logger.info(
                    "No enabled notification channels: "
                    "user=%s module=%s type=%s",
                    getattr(user, "pk", None),
                    module,
                    notification_type,
                )

            if dispatch and selected_channels:

                notification_id = notification.pk
                resolved_channels = tuple(selected_channels)
                push_ids = tuple(
                    push.pk
                    for push in push_deliveries
                    if getattr(push, "pk", None)
                )

                transaction.on_commit(
                    lambda notification_id=notification_id,
                    channels=resolved_channels,
                    push_ids=push_ids: cls._dispatch_after_commit(
                        notification_id=notification_id,
                        channels=channels,
                        push_ids=push_ids,
                    )
                )

        return notification

    # ========================================================================
    # CHANNEL RESOLUTION
    # ========================================================================

    @classmethod
    def resolve_channels(
        cls,
        *,
        user: Any,
        requested_channels: Iterable[str] | None = None,
        module: str | None = None,
        notification_type: str | None = None,
        priority: str = UserNotification.Priority.NORMAL,
    ) -> list[str]:
        """
        Resolve requested channels against notification preferences.
        """

        if requested_channels is None:
            requested = list(DEFAULT_CHANNELS)
        else:
            requested = list(requested_channels)

        cls._validate_channels(requested)

        preferences = cls._get_preferences(user)

        return [
            channel
            for channel in requested
            if cls._channel_enabled(
                channel=channel,
                preferences=preferences,
                user=user,
                module=module,
                notification_type=notification_type,
                priority=priority,
            )
        ]

    @classmethod
    def _channel_enabled(
        cls,
        *,
        channel: str,
        preferences: NotificationPreference,
        user: Any,
        module: str | None,
        notification_type: str | None,
        priority: str,
    ) -> bool:
        """
        Determine whether a notification channel is currently available.

        NotificationPreference remains the authoritative source for user
        notification preferences.
        """

        if not preferences.notifications_enabled:
            return False

        if channel == CHANNEL_IN_APP:
            return preferences.can_deliver_immediately(
                channel=CHANNEL_IN_APP,
                category=module,
            )

        if channel == CHANNEL_PUSH:

            if not preferences.push_enabled:
                return False

            if not preferences.can_deliver_immediately(
                channel=CHANNEL_PUSH,
                category=module,
            ):
                return False

            return cls._push_available(
                user=user,
            )

        if channel == CHANNEL_EMAIL:

            if not preferences.can_deliver_immediately(
                channel=CHANNEL_EMAIL,
                category=module,
            ):
                return False

            return bool(
                getattr(
                    user,
                    "email",
                    None,
                )
            )

        if channel == CHANNEL_SMS:
            return False

        if channel == CHANNEL_WEBSOCKET:

            if preferences.is_within_quiet_hours():
                return False

            if not preferences.should_send_instantly():
                return False

            if module and not preferences.allows_category(module):
                return False

            return True

        return False

    # ========================================================================
    # PUSH COMPATIBILITY ALIASES
    # ========================================================================

    @classmethod
    def _create_push_deliveries(
        cls,
        notification: UserNotification,
    ) -> list[NotificationPush]:
        """
        Backward-compatible alias for create_push_deliveries().

        The authoritative implementation remains:

            NotificationService.create_push_deliveries()
        """

        return cls.create_push_deliveries(
            notification
        )

    @staticmethod
    def mark_push_processing(
        push: NotificationPush,
    ) -> NotificationPush | None:
        """
        Backward-compatible alias for the atomic push claim.

        The authoritative implementation remains:

            NotificationService.claim_push_for_processing()
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted."
            )

        return NotificationService._claim_push_for_processing(
            push
        )

    @staticmethod
    def mark_push_sent(
        push: NotificationPush,
        *,
        provider: str | None = None,
        provider_message_id: str | None = None,
    ) -> NotificationPush:
        """
        Backward-compatible alias for successful push delivery.

        The authoritative implementation remains:

            NotificationService._mark_push_sent()
        """

        return NotificationService._mark_push_sent(
            push,
            provider=provider,
            provider_message_id=provider_message_id,
        )

    # ========================================================================
    # NOTIFICATION PERSISTENCE
    # ========================================================================

    @classmethod
    def _create_notification(
        cls,
        *,
        user: Any,
        module: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Mapping[str, Any],
        action_url: str,
        priority: str,
        event: Any = None,
    ) -> UserNotification:
        """
        Persist one UserNotification.

        Event-backed notifications are idempotent for the event/recipient
        pair. The database uniqueness constraint remains the final guard
        against duplicate records.
        """

        if event is not None:

            notification, created = (
                UserNotification.objects.get_or_create(
                    event=event,
                    recipient=user,
                    defaults={
                        "module": module,
                        "notification_type": notification_type,
                        "priority": priority,
                        "title": title,
                        "message": message,
                        "action_url": action_url or "",
                        "metadata": dict(metadata),
                    },
                )
            )

            if not created:
                logger.info(
                    "Notification already exists: "
                    "event=%s recipient=%s notification=%s",
                    getattr(event, "pk", None),
                    getattr(user, "pk", None),
                    notification.pk,
                )

            return notification

        notification = UserNotification.objects.create(
            recipient=user,
            event=None,
            module=module,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            action_url=action_url or "",
            metadata=dict(metadata),
        )

        logger.info(
            "Notification created: id=%s recipient=%s "
            "module=%s type=%s priority=%s",
            notification.pk,
            getattr(user, "pk", None),
            module,
            notification_type,
            priority,
        )

        return notification

    # ========================================================================
    # AUTHORITATIVE PUSH CREATION
    # ========================================================================

    @classmethod
    def create_push_deliveries(
        cls,
        notification: UserNotification,
    ) -> list[NotificationPush]:
        """
        Create NotificationPush records for every eligible device.

        This is the sole authoritative implementation for push-record
        creation.

        Existing PENDING records are returned for dispatch.

        Existing PROCESSING, SENT, FAILED, or SKIPPED records are not
        re-enqueued by this method.
        """

        if notification is None:
            raise NotificationServiceError(
                "UserNotification is required."
            )

        if not notification.pk:
            raise NotificationServiceError(
                "UserNotification must be persisted."
            )

        devices = cls._get_eligible_devices(
            user=notification.recipient,
        )

        if not devices:
            logger.info(
                "No eligible push devices: "
                "notification=%s user=%s",
                notification.pk,
                notification.recipient_id,
            )

            return []

        deliveries: list[NotificationPush] = []

        for device in devices:

            provider = cls._normalize_provider(
                getattr(
                    device,
                    "provider",
                    None,
                )
            )

            if not provider:
                logger.warning(
                    "Skipping push device without provider: "
                    "notification=%s device=%s",
                    notification.pk,
                    getattr(device, "pk", None),
                )
                continue

            push, created = NotificationPush.objects.get_or_create(
                notification=notification,
                device=device,
                defaults={
                    "provider": provider,
                    "status": NotificationPush.PushStatus.PENDING,
                },
            )

            if created:
                deliveries.append(push)
                continue

            if (
                push.status
                == NotificationPush.PushStatus.PENDING
            ):
                deliveries.append(push)

        logger.debug(
            "Push deliveries prepared: "
            "notification=%s count=%s",
            notification.pk,
            len(deliveries),
        )

        return deliveries

    # ========================================================================
    # AUTHORITATIVE PUSH DELIVERY
    # ========================================================================

    @classmethod
    def send_to_device(
        cls,
        push: NotificationPush,
    ) -> NotificationPush:
        """
        Deliver one NotificationPush.

        Lifecycle:

            PENDING
                │
                │ atomic claim
                ▼
            PROCESSING
                │
                │ provider request
                │
                ├────────► SENT
                │
                └────────► FAILED

        The PENDING -> PROCESSING transaction is intentionally short.

        Provider communication occurs only after the claim transaction has
        committed.
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted before delivery."
            )

        push.refresh_from_db()

        # --------------------------------------------------------------------
        # TERMINAL STATES
        # --------------------------------------------------------------------

        if push.status == NotificationPush.PushStatus.SENT:
            return push

        if push.status == NotificationPush.PushStatus.SKIPPED:
            return push

        # --------------------------------------------------------------------
        # DEVICE
        # --------------------------------------------------------------------

        device = getattr(
            push,
            "device",
            None,
        )

        if device is None:
            return cls.mark_push_failed(
                push,
                "Notification device does not exist.",
                permanent=True,
            )

        # --------------------------------------------------------------------
        # DEVICE ACTIVE STATE
        # --------------------------------------------------------------------

        if not getattr(
            device,
            "is_active",
            False,
        ):
            return cls.mark_push_failed(
                push,
                "Notification device is inactive.",
                permanent=True,
            )

        # --------------------------------------------------------------------
        # DEVICE NOTIFICATION PREFERENCE
        # --------------------------------------------------------------------

        if not getattr(
            device,
            "notifications_enabled",
            False,
        ):
            return cls.mark_push_failed(
                push,
                "Notifications are disabled for this device.",
                permanent=True,
            )

        # --------------------------------------------------------------------
        # DEVICE TOKEN
        # --------------------------------------------------------------------

        device_token = getattr(
            device,
            "device_token",
            None,
        )

        if not device_token:
            return cls.mark_push_failed(
                push,
                "Notification device has no device token.",
                permanent=True,
            )

        # --------------------------------------------------------------------
        # PROVIDER
        # --------------------------------------------------------------------

        provider = cls._normalize_provider(
            getattr(
                device,
                "provider",
                None,
            )
            or getattr(
                push,
                "provider",
                None,
            )
        )

        if not provider:
            return cls.mark_push_failed(
                push,
                "Notification device has no provider.",
                permanent=True,
            )

        # --------------------------------------------------------------------
        # SYNCHRONIZE PROVIDER
        # --------------------------------------------------------------------

        if push.provider != provider:

            push.provider = provider

            push.save(
                update_fields=[
                    "provider",
                    "updated_at",
                ]
            )

        # --------------------------------------------------------------------
        # ATOMIC PROCESSING CLAIM
        # --------------------------------------------------------------------
        #
        # Only the PENDING row can be claimed.
        #
        # The transaction ends before provider communication begins.
        # --------------------------------------------------------------------

        claimed = cls._claim_push_for_processing(
            push
        )

        if claimed is None:

            push.refresh_from_db()

            logger.info(
                "Push delivery was already claimed or completed: "
                "push_id=%s status=%s",
                push.pk,
                push.status,
            )

            return push

        # --------------------------------------------------------------------
        # IMPORTANT
        # --------------------------------------------------------------------
        #
        # From this point forward we deliberately use the authoritative
        # claimed ORM instance returned by _claim_push_for_processing().
        #
        # The claim transaction has already committed.
        #
        # No transaction.atomic() surrounds the provider call.
        # --------------------------------------------------------------------

        push = claimed

        # --------------------------------------------------------------------
        # PROVIDER CALL
        # --------------------------------------------------------------------

        try:

            from ..channels.push import PushChannel

            channel = PushChannel()

            result = channel.send_to_device(
                notification=push.notification,
                device=device,
            )

        except Exception as exc:

            logger.exception(
                "Push delivery exception: "
                "push_id=%s provider=%s device=%s",
                push.pk,
                provider,
                getattr(
                    device,
                    "pk",
                    None,
                ),
            )

            return cls.mark_push_failed(
                push,
                str(exc),
                permanent=False,
            )

        # --------------------------------------------------------------------
        # PROVIDER RESPONSE VALIDATION
        # --------------------------------------------------------------------

        if not isinstance(
            result,
            Mapping,
        ):

            return cls.mark_push_failed(
                push,
                "Push channel returned an invalid response.",
                permanent=False,
            )

        # --------------------------------------------------------------------
        # PROVIDER RESULT
        # --------------------------------------------------------------------

        result_provider = cls._normalize_provider(
            result.get("provider")
            or provider
        )

        provider_message_id = result.get(
            "provider_message_id"
        )

        if result.get("success"):

            return cls._mark_push_sent(
                push,
                provider=result_provider or provider,
                provider_message_id=provider_message_id,
            )

        # --------------------------------------------------------------------
        # PROVIDER FAILURE
        # --------------------------------------------------------------------

        error = (
            result.get("error")
            or result.get("message")
            or "Push provider rejected the notification."
        )

        permanent = bool(
            result.get(
                "permanent",
                False,
            )
        )

        return cls.mark_push_failed(
            push,
            str(error),
            permanent=permanent,
        )

    # ========================================================================
    # ATOMIC PUSH CLAIM
    # ========================================================================

    @staticmethod
    def _claim_push_for_processing(
        push: NotificationPush,
    ) -> NotificationPush | None:
        """
        Atomically claim a PENDING NotificationPush.

        Concurrency contract:

            PENDING -> PROCESSING

        Only one worker can successfully perform this transition.

        The database transaction contains only the state transition.

        Provider communication MUST happen after the transaction commits.
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted."
            )

        with transaction.atomic():

            claimed = (
                NotificationPush.objects
                .select_for_update()
                .filter(
                    pk=push.pk,
                    status=NotificationPush.PushStatus.PENDING,
                )
                .first()
            )

            if claimed is None:
                return None

            claimed.status = (
                NotificationPush.PushStatus.PROCESSING
            )

            claimed.processing_started_at = timezone.now()
            claimed.error_message = ""

            claimed.save(
                update_fields=[
                    "status",
                    "processing_started_at",
                    "error_message",
                    "updated_at",
                ]
            )

        logger.info(
            "NotificationPush claimed for processing: "
            "push_id=%s",
            claimed.pk,
        )

        return claimed

    @staticmethod
    def claim_push_for_processing(
        push_id: int,
    ) -> NotificationPush | None:
        """
        Public ID-based compatibility API for atomic push claiming.

        This method performs no provider communication.
        """

        if not push_id:
            raise NotificationServiceError(
                "NotificationPush ID is required."
            )

        try:

            push = (
                NotificationPush.objects
                .select_related(
                    "notification",
                    "notification__recipient",
                    "notification__event",
                    "device",
                    "device__user",
                )
                .get(
                    pk=push_id
                )
            )

        except NotificationPush.DoesNotExist:

            logger.warning(
                "NotificationPush does not exist: push_id=%s",
                push_id,
            )

            return None

        return NotificationService._claim_push_for_processing(
            push
        )

    # ========================================================================
    # AUTHORITATIVE PUSH FAILURE
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def mark_push_failed(
        push: NotificationPush,
        error_message: str,
        *,
        permanent: bool = False,
    ) -> NotificationPush:
        """
        Mark a push delivery as FAILED.

        This method owns only database state transitions.

        It never performs provider HTTP communication.

        A permanent failure may deactivate the associated device.

        A transient failure may record a device-level error through the
        device's set_error() API when available.
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted."
            )

        error = str(
            error_message
            or "Unknown push delivery failure."
        )[:10000]

        push.status = NotificationPush.PushStatus.FAILED
        push.error_message = error
        push.processing_started_at = None

        push.save(
            update_fields=[
                "status",
                "error_message",
                "processing_started_at",
                "updated_at",
            ]
        )

        device = getattr(
            push,
            "device",
            None,
        )

        if device is not None:

            try:

                if permanent:

                    deactivate = getattr(
                        device,
                        "deactivate",
                        None,
                    )

                    if callable(deactivate):

                        deactivate(
                            error
                        )

                    elif hasattr(
                        device,
                        "is_active",
                    ):

                        device.is_active = False

                        device.save(
                            update_fields=[
                                "is_active",
                                "updated_at",
                            ]
                        )

                else:

                    set_error = getattr(
                        device,
                        "set_error",
                        None,
                    )

                    if callable(set_error):
                        set_error(error)

            except Exception:

                logger.exception(
                    "Unable to update device after push failure: "
                    "push_id=%s device=%s",
                    push.pk,
                    getattr(
                        device,
                        "pk",
                        None,
                    ),
                )

        logger.warning(
            "Push delivery failed: "
            "push_id=%s provider=%s permanent=%s error=%s",
            push.pk,
            push.provider,
            permanent,
            error,
        )

        return push

    # ========================================================================
    # AUTHORITATIVE PUSH RETRY RESET
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def reset_push_for_retry(
        push: NotificationPush,
    ) -> NotificationPush:
        """
        Reset a FAILED push to PENDING.

        This method does not enqueue Celery work.

        Celery owns retry scheduling.
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted."
            )

        push.refresh_from_db()

        if (
            push.status
            != NotificationPush.PushStatus.FAILED
        ):
            return push

        push.status = NotificationPush.PushStatus.PENDING
        push.error_message = ""
        push.processing_started_at = None

        push.save(
            update_fields=[
                "status",
                "error_message",
                "processing_started_at",
                "updated_at",
            ]
        )

        logger.info(
            "Push delivery reset for retry: push_id=%s",
            push.pk,
        )

        return push

    # ========================================================================
    # INTERNAL PUSH STATE HELPERS
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def _mark_push_sent(
        push: NotificationPush,
        *,
        provider: str | None = None,
        provider_message_id: str | None = None,
    ) -> NotificationPush:
        """
        Persist the successful push-delivery state transition.
        """

        if push is None:
            raise NotificationServiceError(
                "NotificationPush is required."
            )

        if not push.pk:
            raise NotificationServiceError(
                "NotificationPush must be persisted."
            )

        push.status = NotificationPush.PushStatus.SENT
        push.sent_at = timezone.now()
        push.processing_started_at = None
        push.error_message = ""

        update_fields = [
            "status",
            "sent_at",
            "processing_started_at",
            "error_message",
            "updated_at",
        ]

        if provider:

            normalized_provider = str(
                provider
            ).strip().lower()

            if normalized_provider:

                push.provider = normalized_provider

                update_fields.append(
                    "provider"
                )

        if provider_message_id:

            push.provider_message_id = str(
                provider_message_id
            )

            update_fields.append(
                "provider_message_id"
            )

        push.save(
            update_fields=list(
                dict.fromkeys(
                    update_fields
                )
            )
        )

        logger.info(
            "Push delivery sent: push_id=%s provider=%s",
            push.pk,
            push.provider,
        )

        return push

    # ========================================================================
    # DEVICE LOOKUP
    # ========================================================================

    @staticmethod
    def _get_eligible_devices(
        *,
        user: Any,
    ) -> list[NotificationDevice]:
        """
        Return active devices eligible for push delivery.
        """

        return list(
            NotificationDevice.objects
            .filter(
                user=user,
                is_active=True,
                notifications_enabled=True,
            )
            .exclude(
                device_token=""
            )
            .exclude(
                provider=""
            )
            .order_by(
                "-last_used_at",
                "-created_at",
            )
        )

    @staticmethod
    def _push_available(
        *,
        user: Any,
    ) -> bool:
        """
        Return whether the user currently has a push-capable device.
        """

        try:

            return (
                NotificationDevice.objects
                .filter(
                    user=user,
                    is_active=True,
                    notifications_enabled=True,
                )
                .exclude(
                    device_token=""
                )
                .exclude(
                    provider=""
                )
                .exists()
            )

        except Exception:

            logger.exception(
                "Unable to determine push availability: user=%s",
                getattr(
                    user,
                    "pk",
                    None,
                ),
            )

            return False

    # ========================================================================
    # DISPATCH
    # ========================================================================

    @classmethod
    def _dispatch_after_commit(
        cls,
        *,
        notification_id: int,
        channels: Iterable[str],
        push_ids: Iterable[int],
    ) -> None:
        """
        Schedule channel-specific asynchronous work after commit.

        This method only schedules work.

        It does not perform provider communication or notification delivery
        itself.
        """

        channels = tuple(channels)
        push_ids = tuple(push_ids)

        for channel in channels:

            try:

                if channel == CHANNEL_PUSH:

                    cls._dispatch_push_ids(
                        push_ids
                    )

                elif channel == CHANNEL_EMAIL:

                    cls._dispatch_email(
                        notification_id
                    )

                elif channel == CHANNEL_SMS:

                    cls._dispatch_sms(
                        notification_id
                    )

                elif channel == CHANNEL_WEBSOCKET:

                    cls._dispatch_websocket(
                        notification_id
                    )

                elif channel == CHANNEL_IN_APP:

                    cls._dispatch_in_app(
                        notification_id
                    )

                else:

                    raise InvalidNotificationChannel(
                        channel
                    )

            except Exception:

                logger.exception(
                    "Failed to queue notification: "
                    "notification=%s channel=%s",
                    notification_id,
                    channel,
                )

    @staticmethod
    def _dispatch_push_ids(
        push_ids: Iterable[int],
    ) -> None:
        """
        Schedule push delivery tasks.

        Celery scheduling remains outside the core push-delivery logic.
        """

        from ..tasks.push import deliver_push_notification

        for push_id in push_ids:

            deliver_push_notification.delay(
                push_id
            )

    @staticmethod
    def _dispatch_in_app(
        notification_id: int,
    ) -> None:
        """
        Schedule in-app notification processing when available.
        """

        try:

            from ..tasks.in_app import (
                send_in_app_notification,
            )

        except ImportError:

            logger.debug(
                "In-app notification task is not available."
            )

            return

        send_in_app_notification.delay(
            notification_id=notification_id
        )

    @staticmethod
    def _dispatch_email(
        notification_id: int,
    ) -> None:
        """
        Schedule email notification processing.
        """

        from ..tasks.email import (
            send_email_notification,
        )

        send_email_notification.delay(
            notification_id=notification_id
        )

    @staticmethod
    def _dispatch_sms(
        notification_id: int,
    ) -> None:
        """
        Schedule SMS notification processing.
        """

        from ..tasks.sms import (
            send_sms_notification,
        )

        send_sms_notification.delay(
            notification_id=notification_id
        )

    @staticmethod
    def _dispatch_websocket(
        notification_id: int,
    ) -> None:
        """
        Schedule websocket notification processing.
        """

        from ..tasks.websocket import (
            send_websocket_notification,
        )

        send_websocket_notification.delay(
            notification_id=notification_id
        )

    # ========================================================================
    # PREFERENCES
    # ========================================================================

    @staticmethod
    def _get_preferences(
        user: Any,
    ) -> NotificationPreference:
        """
        Return the user's notification preferences.

        Preferences are created lazily when absent.
        """

        preferences, _ = (
            NotificationPreference.objects.get_or_create(
                user=user
            )
        )

        return preferences

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @staticmethod
    def _validate_user(
        user: Any,
    ) -> None:

        if user is None:

            raise NotificationRecipientError(
                "Notification recipient cannot be None."
            )

        if not getattr(
            user,
            "pk",
            None,
        ):

            raise NotificationRecipientError(
                "Notification recipient must be a persisted user."
            )

    @staticmethod
    def _validate_module(
        module: str,
    ) -> None:

        if not module:

            raise NotificationServiceError(
                "Notification module is required."
            )

        if not isinstance(
            module,
            str,
        ):

            raise NotificationServiceError(
                "Notification module must be a string."
            )

        if len(module) > 50:

            raise NotificationServiceError(
                "Notification module cannot exceed 50 characters."
            )

    @staticmethod
    def _validate_notification_type(
        notification_type: str,
    ) -> None:

        if not notification_type:

            raise InvalidNotificationType(
                "notification_type is required."
            )

        if not isinstance(
            notification_type,
            str,
        ):

            raise InvalidNotificationType(
                "notification_type must be a string."
            )

        valid_types = {
            choice.value
            for choice in UserNotification.NotificationType
        }

        if notification_type not in valid_types:

            raise InvalidNotificationType(
                "Unsupported notification type: "
                f"{notification_type}. Supported types: "
                f"{', '.join(sorted(valid_types))}"
            )

    @staticmethod
    def _validate_priority(
        priority: str,
    ) -> None:

        valid_priorities = {
            choice.value
            for choice in UserNotification.Priority
        }

        if priority not in valid_priorities:

            raise NotificationServiceError(
                "Unsupported notification priority: "
                f"{priority}. Supported priorities: "
                f"{', '.join(sorted(valid_priorities))}"
            )

    @staticmethod
    def _validate_content(
        title: str,
        message: str,
    ) -> None:

        if not title:

            raise NotificationServiceError(
                "Notification title is required."
            )

        if not isinstance(
            title,
            str,
        ):

            raise NotificationServiceError(
                "Notification title must be a string."
            )

        if not message:

            raise NotificationServiceError(
                "Notification message is required."
            )

        if not isinstance(
            message,
            str,
        ):

            raise NotificationServiceError(
                "Notification message must be a string."
            )

    @staticmethod
    def _validate_channels(
        channels: Iterable[str],
    ) -> None:

        channels = list(channels)

        invalid = (
            set(channels)
            - SUPPORTED_CHANNELS
        )

        if invalid:

            raise InvalidNotificationChannel(
                "Unsupported notification channel(s): "
                + ", ".join(
                    sorted(invalid)
                )
            )

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _normalize_provider(
        provider: Any,
    ) -> str:

        if provider is None:
            return ""

        return str(
            provider
        ).strip().lower()

    # ========================================================================
    # PERSISTENCE POLICY
    # ========================================================================

    @classmethod
    def should_persist_without_delivery(
        cls,
        *,
        notification_type: str,
    ) -> bool:
        """
        Return whether a notification type should be persisted even when
        delivery channels are unavailable.
        """

        return notification_type in {
            UserNotification.NotificationType.SYSTEM,
            UserNotification.NotificationType.ERROR,
        }


# ============================================================================
# EVENT COMPATIBILITY API
# ============================================================================
#
# IMPORTANT:
#
# These functions remain for compatibility with existing event-processing
# callers.
#
# They do NOT make NotificationService responsible for event processing.
#
# Recipient resolution and notification construction are exposed as small
# compatibility helpers because NotificationEventProcessor currently uses
# them.
#
# Event state transitions remain owned by NotificationEventProcessor and
# NotificationEvent itself.
# ============================================================================


'''def resolve_recipients(
    event: NotificationEvent,
) -> list[Any]:
    """
    Resolve persisted users associated with a NotificationEvent.

    Supported sources:

        event.recipient
        event.recipient_id
        payload["recipient_id"]
        payload["recipient_ids"]
        payload["user_id"]
        payload["user_ids"]
        event.actor

    This helper performs recipient resolution only.

    It does not create notifications or modify event state.
    """

    if not isinstance(
        event,
        NotificationEvent,
    ):

        raise ValueError(
            "resolve_recipients requires a NotificationEvent."
        )

    from accounts.models import User

    recipients: list[Any] = []

    # ------------------------------------------------------------------------
    # Explicit event recipient
    # ------------------------------------------------------------------------

    recipient = getattr(
        event,
        "recipient",
        None,
    )

    if recipient is not None:
        recipients.append(recipient)

    # ------------------------------------------------------------------------
    # Explicit recipient ID
    # ------------------------------------------------------------------------

    recipient_id = getattr(
        event,
        "recipient_id",
        None,
    )

    if recipient_id:

        user = (
            User.objects
            .filter(
                pk=recipient_id
            )
            .first()
        )

        if user is not None:
            recipients.append(user)

    # ------------------------------------------------------------------------
    # Payload recipients
    # ------------------------------------------------------------------------

    payload = event.payload or {}

    if not isinstance(
        payload,
        Mapping,
    ):
        payload = {}

    single_ids = [
        payload.get("recipient_id"),
        payload.get("user_id"),
    ]

    multiple_ids: list[Any] = []

    for key in (
        "recipient_ids",
        "user_ids",
    ):

        value = payload.get(key)

        if isinstance(
            value,
            (list, tuple, set),
        ):

            multiple_ids.extend(
                value
            )

    for user_id in (
        single_ids + multiple_ids
    ):

        if not user_id:
            continue

        user = (
            User.objects
            .filter(
                pk=user_id
            )
            .first()
        )

        if user is not None:
            recipients.append(user)

    # ------------------------------------------------------------------------
    # Actor fallback
    # ------------------------------------------------------------------------

    if not recipients:

        actor = getattr(
            event,
            "actor",
            None,
        )

        if (
            actor is not None
            and getattr(
                actor,
                "pk",
                None,
            )
        ):

            recipients.append(actor)

    # ------------------------------------------------------------------------
    # Deduplicate by persisted user ID
    # ------------------------------------------------------------------------

    unique: list[Any] = []
    seen: set[int] = set()

    for user in recipients:

        user_id = getattr(
            user,
            "pk",
            None,
        )

        if not user_id:
            continue

        try:
            normalized_user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if normalized_user_id in seen:
            continue

        seen.add(
            normalized_user_id
        )

        unique.append(user)

    return unique'''

def resolve_recipients(
    event: NotificationEvent,
) -> list[Any]:
    """
    Resolve persisted users associated with a NotificationEvent.

    Supported sources:

        event.recipient
        event.recipient_id
        payload["recipient_id"]
        payload["recipient_ids"]
        payload["user_id"]
        payload["user_ids"]
        event.actor

    Magic link events (ACCOUNT_MAGIC_LINK_REQUESTED) always resolve to
    the actor, bypassing other payload sources for security.

    This helper performs recipient resolution only.

    It does not create notifications or modify event state.
    """

    if not isinstance(
        event,
        NotificationEvent,
    ):

        raise ValueError(
            "resolve_recipients requires a NotificationEvent."
        )

    from accounts.models import User
    from notifications.events.constants import ACCOUNT_MAGIC_LINK_REQUESTED

    recipients: list[Any] = []

    # ------------------------------------------------------------------------
    # Magic link events always go to the actor
    # ------------------------------------------------------------------------
    #
    # Magic link events should only ever be sent to the user who requested
    # the link. This prevents a malicious payload from redirecting the
    # magic link to another user.
    #
    # The actor is set by the mutation when the event is emitted, so it
    # is the authoritative source for the recipient.
    # ------------------------------------------------------------------------

    if event.event_type == ACCOUNT_MAGIC_LINK_REQUESTED:
        actor = getattr(event, "actor", None)
        if actor and getattr(actor, "pk", None):
            return [actor]

    # ------------------------------------------------------------------------
    # Explicit event recipient
    # ------------------------------------------------------------------------

    recipient = getattr(
        event,
        "recipient",
        None,
    )

    if recipient is not None:
        recipients.append(recipient)

    # ------------------------------------------------------------------------
    # Explicit recipient ID
    # ------------------------------------------------------------------------

    recipient_id = getattr(
        event,
        "recipient_id",
        None,
    )

    if recipient_id:

        user = (
            User.objects
            .filter(
                pk=recipient_id
            )
            .first()
        )

        if user is not None:
            recipients.append(user)

    # ------------------------------------------------------------------------
    # Payload recipients
    # ------------------------------------------------------------------------

    payload = event.payload or {}

    if not isinstance(
        payload,
        Mapping,
    ):
        payload = {}

    single_ids = [
        payload.get("recipient_id"),
        payload.get("user_id"),
    ]

    multiple_ids: list[Any] = []

    for key in (
        "recipient_ids",
        "user_ids",
    ):

        value = payload.get(key)

        if isinstance(
            value,
            (list, tuple, set),
        ):

            multiple_ids.extend(
                value
            )

    for user_id in (
        single_ids + multiple_ids
    ):

        if not user_id:
            continue

        user = (
            User.objects
            .filter(
                pk=user_id
            )
            .first()
        )

        if user is not None:
            recipients.append(user)

    # ------------------------------------------------------------------------
    # Actor fallback
    # ------------------------------------------------------------------------

    if not recipients:

        actor = getattr(
            event,
            "actor",
            None,
        )

        if (
            actor is not None
            and getattr(
                actor,
                "pk",
                None,
            )
        ):

            recipients.append(actor)

    # ------------------------------------------------------------------------
    # Deduplicate by persisted user ID
    # ------------------------------------------------------------------------

    unique: list[Any] = []
    seen: set[int] = set()

    for user in recipients:

        user_id = getattr(
            user,
            "pk",
            None,
        )

        if not user_id:
            continue

        try:
            normalized_user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if normalized_user_id in seen:
            continue

        seen.add(
            normalized_user_id
        )

        unique.append(user)

    return unique

'''def create_user_notification(
    *,
    event: NotificationEvent,
    recipient: Any,
) -> UserNotification | None:
    """
    Compatibility API used by NotificationEventProcessor.

    Notification construction ultimately delegates to:

        NotificationService.notify()

    This helper does not process the event or modify event state.
    """

    if event is None:

        raise NotificationServiceError(
            "Notification event is required."
        )

    if recipient is None:
        return None

    payload = event.payload or {}

    if not isinstance(
        payload,
        Mapping,
    ):
        payload = {}

    module = (
        getattr(
            event,
            "module",
            None,
        )
        or payload.get("module")
        or "system"
    )

    notification_type = (
        payload.get("notification_type")
        or payload.get("type")
        or UserNotification.NotificationType.INFO
    )

    title = (
        payload.get("title")
        or payload.get("notification_title")
        or getattr(
            event,
            "event_type",
            None,
        )
        or "Notification"
    )

    message = (
        payload.get("message")
        or payload.get("body")
        or payload.get("notification_message")
        or (
            f"Notification event: "
            f"{getattr(event, 'event_type', 'unknown')}"
        )
    )

    priority = (
        payload.get("priority")
        or UserNotification.Priority.NORMAL
    )

    action_url = (
        payload.get("action_url")
        or ""
    )

    metadata = dict(
        payload
    )

    metadata.setdefault(
        "event_type",
        getattr(
            event,
            "event_type",
            None,
        ),
    )

    metadata.setdefault(
        "event_id",
        event.pk,
    )

    return NotificationService.notify(
        user=recipient,
        module=str(module),
        notification_type=str(notification_type),
        title=str(title),
        message=str(message),
        metadata=metadata,
        action_url=str(action_url),
        priority=str(priority),
        event=event,
        dispatch=True,
    )'''


def create_user_notification(
    *,
    event: NotificationEvent,
    recipient: Any,
) -> UserNotification | None:
    """
    Compatibility API used by NotificationEventProcessor.

    Notification construction ultimately delegates to:

        NotificationService.notify()

    The event registry supplies the default notification presentation.
    Event payload values may override those defaults when explicitly
    provided.

    This helper does not process the event or modify event state.
    """

    if event is None:
        raise NotificationServiceError(
            "Notification event is required."
        )

    if recipient is None:
        return None

    payload = event.payload or {}

    if not isinstance(
        payload,
        Mapping,
    ):
        payload = {}

    # ------------------------------------------------------------------------
    # Resolve registered event definition
    # ------------------------------------------------------------------------

    definition = get_event_definition(
        event.event_type,
    )

    if definition is None:
        raise NotificationServiceError(
            f"Unregistered notification event: {event.event_type}"
        )

    # ------------------------------------------------------------------------
    # Notification identity
    # ------------------------------------------------------------------------

    module = (
        getattr(
            event,
            "module",
            None,
        )
        or definition.category
        or "system"
    )

    notification_type = (
        payload.get("notification_type")
        or payload.get("type")
        or UserNotification.NotificationType.INFO
    )

    # ------------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------------

    title = (
        payload.get("title")
        or payload.get("notification_title")
        or definition.title
    )

    message = (
        payload.get("message")
        or payload.get("body")
        or payload.get("notification_message")
        or definition.body
    )

    priority = (
        payload.get("priority")
        or definition.priority
        or UserNotification.Priority.NORMAL
    )

    # ------------------------------------------------------------------------
    # Action URL
    # ------------------------------------------------------------------------

    action_url = (
        payload.get("action_url")
        or definition.action_url
        or ""
    )

    if action_url:
        action_url = action_url.format(
            object_id=getattr(
                event,
                "object_id",
                "",
            ),
            event_id=event.pk,
        )

    # ------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------

    metadata = dict(
        payload
    )

    metadata.setdefault(
        "event_type",
        getattr(
            event,
            "event_type",
            None,
        ),
    )

    metadata.setdefault(
        "event_id",
        event.pk,
    )

    # ------------------------------------------------------------------------
    # Notification construction
    # ------------------------------------------------------------------------

    return NotificationService.notify(
        user=recipient,
        module=str(module),
        notification_type=str(notification_type),
        title=str(title),
        message=str(message),
        metadata=metadata,
        action_url=str(action_url),
        priority=str(priority),
        channels=definition.channels,
        event=event,
        dispatch=True,
    )


# ============================================================================
# MODULE-LEVEL PUSH API
# ============================================================================
#
# These functions are intentionally thin compatibility aliases.
#
# There is no second implementation here.
#
# The authoritative implementations live on NotificationService.
# ============================================================================


def create_push_deliveries(
    notification: UserNotification,
) -> list[NotificationPush]:
    """
    Compatibility alias for NotificationService.create_push_deliveries().
    """

    return NotificationService.create_push_deliveries(
        notification
    )


def send_to_device(
    push: NotificationPush,
) -> NotificationPush:
    """
    Compatibility alias for NotificationService.send_to_device().
    """

    return NotificationService.send_to_device(
        push
    )


def mark_push_failed(
    push: NotificationPush,
    error_message: str,
    *,
    permanent: bool = False,
) -> NotificationPush:
    """
    Compatibility alias for NotificationService.mark_push_failed().
    """

    return NotificationService.mark_push_failed(
        push,
        error_message,
        permanent=permanent,
    )


def reset_push_for_retry(
    push: NotificationPush,
) -> NotificationPush:
    """
    Compatibility alias for NotificationService.reset_push_for_retry().
    """

    return NotificationService.reset_push_for_retry(
        push
    )


def mark_push_sent(
    push: NotificationPush,
    *,
    provider: str | None = None,
    provider_message_id: str | None = None,
) -> NotificationPush:
    """
    Compatibility alias for successful push-delivery state transition.

    The authoritative implementation remains:

        NotificationService._mark_push_sent()
    """

    return NotificationService._mark_push_sent(
        push,
        provider=provider,
        provider_message_id=provider_message_id,
    )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Channels
    "CHANNEL_IN_APP",
    "CHANNEL_PUSH",
    "CHANNEL_EMAIL",
    "CHANNEL_SMS",
    "CHANNEL_WEBSOCKET",
    "SUPPORTED_CHANNELS",
    "DEFAULT_CHANNELS",

    # Service
    "NotificationService",

    # Exceptions
    "NotificationServiceError",
    "InvalidNotificationChannel",
    "InvalidNotificationType",
    "NotificationRecipientError",

    # Event compatibility
    "resolve_recipients",
    "create_user_notification",

    # Push API
    "create_push_deliveries",
    "send_to_device",
    "mark_push_failed",
    "reset_push_for_retry",
    "mark_push_sent",
]

