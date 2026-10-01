# apps/backend/notifications/tests/test_models.py

"""
Tests for notification models.

These tests verify model fields, methods, properties, and constraints
without making external API calls.
"""
from uuid import uuid4
from datetime import time

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from notifications.models import (
    NotificationDevice,
    NotificationEvent,
    NotificationPreference,
    NotificationPush,
    UserNotification,
)

User = get_user_model()


# ============================================================================
# TEST HELPERS
# ============================================================================
class NotificationModelTestMixin:
    """Mixin providing common test utilities."""

    def create_user(self, **kwargs):
        """
        Create a test user compatible with the centralized email-based
        accounts.User model.

        The production User model does not have a username field.
        """
        unique_email = f"notification-model-{uuid4().hex}@example.com"

        defaults = {
            "email": unique_email,
            "password": "testpass123",
        }

        defaults.update(kwargs)

        # The current User model has no username field.
        defaults.pop("username", None)

        return User.objects.create_user(**defaults)
    
    def create_event(self, **kwargs):
        """Create a test notification event."""
        user = kwargs.pop('actor', None) or self.create_user()
        defaults = {
            'event_type': 'TEST.EVENT',
            'module': 'test',
            'actor': user,
            'object_type': 'Test',
            'object_id': '1',
            'payload': {'test': 'data'},
        }
        defaults.update(kwargs)
        return NotificationEvent.objects.create(**defaults)

    def create_notification(self, **kwargs):
        """Create a test user notification."""
        user = kwargs.pop('recipient', None) or self.create_user()
        event = kwargs.pop('event', None) or self.create_event(actor=user)
        defaults = {
            'recipient': user,
            'event': event,
            'module': 'test',
            'notification_type': UserNotification.NotificationType.INFO,
            'priority': UserNotification.Priority.NORMAL,
            'title': 'Test Notification',
            'message': 'This is a test message.',
        }
        defaults.update(kwargs)
        return UserNotification.objects.create(**defaults)

    def create_device(self, **kwargs):
        """Create a test notification device."""
        user = kwargs.pop('user', None) or self.create_user()
        defaults = {
            'user': user,
            'platform': NotificationDevice.Platform.ANDROID,
            'provider': NotificationDevice.Provider.EXPO,
            'device_token': f'ExponentPushToken[test-{timezone.now().timestamp()}]',
            'device_id': 'device-123',
            'device_name': 'Test Device',
            'is_active': True,
            'notifications_enabled': True,
        }
        defaults.update(kwargs)
        return NotificationDevice.objects.create(**defaults)

    def create_push(self, **kwargs):
        """Create a test notification push."""
        notification = kwargs.pop('notification', None) or self.create_notification()
        device = kwargs.pop('device', None) or self.create_device(user=notification.recipient)
        defaults = {
            'notification': notification,
            'device': device,
            'provider': NotificationDevice.Provider.EXPO,
            'status': NotificationPush.PushStatus.PENDING,
        }
        defaults.update(kwargs)
        return NotificationPush.objects.create(**defaults)

    def create_preference(self, **kwargs):
        """Create a test notification preference."""
        user = kwargs.pop('user', None) or self.create_user()
        defaults = {
            'user': user,
            'notifications_enabled': True,
            'push_enabled': True,
            'in_app_enabled': True,
            'email_enabled': True,
        }
        defaults.update(kwargs)
        return NotificationPreference.objects.create(**defaults)
    
# ============================================================================
# NOTIFICATION EVENT TESTS
# ============================================================================

