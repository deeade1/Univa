# ecommerce/tests/test_models/test_discount.py

from decimal import Decimal

from django.db import models as dj
from django.test import SimpleTestCase

from ecommerce.models.discount import (
    CheckoutDiscount,
    CheckoutLineDiscount,
    OrderDiscount,
    OrderLineDiscount,
    Promotion,
    PromotionRule,
    Voucher,
    VoucherCode,
    VoucherCustomer,
)


class TestVoucherModel(SimpleTestCase):
    def test_min_checkout_items_quantity_is_decimal(self):
        field = Voucher._meta.get_field("min_checkout_items_quantity")
        self.assertIsInstance(field, dj.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 3)

    def test_legacy_fields_removed(self):
        names = {f.name for f in Voucher._meta.get_fields()}
        self.assertNotIn("old_sale_id", names)

    def test_min_qty_constraint(self):
        names = {c.name for c in Voucher._meta.constraints}
        self.assertIn("voucher_min_qty_positive", names)


class TestPromotionModel(SimpleTestCase):
    def test_old_sale_id_removed(self):
        names = {f.name for f in Promotion._meta.get_fields()}
        self.assertNotIn("old_sale_id", names)

    def test_no_assign_old_sale_id_method(self):
        self.assertFalse(hasattr(Promotion, "assign_old_sale_id"))


class TestPromotionRuleModel(SimpleTestCase):
    def test_old_channel_listing_id_removed(self):
        names = {f.name for f in PromotionRule._meta.get_fields()}
        self.assertNotIn("old_channel_listing_id", names)

    def test_no_old_channel_listing_helper(self):
        self.assertFalse(
            hasattr(PromotionRule, "get_old_channel_listing_ids")
        )


class TestOrderDiscountModel(SimpleTestCase):
    def test_old_id_removed(self):
        names = {f.name for f in OrderDiscount._meta.get_fields()}
        self.assertNotIn("old_id", names)


class TestVoucherCodeIndexes(SimpleTestCase):
    def test_voucher_fk_is_indexed(self):
        field = VoucherCode._meta.get_field("voucher")
        self.assertTrue(field.db_index)


class TestVoucherCustomerIndexes(SimpleTestCase):
    def test_voucher_code_fk_is_indexed(self):
        field = VoucherCustomer._meta.get_field("voucher_code")
        self.assertTrue(field.db_index)