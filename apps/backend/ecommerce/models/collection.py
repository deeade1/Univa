# =============================================================================
# COLLECTION MODELS
# =============================================================================
# apps/backend/ecommerce/models/collection.py


from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import JSONField

from ecommerce.models.channel import Channel
from core.models.metadata import  ModelWithMetadata
from core.models.publishable import PublishableModel
from core.models.sortable import SortableModel
from core.utils.editorjs import  default_clean_editor_js


from seo.models import SeoModel, SeoModelTranslationWithSlug


from ecommerce.manager.managers import CollectionManager


from ecommerce.models.product import Product


class CollectionProduct(SortableModel):
    collection = models.ForeignKey(
        "Collection", related_name="collectionproduct", on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, related_name="collectionproduct", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("sort_order",)
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "product"],
                name="unique_collection_product"
            ),
        ]

    def get_ordering_queryset(self):
        return self.product.collectionproduct.all()


class Collection(SeoModel, ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = models.JSONField(blank=True, null=True, default=default_clean_editor_js)

    background_image = models.ImageField(
        upload_to="collection-backgrounds", blank=True, null=True
    )
    background_image_alt = models.CharField(max_length=128, blank=True)
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="collections",
        through=CollectionProduct,
    )

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
        ]

    def __str__(self) -> str:
        return self.name


class CollectionChannelListing(PublishableModel):
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

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "channel"],
                name="unique_collection_channel_listing"
            ),
        ]


class CollectionTranslation(SeoModelTranslationWithSlug):
    collection = models.ForeignKey(
        Collection, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=128, blank=True, null=True)
    description = models.JSONField(blank=True, null=True, default=default_clean_editor_js)

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

