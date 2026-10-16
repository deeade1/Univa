# apps/backend/ecommerce/tests/test_models/test_shipping.py

"""
Tests for ShippingZone and ShippingMethod invariants.

Focus:

    - setting a new default zone silently clears the previous one
    - a default zone must be active
    - ShippingMethod.is_applicable() returns False when the parent
      zone is inactive, regardless of the method's own flags
    - is_applicable() returns False when the method's own status is
      not ACTIVE
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.pricing.money import Money
from ecommerce.models.channel import Channel
from ecommerce.models.enums.shipping import (
    ShippingMethodStatus,
    ShippingMethodType,
)
from ecommerce.models.shipping import (
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingZone,
)
from measurement.measures import Weight


class ShippingFixture(TestCase):
    """Shared fixture for shipping tests."""

    @classmethod
    def setUpTestData(cls):
        cls.channel = Channel.objects.create(
            name="Test Channel",
            slug="ship-channel",
            currency_code="NGN",
            default_country="NG",
            is_active=True,
        )

    def make_zone(self, *, name, default=False, is_active=True):
        zone = ShippingZone.objects.create(
            name=name,
            countries=["NG"],
            default=default,
            is_active=is_active,
        )
        zone.channels.add(self.channel)
        return zone

    def make_method(
        self,
        *,
        zone,
        name="Standard",
        status=ShippingMethodStatus.ACTIVE,
        is_active=True,
    ):
        return ShippingMethod.objects.create(
            name=name,
            shipping_zone=zone,
            type=ShippingMethodType.PRICE_BASED,
            status=status,
            is_active=is_active,
        )

    def price(self, amount="100.00", currency="NGN"):
        return Money(Decimal(amount), currency)


# ----------------------------------------------------------------------
# Default zone uniqueness
# ----------------------------------------------------------------------


class ShippingZoneDefaultTests(ShippingFixture):

    def test_first_default_zone_can_be_set(self):
        zone = self.make_zone(name="First", default=True)

        self.assertTrue(zone.default)

    def test_setting_new_default_clears_previous(self):
        """
        Regression: the pre_save signal silently clears the previous
        default. The old `clean()` check raised instead, making it
        impossible to reassign the default through the admin.
        """
        first = self.make_zone(name="First", default=True)
        second = self.make_zone(name="Second", default=True)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.default)
        self.assertTrue(second.default)

    def test_only_one_default_zone_exists_at_any_time(self):
        self.make_zone(name="A", default=True)
        self.make_zone(name="B", default=True)
        self.make_zone(name="C", default=True)

        count = ShippingZone.objects.filter(default=True).count()
        self.assertEqual(count, 1)

    def test_default_zone_must_be_active(self):
        """
        A default-but-inactive zone is a misconfiguration: the
        default pointer would resolve to a zone the storefront
        cannot use.
        """
        zone = ShippingZone(
            name="Bad default",
            countries=["NG"],
            default=True,
            is_active=False,
        )

        with self.assertRaises(ValidationError) as ctx:
            zone.clean()

        self.assertIn("default", ctx.exception.message_dict)

    def test_inactive_zone_can_be_non_default(self):
        # No exception.
        zone = ShippingZone(
            name="Inactive non-default",
            countries=["NG"],
            default=False,
            is_active=False,
        )
        zone.clean()


# ----------------------------------------------------------------------
# ShippingMethod.is_applicable
# ----------------------------------------------------------------------


class ShippingMethodIsApplicableTests(ShippingFixture):

    def _make_applicable_method(
        self,
        *,
        zone,
        price_min=None,
        price_max=None,
    ):
        method = self.make_method(zone=zone)
        ShippingMethodChannelListing.objects.create(
            shipping_method=method,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("500.00"),
            minimum_order_price_amount=price_min,
            maximum_order_price_amount=price_max,
            is_active=True,
        )
        return method

    def test_applicable_when_all_conditions_met(self):
        zone = self.make_zone(name="Active zone")
        method = self._make_applicable_method(zone=zone)

        self.assertTrue(
            method.is_applicable(
                price=self.price("100.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )

    def test_not_applicable_when_zone_is_inactive(self):
        """
        Regression: is_applicable() used to ignore
        shipping_zone.is_active. A method on a deactivated zone
        must not be applicable.
        """
        zone = self.make_zone(name="Inactive zone", is_active=False)
        method = self._make_applicable_method(zone=zone)

        self.assertFalse(
            method.is_applicable(
                price=self.price("100.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )

    def test_not_applicable_when_method_status_is_not_active(self):
        zone = self.make_zone(name="Zone for non-active method")
        method = self._make_applicable_method(zone=zone)
        method.status = ShippingMethodStatus.INACTIVE
        method.save(update_fields=["status"])

        self.assertFalse(
            method.is_applicable(
                price=self.price("100.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )

    def test_not_applicable_when_method_is_inactive(self):
        zone = self.make_zone(name="Zone for inactive method")
        method = self._make_applicable_method(zone=zone)
        method.is_active = False
        method.save(update_fields=["is_active"])

        self.assertFalse(
            method.is_applicable(
                price=self.price("100.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )

    def test_not_applicable_when_price_below_minimum(self):
        zone = self.make_zone(name="Minimum price zone")
        method = self._make_applicable_method(
            zone=zone,
            price_min=Decimal("200.00"),
        )

        self.assertFalse(
            method.is_applicable(
                price=self.price("50.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )

    def test_applicable_when_price_meets_minimum(self):
        zone = self.make_zone(name="Minimum price zone 2")
        method = self._make_applicable_method(
            zone=zone,
            price_min=Decimal("200.00"),
        )

        self.assertTrue(
            method.is_applicable(
                price=self.price("250.00"),
                weight=Weight(kg=1),
                channel_id=self.channel.pk,
                country_code="NG",
            )
        )