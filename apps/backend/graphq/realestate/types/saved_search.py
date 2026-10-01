# apps/backend/graphq/realestate/types/saved_search.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import SavedSearch


class SavedSearchNode(OptimizedDjangoObjectType):
    class Meta:
        model = SavedSearch
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "user": ["exact"],

            # ---- Traversals into the user -------------------------------
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "name": ["exact", "icontains", "istartswith"],
            "is_active": ["exact"],

            # ---- Timestamps --------------------------------------------
            "last_notified": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
        }