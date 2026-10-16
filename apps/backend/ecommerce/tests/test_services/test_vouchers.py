# ecommerce/tests/test_services/test_vouchers.py

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.discount import (
    CheckoutDiscount,
    DiscountType,
    DiscountValueType,
    Voucher,
    VoucherChannelListing,
    VoucherCode,
)
from ecommerce.models.product import (
    Product, ProductChannelListing, ProductType,
    ProductVariant, ProductVariantChannelListing,
)
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.checkout import (
    add_variant_to_checkout,
    apply_voucher,
    create_checkout,
    remove_voucher,
)


User = get_user_model()


class VoucherTestFixture(TestCase):

    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"voucher-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"voucher-{uid}",
            currency_code="NGN",
            default_country="NG",
        )
        address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            street_address_1="123 Test St",
            city="Lagos",
            postal_code="100001",
            country="NG",
        )
        warehouse = Warehouse.objects.create(
            name="Main",
            slug=f"wh-{uid}",
            address=address,
        )
        warehouse.channels.add(self.channel)

        product_type = ProductType.objects.create(
            name=f"Physical {uid}",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
        )
        product = Product.objects.create(
            name="Test Product",
            slug=f"test-{uid}",
            product_type=product_type,
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{uid}",
            name="Default",
            track_inventory=False,
        )
        ProductVariantChannelListing.objects.create(
            variant=self.variant,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
        )
        ProductChannelListing.objects.create(
            product=product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
            visible_in_listings=True,
        )

    def _make_voucher(self, *, code, value, value_type, **kwargs):
        voucher = Voucher.objects.create(
            name=f"Voucher {code}",
            discount_value_type=value_type,
            **kwargs,
        )
        VoucherChannelListing.objects.create(
            voucher=voucher,
            channel=self.channel,
            currency="NGN",
            discount_value=value,
        )
        VoucherCode.objects.create(
            voucher=voucher,
            code=code,
            is_active=True,
        )
        return voucher


class ApplyVoucherTests(VoucherTestFixture):

    def test_apply_fixed_voucher(self):
        self._make_voucher(
            code="FIXED100",
            value=Decimal("100.00"),
            value_type=DiscountValueType.FIXED,
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))

        checkout = apply_voucher(checkout, "FIXED100")

        self.assertEqual(checkout.voucher_code, "FIXED100")
        discount = CheckoutDiscount.objects.get(checkout=checkout)
        self.assertEqual(discount.type, DiscountType.VOUCHER)
        self.assertEqual(discount.amount_value, Decimal("100.00"))

    def test_apply_percentage_voucher(self):
        self._make_voucher(
            code="PCT10",
            value=Decimal("10.00"),
            value_type=DiscountValueType.PERCENTAGE,
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))

        checkout = apply_voucher(checkout, "PCT10")

        discount = CheckoutDiscount.objects.get(checkout=checkout)
        # 10% of 2000 = 200
        self.assertEqual(discount.amount_value, Decimal("200.00"))

    def test_unknown_code_raises(self):
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        with self.assertRaises(Exception):
            apply_voucher(checkout, "DOESNOTEXIST")

    def test_second_apply_replaces_first(self):
        self._make_voucher(
            code="FIXED100",
            value=Decimal("100.00"),
            value_type=DiscountValueType.FIXED,
        )
        self._make_voucher(
            code="FIXED200",
            value=Decimal("200.00"),
            value_type=DiscountValueType.FIXED,
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))

        apply_voucher(checkout, "FIXED100")
        apply_voucher(checkout, "FIXED200")

        self.assertEqual(
            CheckoutDiscount.objects.filter(checkout=checkout).count(),
            1,
        )
        discount = CheckoutDiscount.objects.get(checkout=checkout)
        self.assertEqual(discount.amount_value, Decimal("200.00"))

    def test_remove_voucher(self):
        self._make_voucher(
            code="FIXED100",
            value=Decimal("100.00"),
            value_type=DiscountValueType.FIXED,
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("2"))
        apply_voucher(checkout, "FIXED100")

        remove_voucher(checkout)

        self.assertFalse(
            CheckoutDiscount.objects.filter(checkout=checkout).exists()
        )
        checkout.refresh_from_db()
        self.assertIsNone(checkout.voucher_code)