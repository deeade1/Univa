# ecommerce/tests/test_services/test_checkout_complete.py

"""
Tests for ecommerce.services.checkout.complete.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.enums import OrderEvents
from ecommerce.models.inventory import Allocation, Reservation, Stock
from ecommerce.models.order import Order, OrderEvent, OrderLine
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.shipping import (
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingZone,
)
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.checkout import (
    CheckoutNotReady,
    add_variant_to_checkout,
    complete_checkout,
    create_checkout,
    set_checkout_billing_address,
    set_checkout_shipping_address,
    set_checkout_shipping_method,
)
from tax.models import TaxClass, TaxClassCountryRate


User = get_user_model()


class CheckoutCompleteTestCase(TestCase):
    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"complete-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"complete-channel-{uid}",
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

        self.tax_class = TaxClass.objects.create(name=f"VAT {uid}")
        TaxClassCountryRate.objects.create(
            tax_class=self.tax_class,
            country="NG",
            rate=Decimal("7.500"),
        )

        self.product_type = ProductType.objects.create(
            name=f"Physical {uid}",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
            tax_class=self.tax_class,
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
        ProductVariantChannelListing.objects.create(
            variant=self.variant,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
        )
        ProductChannelListing.objects.create(
            product=self.product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
            visible_in_listings=True,
        )
        self.stock = Stock.objects.create(
            warehouse=self.warehouse,
            product_variant=self.variant,
            quantity=Decimal("100"),
        )

        # Shipping
        self.zone = ShippingZone.objects.create(
            name=f"Zone {uid}",
            countries=["NG"],
        )
        self.zone.channels.add(self.channel)
        self.shipping_method = ShippingMethod.objects.create(
            name="Standard",
            shipping_zone=self.zone,
            is_active=True,
        )
        ShippingMethodChannelListing.objects.create(
            shipping_method=self.shipping_method,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("500.00"),
            is_active=True,
        )

    def _build_ready_checkout(self, quantity=Decimal("2")):
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, quantity)
        set_checkout_shipping_address(checkout, self.address)
        set_checkout_billing_address(checkout, self.address)
        set_checkout_shipping_method(checkout, self.shipping_method)
        return checkout


class TestValidateCheckout(CheckoutCompleteTestCase):
    def test_empty_checkout_raises(self):
        checkout = create_checkout(self.channel, user=self.user)
        with self.assertRaises(CheckoutNotReady):
            complete_checkout(checkout)

    def test_missing_shipping_address_raises(self):
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))
        with self.assertRaises(CheckoutNotReady):
            complete_checkout(checkout)


class TestCompleteCheckout(CheckoutCompleteTestCase):
    def test_creates_order(self):
        checkout = self._build_ready_checkout()
        order = complete_checkout(checkout)

        self.assertIsInstance(order, Order)
        self.assertEqual(order.user_id, self.user.pk)
        self.assertEqual(order.currency, "NGN")
        self.assertEqual(order.origin, "checkout")

    def test_creates_order_lines(self):
        checkout = self._build_ready_checkout()
        order = complete_checkout(checkout)

        lines = order.lines.all()
        self.assertEqual(lines.count(), 1)

        line = lines.first()
        self.assertEqual(line.variant_id, self.variant.pk)
        self.assertEqual(line.quantity, Decimal("2"))
        self.assertEqual(line.currency, "NGN")
        self.assertEqual(line.quantity_unit, self.variant.quantity_unit)

    def test_totals_are_taxed(self):
        checkout = self._build_ready_checkout(quantity=Decimal("2"))
        order = complete_checkout(checkout)

        # Subtotal net 2000 + VAT 7.5% = 2150 gross
        # Shipping 500 flat
        # Total net 2500, gross 2650
        self.assertEqual(order.subtotal_net_amount, Decimal("2000.00"))
        self.assertEqual(order.subtotal_gross_amount, Decimal("2150.00"))
        self.assertEqual(
            order.shipping_price_net_amount, Decimal("500.00")
        )
        self.assertEqual(order.total_net_amount, Decimal("2500.00"))
        self.assertEqual(order.total_gross_amount, Decimal("2650.00"))

    def test_allocates_stock(self):
        checkout = self._build_ready_checkout(quantity=Decimal("3"))
        order = complete_checkout(checkout)

        line = order.lines.first()
        allocations = Allocation.objects.filter(order_line=line)
        self.assertEqual(
            sum(a.quantity_allocated for a in allocations),
            Decimal("3"),
        )

    def test_releases_checkout_reservations(self):
        checkout = self._build_ready_checkout()
        complete_checkout(checkout)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_deletes_checkout(self):
        checkout = self._build_ready_checkout()
        checkout_pk = checkout.pk
        complete_checkout(checkout)
        self.assertFalse(Checkout.objects.filter(pk=checkout_pk).exists())

    def test_emits_order_event(self):
        checkout = self._build_ready_checkout()
        order = complete_checkout(checkout)

        events = OrderEvent.objects.filter(order=order)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().type, OrderEvents.PLACED)

    def test_second_completion_raises(self):
        checkout = self._build_ready_checkout()
        complete_checkout(checkout)
        # The checkout is deleted; attempting to complete again fails.
        with self.assertRaises(Checkout.DoesNotExist):
            Checkout.objects.get(pk=checkout.pk)