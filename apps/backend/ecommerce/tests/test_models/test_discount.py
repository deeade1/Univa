# apps/backend/ecommerce/tests/test_models/test_discount.py

"""
Tests for manual-discount uniqueness constraints.

A "manual discount" is one with no backing promotion rule
(promotion_rule IS NULL on order/checkout discounts) or no unique
type (unique_type IS NULL on line discounts). The schema permits at
most one such discount per scope.

Promotion-based discounts are unaffected: a checkout can still
carry many of them, one per distinct promotion rule.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.discount import (
    CheckoutDiscount,
    CheckoutLineDiscount,
    OrderDiscount,
    OrderLineDiscount,
)
from ecommerce.models.enums.discount import (
    DiscountType,
    DiscountValueType,
)
from ecommerce.models.enums import OrderStatus
from ecommerce.models.order import Order, OrderLine
from ecommerce.models.product import Product, ProductType, ProductVariant


User = get_user_model()


class DiscountFixture(TestCase):
    """Shared fixture for discount constraint tests."""

    @classmethod
    def setUpTestData(cls):
        uid = uuid.uuid4().hex[:8]

        cls.user = User.objects.create_user(
            email=f"discount-{uid}@example.com",
        )
        cls.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"discount-{uid}",
            currency_code="NGN",
            default_country="NG",
        )
        cls.product_type = ProductType.objects.create(
            name=f"Physical {uid}",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
        )
        cls.product = Product.objects.create(
            name="Test Product",
            slug=f"test-{uid}",
            product_type=cls.product_type,
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku=f"SKU-{uid}",
            name="Default",
            track_inventory=False,
        )

    def make_checkout(self):
        return Checkout.objects.create(
            channel=self.channel,
            currency="NGN",
        )

    def make_checkout_line(self, checkout):
        return CheckoutLine.objects.create(
            checkout=checkout,
            variant=self.variant,
            quantity=Decimal("1"),
            currency="NGN",
        )

    def make_order(self):
        return Order.objects.create(
            user=self.user,
            user_email=self.user.email,
            channel=self.channel,
            currency="NGN",
            origin="checkout",
            status=OrderStatus.UNFULFILLED,
            total_gross_amount=Decimal("1000.00"),
            total_net_amount=Decimal("1000.00"),
            subtotal_gross_amount=Decimal("1000.00"),
            subtotal_net_amount=Decimal("1000.00"),
        )

    def make_order_line(self, order):
        return OrderLine.objects.create(
            order=order,
            variant=self.variant,
            product_name="Test Product",
            variant_name="Default",
            quantity=Decimal("1"),
            quantity_unit="unit",
            is_shipping_required=True,
            is_gift_card=False,
            currency="NGN",
            unit_price_net_amount=Decimal("1000.00"),
            unit_price_gross_amount=Decimal("1000.00"),
            total_price_net_amount=Decimal("1000.00"),
            total_price_gross_amount=Decimal("1000.00"),
        )

    def manual_discount_kwargs(self):
        return {
            "type": DiscountType.MANUAL,
            "value_type": DiscountValueType.FIXED,
            "value": Decimal("100.00"),
            "amount_value": Decimal("100.00"),
            "currency": "NGN",
        }


# ----------------------------------------------------------------------
# CheckoutDiscount
# ----------------------------------------------------------------------


class CheckoutDiscountConstraintTests(DiscountFixture):

    def test_single_manual_discount_is_allowed(self):
        checkout = self.make_checkout()

        CheckoutDiscount.objects.create(
            checkout=checkout,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            CheckoutDiscount.objects.filter(checkout=checkout).count(),
            1,
        )

    def test_second_manual_discount_is_rejected(self):
        checkout = self.make_checkout()
        CheckoutDiscount.objects.create(
            checkout=checkout,
            **self.manual_discount_kwargs(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CheckoutDiscount.objects.create(
                    checkout=checkout,
                    **self.manual_discount_kwargs(),
                )

    def test_manual_discounts_on_different_checkouts_are_independent(self):
        checkout_a = self.make_checkout()
        checkout_b = self.make_checkout()

        CheckoutDiscount.objects.create(
            checkout=checkout_a,
            **self.manual_discount_kwargs(),
        )
        CheckoutDiscount.objects.create(
            checkout=checkout_b,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            CheckoutDiscount.objects.count(),
            2,
        )


# ----------------------------------------------------------------------
# OrderDiscount
# ----------------------------------------------------------------------


class OrderDiscountConstraintTests(DiscountFixture):

    def test_single_manual_discount_is_allowed(self):
        order = self.make_order()

        OrderDiscount.objects.create(
            order=order,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            OrderDiscount.objects.filter(order=order).count(),
            1,
        )

    def test_second_manual_discount_is_rejected(self):
        order = self.make_order()
        OrderDiscount.objects.create(
            order=order,
            **self.manual_discount_kwargs(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderDiscount.objects.create(
                    order=order,
                    **self.manual_discount_kwargs(),
                )

    def test_manual_discounts_on_different_orders_are_independent(self):
        order_a = self.make_order()
        order_b = self.make_order()

        OrderDiscount.objects.create(
            order=order_a,
            **self.manual_discount_kwargs(),
        )
        OrderDiscount.objects.create(
            order=order_b,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            OrderDiscount.objects.count(),
            2,
        )


# ----------------------------------------------------------------------
# CheckoutLineDiscount
# ----------------------------------------------------------------------


class CheckoutLineDiscountConstraintTests(DiscountFixture):

    def test_single_manual_discount_is_allowed(self):
        checkout = self.make_checkout()
        line = self.make_checkout_line(checkout)

        CheckoutLineDiscount.objects.create(
            line=line,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            CheckoutLineDiscount.objects.filter(line=line).count(),
            1,
        )

    def test_second_manual_discount_is_rejected(self):
        checkout = self.make_checkout()
        line = self.make_checkout_line(checkout)
        CheckoutLineDiscount.objects.create(
            line=line,
            **self.manual_discount_kwargs(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CheckoutLineDiscount.objects.create(
                    line=line,
                    **self.manual_discount_kwargs(),
                )


# ----------------------------------------------------------------------
# OrderLineDiscount
# ----------------------------------------------------------------------


class OrderLineDiscountConstraintTests(DiscountFixture):

    def test_single_manual_discount_is_allowed(self):
        order = self.make_order()
        line = self.make_order_line(order)

        OrderLineDiscount.objects.create(
            line=line,
            **self.manual_discount_kwargs(),
        )

        self.assertEqual(
            OrderLineDiscount.objects.filter(line=line).count(),
            1,
        )

    def test_second_manual_discount_is_rejected(self):
        order = self.make_order()
        line = self.make_order_line(order)
        OrderLineDiscount.objects.create(
            line=line,
            **self.manual_discount_kwargs(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderLineDiscount.objects.create(
                    line=line,
                    **self.manual_discount_kwargs(),
                )
                
                

