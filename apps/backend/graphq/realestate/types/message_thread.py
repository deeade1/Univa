# apps/backend/graphq/realestate/types/message_thread.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import MessageThread


class MessageThreadNode(OptimizedDjangoObjectType):
    class Meta:
        model = MessageThread
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward relations (the correct names) ------------------
            "property": ["exact", "isnull"],     # property is nullable
            "participants": ["exact"],           # M2M filter

            # ---- Traversals into the parent listing ---------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],

            # ---- Traversals into participants ---------------------------
            "participants__email": ["exact", "icontains"],
            "participants__first_name": ["exact", "icontains"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }