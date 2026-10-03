# apps/backend/ecommerce/models/collection.py

"""
Collection models.

A Collection is a curated set of products — "Summer Sale", "Top Rated",
"Under ₦5,000", "New This Week". Collections can be:

    - MANUAL      — products hand-picked by an editor
    - RULE_BASED  — products matched by a saved rule definition

The rule engine itself lives in `ecommerce.services.collection`.
This module only stores the rule definition.

Products link to collections via the `CollectionProduct` through-model,
which carries a `sort_order` so manual collections present in a
controlled order.

Design notes
------------

- `Collection.products` is M2M with `through=CollectionProduct`.
- `CollectionProduct.get_ordering_queryset()` returns the sibling rows
  within the *same collection*, so re-ordering one collection does not
  touch another.

- `CollectionChannelListing` is where channel-scoped visibility lives.
  `is_active` on both `Collection` and `CollectionChannelListing` allows
  a soft "hide without unpublishing" workflow.
"""

from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q

from core.models.metadata import ModelWithMetadata
from core.models.publishable import PublishableModel
from core.models.sortable import SortableModel
from core.utils.editorjs import default_clean_editor_js
from ecommerce.manager.managers import CollectionManager
from ecommerce.models.channel import Channel
from ecommerce.models.product import Product
from seo.models import SeoModel, SeoModelTranslationWithSlug


# =============================================================================
# ENUMS
# =============================================================================


class CollectionType(models.TextChoices):
    """How products are added to a collection."""

    MANUAL = "manual", "Manual (curated)"
    RULE_BASED = "rule_based", "Rule-based (dynamic)"


# =============================================================================
# COLLECTION PRODUCT (through)
# =============================================================================


class CollectionProduct(SortableModel):
    """
    Through-model linking a Product to a Collection.

    Ordering is per-collection: `sort_order` values are unique in the
    context of a single collection and are renumbered by SortableModel
    when a row is moved or deleted.
    """

    collection = models.ForeignKey(
        "Collection",
        related_name="collectionproduct",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name="collectionproduct",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("sort_order", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "product"],
                name="unique_collection_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection.name} ↔ {self.product.name}"

    def get_ordering_queryset(self):
        """
        Return sibling rows within the same collection.

        Previous implementation used `self.product.collectionproduct.all()`,
        which returned all collections the product belongs to — the wrong
        scope for renumbering. Now fixed to the collection this row belongs
        to.
        """
        return self.collection.collectionproduct.all()


# =============================================================================
# COLLECTION
# =============================================================================


class Collection(SeoModel, ModelWithMetadata):
    """
    A curated set of products.

    Manual collections list their products via `CollectionProduct`.

    Rule-based collections define their membership in `rule_definition`
    (shape decided by the rule engine) and are populated dynamically.
    The manual `products` M2M is still valid for rule-based collections
    if the editor wants to pin specific products on top of the rule
    result — call it a "pinned products" list.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )
    description = models.JSONField(
        blank=True,
        default=default_clean_editor_js,
    )

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------

    background_image = models.ImageField(
        upload_to="collection-backgrounds",
        blank=True,
        null=True,
    )
    background_image_alt = models.CharField(max_length=128, blank=True)

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    collection_type = models.CharField(
        max_length=32,
        choices=CollectionType.choices,
        default=CollectionType.MANUAL,
        db_index=True,
    )
    rule_definition = models.JSONField(
        blank=True,
        default=dict,
        help_text=(
            "Rule definition for RULE_BASED collections. Shape is "
            "interpreted by ecommerce.services.collection."
        ),
    )
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="collections",
        through=CollectionProduct,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Soft-delete flag. Inactive collections are hidden from "
            "the storefront but remain referenced by historical data."
        ),
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Manager
    # ------------------------------------------------------------------

    objects = CollectionManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                fields=["name", "slug"],
                name="collection_search_gin",
                opclasses=["gin_trgm_ops"] * 2,
            ),
            models.Index(
                fields=["is_active", "collection_type"],
                name="collection_active_type_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def is_manual(self) -> bool:
        return self.collection_type == CollectionType.MANUAL

    @property
    def is_rule_based(self) -> bool:
        return self.collection_type == CollectionType.RULE_BASED


# =============================================================================
# COLLECTION CHANNEL LISTING
# =============================================================================


class CollectionChannelListing(PublishableModel):
    """
    Channel-scoped visibility and status for a Collection.

    `is_active` here is separate from `Collection.is_active`: a
    collection can be globally active but paused on a specific channel,
    or globally inactive but kept "visible" for archival purposes on a
    legacy channel.
    """

    collection = models.ForeignKey(
        Collection,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        related_name="collection_listings",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the collection is shown on this channel.",
    )

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "channel"],
                name="unique_collection_channel_listing",
            ),
        ]
        indexes = [
            models.Index(
                fields=["channel", "is_active"],
                name="coll_listing_channel_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection.name} on {self.channel.slug}"


# =============================================================================
# COLLECTION TRANSLATION
# =============================================================================


class CollectionTranslation(SeoModelTranslationWithSlug):
    """
    Localized name and description for a Collection.
    """

    collection = models.ForeignKey(
        Collection,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=250, blank=True)
    description = models.JSONField(
        blank=True,
        default=default_clean_editor_js,
    )

    class Meta:
        ordering = ["collection_id", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="uniq_lang_slug_collectiontransl",
            ),
            models.UniqueConstraint(
                fields=["language_code", "collection"],
                name="uniq_lang_collection_collectiontransl",
            ),
        ]

    def __str__(self) -> str:
        return self.name or str(self.pk)

    def get_translated_object_id(self):
        return "Collection", self.collection_id

    def get_translated_keys(self):
        return {
            **super().get_translated_keys(),
            "name": self.name,
            "description": self.description,
        }