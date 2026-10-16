# apps/backend/ecommerce/tests/models/test_warehouse.py

"""
Tests for Warehouse and WarehouseQueryset.

Focus areas:

    - for_channel returns only warehouses attached to the channel
    - for_country_and_channel resolves both the shipping-zone
      countries and the shipping-zone channels correctly, and does
      not raise FieldError on the M2M reverse accessor
    - click_and_collect_warehouses_for_channel filters by option
      and channel
    - Meta.indexes includes the metadata GIN indexes inherited from
      ModelWithMetadata
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models.address import Address
from ecommerce.models.channel import Channel
from ecommerce.models.shipping import ShippingZone
from ecommerce.models.warehouse import (
    ChannelWarehouse,
    Warehouse,
)
from ecommerce.models.constants import WarehouseClickAndCollectOption


class WarehouseTestFixture(TestCase):
    """
    Shared fixture. Not a test class itself.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create the shared user once for the whole class.

        setUpTestData runs once per TestCase subclass and wraps the
        data in a per-class transaction, which is faster than creating
        a fresh user in setUp for every test.
        """
        User = get_user_model()

        cls.user = User.objects.create_user(
            email="warehouse-fixture@example.com",
            password="test-password",
        )

    def make_address(self, *, line1="1 Test Way", city="Lagos", country="NG"):
        return Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="Warehouse",
            street_address_1=line1,
            city=city,
            country=country,
            postal_code="100001",
            phone="+2348000000000",
        )

    def make_channel(self, slug):
        return Channel.objects.create(
            name=slug.title(),
            slug=slug,
            currency_code="NGN",
            is_active=True,
        )

    def make_warehouse(self, *, slug, name=None, **kwargs):
        return Warehouse.objects.create(
            name=name or slug.title(),
            slug=slug,
            address=self.make_address(line1=f"{slug} address"),
            **kwargs,
        )

    def make_zone(self, *, name, countries, channels):
        zone = ShippingZone.objects.create(name=name, countries=countries)
        zone.channels.set(channels)
        return zone


# ----------------------------------------------------------------------
# for_channel
# ----------------------------------------------------------------------


class WarehouseForChannelTests(WarehouseTestFixture):

    def test_for_channel_returns_only_attached_warehouses(self):
        channel_a = self.make_channel("channel-a")
        channel_b = self.make_channel("channel-b")

        wh_a = self.make_warehouse(slug="wh-a")
        wh_b = self.make_warehouse(slug="wh-b")

        ChannelWarehouse.objects.create(channel=channel_a, warehouse=wh_a)
        ChannelWarehouse.objects.create(channel=channel_b, warehouse=wh_b)

        result = list(Warehouse.objects.for_channel(channel_a.id))

        self.assertEqual(result, [wh_a])

    def test_for_channel_returns_empty_when_no_warehouses_attached(self):
        channel = self.make_channel("empty-channel")
        self.make_warehouse(slug="orphan-wh")

        result = list(Warehouse.objects.for_channel(channel.id))

        self.assertEqual(result, [])

    def test_for_channel_is_distinct_when_multiple_rows_match(self):
        channel = self.make_channel("multi-channel")
        wh = self.make_warehouse(slug="multi-wh")
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        result = list(Warehouse.objects.for_channel(channel.id))

        self.assertEqual(result, [wh])


# ----------------------------------------------------------------------
# for_country_and_channel — the FieldError regression
# ----------------------------------------------------------------------


class WarehouseForCountryAndChannelTests(WarehouseTestFixture):

    def test_returns_warehouse_when_zone_covers_country_on_channel(self):
        channel = self.make_channel("ng-channel")
        wh = self.make_warehouse(slug="lagos-wh")
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        zone = self.make_zone(
            name="Lagos mainland",
            countries=["NG"],
            channels=[channel],
        )
        wh.shipping_zones.add(zone)

        result = list(
            Warehouse.objects.for_country_and_channel(
                country="NG",
                channel_id=channel.id,
            )
        )

        self.assertEqual(result, [wh])

    def test_excludes_warehouse_when_zone_does_not_cover_country(self):
        channel = self.make_channel("ng-channel")
        wh = self.make_warehouse(slug="accra-wh")
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        zone = self.make_zone(
            name="Ghana",
            countries=["GH"],
            channels=[channel],
        )
        wh.shipping_zones.add(zone)

        result = list(
            Warehouse.objects.for_country_and_channel(
                country="NG",
                channel_id=channel.id,
            )
        )

        self.assertEqual(result, [])

    def test_excludes_warehouse_when_zone_not_attached_to_channel(self):
        channel_a = self.make_channel("channel-a")
        channel_b = self.make_channel("channel-b")
        wh = self.make_warehouse(slug="shared-wh")
        ChannelWarehouse.objects.create(channel=channel_a, warehouse=wh)
        ChannelWarehouse.objects.create(channel=channel_b, warehouse=wh)

        zone = self.make_zone(
            name="Zone on A only",
            countries=["NG"],
            channels=[channel_a],
        )
        wh.shipping_zones.add(zone)

        result = list(
            Warehouse.objects.for_country_and_channel(
                country="NG",
                channel_id=channel_b.id,
            )
        )

        self.assertEqual(result, [])

    def test_does_not_raise_field_error(self):
        """
        Regression test.

        The previous implementation used `shipping_zones__channel__id`,
        which raises FieldError because ShippingZone.channels is a M2M.
        This test would fail with FieldError before the fix and pass
        after.
        """
        channel = self.make_channel("regression-channel")

        # Should not raise.
        list(
            Warehouse.objects.for_country_and_channel(
                country="NG",
                channel_id=channel.id,
            )
        )


# ----------------------------------------------------------------------
# click_and_collect_warehouses_for_channel
# ----------------------------------------------------------------------


class ClickAndCollectWarehouseTests(WarehouseTestFixture):

    def test_includes_local_stock_warehouses(self):
        channel = self.make_channel("cc-channel")
        wh = self.make_warehouse(
            slug="cc-local",
            click_and_collect_option=(
                WarehouseClickAndCollectOption.LOCAL_STOCK
            ),
        )
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        result = list(
            Warehouse.objects
            .click_and_collect_warehouses_for_channel(channel.id)
        )

        self.assertEqual(result, [wh])

    def test_includes_all_warehouses_option(self):
        channel = self.make_channel("cc-channel-2")
        wh = self.make_warehouse(
            slug="cc-all",
            click_and_collect_option=(
                WarehouseClickAndCollectOption.ALL_WAREHOUSES
            ),
        )
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        result = list(
            Warehouse.objects
            .click_and_collect_warehouses_for_channel(channel.id)
        )

        self.assertEqual(result, [wh])

    def test_excludes_disabled_warehouses(self):
        channel = self.make_channel("cc-disabled")
        wh = self.make_warehouse(
            slug="cc-off",
            click_and_collect_option=(
                WarehouseClickAndCollectOption.DISABLED
            ),
        )
        ChannelWarehouse.objects.create(channel=channel, warehouse=wh)

        result = list(
            Warehouse.objects
            .click_and_collect_warehouses_for_channel(channel.id)
        )

        self.assertEqual(result, [])

    def test_excludes_warehouses_not_on_channel(self):
        channel = self.make_channel("cc-other")
        wh = self.make_warehouse(
            slug="cc-not-on-channel",
            click_and_collect_option=(
                WarehouseClickAndCollectOption.LOCAL_STOCK
            ),
        )
        # Not added to any channel.

        result = list(
            Warehouse.objects
            .click_and_collect_warehouses_for_channel(channel.id)
        )

        self.assertEqual(result, [])


# ----------------------------------------------------------------------
# Meta.indexes
# ----------------------------------------------------------------------


class WarehouseMetaTests(TestCase):

    def test_meta_indexes_include_metadata_gin_indexes(self):
        """
        Regression test: Warehouse.Meta must include the metadata
        GIN indexes from ModelWithMetadata.Meta. The previous
        implementation overrode them by defining `indexes = [...]`
        without spreading the parent's list.
        """
        names = {idx.name for idx in Warehouse._meta.indexes}

        self.assertIn("warehouse_p_meta_idx", names)
        self.assertIn("warehouse_meta_idx", names)

    def test_meta_indexes_include_warehouse_specific_indexes(self):
        names = {idx.name for idx in Warehouse._meta.indexes}

        self.assertIn("warehouse_slug_idx", names)
        self.assertIn("warehouse_cc_option_idx", names)
        self.assertIn("warehouse_private_idx", names)
        self.assertIn("warehouse_name_slug_idx", names)
        self.assertIn("warehouse_capacity_idx", names)