# ecommerce/tests/test_models/test_checkout.py

from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.db import models as dj
from django.test import SimpleTestCase, TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import (
    Checkout,
    CheckoutLine,
    CheckoutMetadata,
)
from core.pricing.quantity_unit import QuantityUnit


User = get_user_model()


class TestCheckoutModel(SimpleTestCase):
    def test_user_is_set_null(self):
        field = Checkout._meta.get_field("user")
        self.assertEqual(field.remote_field.on_delete, dj.SET_NULL)

    def test_tax_permissions_removed(self):
        names = {p[0] for p in Checkout._meta.permissions}
        self.assertNotIn("handle_taxes", names)
        self.assertNotIn("manage_taxes", names)
        self.assertIn("manage_checkouts", names)
        self.assertIn("handle_checkouts", names)

    def test_indexes_present(self):
        names = {i.name for i in Checkout._meta.indexes}
        for expected in (
            "checkout_user_last_change_idx",
            "checkout_channel_change_idx",
            "checkout_email_idx",
        ):
            self.assertIn(expected, names)


class TestCheckoutLineModel(SimpleTestCase):
    def test_quantity_is_decimal(self):
        field = CheckoutLine._meta.get_field("quantity")
        self.assertIsInstance(field, dj.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 3)

    def test_quantity_unit_present(self):
        field = CheckoutLine._meta.get_field("quantity_unit")
        self.assertEqual(field.default, QuantityUnit.UNIT.value)

    def test_quantity_constraint(self):
        names = {c.name for c in CheckoutLine._meta.constraints}
        self.assertIn("checkoutline_quantity_positive", names)
        self.assertIn(
            "checkoutline_unique_variant_per_checkout", names
        )

    def test_old_id_removed(self):
        names = {f.name for f in CheckoutLine._meta.get_fields()}
        self.assertNotIn("old_id", names)


class TestCheckoutMetadataModel(SimpleTestCase):
    def test_one_to_one_checkout(self):
        field = CheckoutMetadata._meta.get_field("checkout")
        self.assertIsInstance(field, dj.OneToOneField)


class TestCheckoutCountry(TestCase):
    def setUp(self):
        self.channel = Channel.objects.create(
            name="Test",
            slug="test",
            currency_code="NGN",
            default_country="NG",
        )
        self.checkout = Checkout.objects.create(
            channel=self.channel,
            currency="NGN",
            country="NG",
        )

    def test_get_country_from_cached_field(self):
        self.assertEqual(self.checkout.get_country(), "NG")

    def test_get_country_does_not_write(self):
        initial = self.checkout.country.code
        self.checkout.get_country()
        self.checkout.refresh_from_db()
        self.assertEqual(self.checkout.country.code, initial)