# apps/backend/graphq/realestate/types/virtual_tour.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import VirtualTour


class VirtualTourNode(OptimizedDjangoObjectType):
    class Meta:
        model = VirtualTour
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "property": ["exact"],

            # ---- Traversals into the parent listing ---------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],

            # ---- Scalar filters ----------------------------------------
            "is_primary": ["exact"],
            "tour_url": ["exact", "icontains"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
        }