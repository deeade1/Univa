# apps/backend/ecommerce/models/warehouse.py

"""
Warehouse core models for the ecommerce application.

ARCHITECTURE
------------
This module owns warehouse, channel warehouse association, and basic warehouse operations.
"""

import itertools
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex
from django.db import models
from django.db.models import QuerySet

from accounts.models.address import Address
from core.models.metadata import ModelWithExternalReference, ModelWithMetadata
from core.models.sortable import SortableModel
from ecommerce.models.channel import Channel
from ecommerce.models.shipping import ShippingZone

from .constants import WarehouseClickAndCollectOption


# ============================================================================
# WAREHOUSE QUERYSETS & MANAGERS
# ============================================================================


class WarehouseQueryset(models.QuerySet["Warehouse"]):
    """Optimized queryset for Warehouse model."""

    def for_channel(self, channel_id: int) -> QuerySet["Warehouse"]:
        return (
            self.filter(
                channelwarehouse__channel_id=channel_id,
            )
            .order_by("pk")
            .distinct()
        )

    def for_country_and_channel(
        self,
        country: str,
        channel_id: int,
    ) -> QuerySet["Warehouse"]:
        """
        Return warehouses that serve the given country on the given
        channel.

        A warehouse serves a channel through `ChannelWarehouse`, and
        serves a country through any of its `ShippingZone`s whose
        `countries` include the code and which is attached to the
        same channel.

        Note: `ShippingZone.channels` is a M2M. The reverse filter is
        `shipping_zones__channels__id`, not `shipping_zones__channel__id`.
        """

        return (
            self.filter(
                shipping_zones__countries__contains=country,
                shipping_zones__channels__id=channel_id,
                channelwarehouse__channel_id=channel_id,
            )
            .distinct()
            .order_by("pk")
        )

    def _get_click_and_collect_filter(self) -> models.Q:
        return models.Q(
            click_and_collect_option__in=[
                WarehouseClickAndCollectOption.LOCAL_STOCK,
                WarehouseClickAndCollectOption.ALL_WAREHOUSES,
            ]
        )

    def click_and_collect_warehouses_for_channel(
        self,
        channel_id: int,
    ) -> QuerySet["Warehouse"]:
        """
        Return warehouses on the given channel that are configured for
        click-and-collect.

        This method only filters by the warehouse's
        `click_and_collect_option`. It does NOT verify that any
        particular line can actually be fulfilled from the returned
        warehouses — stock availability is a property of the Stock
        model, not of the Warehouse. Callers that need "warehouses
        that can serve these lines" should intersect this queryset
        with `Stock.objects.for_channel_and_country(...)` filtered by
        variant.

        The previous name (`applicable_for_click_and_collect`)
        and its `lines_qs` argument implied that this method
        filtered by line-level availability. It never did, and
        the argument was silently ignored. The rename and
        signature change make the actual contract explicit.
        """

        return self.for_channel(channel_id).filter(
            self._get_click_and_collect_filter(),
        )

WarehouseManager = models.Manager.from_queryset(WarehouseQueryset)


class ChannelWarehouse(SortableModel):
    """Through model for Channel -> Warehouse relationship."""

    channel = models.ForeignKey(
        Channel,
        related_name="channelwarehouse",
        on_delete=models.CASCADE,
        db_index=True,
    )
    warehouse = models.ForeignKey(
        "Warehouse",
        related_name="channelwarehouse",
        on_delete=models.CASCADE,
        db_index=True,
    )

    class Meta:
        ordering = ("sort_order", "pk")
        indexes = [
            models.Index(
                fields=["channel", "warehouse"],
                name="chanwarehouse_channel_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "warehouse"],
                name="unique_channel_warehouse",
            ),
        ]

    def get_ordering_queryset(self) -> QuerySet["ChannelWarehouse"]:
        return self.channel.channelwarehouse.all()


class Warehouse(
    ModelWithMetadata,
    ModelWithExternalReference,
):
    """Unified warehouse model with logistics integration."""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
    )

    name = models.CharField(
        max_length=250,
        db_index=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )

    channels = models.ManyToManyField(
        Channel,
        related_name="warehouses",
        through=ChannelWarehouse,
    )

    shipping_zones = models.ManyToManyField(
        ShippingZone,
        blank=True,
        related_name="warehouses",
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        db_index=True,
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    click_and_collect_option = models.CharField(
        max_length=30,
        choices=WarehouseClickAndCollectOption.CHOICES,
        default=WarehouseClickAndCollectOption.DISABLED,
    )

    is_private = models.BooleanField(
        default=True,
    )

    # ------------------------------------------------------------------------
    # Capacity & Performance
    # ------------------------------------------------------------------------

    capacity_total = models.PositiveIntegerField(
        default=0,
        help_text="Total storage capacity in cubic meters",
    )

    capacity_used = models.PositiveIntegerField(
        default=0,
        help_text="Used storage capacity",
    )

    max_daily_throughput = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum orders per day",
    )

    # ------------------------------------------------------------------------
    # Location & Timezone
    # ------------------------------------------------------------------------

    timezone = models.CharField(
        max_length=50,
        default="UTC",
    )

    operating_hours_start = models.TimeField(
        null=True,
        blank=True,
    )

    operating_hours_end = models.TimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = WarehouseManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("-slug",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            BTreeIndex(
                fields=["slug"],
                name="warehouse_slug_idx",
            ),
            BTreeIndex(
                fields=["click_and_collect_option"],
                name="warehouse_cc_option_idx",
            ),
            BTreeIndex(
                fields=["is_private"],
                name="warehouse_private_idx",
            ),
            BTreeIndex(
                fields=["name", "slug"],
                name="warehouse_name_slug_idx",
            ),
            BTreeIndex(
                fields=["capacity_used", "capacity_total"],
                name="warehouse_capacity_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def countries(self) -> set[str]:
        return set(
            itertools.chain.from_iterable(
                zone.countries
                for zone in self.shipping_zones.only("countries")
            )
        )

    @property
    def available_capacity(self) -> int:
        return max(
            self.capacity_total - self.capacity_used,
            0,
        )

    @property
    def capacity_utilization(self) -> Decimal:
        if self.capacity_total == 0:
            return Decimal("0")

        return (
            Decimal(self.capacity_used)
            / Decimal(self.capacity_total)
            * Decimal("100")
        ).quantize(Decimal("0.01"))