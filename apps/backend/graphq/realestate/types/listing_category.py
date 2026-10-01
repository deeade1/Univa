# apps/backend/graphq/realestate/types/listing_category.py

from graphene_django import DjangoObjectType
from graphene import Node

from realestate.models import ListingCategory


class ListingCategoryNode(DjangoObjectType):
    class Meta:
        model = ListingCategory
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Scalar filters (note: no trailing space on keys) ------
            "name": ["exact", "icontains", "istartswith"],
            "slug": ["exact", "icontains"],   # ← was "slug " with a space
            "description_plaintext": ["icontains"],
            "background_image_alt": ["exact", "icontains"],

            # ---- Forward FK (self-referential) --------------------------
            "parent": ["exact", "isnull"],    # ← was "children", which is the reverse side

            # ---- Timestamps --------------------------------------------
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }