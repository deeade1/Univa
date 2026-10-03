# apps/backend/ecommerce/models/gotomarket.py

"""
Gotomarket — Universal local-market extension of the catalog.

A Gotomarket item is a `Product` whose `ProductType.kind` is
`ProductTypeKind.MARKET_ITEM`. All shared behaviour (pricing, media,
channels, attributes, inventory, orders) lives in the base catalog.

Only genuinely market-specific fields live here, in a satellite
table:

    Product  ←── 1:1 ──→  MarketItemMetadata

Region-aware:

    - `market_region` is where the item is available for purchase.
      Users see only items whose market_region is their region or an
      ancestor of it.
    - `origin_region` is where the item was sourced from. Usually a
      subset of market_region but not always (e.g. a Lagos market
      sells Kano-grown tomatoes).

Region is defined in `core.models.region`.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models.metadata import ModelWithMetadata


# =====================================================================
# ENUMS
# =====================================================================


class Freshness(models.TextChoices):
    """How a market item is preserved."""

    FRESH = "fresh", "Fresh"
    FROZEN = "frozen", "Frozen"
    DRIED = "dried", "Dried"
    SMOKED = "smoked", "Smoked"
    FERMENTED = "fermented", "Fermented"
    CANNED = "canned", "Canned"
    PICKLED = "pickled", "Pickled"
    ROASTED = "roasted", "Roasted"
    GROUND = "ground", "Ground"


class SourcingType(models.TextChoices):
    """Where a market item comes from."""

    LOCAL_FARM = "local_farm", "Local farm"
    LOCAL_MARKET = "local_market", "Local market"
    LOCAL_SUPPLIER = "local_supplier", "Local supplier"
    IMPORTED = "imported", "Imported"
    UNKNOWN = "unknown", "Unknown"


# =====================================================================
# MODEL
# =====================================================================


class MarketItemMetadata(ModelWithMetadata):
    """
    Gotomarket-specific metadata attached to a Product.

    Fields here exist ONLY for market items and would be noise on a
    regular catalog product. Kept in a separate table so that
    `Product` stays clean.

    The `product` FK is the primary key, guaranteeing exactly one
    metadata row per product.
    """

    product = models.OneToOneField(
        "ecommerce.Product",
        on_delete=models.CASCADE,
        related_name="market_metadata",
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Region scoping
    # ------------------------------------------------------------------

    market_region = models.ForeignKey(
        "core.Region",
        related_name="market_items_available_in",
        on_delete=models.PROTECT,
        help_text=(
            "Region where this item is available for purchase. Users "
            "see items whose market_region is their preferred region "
            "or an ancestor of it."
        ),
    )
    origin_region = models.ForeignKey(
        "core.Region",
        related_name="market_items_sourced_from",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "Region this item was sourced from. May differ from "
            "market_region (e.g. Kano-grown tomatoes sold in Lagos)."
        ),
    )

    # ------------------------------------------------------------------
    # Freshness / preservation
    # ------------------------------------------------------------------

    freshness = models.CharField(
        max_length=32,
        choices=Freshness.choices,
        default=Freshness.FRESH,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Seasonality
    # ------------------------------------------------------------------

    is_seasonal = models.BooleanField(default=False, db_index=True)
    season_start = models.DateField(null=True, blank=True)
    season_end = models.DateField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Sourcing
    # ------------------------------------------------------------------

    sourcing = models.CharField(
        max_length=32,
        choices=SourcingType.choices,
        default=SourcingType.LOCAL_MARKET,
        db_index=True,
    )
    is_organic = models.BooleanField(default=False, db_index=True)

    # ------------------------------------------------------------------
    # Supplier
    # ------------------------------------------------------------------

    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Market Item Metadata"
        verbose_name_plural = "Market Item Metadata"
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["market_region", "freshness"],
                name="market_region_fresh_idx",
            ),
            models.Index(
                fields=["origin_region"],
                name="market_origin_region_idx",
            ),
            models.Index(
                fields=["sourcing", "is_organic"],
                name="market_sourcing_organic_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(season_start__isnull=True)
                    | models.Q(season_end__isnull=True)
                    | models.Q(season_start__lte=models.F("season_end"))
                ),
                name="market_season_start_before_end",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_seasonal=False)
                    | models.Q(season_start__isnull=False)
                ),
                name="market_seasonal_requires_start",
            ),
        ]

    def __str__(self) -> str:
        return f"Market metadata for {self.product.name}"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_in_season(self) -> bool:
        """True if today is within the season window (or not seasonal)."""
        if not self.is_seasonal:
            return True

        today = timezone.now().date()
        if self.season_start and today < self.season_start:
            return False
        if self.season_end and today > self.season_end:
            return False
        return True

    @property
    def is_available_now(self) -> bool:
        """Season check + product active flag if loaded."""
        if not self.is_in_season:
            return False
        if self.product_id is not None:
            return getattr(self.product, "is_active", True)
        return True