class NotificationEventModelTest(TestCase, NotificationModelTestMixin):
    """Tests for NotificationEvent model."""

    def test_create_event(self):
        """Test basic event creation."""
        user = self.create_user()
        event = self.create_event(actor=user)

        self.assertEqual(event.event_type, 'TEST.EVENT')
        self.assertEqual(event.module, 'test')
        self.assertEqual(event.actor, user)
        self.assertEqual(event.status, NotificationEvent.Status.PENDING)
        self.assertEqual(event.attempts, 0)
        self.assertIsNone(event.processed_at)

    def test_event_status_properties(self):
        """Test event status properties."""
        event = self.create_event()

        # Pending
        self.assertTrue(event.is_pending)
        self.assertFalse(event.is_processing)
        self.assertFalse(event.is_processed)
        self.assertFalse(event.has_failed)
        self.assertFalse(event.is_finished)

        # Processing
        event.mark_processing()
        self.assertFalse(event.is_pending)
        self.assertTrue(event.is_processing)
        self.assertFalse(event.is_processed)
        self.assertFalse(event.has_failed)
        self.assertFalse(event.is_finished)

        # Processed
        event.mark_processed()
        self.assertFalse(event.is_pending)
        self.assertFalse(event.is_processing)
        self.assertTrue(event.is_processed)
        self.assertFalse(event.has_failed)
        self.assertTrue(event.is_finished)

    def test_event_mark_processing(self):
        """Test marking event as processing."""
        event = self.create_event()
        initial_attempts = event.attempts

        event.mark_processing()
        event.refresh_from_db()

        self.assertEqual(event.status, NotificationEvent.Status.PROCESSING)
        self.assertEqual(event.attempts, initial_attempts + 1)
        self.assertEqual(event.error_message, "")

    def test_event_mark_processed(self):
        """Test marking event as processed."""
        event = self.create_event()

        event.mark_processed()
        event.refresh_from_db()

        self.assertEqual(event.status, NotificationEvent.Status.PROCESSED)
        self.assertIsNotNone(event.processed_at)
        self.assertEqual(event.error_message, "")

    def test_event_mark_failed(self):
        """Test marking event as failed."""
        event = self.create_event()
        error_message = "Processing failed due to network error"

        event.mark_failed(error_message)
        event.refresh_from_db()

        self.assertEqual(event.status, NotificationEvent.Status.FAILED)
        self.assertEqual(event.error_message, error_message)

    def test_event_mark_cancelled(self):
        """Test marking event as cancelled."""
        event = self.create_event()

        event.mark_cancelled("Duplicate event")
        event.refresh_from_db()

        self.assertEqual(event.status, NotificationEvent.Status.CANCELLED)
        self.assertEqual(event.error_message, "Duplicate event")

    def test_event_reset_for_retry(self):
        """Test resetting failed event for retry."""
        event = self.create_event()
        event.mark_failed("Temporary failure")

        event.reset_for_retry()
        event.refresh_from_db()

        self.assertEqual(event.status, NotificationEvent.Status.PENDING)
        self.assertEqual(event.error_message, "")
        self.assertIsNone(event.processed_at)

    def test_event_can_retry_property(self):
        """Test can_retry property."""
        event = self.create_event()

        # Pending events cannot retry
        self.assertFalse(event.can_retry)

        # Failed events can retry
        event.mark_failed("Failed")
        self.assertTrue(event.can_retry)

        # Processed events cannot retry
        event.mark_processed()
        self.assertFalse(event.can_retry)

    def test_event_string_representation(self):
        """Test string representation of event."""
        event = self.create_event(event_type='ORDER.CREATED', module='order')
        self.assertIn('ORDER.CREATED', str(event))
        self.assertIn('order', str(event))


# ============================================================================
# USER NOTIFICATION TESTS
# ============================================================================

