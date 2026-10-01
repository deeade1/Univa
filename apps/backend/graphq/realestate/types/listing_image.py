# apps/backend/graphq/realestate/types/listing_image.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from django_filters import CharFilter

from realestate.models import ListingImage


class ListingImageNode(OptimizedDjangoObjectType):
    class Meta:
        model = ListingImage
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # FK to Listing — filter images by their parent listing
            "listing": ["exact"],

            # Image presence — the useful filter on an ImageField
           # "image": ["isnull"],

            # Free-text search on the caption
            "short_description": ["exact", "icontains"],

            # Timestamps (TimeStampedModel)
            "created": ["exact", "gte", "lte", "lt", "gt"],
            "updated": ["exact", "gte", "lte", "lt", "gt"],
        }
        # If you truly need to match the stored path/URL string, override
        # the field type so django-filter knows how to build the lookup.
        '''filter_overrides = {
            __import__("django_resized.forms", fromlist=["ResizedImageField"]).ResizedImageField: {
                "filter_class": CharFilter,
                "extra": lambda f: {"lookup_expr": "exact"},
            },
        }'''