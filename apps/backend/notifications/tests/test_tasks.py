"""
apps/backend/notifications/tests/test_tasks.py

Production-oriented tests for the Univa notification task layer.

The tests follow the CURRENT task architecture.

Implementation modules
----------------------

notifications.tasks.delivery_tasks
    - deliver_push_notification
    - deliver_pending_push_notifications
    - retry_failed_push_notifications
    - deliver_notification

notifications.tasks.event_tasks
    - process_notification_event_task
    - recover_stale_notification_events
    - retry_failed_notification_events

notifications.tasks.notification_tasks
    - prepare_notification_delivery

notifications.tasks.process_notification_queue
    - process_notification_queue
    - process_notification_push
    - enqueue_pending_notification_pushes

notifications.tasks.maintenance_tasks
    - cleanup_stale_devices
    - recover_stale_notification_events
    - recover_stale_notification_pushes
    - cleanup_old_notifications
    - cleanup_old_push_deliveries
    - cleanup_old_events
    - run_notification_maintenance

Important
---------

Do NOT import:

    notifications.tasks.process_pending_notifications

The canonical implementation lives in:

    notifications.tasks.process_notification_queue

The queue implementation processes individual pushes synchronously
through process_notification_push.run() rather than dispatching
process_notification_push.delay() for every push.

External provider delivery is never required by these tests.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from accounts.models import User

from notifications.models import (
    NotificationDevice,
    NotificationEvent,
    NotificationPreference,
    NotificationPush,
    UserNotification,
)

from notifications.tasks.delivery_tasks import (
    deliver_notification,
    deliver_pending_push_notifications,
    deliver_push_notification,
    retry_failed_push_notifications,
)

from notifications.tasks.event_tasks import (
    process_notification_event_task,
    recover_stale_notification_events,
    retry_failed_notification_events,
)

from notifications.tasks.maintenance_tasks import (
    cleanup_old_events,
    cleanup_old_notifications,
    cleanup_old_push_deliveries,
    cleanup_stale_devices,
    recover_stale_notification_events as maintenance_recover_stale_events,
    recover_stale_notification_pushes,
    run_notification_maintenance,
)

from notifications.tasks.notification_tasks import (
    prepare_notification_delivery,
)

from notifications.tasks.process_notification_queue import (
    enqueue_pending_notification_pushes,
    process_notification_push,
    process_notification_queue,
)


# ============================================================================
# SHARED FIXTURE
# ============================================================================


class NotificationTaskTestCase(TestCase):
    """Shared fixtures for notification task tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            email=f"notification-task-{uuid4().hex}@example.com",
            password="test-password",
        )

        self.preference = NotificationPreference.objects.create(
            user=self.user,
        )

    # ------------------------------------------------------------------
    # DEVICE
    # ------------------------------------------------------------------

    def create_device(
        self,
        *,
        token=None,
        provider=NotificationDevice.Provider.EXPO,
        platform=NotificationDevice.Platform.ANDROID,
        active=True,
        enabled=True,
        device_id=None,
    ):
        return NotificationDevice.objects.create(
            user=self.user,
            platform=platform,
            provider=provider,
            device_token=token or f"ExponentPushToken[{uuid4().hex}]",
            device_id=device_id or f"device-{uuid4().hex}",
            is_active=active,
            notifications_enabled=enabled,
        )

    # ------------------------------------------------------------------
    # NOTIFICATION
    # ------------------------------------------------------------------

    def create_notification(
        self,
        *,
        event=None,
        notification_type=UserNotification.NotificationType.INFO,
        priority=UserNotification.Priority.NORMAL,
        title="Task test notification",
        message="Task test notification message",
        archived=False,
        read=False,
    ):
        return UserNotification.objects.create(
            recipient=self.user,
            event=event,
            module="system",
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            metadata={
                "source": "test_tasks",
            },
            is_archived=archived,
            is_read=read,
        )

    # ------------------------------------------------------------------
    # PUSH
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # EVENT
    # ------------------------------------------------------------------

    def create_event(
        self,
        *,
        event_type="order.created",
        module="order",
        actor=None,
        object_type="Order",
        object_id="123",
        payload=None,
        status=None,
    ):
        kwargs = {
            "event_type": event_type,
            "module": module,
            "actor": actor,
            "object_type": object_type,
            "object_id": object_id,
            "payload": payload or {
                "order_id": 123,
            },
        }

        if status is not None:
            kwargs["status"] = status

        return NotificationEvent.objects.create(**kwargs)


