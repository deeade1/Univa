# apps/backend/graphq/realestate/types/location_preference.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter  # noqa: F401 — registers the converter

from realestate.models import LocationPreference


class LocationPreferenceNode(OptimizedDjangoObjectType):
    class Meta:
        model = LocationPreference
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "name": ["exact", "icontains", "istartswith"],
            "radius_km": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Timestamps — the model has no explicit *_at fields, so
            #      nothing to filter on here. If you add created_at/
            #      updated_at later, add them then.
        }