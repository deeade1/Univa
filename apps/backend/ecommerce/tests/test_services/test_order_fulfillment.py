# ecommerce/tests/test_services/test_order_fulfillment.py

"""
Tests for ecommerce.services.order.fulfillment.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.enums import (
    FulfillmentStatus,
    OrderEvents,
    OrderStatus,
)
from ecommerce.models.inventory import Allocation, Stock
from ecommerce.models.order import (
    Fulfillment,
    FulfillmentLine,
    Order,
    OrderEvent,
    OrderLine,
)
from ecommerce.models.product import Product, ProductType, ProductVariant
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.order import (
    FulfillmentError,
    FulfillmentLineInput,
    FulfillmentNotPossible,
    cancel_fulfillment,
    create_fulfillment,
    get_fulfillment_by_id,
)
from ecommerce.services.warehouse.allocation import (
    allocate_for_order_line,
)


User = get_user_model()


class FulfillmentTestCase(TestCase):
    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"fulfill-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"fulfill-channel-{uid}",
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

        self.order = Order.objects.create(
            user=self.user,
            user_email=self.user.email,
            channel=self.channel,
            currency="NGN",
            origin="checkout",
            status=OrderStatus.UNFULFILLED,
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
            quantity=Decimal("5"),
            quantity_unit="unit",
            is_shipping_required=True,
            is_gift_card=False,
            currency="NGN",
            unit_price_net_amount=Decimal("1000.00"),
            unit_price_gross_amount=Decimal("1000.00"),
            total_price_net_amount=Decimal("5000.00"),
            total_price_gross_amount=Decimal("5000.00"),
        )

    def _allocate_order(self):
        """Put the order in a fully allocated state."""
        allocate_for_order_line(self.order_line, self.channel)


class TestCreateFulfillment(FulfillmentTestCase):
    def test_creates_fulfillment(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("3"),
                )
            ],
        )
        self.assertEqual(fulfillment.status, FulfillmentStatus.FULFILLED)
        self.assertEqual(fulfillment.lines.count(), 1)

    def test_decrements_stock(self):
        create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("3"),
                )
            ],
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("97"))

    def test_increments_quantity_fulfilled(self):
        create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("2"),
                )
            ],
        )
        self.order_line.refresh_from_db()
        self.assertEqual(
            self.order_line.quantity_fulfilled, Decimal("2")
        )

    def test_partial_fulfillment_sets_partial_status(self):
        create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("2"),
                )
            ],
        )
        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status, OrderStatus.PARTIALLY_FULFILLED
        )

    def test_full_fulfillment_sets_fulfilled_status(self):
        create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("5"),
                )
            ],
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.FULFILLED)

    def test_emits_event(self):
        create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("1"),
                )
            ],
        )
        events = OrderEvent.objects.filter(
            order=self.order,
            type=OrderEvents.FULFILLMENT_FULFILLED_ITEMS,
        )
        self.assertEqual(events.count(), 1)

    def test_cannot_exceed_unfulfilled(self):
        with self.assertRaises(FulfillmentError):
            create_fulfillment(
                self.order,
                [
                    FulfillmentLineInput(
                        order_line=self.order_line,
                        quantity=Decimal("10"),
                    )
                ],
            )

    def test_cannot_fulfill_canceled_order(self):
        self.order.status = OrderStatus.CANCELED
        self.order.save(update_fields=["status"])
        with self.assertRaises(FulfillmentNotPossible):
            create_fulfillment(
                self.order,
                [
                    FulfillmentLineInput(
                        order_line=self.order_line,
                        quantity=Decimal("1"),
                    )
                ],
            )


class TestCancelFulfillment(FulfillmentTestCase):
    def test_cancels_fulfillment(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("2"),
                )
            ],
        )
        cancel_fulfillment(fulfillment)
        fulfillment.refresh_from_db()
        self.assertEqual(fulfillment.status, FulfillmentStatus.CANCELED)

    def test_restocks_on_cancel(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("3"),
                )
            ],
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("97"))

        cancel_fulfillment(fulfillment)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("100"))

    def test_reverts_order_status(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("5"),
                )
            ],
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.FULFILLED)

        cancel_fulfillment(fulfillment)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.UNFULFILLED)

    def test_emits_canceled_event(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("1"),
                )
            ],
        )
        cancel_fulfillment(fulfillment)
        events = OrderEvent.objects.filter(
            order=self.order,
            type=OrderEvents.FULFILLMENT_CANCELED,
        )
        self.assertEqual(events.count(), 1)


class TestGetFulfillment(FulfillmentTestCase):
    def test_get_by_id(self):
        fulfillment = create_fulfillment(
            self.order,
            [
                FulfillmentLineInput(
                    order_line=self.order_line,
                    quantity=Decimal("1"),
                )
            ],
        )
        found = get_fulfillment_by_id(fulfillment.pk)
        self.assertEqual(found.pk, fulfillment.pk)