# ecommerce/tests/test_services/test_product_pricing.py

"""
Tests for ecommerce.services.product.pricing.
"""

import uuid
from decimal import Decimal

from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.services.product import (
    get_product_price_range,
    get_variant_availability,
    get_variant_price,
    resolve_tax_rate,
)
from tax.models import TaxClass, TaxClassCountryRate


class PricingTestCase(TestCase):
    def setUp(self):
        uid = uuid.uuid4().hex[:8]

        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"pricing-channel-{uid}",
            currency_code="NGN",
            default_country="NG",
        )

        self.tax_class = TaxClass.objects.create(
            name=f"Standard VAT {uid}",
        )
        self.tax_rate = TaxClassCountryRate.objects.create(
            tax_class=self.tax_class,
            country="NG",
            rate=Decimal("7.500"),  # percentage
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
            slug=f"test-product-{uid}",
            product_type=self.product_type,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku=f"SKU-{uid}",
            name="Default",
            track_inventory=False,
        )
        self.variant_listing = ProductVariantChannelListing.objects.create(
            variant=self.variant,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
        )
        self.product_listing = ProductChannelListing.objects.create(
            product=self.product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
            visible_in_listings=True,
        )


class TestResolveTaxRate(PricingTestCase):
    def test_resolves_from_product_type_tax_class(self):
        rate = resolve_tax_rate(self.variant, "NG")
        self.assertEqual(rate, Decimal("7.500"))

    def test_returns_zero_for_unknown_country(self):
        rate = resolve_tax_rate(self.variant, "XX")
        self.assertEqual(rate, Decimal("0"))


class TestVariantPrice(PricingTestCase):
    def test_returns_listed_price(self):
        price = get_variant_price(self.variant, self.channel)
        self.assertIsNotNone(price)
        self.assertEqual(price.amount, Decimal("1000.00"))
        self.assertEqual(price.currency, "NGN")

    def test_returns_none_when_not_listed(self):
        other_channel = Channel.objects.create(
            name="Other",
            slug="other-channel",
            currency_code="NGN",
            default_country="NG",
        )
        price = get_variant_price(self.variant, other_channel)
        self.assertIsNone(price)


class TestVariantAvailability(PricingTestCase):
    def test_returns_taxed_price(self):
        availability = get_variant_availability(
            self.variant, self.channel, "NG"
        )
        self.assertIsNotNone(availability)
        # 1000 NGN net + 7.5% VAT = 1075 NGN gross
        self.assertEqual(availability.price.net.amount, Decimal("1000.00"))
        self.assertEqual(availability.price.gross.amount, Decimal("1075.00"))

    def test_returns_none_when_not_listed(self):
        other_channel = Channel.objects.create(
            name="Empty",
            slug="empty-channel",
            currency_code="NGN",
            default_country="NG",
        )
        availability = get_variant_availability(
            self.variant, other_channel, "NG"
        )
        self.assertIsNone(availability)


class TestProductPriceRange(PricingTestCase):
    def test_returns_single_variant_range(self):
        price_range = get_product_price_range(
            self.product, self.channel, "NG"
        )
        self.assertIsNotNone(price_range)
        self.assertEqual(
            price_range.start.gross.amount, Decimal("1075.00")
        )
        self.assertEqual(
            price_range.stop.gross.amount, Decimal("1075.00")
        )

    def test_returns_none_for_unlisted_product(self):
        other_channel = Channel.objects.create(
            name="Empty2",
            slug="empty-channel-2",
            currency_code="NGN",
            default_country="NG",
        )
        price_range = get_product_price_range(
            self.product, other_channel, "NG"
        )
        self.assertIsNone(price_range)