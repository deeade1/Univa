"""
Tests for NotificationService email dispatch.

## Architectural contract

The notification service imports the task locally inside _dispatch_email().
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import TestCase

from notifications.models import (
    NotificationPreference,
    UserNotification,
)
from notifications.services.notification_service import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    NotificationService,
)

User = get_user_model()


# ============================================================================
# TEST HELPERS
# ============================================================================


class NotificationEmailTestMixin:
    """Shared helpers for notification email dispatch tests."""

    def create_user(
        self,
        *,
        email: str = "notification-test@example.com",
    ):
        """Create a persisted user using the configured User model."""

        return User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

    def enable_email_notifications(self, user):
        """
        Configure the user's notification preferences so email delivery
        is permitted by NotificationService.resolve_channels().
        """

        preferences, _ = (
            NotificationPreference.objects.get_or_create(
                user=user,
            )
        )

        update_fields = []

        if not preferences.notifications_enabled:
            preferences.notifications_enabled = True
            update_fields.append("notifications_enabled")

        if hasattr(preferences, "email_enabled"):
            if not preferences.email_enabled:
                preferences.email_enabled = True
                update_fields.append("email_enabled")

        if update_fields:
            preferences.save(
                update_fields=update_fields,
            )

        return preferences

    def create_notification(
        self,
        user,
        *,
        dispatch: bool = True,
        channels=None,
    ):
        """
        Create a notification exclusively through the authoritative
        NotificationService API.
        """

        return NotificationService.notify(
            user=user,
            module="system",
            notification_type=(
                UserNotification.NotificationType.INFO
            ),
            title="Test notification",
            message="This is a test notification.",
            metadata={
                "test": True,
            },
            action_url="https://example.com/notifications/1",
            channels=(
                channels
                if channels is not None
                else [CHANNEL_EMAIL]
            ),
            priority=UserNotification.Priority.NORMAL,
            dispatch=dispatch,
        )


# ============================================================================
# EMAIL DISPATCH TESTS
# ============================================================================


class NotificationEmailDispatchTestCase(
    NotificationEmailTestMixin,
    TestCase,
):
    """
    Tests the NotificationService -> on_commit -> email Celery boundary.
    """

    # ========================================================================
    # dispatch=False
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_dispatch_false_does_not_queue_email_task(
        self,
        mock_email_delay,
    ):
        """
        dispatch=False persists the notification but does not register
        or execute email delivery.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        notification = self.create_notification(
            user,
            dispatch=False,
            channels=[CHANNEL_EMAIL],
        )

        self.assertIsNotNone(notification.pk)

        self.assertTrue(
            UserNotification.objects.filter(
                pk=notification.pk,
            ).exists(),
        )

        mock_email_delay.assert_not_called()

    # ========================================================================
    # ID-only Celery payload
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_dispatch_passes_notification_id(
        self,
        mock_email_delay,
    ):
        """
        Celery receives only the persisted UserNotification primary key.

        The service currently calls:

            delay(notification_id=notification_id)

        Therefore the test intentionally verifies the keyword argument.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            notification = self.create_notification(
                user,
                channels=[CHANNEL_EMAIL],
            )

        mock_email_delay.assert_called_once_with(
            notification_id=notification.pk,
        )

        args, kwargs = mock_email_delay.call_args

        self.assertEqual(
            args,
            (),
        )

        self.assertEqual(
            kwargs,
            {
                "notification_id": notification.pk,
            },
        )

        self.assertIsInstance(
            kwargs["notification_id"],
            int,
        )

        self.assertNotIsInstance(
            kwargs["notification_id"],
            UserNotification,
        )

    # ========================================================================
    # Email channel not selected
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_is_not_queued_when_email_channel_is_not_selected(
        self,
        mock_email_delay,
    ):
        """
        Email is not scheduled when email is absent from the selected
        channels.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            notification = NotificationService.notify(
                user=user,
                module="system",
                notification_type=(
                    UserNotification.NotificationType.INFO
                ),
                title="Test notification",
                message="This is a test notification.",
                metadata={
                    "test": True,
                },
                channels=[CHANNEL_IN_APP],
                priority=UserNotification.Priority.NORMAL,
                dispatch=True,
            )

        self.assertIsNotNone(notification.pk)

        mock_email_delay.assert_not_called()

    # ========================================================================
    # Before commit
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_task_is_not_queued_before_commit(
        self,
        mock_email_delay,
    ):
        """
        Email delivery is registered through on_commit() but is not
        executed while the surrounding transaction is still open.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=False,
        ) as callbacks:

            with transaction.atomic():

                notification = self.create_notification(
                    user,
                    channels=[CHANNEL_EMAIL],
                )

                self.assertIsNotNone(
                    notification.pk,
                )

                self.assertTrue(
                    UserNotification.objects.filter(
                        pk=notification.pk,
                    ).exists(),
                )

                # The transaction is still open.
                # Celery must not have been called.
                mock_email_delay.assert_not_called()

        # One callback was registered.
        self.assertEqual(
            len(callbacks),
            1,
        )

        # execute=False means the callback was captured but deliberately
        # not executed.
        mock_email_delay.assert_not_called()

    # ========================================================================
    # After commit
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_task_is_queued_after_commit(
        self,
        mock_email_delay,
    ):
        """
        Email delivery executes only after a successful transaction commit.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=True,
        ) as callbacks:

            with transaction.atomic():

                notification = self.create_notification(
                    user,
                    channels=[CHANNEL_EMAIL],
                )

                # Still inside the transaction.
                mock_email_delay.assert_not_called()

        # Exactly one on_commit callback was registered.
        self.assertEqual(
            len(callbacks),
            1,
        )

        # Successful commit executed the callback.
        mock_email_delay.assert_called_once_with(
            notification_id=notification.pk,
        )

    # ========================================================================
    # Multiple channels
    # ========================================================================

    @patch(
        "notifications.services.notification_service."
        "NotificationService._dispatch_in_app",
    )
    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_dispatches_once_when_multiple_channels_are_selected(
        self,
        mock_email_delay,
        mock_in_app_dispatch,
    ):
        """
        Multiple selected channels must not cause duplicate email delivery.

        Email is scheduled exactly once, while the independent in-app
        dispatcher is also invoked exactly once.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            notification = NotificationService.notify(
                user=user,
                module="system",
                notification_type=(
                    UserNotification.NotificationType.INFO
                ),
                title="Multi-channel notification",
                message="This notification uses multiple channels.",
                metadata={
                    "test": True,
                },
                channels=[
                    CHANNEL_EMAIL,
                    CHANNEL_IN_APP,
                ],
                priority=UserNotification.Priority.NORMAL,
                dispatch=True,
            )

        mock_email_delay.assert_called_once_with(
            notification_id=notification.pk,
        )

        mock_in_app_dispatch.assert_called_once_with(
            notification.pk,
        )

    # ========================================================================
    # Persistence before dispatch
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_notification_is_persisted_before_email_dispatch(
        self,
        mock_email_delay,
    ):
        """
        The notification must already exist in the database when the
        email task is scheduled.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        def assert_notification_exists(
            *,
            notification_id,
        ):
            self.assertTrue(
                UserNotification.objects.filter(
                    pk=notification_id,
                ).exists(),
                "Email dispatch occurred before UserNotification "
                "was persisted.",
            )

        mock_email_delay.side_effect = (
            assert_notification_exists
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            notification = self.create_notification(
                user,
                channels=[CHANNEL_EMAIL],
            )

        mock_email_delay.assert_called_once_with(
            notification_id=notification.pk,
        )

    # ========================================================================
    # Callback registration count
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_email_registers_exactly_one_on_commit_callback(
        self,
        mock_email_delay,
    ):
        """
        An email-only notification registers exactly one on_commit callback.
        """

        user = self.create_user()
        self.enable_email_notifications(user)

        with self.captureOnCommitCallbacks(
            execute=False,
        ) as callbacks:

            notification = self.create_notification(
                user,
                channels=[CHANNEL_EMAIL],
            )

            self.assertIsNotNone(
                notification.pk,
            )

            mock_email_delay.assert_not_called()

        self.assertEqual(
            len(callbacks),
            1,
        )

        mock_email_delay.assert_not_called()


# ============================================================================
# ROLLBACK TESTS
# ============================================================================


class NotificationEmailRollbackTestCase(
    NotificationEmailTestMixin,
    TestCase,
):
    """
    Tests transaction rollback semantics for email notification dispatch.
    """

    # ========================================================================
    # Rollback
    # ========================================================================

    @patch(
        "notifications.tasks.email.send_email_notification.delay",
    )
    def test_rollback_discards_email_on_commit_callback(
        self,
        mock_email_delay,
    ):
        """
        A rolled-back transaction must discard the email on_commit callback.

        This test explicitly proves both sides of the transaction boundary:

            1. Callback is registered while the transaction is alive.
            2. Rollback removes/discards that callback.
            3. send_email_notification.delay() is never called.
            4. UserNotification does not survive the rollback.
        """

        user = self.create_user(
            email="rollback-notification@example.com",
        )
        self.enable_email_notifications(user)

        # Record the callback state before entering our transaction.
        initial_callbacks = list(
            connection.run_on_commit
        )

        notification = None

        with self.assertRaises(
            RuntimeError,
        ):
            with transaction.atomic():

                notification = NotificationService.notify(
                    user=user,
                    module="accounts",
                    notification_type=(
                        UserNotification.NotificationType.INFO
                    ),
                    title="Rollback test",
                    message=(
                        "This notification must be rolled back."
                    ),
                    channels=[CHANNEL_EMAIL],
                    priority=UserNotification.Priority.NORMAL,
                    dispatch=True,
                )

                # ------------------------------------------------------------
                # 1. Notification exists inside the transaction.
                # ------------------------------------------------------------

                self.assertIsNotNone(
                    notification.pk,
                )

                self.assertTrue(
                    UserNotification.objects.filter(
                        pk=notification.pk,
                    ).exists(),
                )

                # ------------------------------------------------------------
                # 2. on_commit callback has been registered while the
                #    transaction is still alive.
                # ------------------------------------------------------------

                current_callbacks = list(
                    connection.run_on_commit
                )

                self.assertEqual(
                    len(current_callbacks),
                    len(initial_callbacks) + 1,
                    (
                        "NotificationService.notify() must register "
                        "exactly one new on_commit callback while the "
                        "transaction is active."
                    ),
                )

                # ------------------------------------------------------------
                # The callback has NOT executed.
                # ------------------------------------------------------------

                mock_email_delay.assert_not_called()

                # ------------------------------------------------------------
                # Force rollback.
                # ------------------------------------------------------------

                raise RuntimeError(
                    "Intentional rollback for notification email test."
                )

        # --------------------------------------------------------------------
        # 3. Rollback must remove/discard the newly registered callback.
        # --------------------------------------------------------------------

        callbacks_after_rollback = list(
            connection.run_on_commit
        )

        self.assertEqual(
            callbacks_after_rollback,
            initial_callbacks,
            (
                "The email on_commit callback was not discarded "
                "after transaction rollback."
            ),
        )

        # --------------------------------------------------------------------
        # 4. Notification must not survive rollback.
        # --------------------------------------------------------------------

        self.assertIsNotNone(
            notification,
        )

        self.assertFalse(
            UserNotification.objects.filter(
                pk=notification.pk,
            ).exists(),
            "UserNotification survived transaction rollback.",
        )

        # --------------------------------------------------------------------
        # 5. Celery email task must NEVER have been queued.
        # --------------------------------------------------------------------

        mock_email_delay.assert_not_called()