# ============================================================================
# EVENT TASKS
# ============================================================================


class NotificationEventTaskTest(NotificationTaskTestCase):
    """Tests for notifications.tasks.event_tasks."""

    def test_process_notification_event_missing_event_is_safe(self):
        result = process_notification_event_task.run(999999)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("event_id"), 999999)
        self.assertEqual(result.get("status"), "not_found")

    def test_process_notification_event_already_processed_is_idempotent(self):
        event = self.create_event(
            status=NotificationEvent.Status.PROCESSED,
        )

        result = process_notification_event_task.run(event.pk)

        self.assertTrue(result.get("success"))
        self.assertEqual(
            result.get("status"),
            "already_processed",
        )
        self.assertEqual(
            result.get("notifications_created"),
            0,
        )
        self.assertEqual(
            result.get("notification_ids"),
            [],
        )

    def test_process_notification_event_cancelled_is_not_processed(self):
        event = self.create_event(
            status=NotificationEvent.Status.CANCELLED,
        )

        result = process_notification_event_task.run(event.pk)

        self.assertTrue(result.get("success"))
        self.assertEqual(
            result.get("status"),
            "cancelled",
        )
        self.assertEqual(
            result.get("notifications_created"),
            0,
        )

    @patch(
        "notifications.tasks.event_tasks.process_notification_event"
    )
    def test_process_notification_event_task_processes_event(
        self,
        processor,
    ):
        event = self.create_event(
            status=NotificationEvent.Status.PENDING,
        )

        notification = self.create_notification(
            event=event,
        )

        def process_event_side_effect(event_instance):
            NotificationEvent.objects.filter(
                pk=event_instance.pk,
            ).update(
                status=NotificationEvent.Status.PROCESSED,
            )

            return [notification]

        processor.side_effect = process_event_side_effect

        result = process_notification_event_task.run(event.pk)

        processor.assert_called_once_with(event)

        self.assertIsInstance(result, dict)
        self.assertEqual(
            result.get("event_id"),
            event.pk,
        )
        self.assertEqual(
            result.get("notifications_created"),
            1,
        )
        self.assertEqual(
            result.get("notification_ids"),
            [notification.pk],
        )

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PROCESSED,
        )

    def test_recover_stale_notification_events_recovers_old_processing_events(
        self,
    ):
        event = self.create_event(
            status=NotificationEvent.Status.PROCESSING,
        )

        stale_time = timezone.now() - timedelta(hours=2)

        NotificationEvent.objects.filter(
            pk=event.pk,
        ).update(
            updated_at=stale_time,
        )

        result = recover_stale_notification_events.run()

        self.assertIsInstance(result, dict)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PENDING,
        )

        self.assertGreaterEqual(
            result.get("recovered", 0),
            1,
        )

    def test_recover_stale_notification_events_does_not_recover_recent_event(
        self,
    ):
        event = self.create_event(
            status=NotificationEvent.Status.PROCESSING,
        )

        result = recover_stale_notification_events.run()

        self.assertIsInstance(result, dict)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PROCESSING,
        )

    def test_retry_failed_notification_events_returns_failed_events_to_pending(
        self,
    ):
        event = self.create_event(
            status=NotificationEvent.Status.FAILED,
        )

        result = retry_failed_notification_events.run()

        self.assertIsInstance(result, dict)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PENDING,
        )

        self.assertTrue(
            result.get("success", True),
        )


