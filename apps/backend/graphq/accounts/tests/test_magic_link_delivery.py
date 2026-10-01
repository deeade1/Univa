# apps/backend/graphq/accounts/tests/test_magic_link_delivery.py

"""
Tests for magic link delivery via the notification system.

These tests verify that magic link emails and SMS messages are properly
queued through the notification event system.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.models.auth import MagicLoginToken
from graphq.accounts.mutations.auth import (
    SendMagicLinkMutation,
    send_magic_link_email,
    send_magic_link_sms,
)
from notifications.events.constants import ACCOUNT_MAGIC_LINK_REQUESTED
from notifications.models.event import NotificationEvent


class MagicLinkDeliveryTestCase(TestCase):
    """Test cases for magic link delivery functions."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+1234567890",
            password="test-password",
            first_name="Test",
        )
        
        # Clear cache between tests
        cache.clear()
        
        # Create a mock token
        self.token = MagicMock(spec=MagicLoginToken)
        self.token.token = "test-token-123"
        self.token.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        self.token.redirect_to = "/dashboard"
        self.token.device_fingerprint = "test-fingerprint"
        self.token.browser_fingerprint = {"user_agent": "test-browser"}
        self.token.ip_address = "127.0.0.1"
        self.token.pk = 1
        self.token.user = self.user

    def tearDown(self):
        cache.clear()

    # =========================================================================
    # SEND MAGIC LINK EMAIL TESTS
    # =========================================================================

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_emits_event(self, mock_emit):
        """send_magic_link_email should emit a notification event."""
        send_magic_link_email(self.user, self.token)

        # Verify emit was called with correct parameters
        mock_emit.assert_called_once_with(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            module="account",
            actor=self.user,
            object_type="User",
            object_id=self.user.id,
            payload={
                "contact": self.user.email,
                "channel": "email",
                "token": self.token.token,
                "expires_at": self.token.expires_at.isoformat(),
                "redirect_to": self.token.redirect_to,
                "security_context": {
                    "device_fingerprint": self.token.device_fingerprint,
                    "browser_fingerprint": self.token.browser_fingerprint,
                    "ip_address": self.token.ip_address,
                }
            }
        )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_creates_event_in_database(self, mock_emit):
        """send_magic_link_email should create a NotificationEvent record."""
        # Make the emit function actually create the event
        def emit_side_effect(**kwargs):
            event = NotificationEvent.objects.create(
                event_type=kwargs["event_type"],
                module=kwargs["module"],
                actor=kwargs["actor"],
                object_type=kwargs["object_type"],
                object_id=kwargs["object_id"],
                payload=kwargs["payload"],
                status=NotificationEvent.Status.PENDING,
            )
            return event

        mock_emit.side_effect = emit_side_effect

        send_magic_link_email(self.user, self.token)

        # Verify event was created
        event = NotificationEvent.objects.get(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user,
        )
        self.assertEqual(event.payload["contact"], self.user.email)
        self.assertEqual(event.payload["channel"], "email")
        self.assertEqual(event.payload["token"], self.token.token)
        self.assertEqual(event.payload["security_context"]["device_fingerprint"], "test-fingerprint")

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_handles_exception(self, mock_emit):
        """send_magic_link_email should handle emit exceptions."""
        from graphql import GraphQLError

        mock_emit.side_effect = Exception("Emit failed")

        with self.assertRaises(GraphQLError) as exc:
            send_magic_link_email(self.user, self.token)

        self.assertEqual(
            str(exc.exception),
            "Unable to send magic link."
        )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_logs_success(self, mock_emit):
        """send_magic_link_email should log success."""
        with self.assertLogs("graphq.accounts.mutations.auth", level="INFO") as log:
            send_magic_link_email(self.user, self.token)

            self.assertIn(
                f"Magic link email queued: user_id={self.user.pk}",
                log.output[0]
            )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_logs_failure(self, mock_emit):
        """send_magic_link_email should log failure."""
        from graphql import GraphQLError

        mock_emit.side_effect = Exception("Emit failed")

        with self.assertRaises(GraphQLError):
            with self.assertLogs("graphq.accounts.mutations.auth", level="ERROR") as log:
                send_magic_link_email(self.user, self.token)

                self.assertIn(
                    f"Failed to queue magic link email: user_id={self.user.pk}",
                    log.output[0]
                )

    # =========================================================================
    # SEND MAGIC LINK SMS TESTS
    # =========================================================================

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_emits_event(self, mock_emit):
        """send_magic_link_sms should emit a notification event."""
        send_magic_link_sms(self.user, self.token)

        # Verify emit was called with correct parameters
        mock_emit.assert_called_once_with(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            module="account",
            actor=self.user,
            object_type="User",
            object_id=self.user.id,
            payload={
                "contact": self.user.phone_number,
                "channel": "sms",
                "token": self.token.token,
                "expires_at": self.token.expires_at.isoformat(),
                "redirect_to": self.token.redirect_to,
                "security_context": {
                    "device_fingerprint": self.token.device_fingerprint,
                    "browser_fingerprint": self.token.browser_fingerprint,
                    "ip_address": self.token.ip_address,
                }
            }
        )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_creates_event_in_database(self, mock_emit):
        """send_magic_link_sms should create a NotificationEvent record."""
        # Make the emit function actually create the event
        def emit_side_effect(**kwargs):
            event = NotificationEvent.objects.create(
                event_type=kwargs["event_type"],
                module=kwargs["module"],
                actor=kwargs["actor"],
                object_type=kwargs["object_type"],
                object_id=kwargs["object_id"],
                payload=kwargs["payload"],
                status=NotificationEvent.Status.PENDING,
            )
            return event

        mock_emit.side_effect = emit_side_effect

        send_magic_link_sms(self.user, self.token)

        # Verify event was created
        event = NotificationEvent.objects.get(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user,
        )
        self.assertEqual(event.payload["contact"], self.user.phone_number)
        self.assertEqual(event.payload["channel"], "sms")
        self.assertEqual(event.payload["token"], self.token.token)
        self.assertEqual(event.payload["security_context"]["device_fingerprint"], "test-fingerprint")

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_handles_exception(self, mock_emit):
        """send_magic_link_sms should handle emit exceptions."""
        from graphql import GraphQLError

        mock_emit.side_effect = Exception("Emit failed")

        with self.assertRaises(GraphQLError) as exc:
            send_magic_link_sms(self.user, self.token)

        self.assertEqual(
            str(exc.exception),
            "Unable to send magic link."
        )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_logs_success(self, mock_emit):
        """send_magic_link_sms should log success."""
        with self.assertLogs("graphq.accounts.mutations.auth", level="INFO") as log:
            send_magic_link_sms(self.user, self.token)

            self.assertIn(
                f"Magic link SMS queued: user_id={self.user.pk}",
                log.output[0]
            )

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_logs_failure(self, mock_emit):
        """send_magic_link_sms should log failure."""
        from graphql import GraphQLError

        mock_emit.side_effect = Exception("Emit failed")

        with self.assertRaises(GraphQLError):
            with self.assertLogs("graphq.accounts.mutations.auth", level="ERROR") as log:
                send_magic_link_sms(self.user, self.token)

                self.assertIn(
                    f"Failed to queue magic link SMS: user_id={self.user.pk}",
                    log.output[0]
                )

    # =========================================================================
    # INTEGRATION TESTS WITH MUTATIONS
    # =========================================================================

    @patch("graphq.accounts.mutations.auth.send_magic_link_email")
    def test_send_magic_link_mutation_calls_email_delivery(self, mock_send_email):
        """SendMagicLinkMutation should call send_magic_link_email."""
        # Create a request context
        from graphql import ResolveInfo
        context = MagicMock()
        context.META = {"REMOTE_ADDR": "127.0.0.1"}
        info = MagicMock(spec=ResolveInfo)
        info.context = context

        result = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            info,
            contact=self.user.email,
            channel="email",
            redirect_to="/dashboard",
        )

        # Verify send_magic_link_email was called
        mock_send_email.assert_called_once()
        
        # Check the token passed to send_magic_link_email
        call_args = mock_send_email.call_args[0]
        self.assertEqual(call_args[0].pk, self.user.pk)
        self.assertIsNotNone(call_args[1])  # Token should be a MagicLoginToken

        # Verify mutation result
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Magic link sent to your email.")

    @patch("graphq.accounts.mutations.auth.send_magic_link_sms")
    def test_send_magic_link_mutation_calls_sms_delivery(self, mock_send_sms):
        """SendMagicLinkMutation should call send_magic_link_sms."""
        from graphql import ResolveInfo
        context = MagicMock()
        context.META = {"REMOTE_ADDR": "127.0.0.1"}
        info = MagicMock(spec=ResolveInfo)
        info.context = context

        result = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            info,
            contact=self.user.phone_number,
            channel="sms",
        )

        # Verify send_magic_link_sms was called
        mock_send_sms.assert_called_once()
        
        # Verify mutation result
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Magic link sent via SMS.")

    @patch("graphq.accounts.mutations.auth.send_magic_link_email")
    def test_send_magic_link_mutation_unknown_account_returns_success(self, mock_send_email):
        """SendMagicLinkMutation should return success for unknown accounts."""
        from graphql import ResolveInfo
        context = MagicMock()
        context.META = {"REMOTE_ADDR": "127.0.0.1"}
        info = MagicMock(spec=ResolveInfo)
        info.context = context

        result = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            info,
            contact="unknown@example.com",
            channel="email",
        )

        # send_magic_link_email should NOT be called for unknown accounts
        mock_send_email.assert_not_called()

        # Verify mutation result (success to prevent account enumeration)
        self.assertTrue(result.success)
        self.assertEqual(
            result.message,
            "If the account exists, a magic link will be sent."
        )

    @patch("graphq.accounts.mutations.auth.send_magic_link_email")
    def test_send_magic_link_mutation_rate_limit(self, mock_send_email):
        """SendMagicLinkMutation should enforce rate limiting."""
        from graphql import ResolveInfo
        from graphql import GraphQLError

        context = MagicMock()
        context.META = {"REMOTE_ADDR": "127.0.0.1"}
        info = MagicMock(spec=ResolveInfo)
        info.context = context

        # First request should succeed
        result1 = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            info,
            contact=self.user.email,
            channel="email",
        )
        self.assertTrue(result1.success)
        mock_send_email.assert_called_once()

        # Second request should be rate limited
        with self.assertRaises(GraphQLError) as exc:
            SendMagicLinkMutation.mutate_and_get_payload(
                None,
                info,
                contact=self.user.email,
                channel="email",
            )
        
        self.assertEqual(
            str(exc.exception),
            "Please wait before requesting another magic link."
        )

    # =========================================================================
    # SECURITY CONTEXT TESTS
    # =========================================================================

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_magic_link_email_includes_security_context(self, mock_emit):
        """send_magic_link_email should include security context in payload."""
        send_magic_link_email(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]
        security_context = payload["security_context"]

        self.assertEqual(security_context["device_fingerprint"], "test-fingerprint")
        self.assertEqual(security_context["browser_fingerprint"], {"user_agent": "test-browser"})
        self.assertEqual(security_context["ip_address"], "127.0.0.1")

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_magic_link_sms_includes_security_context(self, mock_emit):
        """send_magic_link_sms should include security context in payload."""
        send_magic_link_sms(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]
        security_context = payload["security_context"]

        self.assertEqual(security_context["device_fingerprint"], "test-fingerprint")
        self.assertEqual(security_context["browser_fingerprint"], {"user_agent": "test-browser"})
        self.assertEqual(security_context["ip_address"], "127.0.0.1")

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_magic_link_email_includes_token_expiry(self, mock_emit):
        """send_magic_link_email should include token expiry in payload."""
        send_magic_link_email(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]

        self.assertEqual(payload["token"], self.token.token)
        self.assertEqual(payload["expires_at"], self.token.expires_at.isoformat())

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_without_redirect_to(self, mock_emit):
        """send_magic_link_email should work without redirect_to."""
        self.token.redirect_to = None

        send_magic_link_email(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]
        self.assertIsNone(payload["redirect_to"])

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_sms_without_phone_number(self, mock_emit):
        """send_magic_link_sms should handle None phone_number."""
        self.user.phone_number = None

        send_magic_link_sms(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]
        self.assertIsNone(payload["contact"])

    @patch("graphq.accounts.mutations.auth.emit_and_queue_notification_event")
    def test_send_magic_link_email_with_empty_security_context(self, mock_emit):
        """send_magic_link_email should handle empty security context."""
        self.token.device_fingerprint = None
        self.token.browser_fingerprint = {}
        self.token.ip_address = None

        send_magic_link_email(self.user, self.token)

        call_args = mock_emit.call_args[1]
        payload = call_args["payload"]
        security_context = payload["security_context"]

        self.assertIsNone(security_context["device_fingerprint"])
        self.assertEqual(security_context["browser_fingerprint"], {})
        self.assertIsNone(security_context["ip_address"])

    def test_send_magic_link_email_requires_user(self):
        """send_magic_link_email should require a user."""
        from graphql import GraphQLError

        with self.assertRaises(GraphQLError) as exc:
            send_magic_link_email(None, self.token)  # type: ignore

        self.assertEqual(
            str(exc.exception),
            "Unable to send magic link."
        )

    def test_send_magic_link_email_requires_token(self):
        """send_magic_link_email should require a token."""
        from graphql import GraphQLError

        with self.assertRaises(GraphQLError) as exc:
            send_magic_link_email(self.user, None)  # type: ignore

        self.assertEqual(
            str(exc.exception),
            "Unable to send magic link."
        )


# =========================================================================
# RUNNER
# =========================================================================

if __name__ == "__main__":
    import django
    django.setup()
    from django.test import runner
    runner.DiscoverRunner().run_tests([
        "graphq.accounts.tests.test_magic_link_delivery"
    ])