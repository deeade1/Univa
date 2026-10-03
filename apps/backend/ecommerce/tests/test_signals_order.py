# ecommerce/tests/test_signals_order.py

"""
Tests for the OrderEvent → notification / audit bridge.

These tests use `mock.patch` to intercept the emit and audit calls
rather than performing real delivery or DB writes.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.enums import OrderEvents
from ecommerce.models.order import Order, OrderEvent
from ecommerce.signals.order import (
    ORDER_EVENT_TO_AUDIT,
    ORDER_EVENT_TO_NOTIFICATION,
)


User = get_user_model()


class _OrderTestBase(TestCase):
    """Shared setup for order signal tests."""

    def setUp(self):
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug="test-channel",
            currency_code="NGN",
            default_country="NG",
        )
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="test-password",
        )
        self.order = Order.objects.create(
            status="unfulfilled",
            origin="checkout",
            currency="NGN",
            channel=self.channel,
            user=self.user,
            user_email=self.user.email,
        )


class TestNotificationBridge(_OrderTestBase):
    @patch("notifications.events.emit_notification_event")
    def test_placed_event_emits_notification(self, mock_emit):
        OrderEvent.objects.create(
            order=self.order,
            type=OrderEvents.PLACED,
        )
        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args.kwargs
        self.assertEqual(call_kwargs["event_type"], "ORDER.CREATED")
        self.assertEqual(call_kwargs["object_type"], "Order")
        self.assertEqual(call_kwargs["object_id"], str(self.order.pk))

    @patch("notifications.events.emit_notification_event")
    def test_unmapped_event_does_not_emit(self, mock_emit):
        OrderEvent.objects.create(
            order=self.order,
            type=OrderEvents.DRAFT_CREATED,
        )
        mock_emit.assert_not_called()

    @patch("notifications.events.emit_notification_event")
    def test_guest_order_does_not_emit(self, mock_emit):
        # Create a guest order (no user)
        guest_order = Order.objects.create(
            status="unfulfilled",
            origin="checkout",
            currency="NGN",
            channel=self.channel,
            user=None,
            user_email="guest@example.com",
        )
        OrderEvent.objects.create(
            order=guest_order,
            type=OrderEvents.PLACED,
        )
        mock_emit.assert_not_called()


class TestAuditBridge(_OrderTestBase):
    @patch("audit.services.audit.audit")
    def test_placed_event_writes_audit(self, mock_audit):
        OrderEvent.objects.create(
            order=self.order,
            type=OrderEvents.PLACED,
        )
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "ECOMMERCE.ORDER_CREATED")

    @patch("audit.services.audit.audit")
    def test_canceled_event_writes_audit(self, mock_audit):
        OrderEvent.objects.create(
            order=self.order,
            type=OrderEvents.CANCELED,
        )
        mock_audit.assert_called_once()
        self.assertEqual(
            mock_audit.call_args.kwargs["action"],
            "ECOMMERCE.ORDER_CANCELLED",
        )

    @patch("audit.services.audit.audit")
    def test_unmapped_event_does_not_audit(self, mock_audit):
        OrderEvent.objects.create(
            order=self.order,
            type=OrderEvents.DRAFT_CREATED,
        )
        mock_audit.assert_not_called()


class TestMappings(TestCase):
    def test_notification_mappings_use_registered_events(self):
        from notifications.events.registry import is_registered_event

        for event_type in ORDER_EVENT_TO_NOTIFICATION.values():
            self.assertTrue(
                is_registered_event(event_type),
                f"{event_type} not registered in notifications registry",
            )

    def test_audit_mappings_use_known_actions(self):
        from audit.constants import AUDIT_ACTIONS

        for action in ORDER_EVENT_TO_AUDIT.values():
            self.assertIn(
                action,
                AUDIT_ACTIONS,
                f"{action} not in canonical AuditAction set",
            )