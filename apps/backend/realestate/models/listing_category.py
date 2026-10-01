# apps/backend/realestate/models/listing_category.py

"""
Listing Category model for real estate.
"""

from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.db import models
from django.db.models import JSONField, TextField
from mptt.models import MPTTModel, TreeForeignKey, TreeManager

from core.models.metadata import ModelWithMetadata
from seo.models import SeoModel


class ListingCategory(ModelWithMetadata, MPTTModel, SeoModel):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = JSONField(blank=True, null=True)
    description_plaintext = TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    parent = TreeForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
    background_image = models.ImageField(upload_to="category-backgrounds", blank=True, null=True)
    background_image_alt = models.CharField(max_length=128, blank=True)

    objects = models.Manager()
    tree = TreeManager()

    class Meta:
        indexes = [
            GinIndex(fields=["name", "slug", "description_plaintext"], name="listcat_name_slug_gin",
                    opclasses=["gin_trgm_ops"] * 3),
            BTreeIndex(fields=["updated_at"], name="listcat_updated_idx"),
            GinIndex(fields=["description"], name="listcat_desc_gin"),
            models.Index(fields=["parent"], name="listcat_parent_idx"),
        ]

    def __str__(self):
        return self.name