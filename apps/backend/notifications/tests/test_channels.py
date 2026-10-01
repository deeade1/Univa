# apps/backend/notifications/tests/test_channels.py

"""
Tests for notification push channels and the Expo provider.

These tests intentionally mock the external Expo HTTP API.
No real notification is sent during the test suite.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from notifications.channels.expo import ExpoProvider
from notifications.channels.push import (
    PermanentPushError,
    PushChannel,
    PushResult,
    RetryablePushError,
)


class MockNotification:
    """Minimal notification object used by channel tests."""

    pk = 100
    title = "Test Notification"
    message = "This is a test notification."
    module = "system"
    notification_type = "general"
    priority = "normal"
    action_url = ""
    metadata = {}


class MockDevice:
    """Minimal notification device object used by channel tests."""

    pk = 200
    provider = "expo"
    device_token = "ExponentPushToken[test-token]"


class ExpoProviderTokenTest(TestCase):
    """Tests for Expo push-token validation."""

    def test_exponent_push_token_is_valid(self):
        token = "ExponentPushToken[abcdef123456]"

        self.assertTrue(
            ExpoProvider.is_valid_token(token)
        )

    def test_expo_push_token_is_valid(self):
        token = "ExpoPushToken[abcdef123456]"

        self.assertTrue(
            ExpoProvider.is_valid_token(token)
        )

    def test_empty_token_is_invalid(self):
        self.assertFalse(
            ExpoProvider.is_valid_token("")
        )

    def test_none_token_is_invalid(self):
        self.assertFalse(
            ExpoProvider.is_valid_token(None)
        )

    def test_invalid_prefix_is_rejected(self):
        token = "InvalidPushToken[abcdef123456]"

        self.assertFalse(
            ExpoProvider.is_valid_token(token)
        )

    def test_missing_closing_bracket_is_rejected(self):
        token = "ExponentPushToken[abcdef123456"

        self.assertFalse(
            ExpoProvider.is_valid_token(token)
        )

    def test_empty_token_body_is_rejected(self):
        token = "ExponentPushToken[]"

        self.assertFalse(
            ExpoProvider.is_valid_token(token)
        )


class ExpoProviderPayloadTest(TestCase):
    """Tests for Expo payload construction."""

    def setUp(self):
        self.provider = ExpoProvider(
            endpoint="http://test-expo.local",
        )

        self.notification = MockNotification()
        self.device = MockDevice()

    def test_build_payload_contains_required_fields(self):
        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertEqual(
            payload["to"],
            self.device.device_token,
        )

        self.assertEqual(
            payload["title"],
            self.notification.title,
        )

        self.assertEqual(
            payload["body"],
            self.notification.message,
        )

        self.assertEqual(
            payload["sound"],
            "default",
        )

        self.assertEqual(
            payload["priority"],
            "default",
        )

    def test_build_payload_contains_notification_metadata(self):
        self.notification.metadata = {
            "order_id": "ORD-123",
            "screen": "orders",
        }

        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertEqual(
            payload["data"]["notification_id"],
            str(self.notification.pk),
        )

        self.assertEqual(
            payload["data"]["module"],
            self.notification.module,
        )

        self.assertEqual(
            payload["data"]["notification_type"],
            self.notification.notification_type,
        )

        self.assertEqual(
            payload["data"]["metadata"],
            self.notification.metadata,
        )

    def test_android_channel_is_added_from_metadata(self):
        self.notification.metadata = {
            "android_channel_id": "orders",
        }

        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertEqual(
            payload["channelId"],
            "orders",
        )

    def test_category_id_is_added_from_metadata(self):
        self.notification.metadata = {
            "category_id": "order_updates",
        }

        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertEqual(
            payload["categoryId"],
            "order_updates",
        )

    def test_valid_ttl_is_added(self):
        self.notification.metadata = {
            "ttl": 3600,
        }

        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertEqual(
            payload["ttl"],
            3600,
        )

    def test_invalid_ttl_is_ignored(self):
        self.notification.metadata = {
            "ttl": "invalid",
        }

        payload = self.provider.build_payload(
            notification=self.notification,
            device=self.device,
        )

        self.assertNotIn(
            "ttl",
            payload,
        )


class ExpoProviderPriorityTest(TestCase):
    """Tests for priority mapping."""

    def test_urgent_priority_maps_to_high(self):
        self.assertEqual(
            ExpoProvider._map_priority("urgent"),
            "high",
        )

    def test_high_priority_maps_to_high(self):
        self.assertEqual(
            ExpoProvider._map_priority("high"),
            "high",
        )

    def test_low_priority_maps_to_low(self):
        self.assertEqual(
            ExpoProvider._map_priority("low"),
            "low",
        )

    def test_normal_priority_maps_to_default(self):
        self.assertEqual(
            ExpoProvider._map_priority("normal"),
            "default",
        )

    def test_unknown_priority_maps_to_default(self):
        self.assertEqual(
            ExpoProvider._map_priority("unknown"),
            "default",
        )


class ExpoProviderResponseTest(TestCase):
    """Tests for Expo response parsing."""

    def setUp(self):
        self.provider = ExpoProvider(
            endpoint="http://test-expo.local",
        )

    def test_successful_response_is_parsed(self):
        response = Mock()

        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "status": "ok",
                "id": "ticket-123",
            }
        }

        result = self.provider._parse_response(
            response
        )

        self.assertTrue(
            result["success"]
        )

        self.assertEqual(
            result["ticket_id"],
            "ticket-123",
        )

        self.assertFalse(
            result["permanent"]
        )

    def test_device_not_registered_is_permanent(self):
        response = Mock()

        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "status": "error",
                "message": "The device is not registered.",
                "details": {
                    "error": "DeviceNotRegistered",
                },
            }
        }

        result = self.provider._parse_response(
            response
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["permanent"]
        )

        self.assertEqual(
            result["error_code"],
            "DeviceNotRegistered",
        )

    def test_http_failure_is_retryable(self):
        response = Mock()

        response.ok = False
        response.status_code = 500
        response.json.return_value = {
            "error": "Internal server error",
        }

        result = self.provider._parse_response(
            response
        )

        self.assertFalse(
            result["success"]
        )

        self.assertFalse(
            result["permanent"]
        )

    def test_invalid_json_response_is_handled(self):
        response = Mock()

        response.ok = True
        response.status_code = 200
        response.json.side_effect = ValueError()

        result = self.provider._parse_response(
            response
        )

        self.assertFalse(
            result["success"]
        )

        self.assertFalse(
            result["permanent"]
        )


class PushChannelProviderTest(TestCase):
    """Tests for PushChannel provider selection."""

    def setUp(self):
        self.channel = PushChannel()

        self.notification = MockNotification()
        self.device = MockDevice()

    def test_expo_provider_is_registered(self):
        self.assertIn(
            "expo",
            self.channel._providers,
        )

        self.assertIsInstance(
            self.channel._providers["expo"],
            ExpoProvider,
        )

    def test_provider_name_is_normalized(self):
        self.assertEqual(
            self.channel._normalize_provider(" EXPO "),
            "expo",
        )

        self.assertEqual(
            self.channel._normalize_provider("Expo"),
            "expo",
        )

    def test_missing_provider_returns_permanent_failure(self):
        self.device.provider = ""

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["permanent"]
        )

        self.assertFalse(
            result["retryable"]
        )

        self.assertEqual(
            result["error_code"],
            "MISSING_PROVIDER",
        )

    def test_unsupported_provider_returns_permanent_failure(self):
        self.device.provider = "unknown"

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["permanent"]
        )

        self.assertEqual(
            result["error_code"],
            "UNSUPPORTED_PROVIDER",
        )

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_successful_provider_response_is_normalized(
        self,
        mock_send,
    ):
        mock_send.return_value = {
            "success": True,
            "ticket_id": "ticket-456",
        }

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertTrue(
            result["success"]
        )

        self.assertFalse(
            result["retryable"]
        )

        self.assertFalse(
            result["permanent"]
        )

        self.assertEqual(
            result["provider"],
            "expo",
        )

        self.assertEqual(
            result["provider_message_id"],
            "ticket-456",
        )

        mock_send.assert_called_once_with(
            notification=self.notification,
            device=self.device,
        )

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_permanent_provider_response_is_normalized(
        self,
        mock_send,
    ):
        mock_send.return_value = {
            "success": False,
            "permanent": True,
            "error": "DeviceNotRegistered",
            "error_code": "DeviceNotRegistered",
        }

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["permanent"]
        )

        self.assertFalse(
            result["retryable"]
        )

        self.assertEqual(
            result["error_code"],
            "DeviceNotRegistered",
        )

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_retryable_provider_response_is_normalized(
        self,
        mock_send,
    ):
        mock_send.return_value = {
            "success": False,
            "retryable": True,
            "error": "Temporary network failure",
            "error_code": "NETWORK_ERROR",
        }

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["retryable"]
        )

        self.assertFalse(
            result["permanent"]
        )

        self.assertEqual(
            result["error_code"],
            "NETWORK_ERROR",
        )

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_unexpected_provider_exception_is_retryable(
        self,
        mock_send,
    ):
        mock_send.side_effect = RuntimeError(
            "Temporary provider failure"
        )

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["retryable"]
        )

        self.assertFalse(
            result["permanent"]
        )

        self.assertEqual(
            result["error_code"],
            "PROVIDER_EXCEPTION",
        )


class PushResultTest(TestCase):
    """Tests for PushResult serialization."""

    def test_push_result_as_dict(self):
        result = PushResult(
            success=True,
            provider="expo",
            provider_message_id="ticket-789",
        )

        data = result.as_dict()

        self.assertTrue(
            data["success"]
        )

        self.assertFalse(
            data["retryable"]
        )

        self.assertFalse(
            data["permanent"]
        )

        self.assertEqual(
            data["provider"],
            "expo",
        )

        self.assertEqual(
            data["provider_message_id"],
            "ticket-789",
        )

        self.assertEqual(
            data["raw"],
            {},
        )


class PushChannelExceptionTest(TestCase):
    """Tests provider exception classification."""

    def setUp(self):
        self.channel = PushChannel()

        self.notification = MockNotification()
        self.device = MockDevice()

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_permanent_exception_becomes_permanent_result(
        self,
        mock_send,
    ):
        mock_send.side_effect = PermanentPushError(
            "Invalid credentials"
        )

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["permanent"]
        )

        self.assertFalse(
            result["retryable"]
        )

    @patch(
        "notifications.channels.push.ExpoProvider.send"
    )
    def test_retryable_exception_becomes_retryable_result(
        self,
        mock_send,
    ):
        mock_send.side_effect = RetryablePushError(
            "Expo temporarily unavailable"
        )

        result = self.channel.send_to_device(
            notification=self.notification,
            device=self.device,
        )

        self.assertFalse(
            result["success"]
        )

        self.assertTrue(
            result["retryable"]
        )

        self.assertFalse(
            result["permanent"]
        )
