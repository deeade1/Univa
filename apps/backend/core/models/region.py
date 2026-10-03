# core/models/region.py

"""
Canonical hierarchical region model for Univa.

Regions form a tree:

    World
    ├── Africa
    │   ├── Nigeria                (COUNTRY)
    │   │   ├── Lagos              (STATE)
    │   │   │   ├── Ikeja          (CITY)
    │   │   │   │   ├── Allen      (NEIGHBORHOOD)
    │   │   │   │   └── Opebi      (NEIGHBORHOOD)
    │   │   │   └── Victoria Island (CITY)
    │   │   └── Kano               (STATE)
    │   └── Kenya
    └── Europe
        └── United Kingdom
            └── England
                └── London

Every app that needs to scope data by geography should FK to `Region`:

    - Category.region           (nullable — null = global)
    - MarketItemMetadata.market_region
    - MarketItemMetadata.origin_region
    - User.preferred_region
    - Warehouse.region

Region is MPTT-based so that "everything under Nigeria" is one query:

    Region.objects.get(slug="nigeria").get_descendants(include_self=True)
"""

from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.managers import TreeManager
from mptt.models import MPTTModel

from core.models.metadata import ModelWithMetadata
from seo.models import SeoModel, SeoModelTranslationWithSlug


# =====================================================================
# ENUMS
# =====================================================================


class RegionLevel(models.TextChoices):
    """Granularity of a Region node."""

    CONTINENT = "continent", _("Continent")
    COUNTRY = "country", _("Country")
    STATE = "state", _("State / Province / Region")
    CITY = "city", _("City")
    NEIGHBORHOOD = "neighborhood", _("Neighborhood / District")
    MARKET = "market", _("Market / Physical location")


# =====================================================================
# REGION
# =====================================================================


class Region(ModelWithMetadata, MPTTModel, SeoModel):
    """
    A hierarchical geographic region.

    Region type is explicit (`region_type`) so consumers can filter without
    inspecting tree depth. Examples:

        Region(region_type=RegionLevel.COUNTRY, name="Nigeria", slug="nigeria",
               code="NG", timezone="Africa/Lagos", currency="NGN")

        Region(region_type=RegionLevel.STATE, name="Lagos", slug="lagos",
               parent=nigeria, code="NG-LA")

        Region(region_type=RegionLevel.CITY, name="Ikeja", slug="ikeja",
               parent=lagos)

        Region(region_type=RegionLevel.MARKET, name="Mile 12 Market",
               slug="mile-12-market", parent=lagos)
        Region(region_type=RegionLevel.COUNTRY, name="Nigeria", ...)
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = models.CharField(
        max_length=250,
        help_text=_("Display name of the region."),
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
        help_text=_("URL-safe identifier. Globally unique."),
    )
    code = models.CharField(
        max_length=16,
        blank=True,
        db_index=True,
        help_text=_(
            "External code: ISO 3166-1 alpha-2 (country), "
            "ISO 3166-2 (state), or blank."
        ),
    )
    
    region_type = models.CharField(
        max_length=32,
        choices=RegionLevel.choices,
        db_index=True,
        help_text=_(
            "Granularity of this region node: country, state, city, etc."
        ),
    )

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.PROTECT,
        help_text=_(
            "Parent region. PROTECT prevents accidental deletion of "
            "a subtree that still has children."
        ),
    )

    # ------------------------------------------------------------------
    # Localization defaults
    # ------------------------------------------------------------------

    timezone = models.CharField(
        max_length=64,
        blank=True,
        help_text=_(
            "IANA timezone. Example: 'Africa/Lagos'. If empty, "
            "inherited from parent at resolution time."
        ),
    )
    currency = models.CharField(
        max_length=3,
        blank=True,
        help_text=_(
            "ISO 4217 currency code. If empty, inherited from parent."
        ),
    )

    # ------------------------------------------------------------------
    # Geography
    # ------------------------------------------------------------------

    location_point = gis_models.PointField(
        geography=True,
        srid=4326,
        blank=True,
        null=True,
        spatial_index=True,
        help_text=_(
            "Centroid of the region for distance queries. Not a "
            "polygon — that belongs in a future boundary model."
        ),
    )

    # ------------------------------------------------------------------
    # External IDs
    # ------------------------------------------------------------------

    external_ids = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Provider-specific identifiers. Example: "
            "{'nominatim': '12345', 'google': 'ChIJ...'}"
        ),
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_(
            "Inactive regions are hidden from storefronts but remain "
            "referenced by historical data."
        ),
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Managers
    # ------------------------------------------------------------------

    objects = TreeManager()

    class Meta:
        ordering = ("region_type", "name")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            # Storefront queries: filter by type + active flag.
            models.Index(fields=["region_type", "is_active"]),
            # Tree navigation: children of a parent, filtered by type.
            models.Index(fields=["parent", "region_type"]),
            # External code lookup (ISO codes).
            models.Index(fields=["code"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(parent__isnull=False)
                    | models.Q(region_type__in=["continent", "country"])
                ),
                name="region_deep_levels_have_parent",
            ),
        ]
    def __str__(self) -> str:
        return self.name

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Inheritance helpers
    # ------------------------------------------------------------------

    def _inherited(self, attribute: str) -> str:
        """Walk up the tree to find the first non-empty value."""
        node = self
        while node is not None:
            value = getattr(node, attribute, "")
            if value:
                return value
            node = node.parent
        return ""

    @property
    def effective_timezone(self) -> str:
        """Timezone for this region, inherited from ancestors if unset."""
        return self._inherited("timezone")

    @property
    def effective_currency(self) -> str:
        """Currency for this region, inherited from ancestors if unset."""
        return self._inherited("currency")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @classmethod
    def resolve_path(cls, *slugs: str) -> "Region | None":
        """
        Resolve a chain of slugs to the deepest region, validating
        the parent-child path.

        Example:
            Region.resolve_path("nigeria", "lagos", "ikeja")

        Returns:
            The deepest Region, or None if any step is missing.
        """
        parent = None
        node = None
        for slug in slugs:
            qs = cls.objects.filter(slug=slug)
            if parent is None:
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent=parent)
            node = qs.first()
            if node is None:
                return None
            parent = node
        return node

    def get_subtree(self, include_self: bool = True):
        """All regions at or below this one."""
        return self.get_descendants(include_self=include_self)

    def ancestor_chain(self) -> list["Region"]:
        """Region + all ancestors, nearest first."""
        return [self, *self.get_ancestors(ascending=True, include_self=False)]


# =====================================================================
# REGION TRANSLATION
# =====================================================================


class RegionTranslation(SeoModelTranslationWithSlug):
    """
    Localized name and slug for a Region.

    Follows the same pattern as CategoryTranslation and
    CollectionTranslation.
    """

    region = models.ForeignKey(
        Region,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="uniq_lang_slug_regiontransl",
            ),
            models.UniqueConstraint(
                fields=["language_code", "region"],
                name="uniq_lang_region_regiontransl",
            ),
        ]

    def __str__(self) -> str:
        return self.name or str(self.pk)

    def get_translated_object_id(self):
        return "Region", self.region_id

    def get_translated_keys(self):
        return {
            **super().get_translated_keys(),
            "name": self.name,
        }