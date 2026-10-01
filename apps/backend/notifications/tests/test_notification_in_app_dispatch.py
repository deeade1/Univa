# apps/backend/notifications/tests/test_notification_in_app_dispatch.py

"""
Tests for the in-app notification Celery task.

Architectural contract
----------------------

    NotificationService.notify()
            |
            v
    UserNotification persisted
            |
            v
    transaction.on_commit()
            |
            v
    send_in_app_notification.delay(notification_id)
            |
            v
    Existing UserNotification loaded
            |
            +----> preference check
            |
            +----> rate-limit check
            |
            +----> WebSocket dispatch

The authoritative in-app Celery task MUST:

    1. Receive a UserNotification primary key.
    2. Load the existing UserNotification.
    3. Never create a second UserNotification.
    4. Return a structured result.
    5. Dispatch WebSocket delivery only after the notification exists.
    6. Respect in-app notification preferences.
    7. Respect the in-app rate limit.

These tests deliberately call the task directly rather than through a
Celery worker. Celery's scheduling behavior is tested separately at the
NotificationService boundary.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from notifications.models import (
    NotificationPreference,
    UserNotification,
)
from notifications.tasks.in_app import (
    send_in_app_notification,
)
from notifications.services.notification_service import NotificationService
from notifications.services.notification_service import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_PUSH,
    CHANNEL_SMS,
    CHANNEL_WEBSOCKET,
)

User = get_user_model()


# ============================================================================
# TEST HELPERS
# ============================================================================


class InAppNotificationTestMixin:
    """Shared helpers for in-app notification tests."""

    def create_user(
        self,
        *,
        email: str = "in-app-test@example.com",
    ):
        """Create a persisted test user."""

        return User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

    def enable_in_app_notifications(
        self,
        user,
    ):
        """Enable global and in-app notification preferences."""

        preferences, _ = (
            NotificationPreference.objects.get_or_create(
                user=user,
            )
        )

        update_fields = []

        if not preferences.notifications_enabled:
            preferences.notifications_enabled = True
            update_fields.append("notifications_enabled")

        if hasattr(preferences, "in_app_enabled"):
            if not preferences.in_app_enabled:
                preferences.in_app_enabled = True
                update_fields.append("in_app_enabled")

        if update_fields:
            preferences.save(
                update_fields=update_fields,
            )

        return preferences

    def create_notification(
        self,
        user,
        *,
        title: str = "Test notification",
        message: str = "This is an in-app test notification.",
        module: str = "system",
    ):
        """Create the notification through the authoritative service."""

        from notifications.services.notification_service import (
            NotificationService,
        )

        return NotificationService.notify(
            user=user,
            module=module,
            notification_type=(
                UserNotification.NotificationType.INFO
            ),
            title=title,
            message=message,
            metadata={
                "test": True,
            },
            action_url="",
            channels=("in_app",),
            priority=UserNotification.Priority.NORMAL,
            dispatch=False,
        )


# ============================================================================
# AUTHORITATIVE TASK CONTRACT
# ============================================================================


class InAppNotificationTaskTestCase(
    InAppNotificationTestMixin,
    TestCase,
):
    """
    Tests for the authoritative send_in_app_notification task.
    """

    def setUp(self):
        super().setUp()
        cache.clear()

    # ========================================================================
    # Notification ID contract
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_task_accepts_notification_id(
        self,
        mock_websocket,
    ):
        """
        The task receives the persisted UserNotification primary key.

        It must not require user_id/event_type as separate arguments.
        """

        user = self.create_user()
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=False,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "dispatched",
        )

        self.assertEqual(
            result["notification_id"],
            notification.pk,
        )

        self.assertEqual(
            result["user_id"],
            user.pk,
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Existing notification
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_task_uses_existing_notification(
        self,
        mock_websocket,
    ):
        """
        The task must load the existing UserNotification.

        It must not construct a new notification.
        """

        user = self.create_user(
            email="existing-notification@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(
            user,
            title="Existing notification",
            message="This notification already exists.",
        )

        notification_id = notification.pk
        before_count = UserNotification.objects.count()

        result = send_in_app_notification(
            notification_id,
            dispatch_websocket=False,
        )

        after_count = UserNotification.objects.count()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["notification_id"],
            notification_id,
        )

        self.assertEqual(
            before_count,
            after_count,
        )

        self.assertTrue(
            UserNotification.objects.filter(
                pk=notification_id,
            ).exists(),
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # No duplicate notification
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_task_does_not_create_duplicate_notification(
        self,
        mock_websocket,
    ):
        """
        Regression test for the previous task architecture.

        The task must never create another UserNotification.
        """

        user = self.create_user(
            email="no-duplicate@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        existing_ids = set(
            UserNotification.objects.values_list(
                "pk",
                flat=True,
            )
        )

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=False,
        )

        resulting_ids = set(
            UserNotification.objects.values_list(
                "pk",
                flat=True,
            )
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            existing_ids,
            resulting_ids,
        )

        self.assertEqual(
            UserNotification.objects.filter(
                recipient=user,
            ).count(),
            1,
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # WebSocket dispatch
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_successful_delivery_dispatches_websocket(
        self,
        mock_websocket,
    ):
        """
        Successful in-app delivery may queue the WebSocket task using only
        the persisted notification ID.
        """

        user = self.create_user(
            email="websocket@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "dispatched",
        )

        mock_websocket.assert_called_once_with(
            notification.pk,
        )

    # ========================================================================
    # WebSocket disabled
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_websocket_dispatch_can_be_disabled(
        self,
        mock_websocket,
    ):
        """
        dispatch_websocket=False must prevent WebSocket scheduling.
        """

        user = self.create_user(
            email="no-websocket@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=False,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "dispatched",
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Preference disabled
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_disabled_in_app_preferences_skip_delivery(
        self,
        mock_websocket,
    ):
        """
        Disabled in-app preferences must suppress delivery.
        """

        user = self.create_user(
            email="preferences-disabled@example.com",
        )

        preferences = self.enable_in_app_notifications(
            user,
        )

        if hasattr(preferences, "in_app_enabled"):
            preferences.in_app_enabled = False
            preferences.save(
                update_fields=["in_app_enabled"],
            )
        else:
            self.skipTest(
                "NotificationPreference has no in_app_enabled field.",
            )

        notification = self.create_notification(user)

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "preference_disabled",
        )

        self.assertEqual(
            result["notification_id"],
            notification.pk,
        )

        mock_websocket.assert_not_called()

        self.assertTrue(
            UserNotification.objects.filter(
                pk=notification.pk,
            ).exists(),
        )

    # ========================================================================
    # Global notifications disabled
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_disabled_global_notifications_skip_delivery(
        self,
        mock_websocket,
    ):
        """
        Global notification preferences must suppress in-app delivery.
        """

        user = self.create_user(
            email="global-disabled@example.com",
        )

        preferences = self.enable_in_app_notifications(
            user,
        )

        preferences.notifications_enabled = False

        update_fields = [
            "notifications_enabled",
        ]

        preferences.save(
            update_fields=update_fields,
        )

        notification = self.create_notification(
            user,
        )

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "preference_disabled",
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Missing notification
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_missing_notification_is_handled(
        self,
        mock_websocket,
    ):
        """
        A missing UserNotification must not produce a provider/WebSocket
        dispatch.
        """

        result = send_in_app_notification(
            999999999,
            dispatch_websocket=True,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "not_found",
        )

        self.assertEqual(
            result["notification_id"],
            999999999,
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Invalid notification ID
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_missing_notification_id_is_rejected(
        self,
        mock_websocket,
    ):
        """
        A missing notification ID is a programming error and must be
        rejected explicitly.
        """

        with self.assertRaises(
            ValueError,
        ):
            send_in_app_notification(
                None,
                dispatch_websocket=False,
            )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Rate limiting
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_rate_limit_suppresses_delivery(
        self,
        mock_websocket,
    ):
        """
        Once the hourly in-app rate limit has been reached, delivery must
        be suppressed.
        """

        user = self.create_user(
            email="rate-limit@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        cache.set(
            f"in_app_rate_limit:{user.pk}",
            100,
            timeout=3600,
        )

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=True,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "rate_limited",
        )

        self.assertEqual(
            result["notification_id"],
            notification.pk,
        )

        self.assertEqual(
            result["user_id"],
            user.pk,
        )

        mock_websocket.assert_not_called()

    # ========================================================================
    # Rate limit increments
    # ========================================================================

    @patch(
        "notifications.tasks.in_app._dispatch_websocket",
    )
    def test_successful_delivery_increments_rate_limit(
        self,
        mock_websocket,
    ):
        """
        Successful in-app delivery consumes one rate-limit slot.
        """

        user = self.create_user(
            email="rate-limit-increment@example.com",
        )
        self.enable_in_app_notifications(user)

        notification = self.create_notification(user)

        key = f"in_app_rate_limit:{user.pk}"

        self.assertIsNone(
            cache.get(key),
        )

        result = send_in_app_notification(
            notification.pk,
            dispatch_websocket=False,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["status"],
            "dispatched",
        )

        self.assertEqual(
            cache.get(key),
            1,
        )

        mock_websocket.assert_not_called()



# ============================================================================
# SERVICE -> TASK CONTRACT
# ============================================================================

class InAppNotificationDispatchContractTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="08012345678",
            password="testpass123",
        )

        NotificationPreference.objects.create(
            user=self.user,
            notifications_enabled=True,
            in_app_enabled=True,
        )

    @patch("notifications.tasks.in_app.send_in_app_notification.delay")
    def test_in_app_notification_dispatches_to_celery(self, mock_delay):
        """
        NotificationService must dispatch the persisted UserNotification
        to the in-app Celery task using only its primary key.
        """

        # NotificationService schedules channel dispatch with
        # transaction.on_commit(). Execute that callback explicitly so
        # the test verifies the real production contract.
        with self.captureOnCommitCallbacks(execute=True):
            notification = NotificationService.notify(
                user=self.user,
                module="accounts",
                notification_type=UserNotification.NotificationType.INFO,
                title="Test notification",
                message="Test message",
                channels=[CHANNEL_IN_APP],
            )

        # The in-app Celery task must receive only the persisted
        # UserNotification primary key.
        mock_delay.assert_called_once_with(
            notification_id=notification.pk,
        )

        # Explicitly verify that the task received the correct ID.
        call_args = mock_delay.call_args.kwargs

        self.assertEqual(
            call_args["notification_id"],
            notification.pk,
        )

        # Verify that the notification was actually persisted.
        self.assertTrue(
            UserNotification.objects.filter(
                pk=notification.pk,
            ).exists()
        )