class UserNotificationModelTest(TestCase, NotificationModelTestMixin):
    """Tests for UserNotification model."""

    def test_create_notification(self):
        """Test basic notification creation."""
        user = self.create_user()
        event = self.create_event(actor=user)
        notification = self.create_notification(
            recipient=user,
            event=event,
            title="Test Notification",
            message="Test Message"
        )

        self.assertEqual(notification.recipient, user)
        self.assertEqual(notification.event, event)
        self.assertEqual(notification.title, "Test Notification")
        self.assertEqual(notification.message, "Test Message")
        self.assertFalse(notification.is_read)
        self.assertFalse(notification.is_archived)

    def test_notification_read_state(self):
        """Test marking notification as read/unread."""
        notification = self.create_notification()

        # Initially unread
        self.assertTrue(notification.is_unread)
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

        # Mark as read
        notification.mark_as_read()
        notification.refresh_from_db()
        self.assertFalse(notification.is_unread)
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

        # Mark as unread
        notification.mark_as_unread()
        notification.refresh_from_db()
        self.assertTrue(notification.is_unread)
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_notification_archive_state(self):
        """Test archiving and unarchiving notification."""
        notification = self.create_notification()

        # Initially not archived
        self.assertTrue(notification.is_active)
        self.assertFalse(notification.is_archived)
        self.assertIsNone(notification.archived_at)

        # Archive
        notification.archive()
        notification.refresh_from_db()
        self.assertFalse(notification.is_active)
        self.assertTrue(notification.is_archived)
        self.assertIsNotNone(notification.archived_at)

        # Unarchive
        notification.unarchive()
        notification.refresh_from_db()
        self.assertTrue(notification.is_active)
        self.assertFalse(notification.is_archived)
        self.assertIsNone(notification.archived_at)

    def test_notification_unique_constraint(self):
        """Test unique constraint for event and recipient."""
        user = self.create_user()
        event = self.create_event(actor=user)

        # Create first notification
        self.create_notification(recipient=user, event=event)

        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            self.create_notification(recipient=user, event=event)

    def test_notification_string_representation(self):
        """Test string representation of notification."""
        notification = self.create_notification(title="Welcome!")
        self.assertIn("Welcome!", str(notification))
        self.assertIn(str(notification.recipient), str(notification))


# ============================================================================
# NOTIFICATION DEVICE TESTS
# ============================================================================

class NotificationDeviceModelTest(TestCase, NotificationModelTestMixin):
    """Tests for NotificationDevice model."""

    def test_create_device(self):
        """Test basic device creation."""
        user = self.create_user()
        device = self.create_device(user=user)

        self.assertEqual(device.user, user)
        self.assertEqual(device.platform, NotificationDevice.Platform.ANDROID)
        self.assertEqual(device.provider, NotificationDevice.Provider.EXPO)
        self.assertTrue(device.is_active)
        self.assertTrue(device.notifications_enabled)

    def test_device_can_receive_notifications(self):
        """Test can_receive_notifications property."""
        user = self.create_user()
        device = self.create_device(user=user)

        # Fully active
        self.assertTrue(device.can_receive_notifications)

        # Inactive
        device.is_active = False
        self.assertFalse(device.can_receive_notifications)

        # Notifications disabled
        device.is_active = True
        device.notifications_enabled = False
        self.assertFalse(device.can_receive_notifications)

        # No token
        device.notifications_enabled = True
        device.device_token = ""
        self.assertFalse(device.can_receive_notifications)

    def test_device_touch(self):
        """Test updating last_used_at."""
        user = self.create_user()
        device = self.create_device(user=user)

        initial_last_used = device.last_used_at
        device.touch()
        device.refresh_from_db()

        self.assertIsNotNone(device.last_used_at)
        if initial_last_used:
            self.assertGreater(device.last_used_at, initial_last_used)

    def test_device_activate_deactivate(self):
        """Test activating and deactivating device."""
        user = self.create_user()
        device = self.create_device(user=user)

        # Deactivate
        device.deactivate("Token expired")
        device.refresh_from_db()
        self.assertFalse(device.is_active)
        self.assertEqual(device.last_error, "Token expired")

        # Activate
        device.activate()
        device.refresh_from_db()
        self.assertTrue(device.is_active)
        self.assertEqual(device.last_error, "")

    def test_device_notifications_enable_disable(self):
        """Test enabling/disabling notifications."""
        user = self.create_user()
        device = self.create_device(user=user)

        # Disable
        device.disable_notifications()
        device.refresh_from_db()
        self.assertFalse(device.notifications_enabled)

        # Enable
        device.enable_notifications()
        device.refresh_from_db()
        self.assertTrue(device.notifications_enabled)
        self.assertTrue(device.is_active)

    
    def test_device_string_representation(self):
        """Test string representation of device."""
        user = self.create_user(email="testuser@example.com")
        device = self.create_device(user=user)

        self.assertIn(str(user), str(device))
        self.assertIn("android/expo", str(device).lower())