# ============================================================================
# DELIVERY TASKS
# ============================================================================


class NotificationDeliveryTaskTest(NotificationTaskTestCase):
    """Tests for notifications.tasks.delivery_tasks."""

    def test_deliver_push_notification_missing_push_is_safe(self):
        result = deliver_push_notification.run(999999)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("success"))
        self.assertEqual(
            result.get("push_id"),
            999999,
        )
        self.assertEqual(
            result.get("status"),
            "not_found",
        )

    @patch(
        "notifications.tasks.delivery_tasks.send_push",
        create=True,
    )
    def test_deliver_push_notification_provider_boundary_is_isolated(
        self,
        send_push,
    ):
        """
        Provider delivery is mocked.

        The important task-layer contract is that no real provider
        connection is required.
        """
        push = self.create_push()

        send_push.return_value = {
            "success": True,
        }

        result = deliver_push_notification.run(push.pk)

        self.assertIsInstance(result, dict)
        self.assertEqual(
            result.get("push_id"),
            push.pk,
        )

    def test_deliver_push_notification_does_not_redeliver_finished_push(
        self,
    ):
        push = self.create_push(
            status=NotificationPush.PushStatus.SENT,
        )

        result = deliver_push_notification.run(push.pk)

        self.assertIsInstance(result, dict)

        push.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.SENT,
        )

    @patch(
        "notifications.tasks.delivery_tasks.deliver_push_notification.delay"
    )
    def test_deliver_pending_push_notifications_queues_pending_pushes(
        self,
        delay,
    ):
        notification = self.create_notification()

        push_one = self.create_push(
            notification=notification,
        )

        push_two = self.create_push(
            notification=notification,
            device=self.create_device(),
        )

        result = deliver_pending_push_notifications.run(
            batch_size=10,
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(
            result.get("queued"),
            2,
        )
        self.assertEqual(
            delay.call_count,
            2,
        )

        queued_ids = {
            call.args[0]
            for call in delay.call_args_list
        }

        self.assertEqual(
            queued_ids,
            {
                push_one.pk,
                push_two.pk,
            },
        )

    @patch(
        "notifications.tasks.delivery_tasks.deliver_push_notification.delay"
    )
    def test_deliver_pending_push_notifications_respects_batch_size(
        self,
        delay,
    ):
        notification = self.create_notification()

        pushes = [
            self.create_push(
                notification=notification,
                device=self.create_device(),
            )
            for _ in range(5)
        ]

        result = deliver_pending_push_notifications.run(
            batch_size=2,
        )

        self.assertEqual(
            result.get("queued"),
            2,
        )

        self.assertEqual(
            delay.call_count,
            2,
        )

        queued_ids = {
            call.args[0]
            for call in delay.call_args_list
        }

        self.assertEqual(
            len(queued_ids),
            2,
        )

        self.assertTrue(
            queued_ids.issubset(
                {
                    push.pk
                    for push in pushes
                }
            )
        )

    @patch(
        "notifications.tasks.delivery_tasks.deliver_push_notification.delay"
    )
    def test_retry_failed_push_notifications_resets_failed_push(
        self,
        delay,
    ):
        push = self.create_push(
            status=NotificationPush.PushStatus.FAILED,
        )

        result = retry_failed_push_notifications.run(
            batch_size=10,
        )

        self.assertIsInstance(result, dict)

        push.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.PENDING,
        )

        self.assertGreaterEqual(
            result.get("queued", 0),
            1,
        )

        delay.assert_called()

    @patch(
        "notifications.tasks.delivery_tasks.deliver_push_notification.delay"
    )
    def test_retry_failed_push_notifications_respects_batch_size(
        self,
        delay,
    ):
        notification = self.create_notification()

        pushes = [
            self.create_push(
                notification=notification,
                device=self.create_device(),
                status=NotificationPush.PushStatus.FAILED,
            )
            for _ in range(5)
        ]

        result = retry_failed_push_notifications.run(
            batch_size=2,
        )

        self.assertEqual(
            result.get("queued"),
            2,
        )

        self.assertEqual(
            delay.call_count,
            2,
        )

        reset_count = NotificationPush.objects.filter(
            pk__in=[push.pk for push in pushes],
            status=NotificationPush.PushStatus.PENDING,
        ).count()

        self.assertEqual(
            reset_count,
            2,
        )

    @patch(
        "notifications.tasks.delivery_tasks.deliver_push_notification.delay"
    )
    def test_deliver_notification_queues_pending_pushes_for_notification(
        self,
        delay,
    ):
        notification = self.create_notification()

        push = self.create_push(
            notification=notification,
        )

        result = deliver_notification.run(
            notification.pk,
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(
            result.get("notification_id"),
            notification.pk,
        )
        self.assertEqual(
            result.get("queued"),
            1,
        )

        delay.assert_called_once_with(
            push.pk,
        )

    def test_deliver_notification_with_no_pending_pushes_is_safe(
        self,
    ):
        notification = self.create_notification()

        result = deliver_notification.run(
            notification.pk,
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(
            result.get("notification_id"),
            notification.pk,
        )
        self.assertEqual(
            result.get("queued"),
            0,
        )


# ============================================================================
# QUEUE TASKS
# ============================================================================


class NotificationQueueTaskTest(NotificationTaskTestCase):
    """
    Tests for notifications.tasks.process_notification_queue.

    The current implementation processes pushes synchronously through
    process_notification_push.run() rather than dispatching
    process_notification_push.delay() for every push.
    """

    def test_process_notification_queue_empty(self):
        result = process_notification_queue.run()

        self.assertIsInstance(result, dict)

        self.assertEqual(
            result.get("processed", 0),
            0,
        )

    @patch("notifications.tasks.process_notification_queue._get_delivery_task")
    def test_process_notification_push_delegates_to_delivery_task(
        self,
        mock_get_delivery,
    ):
        """
        process_notification_push delegates directly to the delivery task,
        NOT to process_single_push from the queue compatibility layer.
        """
        push = self.create_push()
        
        mock_delivery = MagicMock()
        mock_delivery.run.return_value = {
            "status": NotificationPush.PushStatus.SENT,
            "push_id": push.pk,
        }
        mock_get_delivery.return_value = mock_delivery
        
        result = process_notification_push.run(push.pk)
        
        mock_delivery.run.assert_called_once_with(push.pk)
        self.assertEqual(result.get("push_id"), push.pk)
        self.assertEqual(result.get("status"), NotificationPush.PushStatus.SENT)

    def test_process_notification_push_missing_push_is_safe(self):
        result = process_notification_push.run(
            999999,
        )

        self.assertIsInstance(result, dict)

        self.assertEqual(
            result.get("push_id"),
            999999,
        )

        self.assertIn(
            result.get("status"),
            {
                "not_claimed",
                "not_found",
                "failed",
            },
        )

    
    @patch("notifications.tasks.process_notification_queue.process_notification_push.run")
    def test_process_notification_queue_processes_pending_pushes(self, mock_run):
        """
        process_notification_queue calls process_notification_push.run()
        synchronously for each pending push.
        """
        notification = self.create_notification()

        push_one = self.create_push(
            notification=notification,
        )

        push_two = self.create_push(
            notification=notification,
            device=self.create_device(),
        )

        mock_run.side_effect = [
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push_one.pk,
            },
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push_two.pk,
            },
        ]

        result = process_notification_queue.run(
            batch_size=10,
        )

        self.assertIsInstance(result, dict)

        self.assertEqual(
            result.get("processed"),
            2,
        )

        self.assertEqual(
            result.get("sent"),
            2,
        )

        self.assertEqual(
            mock_run.call_count,
            2,
        )

        mock_run.assert_any_call(push_one.pk)
        mock_run.assert_any_call(push_two.pk)


    @patch("notifications.tasks.process_notification_queue.process_notification_push.run")
    def test_process_notification_queue_respects_batch_size(self, mock_run):
        """
        process_notification_queue only processes up to batch_size pushes.
        """
        notification = self.create_notification()

        pushes = [
            self.create_push(
                notification=notification,
                device=self.create_device(),
            )
            for _ in range(5)
        ]

        mock_run.side_effect = [
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push.pk,
            }
            for push in pushes[:2]
        ]

        result = process_notification_queue.run(
            batch_size=2,
        )

        self.assertEqual(
            result.get("processed"),
            2,
        )

        # Change from processor.call_count to mock_run.call_count
        self.assertEqual(
            mock_run.call_count,
            2,
        )

        processed_ids = {
            call.args[0]
            for call in mock_run.call_args_list
        }

        self.assertTrue(
            processed_ids.issubset(
                {
                    push.pk
                    for push in pushes
                }
            )
        )


    @patch("notifications.tasks.process_notification_queue.process_notification_push.run")
    def test_enqueue_pending_notification_pushes_processes_pending_pushes(
        self,
        mock_run,
    ):
        """
        enqueue_pending_notification_pushes processes pushes synchronously
        through process_notification_push.run(), NOT via .delay().
        """
        notification = self.create_notification()

        push_one = self.create_push(
            notification=notification,
        )

        push_two = self.create_push(
            notification=notification,
            device=self.create_device(),
        )

        mock_run.side_effect = [
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push_one.pk,
            },
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push_two.pk,
            },
        ]

        result = enqueue_pending_notification_pushes.run(
            batch_size=10,
        )

        self.assertIsInstance(result, dict)

        self.assertEqual(
            result.get("queued"),
            2,
        )

        self.assertEqual(
            mock_run.call_count,
            2,
        )

        processed_ids = {
            call.args[0]
            for call in mock_run.call_args_list
        }

        self.assertEqual(
            processed_ids,
            {
                push_one.pk,
                push_two.pk,
            },
        )

    @patch("notifications.tasks.process_notification_queue.process_notification_push.run")
    def test_enqueue_pending_notification_pushes_respects_batch_size(
        self,
        mock_run,
    ):
        """
        enqueue_pending_notification_pushes only processes up to batch_size pushes.
        """
        notification = self.create_notification()

        pushes = [
            self.create_push(
                notification=notification,
                device=self.create_device(),
            )
            for _ in range(5)
        ]

        mock_run.side_effect = [
            {
                "status": NotificationPush.PushStatus.SENT,
                "push_id": push.pk,
            }
            for push in pushes[:2]
        ]

        result = enqueue_pending_notification_pushes.run(
            batch_size=2,
        )

        self.assertEqual(
            result.get("queued"),
            2,
        )

        self.assertEqual(
            mock_run.call_count,
            2,
        )

        processed_ids = {
            call.args[0]
            for call in mock_run.call_args_list
        }

        self.assertEqual(
            len(processed_ids),
            2,
        )

        self.assertTrue(
            processed_ids.issubset(
                {
                    push.pk
                    for push in pushes
                }
            )
        )


