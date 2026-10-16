# ecommerce/tests/test_services/test_checkout_lifecycle.py

"""
Tests for ecommerce.services.checkout.lifecycle.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.exceptions import InsufficientStock
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.inventory import Reservation, Stock
from ecommerce.models.product import Product, ProductType, ProductVariant
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.checkout import (
    add_variant_to_checkout,
    clear_checkout,
    create_checkout,
    remove_checkout_line,
    set_checkout_shipping_method,
    update_checkout_line_quantity,
)


User = get_user_model()


class CheckoutLifecycleTestCase(TestCase):
    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"checkout-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"checkout-channel-{uid}",
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
            slug=f"main-{uid}",
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


class TestCreateCheckout(CheckoutLifecycleTestCase):
    def test_creates_with_defaults(self):
        checkout = create_checkout(self.channel)
        self.assertEqual(checkout.channel_id, self.channel.pk)
        self.assertEqual(checkout.currency, "NGN")
        self.assertIsNone(checkout.user_id)

    def test_attaches_user(self):
        checkout = create_checkout(self.channel, user=self.user)
        self.assertEqual(checkout.user_id, self.user.pk)
        self.assertEqual(checkout.email, self.user.email)

    def test_guest_with_email(self):
        checkout = create_checkout(
            self.channel, email="guest@example.com"
        )
        self.assertIsNone(checkout.user_id)
        self.assertEqual(checkout.email, "guest@example.com")


class TestAddVariant(CheckoutLifecycleTestCase):
    def test_adds_first_line(self):
        checkout = create_checkout(self.channel)
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        self.assertEqual(line.quantity, Decimal("2"))
        self.assertEqual(checkout.lines.count(), 1)

    def test_merges_into_existing_line(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("3")
        )
        self.assertEqual(line.quantity, Decimal("5"))
        self.assertEqual(checkout.lines.count(), 1)

    def test_replace_sets_quantity(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("7"), replace=True
        )
        self.assertEqual(line.quantity, Decimal("7"))

    def test_reserves_stock(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(checkout, self.variant, Decimal("3"))
        reservations = Reservation.objects.filter(
            checkout_line__checkout=checkout
        )
        self.assertEqual(
            sum(r.quantity_reserved for r in reservations),
            Decimal("3"),
        )

    def test_raises_when_insufficient(self):
        checkout = create_checkout(self.channel)
        with self.assertRaises(InsufficientStock):
            add_variant_to_checkout(
                checkout, self.variant, Decimal("101")
            )


class TestUpdateLineQuantity(CheckoutLifecycleTestCase):
    def test_updates_quantity(self):
        checkout = create_checkout(self.channel)
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        result = update_checkout_line_quantity(
            checkout, line, Decimal("5")
        )
        self.assertEqual(result.quantity, Decimal("5"))

    def test_zero_deletes_line(self):
        checkout = create_checkout(self.channel)
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        result = update_checkout_line_quantity(
            checkout, line, Decimal("0")
        )
        self.assertIsNone(result)
        self.assertEqual(checkout.lines.count(), 0)

class TestRemoveLine(CheckoutLifecycleTestCase):
    def test_removes_line_and_releases_reservation(self):
        checkout = create_checkout(self.channel)
        line = add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        line_pk = line.pk  # capture before delete

        remove_checkout_line(checkout, line)

        self.assertEqual(checkout.lines.count(), 0)
        self.assertEqual(
            Reservation.objects.filter(checkout_line_id=line_pk).count(),
            0,
        )
class TestClearCheckout(CheckoutLifecycleTestCase):
    def test_removes_all_lines(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))
        clear_checkout(checkout)
        self.assertEqual(checkout.lines.count(), 0)