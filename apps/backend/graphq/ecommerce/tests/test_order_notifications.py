# graphq/ecommerce/tests/test_order_notifications.py

"""
Tests for the OrderEvent → NotificationEvent bridge.

Each test creates an OrderEvent directly and asserts that a
NotificationEvent is emitted (or not) based on the mapping.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from ecommerce.models.enums import OrderEvents
from ecommerce.models.order import Order, OrderEvent
from ecommerce.models.channel import Channel
from notifications.models.event import NotificationEvent


# =====================================================================
# FIXTURES
# =====================================================================


@pytest.fixture
def user_a(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        email="customer@example.com",
        password="secret",
    )


@pytest.fixture
def channel(db):
    return Channel.objects.create(
        name="Test Channel",
        slug=f"test-{uuid4().hex[:8]}",
        currency_code="NGN",
        default_country="NG",
        is_active=True,
    )


@pytest.fixture
def order(db, channel, user_a):
    return Order.objects.create(
        channel=channel,
        currency="NGN",
        user=user_a,
        user_email=user_a.email,
        origin="checkout",
        status="unfulfilled",
        total_gross_amount=Decimal("1500.00"),
    )


# =====================================================================
# HELPERS
# =====================================================================


def _emit_event(order, event_type, **parameters):
    return OrderEvent.objects.create(
        order=order,
        type=event_type,
        parameters=parameters,
    )


def _notifications_for(order, event_type):
    return NotificationEvent.objects.filter(
        event_type=event_type,
        object_type="Order",
        object_id=str(order.pk),
    )


# =====================================================================
# TESTS
# =====================================================================


class TestOrderPlaced:

    def test_placed_emits_order_created_notification(self, order):
        _emit_event(order, OrderEvents.PLACED)
        assert _notifications_for(order, "ORDER.CREATED").count() == 1

    def test_placed_emits_only_one_notification(self, order):
        _emit_event(order, OrderEvents.PLACED)
        _emit_event(order, OrderEvents.PLACED)  # duplicate event
        # Idempotency guard on the relay prevents duplicate notifications.
        assert _notifications_for(order, "ORDER.CREATED").count() == 1


class TestOrderPaid:

    def test_marked_as_paid_emits_payment_successful_notification(
        self, order,
    ):
        _emit_event(order, OrderEvents.ORDER_MARKED_AS_PAID)
        assert _notifications_for(order, "PAYMENT.SUCCESSFUL").count() == 1


class TestOrderCanceled:

    def test_canceled_emits_order_cancelled_notification(self, order):
        _emit_event(order, OrderEvents.CANCELED)
        assert _notifications_for(order, "ORDER.CANCELLED").count() == 1


class TestOrderRefunded:

    def test_payment_refunded_emits_order_refunded_notification(
        self, order,
    ):
        _emit_event(
            order,
            OrderEvents.PAYMENT_REFUNDED,
            refund_id="1",
            amount="1500.00",
            currency="NGN",
        )
        assert _notifications_for(order, "ORDER.REFUNDED").count() == 1


class TestOrderPaymentFailed:

    def test_payment_failed_emits_payment_failed_notification(
        self, order,
    ):
        _emit_event(
            order,
            OrderEvents.PAYMENT_FAILED,
            execution_id="exec-1",
            failure_code="provider_error",
            failure_reason="Card declined",
        )
        assert _notifications_for(order, "PAYMENT.FAILED").count() == 1


class TestEventWithoutMapping:

    def test_unmapped_event_type_emits_no_notification(self, order):
        _emit_event(order, OrderEvents.NOTE_ADDED, message="...")
        # There is no mapping for NOTE_ADDED.
        assert NotificationEvent.objects.filter(
            object_type="Order",
            object_id=str(order.pk),
        ).count() == 0


class TestGuestOrder:

    def test_guest_order_emits_no_notification(
        self, db, channel,
    ):
        """
        Guest orders have no user_id; the relay skips them.

        This documents the current behavior — see Phase 10's known
        limitation for guest-order notifications.
        """
        guest_order = Order.objects.create(
            channel=channel,
            currency="NGN",
            user=None,
            user_email="guest@example.com",
            origin="checkout",
            status="unfulfilled",
            total_gross_amount=Decimal("1500.00"),
        )

        _emit_event(guest_order, OrderEvents.PLACED)

        assert NotificationEvent.objects.filter(
            object_type="Order",
            object_id=str(guest_order.pk),
        ).count() == 0
        
# =====================================================================
# GUEST ORDERS
# =====================================================================


class TestGuestOrderEmails:

    def test_guest_order_sends_email(
        self, db, channel, mailoutbox,
    ):
        guest_order = Order.objects.create(
            channel=channel,
            currency="NGN",
            user=None,
            user_email="guest@example.com",
            origin="checkout",
            status="unfulfilled",
            total_gross_amount=Decimal("1500.00"),
        )

        _emit_event(guest_order, OrderEvents.PLACED)

        assert len(mailoutbox) == 1
        msg = mailoutbox[0]
        assert "guest@example.com" in msg.to
        assert "Order received" in msg.subject

    def test_guest_order_creates_no_notification_event(
        self, db, channel, mailoutbox,
    ):
        """
        Guest orders skip the notification subsystem entirely.
        They get an email, not a NotificationEvent.
        """
        guest_order = Order.objects.create(
            channel=channel,
            currency="NGN",
            user=None,
            user_email="guest@example.com",
            origin="checkout",
            status="unfulfilled",
            total_gross_amount=Decimal("1500.00"),
        )

        _emit_event(guest_order, OrderEvents.PLACED)

        assert NotificationEvent.objects.filter(
            object_type="Order",
            object_id=str(guest_order.pk),
        ).count() == 0

    def test_guest_order_without_email_skips_everything(
        self, db, channel, mailoutbox,
    ):
        """
        An order with no user and no email produces nothing.
        """
        orphan_order = Order.objects.create(
            channel=channel,
            currency="NGN",
            user=None,
            user_email="",
            origin="checkout",
            status="unfulfilled",
            total_gross_amount=Decimal("1500.00"),
        )

        _emit_event(orphan_order, OrderEvents.PLACED)

        assert len(mailoutbox) == 0
        assert NotificationEvent.objects.filter(
            object_type="Order",
            object_id=str(orphan_order.pk),
        ).count() == 0

    def test_registered_user_does_not_trigger_guest_email(
        self, order, mailoutbox,
    ):
        """
        Registered users flow through the notification subsystem;
        the direct email path is not taken.
        """
        _emit_event(order, OrderEvents.PLACED)

        assert len(mailoutbox) == 0
        # But the notification event was created.
        assert NotificationEvent.objects.filter(
            object_type="Order",
            object_id=str(order.pk),
        ).count() == 1