# ============================================================================
# NOTIFICATION PREPARATION
# ============================================================================


class NotificationPreparationTaskTest(NotificationTaskTestCase):
    """Tests for notifications.tasks.notification_tasks."""

    def test_prepare_notification_delivery_missing_notification_is_safe(
        self,
    ):
        result = prepare_notification_delivery.run(
            999999,
        )

        self.assertIsInstance(result, dict)

        self.assertFalse(
            result.get("success"),
        )

        self.assertEqual(
            result.get("notification_id"),
            999999,
        )

    def test_prepare_notification_delivery_creates_push_records(
        self,
    ):
        self.create_device()

        notification = self.create_notification()

        result = prepare_notification_delivery.run(
            notification.pk,
        )

        self.assertIsInstance(result, dict)

        self.assertEqual(
            result.get("notification_id"),
            notification.pk,
        )

        self.assertGreaterEqual(
            NotificationPush.objects.filter(
                notification=notification,
            ).count(),
            1,
        )

    def test_prepare_notification_delivery_is_idempotent(
        self,
    ):
        self.create_device()

        notification = self.create_notification()

        first = prepare_notification_delivery.run(
            notification.pk,
        )

        first_count = NotificationPush.objects.filter(
            notification=notification,
        ).count()

        second = prepare_notification_delivery.run(
            notification.pk,
        )

        second_count = NotificationPush.objects.filter(
            notification=notification,
        ).count()

        self.assertIsInstance(first, dict)
        self.assertIsInstance(second, dict)

        self.assertEqual(
            first_count,
            second_count,
        )


