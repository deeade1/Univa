# ecommerce/tests/test_services/test_checkout_calculations.py

"""
Tests for ecommerce.services.checkout.calculations.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout
from ecommerce.models.inventory import Stock
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
    add_variant_to_checkout,
    calculate_checkout_shipping,
    calculate_checkout_subtotal,
    calculate_checkout_total,
    create_checkout,
    set_checkout_shipping_method,
    update_checkout_totals,
)
from tax.models import TaxClass, TaxClassCountryRate


User = get_user_model()


class CheckoutCalculationsTestCase(TestCase):
    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"calc-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"calc-channel-{uid}",
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

        # 7.5% VAT for NG
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
        self.variant_listing = ProductVariantChannelListing.objects.create(
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

        # Shipping method
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


class TestSubtotal(CheckoutCalculationsTestCase):
    def test_empty_checkout_subtotal_is_zero(self):
        checkout = create_checkout(self.channel)
        subtotal = calculate_checkout_subtotal(checkout, "NG")
        self.assertEqual(subtotal.net.amount, Decimal("0"))
        self.assertEqual(subtotal.gross.amount, Decimal("0"))

    def test_subtotal_with_one_line(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        subtotal = calculate_checkout_subtotal(checkout, "NG")
        # 2 * 1000 net = 2000, +7.5% = 2150 gross
        self.assertEqual(subtotal.net.amount, Decimal("2000.00"))
        self.assertEqual(subtotal.gross.amount, Decimal("2150.00"))


class TestShipping(CheckoutCalculationsTestCase):
    def test_no_method_returns_zero(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("1")
        )
        shipping = calculate_checkout_shipping(checkout, "NG")
        self.assertEqual(shipping.net.amount, Decimal("0"))

    def test_with_method(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("1")
        )
        set_checkout_shipping_method(checkout, self.shipping_method)
        shipping = calculate_checkout_shipping(checkout, "NG")
        self.assertEqual(shipping.net.amount, Decimal("500.00"))
        self.assertEqual(shipping.gross.amount, Decimal("500.00"))

    def test_no_shipping_required_returns_zero(self):
        # Set is_shipping_required=False on the product type
        self.product_type.is_shipping_required = False
        self.product_type.save(update_fields=["is_shipping_required"])

        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("1")
        )
        set_checkout_shipping_method(checkout, self.shipping_method)
        shipping = calculate_checkout_shipping(checkout, "NG")
        self.assertEqual(shipping.net.amount, Decimal("0"))


class TestTotal(CheckoutCalculationsTestCase):
    def test_total_with_line_and_shipping(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        set_checkout_shipping_method(checkout, self.shipping_method)
        total = calculate_checkout_total(checkout, "NG")
        # subtotal net 2000 + shipping 500 = 2500
        # subtotal gross 2150 + shipping 500 = 2650
        self.assertEqual(total.net.amount, Decimal("2500.00"))
        self.assertEqual(total.gross.amount, Decimal("2650.00"))


class TestUpdateCheckoutTotals(CheckoutCalculationsTestCase):
    def test_persists_totals(self):
        checkout = create_checkout(self.channel)
        add_variant_to_checkout(
            checkout, self.variant, Decimal("2")
        )
        set_checkout_shipping_method(checkout, self.shipping_method)
        update_checkout_totals(checkout, "NG")

        checkout.refresh_from_db()
        self.assertEqual(
            checkout.subtotal_net_amount, Decimal("2000.00")
        )
        self.assertEqual(
            checkout.shipping_price_net_amount, Decimal("500.00")
        )
        self.assertEqual(
            checkout.total_net_amount, Decimal("2500.00")
        )