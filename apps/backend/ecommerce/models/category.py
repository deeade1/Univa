# apps/backend/ecommerce/models/category.py

"""
Ecommerce Category Models.

This module contains the category hierarchy and category translations.

Architecture:
    Category
        └── CategoryTranslation

Categories are independent of Product at the Python import level.
Products reference Category through a ForeignKey, while Django resolves
the relationship at model initialization time.

This keeps the ecommerce model layer modular and helps prevent circular
imports between product, category, collection, and attribute modules.
"""

from __future__ import annotations

from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import TextField

from mptt.managers import TreeManager
from mptt.models import MPTTModel

from core.models.metadata import ModelWithMetadata
from core.utils.editorjs import default_clean_editor_js
from seo.models import SeoModel, SeoModelTranslationWithSlug


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
    """

    name = models.CharField(
        max_length=250,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )

    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )

    description_plaintext = TextField(
        blank=True,
    )

    background_image = models.ImageField(
        upload_to="category-backgrounds",
        blank=True,
        null=True,
    )

    background_image_alt = models.CharField(
        max_length=128,
        blank=True,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    search_vector = SearchVectorField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
    )

    # -------------------------------------------------------------------------
    # Managers
    # -------------------------------------------------------------------------

    objects = models.Manager()
    tree = TreeManager()

    # -------------------------------------------------------------------------
    # Meta
    # -------------------------------------------------------------------------

    class Meta:
        indexes = [
            *ModelWithMetadata.Meta.indexes,

            GinIndex(
                fields=[
                    "name",
                    "slug",
                    "description_plaintext",
                ],
                name="prod_cat_name_slug_gin",
                opclasses=[
                    "gin_trgm_ops",
                    "gin_trgm_ops",
                    "gin_trgm_ops",
                ],
            ),

            GinIndex(
                fields=["search_vector"],
                name="prod_cat_search_vec_gin",
            ),

            BTreeIndex(
                fields=["updated_at"],
                name="prod_cat_updated_idx",
            ),
        ]

        ordering = ("name",)

    # -------------------------------------------------------------------------
    # String representation
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return self.name


# =============================================================================
# CATEGORY TRANSLATION
# =============================================================================


class CategoryTranslation(SeoModelTranslationWithSlug):
    """
    Localized category data.

    A category can have one translation per language.

    The base Category remains responsible for the canonical category
    identity, while this model stores localized presentation data.
    """

    category = models.ForeignKey(
        Category,
        related_name="translations",
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )

    # -------------------------------------------------------------------------
    # Meta
    # -------------------------------------------------------------------------

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "language_code",
                    "slug",
                ],
                name="uniq_lang_slug_categorytransl",
            ),

            models.UniqueConstraint(
                fields=[
                    "language_code",
                    "category",
                ],
                name="uniq_lang_category_categorytransl",
            ),
        ]

    # -------------------------------------------------------------------------
    # String representation
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return self.name or str(self.pk)

    # -------------------------------------------------------------------------
    # Translation API
    # -------------------------------------------------------------------------

    def get_translated_object_id(self):
        return "Category", self.category_id

    def get_translated_keys(self):
        return {
            **super().get_translated_keys(),
            "name": self.name,
            "description": self.description,
        }