# ============================================================================
# NOTIFICATION PUSH TESTS
# ============================================================================

class NotificationPushModelTest(TestCase, NotificationModelTestMixin):
    """Tests for NotificationPush model."""

    def test_create_push(self):
        """Test basic push creation."""
        notification = self.create_notification()
        device = self.create_device(user=notification.recipient)
        push = self.create_push(
            notification=notification,
            device=device,
            provider=NotificationDevice.Provider.EXPO
        )

        self.assertEqual(push.notification, notification)
        self.assertEqual(push.device, device)
        self.assertEqual(push.provider, NotificationDevice.Provider.EXPO)
        self.assertEqual(push.status, NotificationPush.PushStatus.PENDING)
        self.assertEqual(push.attempts, 0)

    def test_push_unique_constraint(self):
        """Test unique constraint for notification and device."""
        notification = self.create_notification()
        device = self.create_device(user=notification.recipient)

        # Create first push
        self.create_push(notification=notification, device=device)

        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            self.create_push(notification=notification, device=device)

    def test_push_status_properties(self):
        """Test push status properties."""
        push = self.create_push()

        # Pending
        self.assertTrue(push.is_pending)
        self.assertFalse(push.is_sent)
        self.assertFalse(push.is_failed)
        self.assertFalse(push.is_finished)

        # Processing
        push.mark_processing()
        self.assertFalse(push.is_pending)
        self.assertTrue(push.is_processing)
        self.assertFalse(push.is_sent)

        # Sent
        push.mark_sent(provider="expo", provider_message_id="ticket-123")
        self.assertFalse(push.is_processing)
        self.assertTrue(push.is_sent)
        self.assertTrue(push.is_finished)
        self.assertEqual(push.provider_message_id, "ticket-123")

        # Failed
        push = self.create_push()
        push.mark_failed("Device not registered")
        self.assertTrue(push.is_failed)
        self.assertTrue(push.can_retry)
        self.assertEqual(push.error_message, "Device not registered")

    def test_push_skipped_status(self):
        """Test skipped status."""
        push = self.create_push()
        push.mark_skipped("User opted out")

        self.assertTrue(push.is_skipped)
        self.assertTrue(push.is_finished)
        self.assertEqual(push.error_message, "User opted out")

    def test_push_increment_attempts(self):
        """Test incrementing push attempts."""
        push = self.create_push()

        push.increment_attempts()
        push.refresh_from_db()
        self.assertEqual(push.attempts, 1)

        push.increment_attempts()
        push.refresh_from_db()
        self.assertEqual(push.attempts, 2)

    def test_push_string_representation(self):
        """Test string representation of push."""
        notification = self.create_notification()
        device = self.create_device(user=notification.recipient)
        push = self.create_push(notification=notification, device=device)

        self.assertIn(str(push.notification_id), str(push))
        self.assertIn(str(push.device_id), str(push))


# ============================================================================
# NOTIFICATION PREFERENCE TESTS
# ============================================================================

