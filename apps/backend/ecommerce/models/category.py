# apps/backend/ecommerce/models/category.py

"""
Ecommerce Category models.

Categories form a hierarchical tree using django-mptt. A Category
can be:

    - Base (region=None) — visible everywhere.
    - Regional (region=FK) — visible only where the region matches.

This lets Univa build one taxonomy tree that covers both global
categories ("Meat", "Electronics") and region-specific ones
("Ugu" for Nigeria, "Sukuma Wiki" for Kenya).

Architecture:

    Category
        └── CategoryTranslation

Products reference Category through a ForeignKey with on_delete=PROTECT.
Categories are never hard-deleted; set `is_active=False` instead.

Import discipline: this module does not import Product at module load.
Django resolves the Product.category FK lazily via string reference.
"""

from __future__ import annotations

from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import Q, TextField
from mptt.managers import TreeManager
from mptt.models import MPTTModel
from mptt.querysets import TreeQuerySet

from core.models.metadata import ModelWithMetadata
from core.utils.editorjs import default_clean_editor_js
from seo.models import SeoModel, SeoModelTranslationWithSlug


# =============================================================================
# QUERYSET & MANAGER
# =============================================================================


class CategoryQuerySet(TreeQuerySet):
    """
    MPTT-aware queryset for Category.

    Extends TreeQuerySet so that `get_descendants`, `get_ancestors`,
    `get_children`, and friends work as `Category.objects.*`.
    """

    def active(self):
        """Only categories that are not soft-deleted."""
        return self.filter(is_active=True)

    def base(self):
        """Categories that are not region-scoped."""
        return self.filter(region__isnull=True)

    def for_region(self, region):
        """
        Categories applicable in a region: base categories plus
        categories scoped to that region or any ancestor.
        """
        if region is None:
            return self.base()

        region_ids = [region.pk, *region.get_ancestors(include_self=False).values_list("pk", flat=True)]
        return self.filter(
            Q(region__isnull=True) | Q(region_id__in=region_ids)
        )

    def top_level(self):
        """Root categories (no parent)."""
        return self.filter(parent__isnull=True)


CategoryManager = TreeManager.from_queryset(CategoryQuerySet)


# =============================================================================
# CATEGORY
# =============================================================================


class Category(ModelWithMetadata, MPTTModel, SeoModel):
    """
    Product category.

    Categories form a hierarchical tree using django-mptt.

    Example:

        Electronics
        ├── Phones
        │   ├── Android Phones
        │   └── iPhones
        └── Computers
            ├── Laptops
            └── Desktops

    Region scoping:

        Category(name="Produce")                      # base — everywhere
        Category(name="Ugu", parent=Produce,          # Nigeria only
                 region=nigeria_region)
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
        help_text="Globally unique URL-safe identifier.",
    )

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------

    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )
    description_plaintext = TextField(blank=True)
    background_image = models.ImageField(
        upload_to="category-backgrounds",
        blank=True,
        null=True,
    )
    background_image_alt = models.CharField(max_length=128, blank=True)

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    # ------------------------------------------------------------------
    # Region scoping
    # ------------------------------------------------------------------

    region = models.ForeignKey(
        "core.Region",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="categories",
        help_text=(
            "NULL = base category, visible everywhere. "
            "Non-null = scoped to this region (and its descendants)."
        ),
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search_vector = SearchVectorField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Soft-delete flag. Inactive categories are hidden from the "
            "storefront but remain referenced by historical data."
        ),
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Managers
    # ------------------------------------------------------------------

    objects = CategoryManager()

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        ordering = ("name",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                fields=["name", "slug", "description_plaintext"],
                name="prod_cat_name_slug_gin",
                opclasses=["gin_trgm_ops"] * 3,
            ),
            GinIndex(
                fields=["search_vector"],
                name="prod_cat_search_vec_gin",
            ),
            BTreeIndex(
                fields=["updated_at"],
                name="prod_cat_updated_idx",
            ),
            models.Index(
                fields=["is_active", "region"],
                name="cat_active_region_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(pk=models.F("parent_id")),
                name="category_not_own_parent",
            ),
        ]

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self.name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_applicable_in_region(self, region) -> bool:
        """True if the category is visible in the given region."""
        if self.region_id is None:
            return True
        if region is None:
            return False
        return self.region_id in {
            region.pk,
            *region.get_ancestors(include_self=False).values_list("pk", flat=True),
        }


# =============================================================================
# CATEGORY TRANSLATION
# =============================================================================


class CategoryTranslation(SeoModelTranslationWithSlug):
    """
    Localized category data.

    A category can have one translation per language.
    """

    category = models.ForeignKey(
        Category,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=250, blank=True)
    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="uniq_lang_slug_categorytransl",
            ),
            models.UniqueConstraint(
                fields=["language_code", "category"],
                name="uniq_lang_category_categorytransl",
            ),
        ]

    def __str__(self) -> str:
        return self.name or str(self.pk)

    def get_translated_object_id(self):
        return "Category", self.category_id

    def get_translated_keys(self):
        return {
            **super().get_translated_keys(),
            "name": self.name,
            "description": self.description,
        }