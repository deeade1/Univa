"""
Tests for notifications.services.notification_service.

Coverage:

    - notification creation
    - metadata and action URLs
    - default channel resolution
    - explicit channel resolution
    - notification preferences
    - category filtering
    - quiet hours
    - device eligibility
    - push delivery creation
    - push delivery idempotency
    - event/recipient idempotency
    - Celery dispatch
    - push state transitions
    - permanent device failure handling
    - retry/reset behavior
    - validation
    - persistence policy
    - module-level helper functions
"""

from __future__ import annotations

from datetime import time
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.models import User

from notifications.models import (
    NotificationDevice,
    NotificationEvent,
    NotificationPreference,
    NotificationPush,
    UserNotification,
)

from notifications.services.notification_service import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_PUSH,
    CHANNEL_SMS,
    CHANNEL_WEBSOCKET,
    DEFAULT_CHANNELS,
    InvalidNotificationChannel,
    InvalidNotificationType,
    NotificationRecipientError,
    NotificationService,
    NotificationServiceError,
    SUPPORTED_CHANNELS,
    mark_push_failed,
    mark_push_sent,
    reset_push_for_retry,
)


import threading

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone


# ============================================================================
# BASE TEST CASE
# ============================================================================


class NotificationServiceTestCase(TestCase):
    """Shared fixtures for NotificationService tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="notification-user@example.com",
            password="test-password",
        )

        self.preference = NotificationPreference.objects.create(
            user=self.user,
        )

    # ------------------------------------------------------------------------
    # DEVICE FACTORY
    # ------------------------------------------------------------------------

    def create_device(
        self,
        *,
        token="ExponentPushToken[test-token]",
        provider=NotificationDevice.Provider.EXPO,
        platform=NotificationDevice.Platform.ANDROID,
        active=True,
        enabled=True,
        device_id="device-001",
    ):
        return NotificationDevice.objects.create(
            user=self.user,
            platform=platform,
            provider=provider,
            device_token=token,
            device_id=device_id,
            is_active=active,
            notifications_enabled=enabled,
        )

    # ------------------------------------------------------------------------
    # NOTIFICATION FACTORY
    # ------------------------------------------------------------------------

    def create_notification(
        self,
        *,
        notification_type=UserNotification.NotificationType.INFO,
        priority=UserNotification.Priority.NORMAL,
        event=None,
    ):
        return UserNotification.objects.create(
            recipient=self.user,
            event=event,
            module="system",
            notification_type=notification_type,
            priority=priority,
            title="Test notification",
            message="Test notification message",
            metadata={"test": True},
        )

    # ------------------------------------------------------------------------
    # PUSH FACTORY
    # ------------------------------------------------------------------------

    def create_push(
        self,
        *,
        notification=None,
        device=None,
        status=NotificationPush.PushStatus.PENDING,
        provider=None,
    ):
        if notification is None:
            notification = self.create_notification()

        if device is None:
            device = self.create_device()

        if provider is None:
            provider = device.provider

        return NotificationPush.objects.create(
            notification=notification,
            device=device,
            provider=provider,
            status=status,
        )

    # ------------------------------------------------------------------------
    # EVENT FACTORY
    # ------------------------------------------------------------------------

    def create_event(
        self,
        *,
        event_type="order.created",
        module="order",
        actor=None,
        object_type="Order",
        object_id="123",
        payload=None,
    ):
        return NotificationEvent.objects.create(
            event_type=event_type,
            module=module,
            actor=actor,
            object_type=object_type,
            object_id=object_id,
            payload=payload or {"order_id": 123},
        )


# ============================================================================
# NOTIFY
# ============================================================================


class NotificationServiceNotifyTest(NotificationServiceTestCase):
    """Tests for NotificationService.notify()."""

    def test_notify_creates_notification(self):
        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="New trip",
            message="You have a new trip assignment.",
            dispatch=False,
        )

        self.assertIsNotNone(notification.pk)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.module, "transport")

        self.assertEqual(
            notification.notification_type,
            UserNotification.NotificationType.INFO,
        )

        self.assertEqual(
            notification.title,
            "New trip",
        )

        self.assertEqual(
            notification.message,
            "You have a new trip assignment.",
        )

    def test_notify_persists_metadata_and_action_url(self):
        notification = NotificationService.notify(
            user=self.user,
            module="order",
            notification_type="success",
            title="Order completed",
            message="Your order has been completed.",
            metadata={
                "order_id": 123,
                "source": "checkout",
            },
            action_url="/orders/123",
            dispatch=False,
        )

        self.assertEqual(
            notification.metadata,
            {
                "order_id": 123,
                "source": "checkout",
            },
        )

        self.assertEqual(
            notification.action_url,
            "/orders/123",
        )

    def test_notify_creates_push_deliveries_for_eligible_devices(self):
        device_one = self.create_device(
            token="ExponentPushToken[one]",
            device_id="device-one",
        )

        device_two = self.create_device(
            token="ExponentPushToken[two]",
            device_id="device-two",
        )

        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned to you.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        pushes = NotificationPush.objects.filter(
            notification=notification,
        )

        self.assertEqual(
            pushes.count(),
            2,
        )

        self.assertSetEqual(
            set(
                pushes.values_list(
                    "device_id",
                    flat=True,
                )
            ),
            {
                device_one.pk,
                device_two.pk,
            },
        )

        self.assertTrue(
            all(
                push.status == NotificationPush.PushStatus.PENDING
                for push in pushes
            )
        )

    def test_notify_ignores_inactive_device(self):
        active_device = self.create_device(
            token="ExponentPushToken[active]",
            device_id="active",
            active=True,
        )

        self.create_device(
            token="ExponentPushToken[inactive]",
            device_id="inactive",
            active=False,
        )

        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        pushes = NotificationPush.objects.filter(
            notification=notification,
        )

        self.assertEqual(
            pushes.count(),
            1,
        )

        push = pushes.first()

        self.assertIsNotNone(push)

        self.assertEqual(
            push.device_id,
            active_device.pk,
        )

        push.device.refresh_from_db()

        self.assertEqual(
            push.device.device_id,
            active_device.device_id,
        )

    def test_notify_ignores_disabled_device(self):
        self.create_device(
            token="ExponentPushToken[disabled]",
            device_id="disabled",
            enabled=False,
        )

        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        self.assertFalse(
            NotificationPush.objects.filter(
                notification=notification,
            ).exists()
        )

    def test_notify_ignores_device_without_token(self):
        NotificationDevice.objects.create(
            user=self.user,
            platform=NotificationDevice.Platform.ANDROID,
            provider=NotificationDevice.Provider.EXPO,
            device_token="",
            device_id="empty-token",
        )

        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        self.assertFalse(
            NotificationPush.objects.filter(
                notification=notification,
            ).exists()
        )

    def test_notify_ignores_device_without_provider(self):
        NotificationDevice.objects.create(
            user=self.user,
            platform=NotificationDevice.Platform.ANDROID,
            provider="",
            device_token="valid-token",
            device_id="no-provider",
        )

        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        self.assertFalse(
            NotificationPush.objects.filter(
                notification=notification,
            ).exists()
        )

    def test_notification_is_persisted_without_eligible_devices(self):
        notification = NotificationService.notify(
            user=self.user,
            module="transport",
            notification_type="info",
            title="Trip assigned",
            message="A trip was assigned.",
            channels=[CHANNEL_PUSH],
            dispatch=False,
        )

        self.assertTrue(
            UserNotification.objects.filter(
                pk=notification.pk,
            ).exists()
        )

        self.assertFalse(
            NotificationPush.objects.filter(
                notification=notification,
            ).exists()
        )


# ============================================================================
# CHANNEL RESOLUTION
# ============================================================================


class NotificationServiceChannelResolutionTest(
    NotificationServiceTestCase
):
    """Tests channel preference resolution."""

    def test_default_channels_are_in_app_and_push(self):
        self.create_device()

        channels = NotificationService.resolve_channels(
            user=self.user,
            module="order",
        )

        self.assertEqual(
            channels,
            list(DEFAULT_CHANNELS),
        )

    def test_push_removed_when_push_disabled(self):
        self.create_device()

        self.preference.push_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            module="order",
        )

        self.assertIn(
            CHANNEL_IN_APP,
            channels,
        )

        self.assertNotIn(
            CHANNEL_PUSH,
            channels,
        )

    def test_in_app_removed_when_in_app_disabled(self):
        self.preference.in_app_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_email_requires_user_email(self):
        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_EMAIL],
            module="order",
        )

        self.assertEqual(
            channels,
            [CHANNEL_EMAIL],
        )

    def test_sms_is_never_enabled(self):
        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_SMS],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_websocket_can_be_enabled(self):
        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_WEBSOCKET],
            module="order",
        )

        self.assertEqual(
            channels,
            [CHANNEL_WEBSOCKET],
        )

    def test_unknown_channel_raises_error(self):
        with self.assertRaises(
            InvalidNotificationChannel
        ):
            NotificationService.resolve_channels(
                user=self.user,
                requested_channels=["unknown"],
                module="order",
            )

    def test_supported_channels_are_correct(self):
        self.assertSetEqual(
            set(SUPPORTED_CHANNELS),
            {
                CHANNEL_IN_APP,
                CHANNEL_PUSH,
                CHANNEL_EMAIL,
                CHANNEL_SMS,
                CHANNEL_WEBSOCKET,
            },
        )


# ============================================================================
# PREFERENCE RESOLUTION
# ============================================================================


class NotificationServicePreferenceTest(
    NotificationServiceTestCase
):
    """Tests preference behavior."""

    def test_preferences_are_created_when_missing(self):
        self.preference.delete()

        preferences = NotificationService._get_preferences(
            self.user,
        )

        self.assertEqual(
            preferences.user,
            self.user,
        )

        self.assertEqual(
            NotificationPreference.objects.filter(
                user=self.user,
            ).count(),
            1,
        )

    def test_global_disable_blocks_channels(self):
        self.preference.disable_all()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[
                CHANNEL_IN_APP,
                CHANNEL_PUSH,
                CHANNEL_EMAIL,
                CHANNEL_WEBSOCKET,
            ],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_security_category_respects_security_preference(self):
        self.preference.security_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="account",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_social_category_respects_social_preference(self):
        self.preference.social_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="social",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_marketing_category_respects_marketing_preference(self):
        self.preference.marketing_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="marketing",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_transactional_category_respects_transactional_preference(
        self,
    ):
        self.preference.transactional_enabled = False
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_daily_frequency_blocks_instant_delivery(self):
        self.preference.frequency = (
            NotificationPreference.Frequency.DAILY
        )
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_weekly_frequency_blocks_instant_delivery(self):
        self.preference.frequency = (
            NotificationPreference.Frequency.WEEKLY
        )
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )

    def test_quiet_hours_block_delivery(self):
        self.preference.quiet_hours_enabled = True
        self.preference.quiet_hours_start = time(0, 0)
        self.preference.quiet_hours_end = time(23, 59)
        self.preference.save()

        channels = NotificationService.resolve_channels(
            user=self.user,
            requested_channels=[CHANNEL_IN_APP],
            module="order",
        )

        self.assertEqual(
            channels,
            [],
        )


# ============================================================================
# PUSH AVAILABILITY
# ============================================================================


class NotificationServicePushAvailabilityTest(
    NotificationServiceTestCase
):
    """Tests push device availability."""

    def test_push_available_when_eligible_device_exists(self):
        self.create_device()

        self.assertTrue(
            NotificationService._push_available(
                user=self.user,
            )
        )

    def test_push_unavailable_without_devices(self):
        self.assertFalse(
            NotificationService._push_available(
                user=self.user,
            )
        )

    def test_push_unavailable_for_inactive_device(self):
        self.create_device(
            active=False,
        )

        self.assertFalse(
            NotificationService._push_available(
                user=self.user,
            )
        )

    def test_push_unavailable_for_disabled_device(self):
        self.create_device(
            enabled=False,
        )

        self.assertFalse(
            NotificationService._push_available(
                user=self.user,
            )
        )


# ============================================================================
# EVENT IDEMPOTENCY
# ============================================================================


class NotificationServiceEventIdempotencyTest(
    NotificationServiceTestCase
):
    """Tests event/recipient idempotency."""

    def test_same_event_and_recipient_reuse_notification(self):
        event = self.create_event()

        first = NotificationService.notify(
            user=self.user,
            module="order",
            notification_type="info",
            title="Order created",
            message="Your order was created.",
            event=event,
            channels=[],
            dispatch=False,
        )

        second = NotificationService.notify(
            user=self.user,
            module="order",
            notification_type="success",
            title="Different title",
            message="Different message.",
            event=event,
            channels=[],
            dispatch=False,
        )

        self.assertEqual(
            first.pk,
            second.pk,
        )

        self.assertEqual(
            UserNotification.objects.filter(
                event=event,
                recipient=self.user,
            ).count(),
            1,
        )

    def test_same_event_can_notify_different_users(self):
        other_user = User.objects.create_user(
            email="other-user@example.com",
            password="test-password",
        )

        event = self.create_event()

        first = NotificationService.notify(
            user=self.user,
            module="order",
            notification_type="info",
            title="Order update",
            message="Order updated.",
            event=event,
            channels=[],
            dispatch=False,
        )

        second = NotificationService.notify(
            user=other_user,
            module="order",
            notification_type="info",
            title="Order update",
            message="Order updated.",
            event=event,
            channels=[],
            dispatch=False,
        )

        self.assertNotEqual(
            first.pk,
            second.pk,
        )

        self.assertEqual(
            UserNotification.objects.filter(
                event=event,
            ).count(),
            2,
        )


# ============================================================================
# PUSH DELIVERY CREATION
# ============================================================================


class NotificationServicePushDeliveryTest(
    NotificationServiceTestCase
):
    """Tests NotificationPush creation."""

    def test_create_push_deliveries_returns_pending_records(self):
        device = self.create_device()

        notification = self.create_notification()

        deliveries = NotificationService._create_push_deliveries(
            notification=notification,
        )

        self.assertEqual(
            len(deliveries),
            1,
        )

        push = deliveries[0]

        self.assertEqual(
            push.notification,
            notification,
        )

        self.assertEqual(
            push.device,
            device,
        )

        self.assertEqual(
            push.provider,
            device.provider,
        )

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.PENDING,
        )

    def test_create_push_deliveries_is_idempotent(self):
        self.create_device()

        notification = self.create_notification()

        first = NotificationService._create_push_deliveries(
            notification=notification,
        )

        second = NotificationService._create_push_deliveries(
            notification=notification,
        )

        self.assertEqual(
            len(first),
            1,
        )

        self.assertEqual(
            len(second),
            1,
        )

        self.assertEqual(
            first[0].pk,
            second[0].pk,
        )

        self.assertEqual(
            NotificationPush.objects.filter(
                notification=notification,
            ).count(),
            1,
        )

    def test_finished_push_is_not_returned_for_redelivery(self):
        device = self.create_device()

        notification = self.create_notification()

        push = NotificationPush.objects.create(
            notification=notification,
            device=device,
            provider=device.provider,
            status=NotificationPush.PushStatus.SENT,
        )

        deliveries = NotificationService._create_push_deliveries(
            notification=notification,
        )

        self.assertEqual(
            deliveries,
            [],
        )

        push.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.SENT,
        )


# ============================================================================
# DISPATCH
# ============================================================================


class NotificationServiceDispatchTest(
    NotificationServiceTestCase
):
    """Tests post-commit task dispatch."""

    def test_push_dispatch_queues_each_push(self):
        push_one = self.create_push()

        device_two = self.create_device(
            token="ExponentPushToken[two]",
            device_id="two",
        )

        push_two = self.create_push(
            notification=push_one.notification,
            device=device_two,
        )

        mock_task = MagicMock()

        with patch(
            "notifications.tasks.push.deliver_push_notification",
            mock_task,
        ):
            NotificationService._dispatch_push_ids(
                [
                    push_one.pk,
                    push_two.pk,
                ]
            )

        self.assertEqual(
            mock_task.delay.call_count,
            2,
        )

        mock_task.delay.assert_any_call(
            push_one.pk,
        )

        mock_task.delay.assert_any_call(
            push_two.pk,
        )

    def test_in_app_dispatch_queues_task(self):
        mock_task = MagicMock()

        with patch(
            "notifications.tasks.in_app.send_in_app_notification",
            mock_task,
        ):
            NotificationService._dispatch_in_app(
                notification_id=123,
            )

        mock_task.delay.assert_called_once_with(
            notification_id=123,
        )

    def test_email_dispatch_queues_task(self):
        mock_task = MagicMock()

        with patch(
            "notifications.tasks.email.send_email_notification",
            mock_task,
        ):
            NotificationService._dispatch_email(
                notification_id=123,
            )

        mock_task.delay.assert_called_once_with(
            notification_id=123,
        )

    def test_sms_dispatch_queues_task(self):
        mock_task = MagicMock()

        with patch(
            "notifications.tasks.sms.send_sms_notification",
            mock_task,
        ):
            NotificationService._dispatch_sms(
                notification_id=123,
            )

        mock_task.delay.assert_called_once_with(
            notification_id=123,
        )

    def test_websocket_dispatch_queues_task(self):
        mock_task = MagicMock()

        with patch(
            "notifications.tasks.websocket.send_websocket_notification",
            mock_task,
        ):
            NotificationService._dispatch_websocket(
                notification_id=123,
            )

        mock_task.delay.assert_called_once_with(
            notification_id=123,
        )

    
    def test_notify_dispatches_after_commit(self):
        """
        Verify that notify() registers and executes the
        post-commit dispatch callback.
        """
        device = self.create_device()

        with patch.object(
            NotificationService,
            "_dispatch_after_commit",
        ) as dispatch_mock:

            with self.captureOnCommitCallbacks(
                execute=True,
            ):
                notification = NotificationService.notify(
                    user=self.user,
                    module="transport",
                    notification_type="info",
                    title="Trip assigned",
                    message="A trip was assigned.",
                    channels=[CHANNEL_PUSH],
                    dispatch=True,
                )

        # The on_commit callback must execute exactly once.
        dispatch_mock.assert_called_once()

        call = dispatch_mock.call_args

        # Notification ID must match the created notification.
        self.assertEqual(
            call.kwargs["notification_id"],
            notification.pk,
        )

        # Channels are normalized internally to a tuple before
        # _dispatch_after_commit receives them.
        self.assertEqual(
            call.kwargs["channels"],
            (CHANNEL_PUSH,),
        )

        # Exactly one eligible push delivery should have been created.
        self.assertEqual(
            len(call.kwargs["push_ids"]),
            1,
        )

        # The dispatched push ID must belong to this notification/device.
        push = NotificationPush.objects.get(
            notification=notification,
            device=device,
        )

        self.assertEqual(
            call.kwargs["push_ids"][0],
            push.pk,
        )


# ============================================================================
# PUSH STATE TRANSITIONS
# ============================================================================


class NotificationServicePushStateTest(
    NotificationServiceTestCase
):
    """Tests push state transition helpers."""

    def test_mark_push_processing(self):
        push = self.create_push()

        result = NotificationService.mark_push_processing(
            push,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.PROCESSING,
        )

        self.assertIsNotNone(
            result.processing_started_at,
        )

        self.assertEqual(
            result.error_message,
            "",
        )

    def test_mark_push_sent(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.PROCESSING,
        )

        result = NotificationService.mark_push_sent(
            push,
            provider="expo",
            provider_message_id="ticket-123",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.SENT,
        )

        self.assertIsNotNone(
            result.sent_at,
        )

        self.assertEqual(
            result.provider,
            "expo",
        )

        self.assertEqual(
            result.provider_message_id,
            "ticket-123",
        )

        self.assertEqual(
            result.error_message,
            "",
        )

    def test_mark_push_sent_normalizes_provider(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.PROCESSING,
        )

        NotificationService.mark_push_sent(
            push,
            provider="  EXPO  ",
        )

        push.refresh_from_db()

        self.assertEqual(
            push.provider,
            "expo",
        )

    def test_mark_push_failed(self):
        push = self.create_push()

        result = NotificationService.mark_push_failed(
            push,
            "Provider unavailable",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.FAILED,
        )

        self.assertEqual(
            result.error_message,
            "Provider unavailable",
        )

        push.device.refresh_from_db()

        self.assertEqual(
            push.device.last_error,
            "Provider unavailable",
        )

        self.assertTrue(
            push.device.is_active,
        )

    def test_mark_push_failed_permanent_deactivates_device(self):
        push = self.create_push()

        NotificationService.mark_push_failed(
            push,
            "Device token is invalid",
            permanent=True,
        )

        push.refresh_from_db()
        push.device.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.FAILED,
        )

        self.assertFalse(
            push.device.is_active,
        )

        self.assertEqual(
            push.device.last_error,
            "Device token is invalid",
        )

    def test_reset_failed_push_for_retry(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.FAILED,
        )

        push.error_message = "Temporary provider failure"

        # Correct timezone API.
        from django.utils import timezone

        push.processing_started_at = timezone.now()

        push.save(
            update_fields=[
                "error_message",
                "processing_started_at",
            ]
        )

        result = NotificationService.reset_push_for_retry(
            push,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.PENDING,
        )

        self.assertEqual(
            result.error_message,
            "",
        )

        self.assertIsNone(
            result.processing_started_at,
        )

    def test_reset_push_does_nothing_when_not_failed(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.SENT,
        )

        result = NotificationService.reset_push_for_retry(
            push,
        )

        self.assertEqual(
            result.pk,
            push.pk,
        )

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.SENT,
        )


# ============================================================================
# PUSH CLAIM CONCURRENCY
# ============================================================================


class NotificationServicePushClaimConcurrencyTest(
    TransactionTestCase
):
    """
    Tests the atomic NotificationPush PENDING -> PROCESSING claim.

    These tests intentionally use TransactionTestCase because the claim
    implementation depends on real database transactions and row-level
    locking.

    PostgreSQL is required for the concurrency guarantee being tested.
    """

    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            email="notification-concurrency@example.com",
            password="test-password",
        )

        self.preference = NotificationPreference.objects.create(
            user=self.user,
        )

        self.device = NotificationDevice.objects.create(
            user=self.user,
            platform=NotificationDevice.Platform.ANDROID,
            provider=NotificationDevice.Provider.EXPO,
            device_token="ExponentPushToken[concurrency-test]",
            device_id="concurrency-device-001",
            is_active=True,
            notifications_enabled=True,
        )

        self.notification = UserNotification.objects.create(
            recipient=self.user,
            event=None,
            module="system",
            notification_type=(
                UserNotification.NotificationType.INFO
            ),
            priority=UserNotification.Priority.NORMAL,
            title="Concurrency test",
            message="Concurrency test notification.",
            metadata={"test": "concurrency"},
        )

        self.push = NotificationPush.objects.create(
            notification=self.notification,
            device=self.device,
            provider=self.device.provider,
            status=NotificationPush.PushStatus.PENDING,
        )

    def test_only_one_worker_can_claim_same_push(self):
        """
        Two workers attempting to claim the same PENDING push concurrently
        must result in exactly one successful claim.

        Expected:

            worker 1 -> NotificationPush
            worker 2 -> None

        Final database state:

            status = PROCESSING
        """

        push_id = self.push.pk

        barrier = threading.Barrier(2)

        results = []
        errors = []
        results_lock = threading.Lock()

        def worker():
            try:
                close_old_connections()

                # Make both workers reach the claim boundary together.
                barrier.wait(timeout=10)

                claimed = (
                    NotificationService.claim_push_for_processing(
                        push_id
                    )
                )

                with results_lock:
                    results.append(claimed)

            except Exception as exc:
                with results_lock:
                    errors.append(exc)

            finally:
                close_old_connections()

        thread_one = threading.Thread(
            target=worker,
            name="notification-claim-worker-1",
        )

        thread_two = threading.Thread(
            target=worker,
            name="notification-claim-worker-2",
        )

        thread_one.start()
        thread_two.start()

        thread_one.join(timeout=30)
        thread_two.join(timeout=30)

        self.assertFalse(
            thread_one.is_alive(),
            "First concurrency worker did not finish.",
        )

        self.assertFalse(
            thread_two.is_alive(),
            "Second concurrency worker did not finish.",
        )

        self.assertEqual(
            errors,
            [],
            msg=(
                "Concurrent claim workers raised unexpected "
                f"exceptions: {errors}"
            ),
        )

        # Exactly two worker results must exist.
        self.assertEqual(
            len(results),
            2,
        )

        # Exactly one worker owns the claim.
        successful_claims = [
            result
            for result in results
            if result is not None
        ]

        self.assertEqual(
            len(successful_claims),
            1,
            msg=(
                "Exactly one worker must successfully claim "
                "the NotificationPush."
            ),
        )

        # Exactly one worker must lose the race.
        unsuccessful_claims = [
            result
            for result in results
            if result is None
        ]

        self.assertEqual(
            len(unsuccessful_claims),
            1,
            msg=(
                "Exactly one concurrent worker must receive None "
                "after another worker claims the push."
            ),
        )

        claimed_push = successful_claims[0]

        self.assertEqual(
            claimed_push.pk,
            push_id,
        )

        self.assertEqual(
            claimed_push.status,
            NotificationPush.PushStatus.PROCESSING,
        )

        self.assertIsNotNone(
            claimed_push.processing_started_at,
        )

        # Verify the persisted database state after both workers finish.
        final_push = (
            NotificationPush.objects
            .get(pk=push_id)
        )

        self.assertEqual(
            final_push.status,
            NotificationPush.PushStatus.PROCESSING,
        )

        self.assertIsNotNone(
            final_push.processing_started_at,
        )

    def test_already_processing_push_cannot_be_claimed_again(self):
        """
        A push that has already been claimed must not be claimed again.
        """

        self.push.status = (
            NotificationPush.PushStatus.PROCESSING
        )
        self.push.processing_started_at = timezone.now()
        self.push.save(
            update_fields=[
                "status",
                "processing_started_at",
            ]
        )

        result = (
            NotificationService.claim_push_for_processing(
                self.push.pk
            )
        )

        self.assertIsNone(
            result,
        )

        self.push.refresh_from_db()

        self.assertEqual(
            self.push.status,
            NotificationPush.PushStatus.PROCESSING,
        )

    def test_sent_push_cannot_be_claimed(self):
        """
        A completed SENT push must never return to PROCESSING.
        """

        self.push.status = (
            NotificationPush.PushStatus.SENT
        )
        self.push.sent_at = timezone.now()
        self.push.save(
            update_fields=[
                "status",
                "sent_at",
            ]
        )

        result = (
            NotificationService.claim_push_for_processing(
                self.push.pk
            )
        )

        self.assertIsNone(
            result,
        )

        self.push.refresh_from_db()

        self.assertEqual(
            self.push.status,
            NotificationPush.PushStatus.SENT,
        )


# ============================================================================
# MODULE LEVEL HELPERS
# ============================================================================


class NotificationServiceModuleHelperTest(
    NotificationServiceTestCase
):
    """Tests module-level convenience functions."""

    def test_mark_push_sent_helper(self):
        push = self.create_push()

        result = mark_push_sent(
            push,
            provider="expo",
            provider_message_id="helper-ticket",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.SENT,
        )

        self.assertEqual(
            result.provider,
            "expo",
        )

        self.assertEqual(
            result.provider_message_id,
            "helper-ticket",
        )

    def test_mark_push_failed_helper(self):
        push = self.create_push()

        result = mark_push_failed(
            push,
            "helper failure",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.FAILED,
        )

        self.assertEqual(
            result.error_message,
            "helper failure",
        )

    def test_reset_push_for_retry_helper(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.FAILED,
        )

        result = reset_push_for_retry(
            push,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            NotificationPush.PushStatus.PENDING,
        )


# ============================================================================
# VALIDATION
# ============================================================================


class NotificationServiceValidationTest(
    NotificationServiceTestCase
):
    """Tests service input validation."""

    def test_none_user_is_rejected(self):
        with self.assertRaises(
            NotificationRecipientError
        ):
            NotificationService.notify(
                user=None,
                module="system",
                notification_type="info",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_unsaved_user_is_rejected(self):
        unsaved_user = User(
            email="unsaved@example.com",
        )

        with self.assertRaises(
            NotificationRecipientError
        ):
            NotificationService.notify(
                user=unsaved_user,
                module="system",
                notification_type="info",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_missing_module_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module="",
                notification_type="info",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_non_string_module_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module=123,
                notification_type="info",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_module_longer_than_50_characters_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module="x" * 51,
                notification_type="info",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_invalid_notification_type_is_rejected(self):
        with self.assertRaises(
            InvalidNotificationType
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="invalid",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_empty_notification_type_is_rejected(self):
        with self.assertRaises(
            InvalidNotificationType
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="",
                title="Test",
                message="Test message",
                dispatch=False,
            )

    def test_invalid_priority_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="info",
                title="Test",
                message="Test message",
                priority="invalid",
                dispatch=False,
            )

    def test_empty_title_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="info",
                title="",
                message="Test message",
                dispatch=False,
            )

    def test_empty_message_is_rejected(self):
        with self.assertRaises(
            NotificationServiceError
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="info",
                title="Test",
                message="",
                dispatch=False,
            )

    def test_invalid_channel_is_rejected(self):
        with self.assertRaises(
            InvalidNotificationChannel
        ):
            NotificationService.notify(
                user=self.user,
                module="system",
                notification_type="info",
                title="Test",
                message="Test message",
                channels=["invalid"],
                dispatch=False,
            )


# ============================================================================
# PERSISTENCE POLICY
# ============================================================================


class NotificationServicePersistencePolicyTest(
    NotificationServiceTestCase
):
    """Tests should_persist_without_delivery()."""

    def test_system_notification_should_persist(self):
        self.assertTrue(
            NotificationService.should_persist_without_delivery(
                notification_type=(
                    UserNotification.NotificationType.SYSTEM
                ),
            )
        )

    def test_error_notification_should_persist(self):
        self.assertTrue(
            NotificationService.should_persist_without_delivery(
                notification_type=(
                    UserNotification.NotificationType.ERROR
                ),
            )
        )

    def test_info_notification_does_not_require_persistence_policy(self):
        self.assertFalse(
            NotificationService.should_persist_without_delivery(
                notification_type=(
                    UserNotification.NotificationType.INFO
                ),
            )
        )

    def test_success_notification_does_not_require_persistence_policy(self):
        self.assertFalse(
            NotificationService.should_persist_without_delivery(
                notification_type=(
                    UserNotification.NotificationType.SUCCESS
                ),
            )
        )

    def test_warning_notification_does_not_require_persistence_policy(self):
        self.assertFalse(
            NotificationService.should_persist_without_delivery(
                notification_type=(
                    UserNotification.NotificationType.WARNING
                ),
            )
        )