class NotificationPreferenceModelTest(TestCase, NotificationModelTestMixin):
    """Tests for NotificationPreference model."""

    def test_create_preference(self):
        """Test basic preference creation."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        self.assertEqual(preference.user, user)
        self.assertTrue(preference.notifications_enabled)
        self.assertTrue(preference.push_enabled)
        self.assertTrue(preference.in_app_enabled)
        self.assertTrue(preference.email_enabled)

    def test_preference_allows_channel(self):
        """Test channel permission checks."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Default: all enabled
        self.assertTrue(preference.allows_channel('push'))
        self.assertTrue(preference.allows_channel('in_app'))
        self.assertTrue(preference.allows_channel('email'))
        self.assertFalse(preference.allows_channel('sms'))

        # Disable push
        preference.push_enabled = False
        self.assertFalse(preference.allows_channel('push'))

        # Disable global
        preference.notifications_enabled = False
        self.assertFalse(preference.allows_channel('in_app'))

    def test_preference_allows_category(self):
        """Test category permission checks."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Security categories
        self.assertTrue(preference.allows_category('security'))
        self.assertTrue(preference.allows_category('account'))

        # Social categories
        self.assertTrue(preference.allows_category('social'))
        self.assertTrue(preference.allows_category('chat'))

        # Transactional categories (default)
        self.assertTrue(preference.allows_category('order'))
        self.assertTrue(preference.allows_category('payment'))
        self.assertTrue(preference.allows_category('transport'))

        # Disable transactional
        preference.transactional_enabled = False
        self.assertFalse(preference.allows_category('order'))
        self.assertTrue(preference.allows_category('security'))  # Still enabled
 
    def test_preference_quiet_hours(self):
        """Test quiet hours functionality."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Configure quiet hours (10 PM to 7 AM)
        preference.quiet_hours_enabled = True
        preference.quiet_hours_start = time(22, 0, 0)
        preference.quiet_hours_end = time(7, 0, 0)
        preference.save()

        # Test within quiet hours (11 PM)
        test_time = time(23, 0, 0)
        self.assertTrue(preference.is_within_quiet_hours(test_time))

        # Test outside quiet hours (10 AM)
        test_time = time(10, 0, 0)
        self.assertFalse(preference.is_within_quiet_hours(test_time))

        # Test normal range (8 AM to 5 PM)
        preference.quiet_hours_start = time(8, 0, 0)
        preference.quiet_hours_end = time(17, 0, 0)
        preference.save()

        test_time = time(12, 0, 0)
        self.assertTrue(preference.is_within_quiet_hours(test_time))

        test_time = time(20, 0, 0)
        self.assertFalse(preference.is_within_quiet_hours(test_time))


    def test_preference_can_deliver_immediately(self):
        """Test immediate delivery permission."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Default: can deliver
        self.assertTrue(preference.can_deliver_immediately())

        # Disabled global
        preference.notifications_enabled = False
        self.assertFalse(preference.can_deliver_immediately())
        preference.notifications_enabled = True

        # Disabled channel
        preference.push_enabled = False
        self.assertFalse(
            preference.can_deliver_immediately(
                channel="push",
            )
        )
        preference.push_enabled = True

        # Non-instant frequency
        preference.frequency = NotificationPreference.Frequency.DAILY
        self.assertFalse(preference.can_deliver_immediately())
        preference.frequency = NotificationPreference.Frequency.INSTANT

        # Quiet hours
        preference.quiet_hours_enabled = True
        preference.quiet_hours_start = time(22, 0, 0)
        preference.quiet_hours_end = time(7, 0, 0)
        preference.save()

        test_time = time(23, 0, 0)
        self.assertFalse(
            preference.can_deliver_immediately(
                current_time=test_time,
            )
        )
        
        
    def test_preference_enable_disable_all(self):
        """Test enable/disable all notifications."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Disable all
        preference.disable_all()
        preference.refresh_from_db()
        self.assertFalse(preference.notifications_enabled)

        # Enable all
        preference.enable_all()
        preference.refresh_from_db()
        self.assertTrue(preference.notifications_enabled)

    def test_preference_channel_helpers(self):
        """Test channel helper methods."""
        user = self.create_user()
        preference = self.create_preference(user=user)

        # Disable push
        preference.disable_push()
        preference.refresh_from_db()
        self.assertFalse(preference.push_enabled)

        # Enable push
        preference.enable_push()
        preference.refresh_from_db()
        self.assertTrue(preference.push_enabled)
        self.assertTrue(preference.notifications_enabled)

        # Disable in-app
        preference.disable_in_app()
        preference.refresh_from_db()
        self.assertFalse(preference.in_app_enabled)

        # Enable in-app
        preference.enable_in_app()
        preference.refresh_from_db()
        self.assertTrue(preference.in_app_enabled)

        # Disable email
        preference.disable_email()
        preference.refresh_from_db()
        self.assertFalse(preference.email_enabled)

        # Enable email
        preference.enable_email()
        preference.refresh_from_db()
        self.assertTrue(preference.email_enabled)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "NotificationDeviceModelTest",
    "NotificationEventModelTest",
    "NotificationPreferenceModelTest",
    "NotificationPushModelTest",
    "UserNotificationModelTest",
]