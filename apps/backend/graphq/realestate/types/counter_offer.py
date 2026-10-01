# apps/backend/graphq/realestate/types/counter_offer.py

from graphene_django import DjangoObjectType
from graphene import Node, Boolean
from graphql_relay import from_global_id

from realestate.models import CounterOffer


class CounterOfferNode(DjangoObjectType):
    is_expired = Boolean()

    class Meta:
        model = CounterOffer
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "original_offer": ["exact"],
            "created_by": ["exact"],

            # ---- Traversals into the parent offer -----------------------
            "original_offer__property": ["exact"],
            "original_offer__buyer": ["exact"],
            "original_offer__status": ["exact"],
            "original_offer__offer_price": ["exact", "gte", "lte"],

            # ---- Traversals into the creator ----------------------------
            "created_by__email": ["exact", "icontains"],
            "created_by__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "status": ["exact", "in"],
            "counter_price": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Timestamps --------------------------------------------
            "expiration_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }

    def resolve_is_expired(self, info):
        return self.is_expired()