# ============================================================================
# MAINTENANCE TASKS
# ============================================================================


class NotificationMaintenanceTaskTest(NotificationTaskTestCase):
    """Tests for notifications.tasks.maintenance_tasks."""

    def test_cleanup_stale_devices_runs_safely(self):
        device = self.create_device(
            active=True,
        )

        old_time = timezone.now() - timedelta(days=365)

        NotificationDevice.objects.filter(
            pk=device.pk,
        ).update(
            updated_at=old_time,
        )

        result = cleanup_stale_devices.run()

        self.assertIsInstance(result, dict)

    def test_maintenance_recover_stale_events_runs_safely(self):
        event = self.create_event(
            status=NotificationEvent.Status.PROCESSING,
        )

        stale_time = timezone.now() - timedelta(hours=2)

        NotificationEvent.objects.filter(
            pk=event.pk,
        ).update(
            updated_at=stale_time,
        )

        result = maintenance_recover_stale_events.run()

        self.assertIsInstance(result, dict)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PENDING,
        )

    def test_maintenance_recover_stale_pushes_runs_safely(
        self,
    ):
        push = self.create_push(
            status=NotificationPush.PushStatus.PROCESSING,
        )

        stale_time = timezone.now() - timedelta(hours=2)

        NotificationPush.objects.filter(
            pk=push.pk,
        ).update(
            processing_started_at=stale_time,
        )

        result = recover_stale_notification_pushes.run()

        self.assertIsInstance(result, dict)

        push.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.PENDING,
        )

        self.assertGreaterEqual(
            result.get("recovered", 0),
            1,
        )

    def test_maintenance_recover_stale_pushes_does_not_recover_recent_push(
        self,
    ):
        push = self.create_push(
            status=NotificationPush.PushStatus.PROCESSING,
        )

        result = recover_stale_notification_pushes.run()

        self.assertIsInstance(result, dict)

        push.refresh_from_db()

        self.assertEqual(
            push.status,
            NotificationPush.PushStatus.PROCESSING,
        )

    def test_cleanup_old_notifications_runs_safely(self):
        notification = self.create_notification(
            archived=True,
            read=True,
        )

        old_time = timezone.now() - timedelta(days=365)

        UserNotification.objects.filter(
            pk=notification.pk,
        ).update(
            updated_at=old_time,
        )

        result = cleanup_old_notifications.run()

        self.assertIsInstance(result, dict)

    def test_cleanup_old_push_deliveries_runs_safely(self):
        push = self.create_push(
            status=NotificationPush.PushStatus.SENT,
        )

        old_time = timezone.now() - timedelta(days=365)

        NotificationPush.objects.filter(
            pk=push.pk,
        ).update(
            updated_at=old_time,
        )

        result = cleanup_old_push_deliveries.run()

        self.assertIsInstance(result, dict)

    def test_cleanup_old_events_runs_safely(self):
        event = self.create_event(
            status=NotificationEvent.Status.PROCESSED,
        )

        old_time = timezone.now() - timedelta(days=365)

        NotificationEvent.objects.filter(
            pk=event.pk,
        ).update(
            updated_at=old_time,
        )

        result = cleanup_old_events.run()

        self.assertIsInstance(result, dict)

    @patch(
        "notifications.tasks.maintenance_tasks.cleanup_stale_devices"
    )
    @patch(
        "notifications.tasks.maintenance_tasks.recover_stale_notification_events"
    )
    @patch(
        "notifications.tasks.maintenance_tasks.recover_stale_notification_pushes"
    )
    @patch(
        "notifications.tasks.maintenance_tasks.cleanup_old_notifications"
    )
    @patch(
        "notifications.tasks.maintenance_tasks.cleanup_old_push_deliveries"
    )
    @patch(
        "notifications.tasks.maintenance_tasks.cleanup_old_events"
    )
    def test_run_notification_maintenance_runs_all_tasks(
        self,
        cleanup_events,
        cleanup_pushes,
        cleanup_notifications,
        recover_pushes,
        recover_events,
        cleanup_devices,
    ):
        cleanup_devices.return_value = {
            "deactivated": 1,
        }

        recover_events.return_value = {
            "recovered": 2,
        }

        recover_pushes.return_value = {
            "recovered": 3,
        }

        cleanup_notifications.return_value = {
            "deleted": 4,
        }

        cleanup_pushes.return_value = {
            "deleted": 5,
        }

        cleanup_events.return_value = {
            "deleted": 6,
        }

        result = run_notification_maintenance.run()

        self.assertIsInstance(result, dict)

        cleanup_devices.assert_called_once()
        recover_events.assert_called_once()
        recover_pushes.assert_called_once()
        cleanup_notifications.assert_called_once()
        cleanup_pushes.assert_called_once()
        cleanup_events.assert_called_once()

        self.assertEqual(
            result["stale_devices"],
            {
                "deactivated": 1,
            },
        )

        self.assertEqual(
            result["stale_events"],
            {
                "recovered": 2,
            },
        )

        self.assertEqual(
            result["stale_pushes"],
            {
                "recovered": 3,
            },
        )

        self.assertEqual(
            result["old_notifications"],
            {
                "deleted": 4,
            },
        )

        self.assertEqual(
            result["old_pushes"],
            {
                "deleted": 5,
            },
        )

        self.assertEqual(
            result["old_events"],
            {
                "deleted": 6,
            },
        )


