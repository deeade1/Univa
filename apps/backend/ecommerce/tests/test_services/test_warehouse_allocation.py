# ecommerce/tests/test_services/test_warehouse_allocation.py

"""
Tests for ecommerce.services.warehouse.allocation.

These tests exercise the stock availability, reservation, and
allocation flows against the new Decimal-based model layer.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.exceptions import InsufficientStock
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.inventory import Allocation, Reservation, Stock
from ecommerce.models.order import Order, OrderLine
from ecommerce.models.product import Product, ProductType, ProductVariant
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.warehouse import (
    check_stock_availability,
    get_available_quantity,
)


User = get_user_model()


class WarehouseAllocationTestCase(TestCase):
    """Shared fixture setup for allocation tests."""

    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        # --- User + Address ---
        self.user = User.objects.create_user(
            email=f"warehouse-test-{uid}@example.com",
        )
        self.address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="Warehouse",
            street_address_1="123 Test Street",
            city="Lagos",
            postal_code="100001",
            country="NG",
        )

        # --- Channel ---
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"test-channel-{uid}",
            currency_code="NGN",
            default_country="NG",
        )

        # --- Warehouse ---
        self.warehouse = Warehouse.objects.create(
            name="Main Warehouse",
            slug=f"main-warehouse-{uid}",
            address=self.address,
        )
        self.warehouse.channels.add(self.channel)

        # --- Product + Variant + Stock ---
        self.product_type = ProductType.objects.create(
            name="Physical",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
        )
        self.product = Product.objects.create(
            name="Test Product",
            slug=f"test-product-{uid}",
            product_type=self.product_type,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku=f"TEST-SKU-{uid}",
            name="Default",
            track_inventory=True,
        )
        self.stock = Stock.objects.create(
            warehouse=self.warehouse,
            product_variant=self.variant,
            quantity=Decimal("100"),
        )

        # --- Checkout + CheckoutLine (for Reservation tests) ---
        self.checkout = Checkout.objects.create(
            channel=self.channel,
            currency="NGN",
        )
        self.checkout_line = CheckoutLine.objects.create(
            checkout=self.checkout,
            variant=self.variant,
            quantity=Decimal("1"),
            currency="NGN",
        )

        # --- Order + OrderLine (for Allocation tests) ---
        self.order = Order.objects.create(
            status="unfulfilled",
            origin="checkout",
            currency="NGN",
            channel=self.channel,
            user=self.user,
            user_email=self.user.email,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test Product",
            variant_name="Default",
            quantity=Decimal("1"),
            quantity_unit="unit",
            is_shipping_required=True,
            is_gift_card=False,
            currency="NGN",
            unit_price_net_amount=Decimal("100"),
            unit_price_gross_amount=Decimal("100"),
            total_price_net_amount=Decimal("100"),
            total_price_gross_amount=Decimal("100"),
        )


class TestGetAvailableQuantity(WarehouseAllocationTestCase):
    def test_returns_full_quantity_when_empty(self):
        available = get_available_quantity(self.variant, self.channel)
        self.assertEqual(available, Decimal("100"))

    def test_subtracts_allocations(self):
        # Create a real Allocation row of 30.
        Allocation.objects.create(
            order_line=self.order_line,
            stock=self.stock,
            quantity_allocated=Decimal("30"),
        )
        available = get_available_quantity(self.variant, self.channel)
        self.assertEqual(available, Decimal("70"))

    def test_subtracts_active_reservations(self):
        Reservation.objects.create(
            checkout_line=self.checkout_line,
            stock=self.stock,
            quantity_reserved=Decimal("15"),
            reserved_until=timezone.now() + timezone.timedelta(minutes=30),
        )
        available = get_available_quantity(self.variant, self.channel)
        self.assertEqual(available, Decimal("85"))

    def test_ignores_expired_reservations(self):
        Reservation.objects.create(
            checkout_line=self.checkout_line,
            stock=self.stock,
            quantity_reserved=Decimal("15"),
            reserved_until=timezone.now() - timezone.timedelta(minutes=1),
        )
        available = get_available_quantity(self.variant, self.channel)
        # Expired reservation should not count.
        self.assertEqual(available, Decimal("100"))


class TestCheckStockAvailability(WarehouseAllocationTestCase):
    def test_passes_when_quantity_available(self):
        # Should not raise.
        check_stock_availability(
            self.variant,
            Decimal("50"),
            self.channel,
        )

    def test_raises_when_quantity_exceeds_stock(self):
        with self.assertRaises(InsufficientStock):
            check_stock_availability(
                self.variant,
                Decimal("101"),
                self.channel,
            )

    def test_no_op_for_untracked_variant(self):
        self.variant.track_inventory = False
        self.variant.save(update_fields=["track_inventory"])
        # Should not raise, even for absurd quantities.
        check_stock_availability(
            self.variant,
            Decimal("1000000"),
            self.channel,
        )