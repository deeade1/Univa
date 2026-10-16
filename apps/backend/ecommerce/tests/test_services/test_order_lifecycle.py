# ecommerce/tests/test_services/test_order_lifecycle.py

"""
Tests for ecommerce.services.order.lifecycle.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.enums import OrderEvents, OrderStatus
from ecommerce.models.inventory import Allocation, Stock
from ecommerce.models.order import Order, OrderEvent, OrderLine
from ecommerce.models.product import Product, ProductType, ProductVariant
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.order import (
    OrderNotCancelable,
    OrderNotConfirmable,
    cancel_order,
    confirm_order,
    get_order_by_id,
    get_user_orders,
    mark_order_as_paid,
)
from django.db.models import Sum

User = get_user_model()


class OrderLifecycleTestCase(TestCase):
    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"order-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"order-channel-{uid}",
            currency_code="NGN",
            default_country="NG",
        )
        self.address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            street_address_1="123 Test St",
            city="Lagos",
            postal_code="100001",
            country="NG",
        )
        self.warehouse = Warehouse.objects.create(
            name="Main Warehouse",
            slug=f"wh-{uid}",
            address=self.address,
        )
        self.warehouse.channels.add(self.channel)

        self.product_type = ProductType.objects.create(
            name=f"Physical {uid}",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
        )
        self.product = Product.objects.create(
            name="Test Product",
            slug=f"test-{uid}",
            product_type=self.product_type,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku=f"SKU-{uid}",
            name="Default",
            track_inventory=True,
        )
        self.stock = Stock.objects.create(
            warehouse=self.warehouse,
            product_variant=self.variant,
            quantity=Decimal("100"),
            
        )

        # Create an order directly (bypassing checkout)
        self.order = Order.objects.create(
            user=self.user,
            user_email=self.user.email,
            channel=self.channel,
            currency="NGN",
            origin="checkout",
            status=OrderStatus.UNCONFIRMED,
            total_gross_amount=Decimal("2000.00"),
            total_net_amount=Decimal("2000.00"),
            subtotal_gross_amount=Decimal("2000.00"),
            subtotal_net_amount=Decimal("2000.00"),
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test Product",
            variant_name="Default",
            quantity=Decimal("2"),
            quantity_unit="unit",
            is_shipping_required=True,
            is_gift_card=False,
            currency="NGN",
            unit_price_net_amount=Decimal("1000.00"),
            unit_price_gross_amount=Decimal("1000.00"),
            total_price_net_amount=Decimal("2000.00"),
            total_price_gross_amount=Decimal("2000.00"),
        )


class TestGetOrder(OrderLifecycleTestCase):
    def test_get_by_id(self):
        order = get_order_by_id(self.order.pk)
        self.assertEqual(order.pk, self.order.pk)

    def test_get_user_orders(self):
        orders = list(get_user_orders(self.user))
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].pk, self.order.pk)


class TestConfirmOrder(OrderLifecycleTestCase):
    def test_confirms_unconfirmed(self):
        order = confirm_order(self.order)
        self.assertEqual(order.status, OrderStatus.UNFULFILLED)

    def test_emits_confirmed_event(self):
        confirm_order(self.order)
        events = OrderEvent.objects.filter(
            order=self.order, type=OrderEvents.CONFIRMED
        )
        self.assertEqual(events.count(), 1)

    def test_idempotent(self):
        confirm_order(self.order)
        confirm_order(self.order)  # should not raise
        events = OrderEvent.objects.filter(
            order=self.order, type=OrderEvents.CONFIRMED
        )
        self.assertEqual(events.count(), 1)

    def test_cannot_confirm_canceled(self):
        self.order.status = OrderStatus.CANCELED
        self.order.save(update_fields=["status"])
        with self.assertRaises(OrderNotConfirmable):
            confirm_order(self.order)


class TestMarkOrderAsPaid(OrderLifecycleTestCase):
    def test_marks_as_paid(self):
        order = mark_order_as_paid(
            self.order, payment_reference="REF-123"
        )
        self.assertEqual(order.charge_status, "full")
        self.assertEqual(
            order.total_charged_amount, order.total_gross_amount
        )

    def test_emits_event(self):
        mark_order_as_paid(self.order)
        events = OrderEvent.objects.filter(
            order=self.order, type=OrderEvents.ORDER_MARKED_AS_PAID
        )
        self.assertEqual(events.count(), 1)

    def test_idempotent(self):
        mark_order_as_paid(self.order)
        mark_order_as_paid(self.order)
        events = OrderEvent.objects.filter(
            order=self.order, type=OrderEvents.ORDER_MARKED_AS_PAID
        )
        self.assertEqual(events.count(), 1)


class TestCancelOrder(OrderLifecycleTestCase):
    def test_cancels_order(self):
        order = cancel_order(self.order, reason="customer request")
        self.assertEqual(order.status, OrderStatus.CANCELED)

    def test_emits_canceled_event(self):
        cancel_order(self.order)
        events = OrderEvent.objects.filter(
            order=self.order, type=OrderEvents.CANCELED
        )
        self.assertEqual(events.count(), 1)

    def test_deallocates_stock(self):
        from ecommerce.services.warehouse.allocation import (
            allocate_for_order_line,
        )

        # Use the real service.
        allocate_for_order_line(self.order_line, self.channel)

        # Sanity: an Allocation row exists for the order line.
        self.assertTrue(
            Allocation.objects.filter(order_line=self.order_line).exists()
        )
        self.assertEqual(
            Allocation.objects.filter(
                order_line=self.order_line,
            ).aggregate(total=Sum("quantity_allocated"))["total"],
            Decimal("2"),
        )

        cancel_order(self.order)

        self.assertFalse(
            Allocation.objects.filter(order_line=self.order_line).exists()
        )

    def test_cannot_cancel_canceled(self):
        cancel_order(self.order)
        with self.assertRaises(OrderNotCancelable):
            cancel_order(self.order)