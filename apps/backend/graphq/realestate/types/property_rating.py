# apps/backend/graphq/realestate/types/property_rating.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import PropertyRating


class PropertyRatingNode(OptimizedDjangoObjectType):
    class Meta:
        model = PropertyRating
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "property": ["exact"],
            "user": ["exact"],

            # ---- Traversals into the listing ----------------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],
            "property__owner": ["exact"],

            # ---- Traversals into the user -------------------------------
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "rating": ["exact", "gte", "lte", "lt", "gt"],
            "review": ["exact", "icontains"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }