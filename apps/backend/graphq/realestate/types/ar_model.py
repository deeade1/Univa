# apps/backend/graphq/realestate/types/ar_model.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import ARModel


class ARModelNode(OptimizedDjangoObjectType):
    class Meta:
        model = ARModel
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
            "anchor_type": ["exact", "in"],
            "scale": ["exact", "gte", "lte", "lt", "gt"],

            # ---- URL search --------------------------------------------
            "model_url": ["exact", "icontains"],
        }