# ============================================================================
# CELERY REGISTRATION
# ============================================================================


class NotificationCeleryRegistrationTest(TestCase):
    """Protect the public Celery task names."""

    def test_push_task_names(self):
        self.assertEqual(
            deliver_push_notification.name,
            "notifications.tasks.deliver_push_notification",
        )

        self.assertEqual(
            deliver_pending_push_notifications.name,
            "notifications.tasks.deliver_pending_push_notifications",
        )

        self.assertEqual(
            retry_failed_push_notifications.name,
            "notifications.tasks.retry_failed_push_notifications",
        )

        self.assertEqual(
            deliver_notification.name,
            "notifications.tasks.deliver_notification",
        )

    def test_event_task_names(self):
        self.assertEqual(
            process_notification_event_task.name,
            "notifications.tasks.process_notification_event",
        )

        self.assertEqual(
            recover_stale_notification_events.name,
            "notifications.tasks.recover_stale_notification_events",
        )

        self.assertEqual(
            retry_failed_notification_events.name,
            "notifications.tasks.retry_failed_notification_events",
        )

    def test_notification_task_names(self):
        self.assertEqual(
            prepare_notification_delivery.name,
            "notifications.tasks.prepare_notification_delivery",
        )

    def test_queue_task_names(self):
        self.assertEqual(
            process_notification_queue.name,
            "notifications.tasks.process_notification_queue",
        )

        self.assertEqual(
            process_notification_push.name,
            "notifications.tasks.process_notification_push",
        )

        self.assertEqual(
            enqueue_pending_notification_pushes.name,
            "notifications.tasks.enqueue_pending_notification_pushes",
        )