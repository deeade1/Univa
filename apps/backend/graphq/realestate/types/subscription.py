# apps/backend/graphq/realestate/types/subscription.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter  # noqa: F401 — registers the converter

from realestate.models import PropertySubscription


class PropertySubscriptionNode(OptimizedDjangoObjectType):
    class Meta:
        model = PropertySubscription
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "property_type": ["exact", "icontains"],
            "radius_km": ["exact", "gte", "lte"],
            "is_active": ["exact"],
            "notification_frequency": ["exact", "in"],

            # ---- Timestamps --------------------------------------------
            "last_notified": ["exact", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }