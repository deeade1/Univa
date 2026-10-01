# apps/backend/graphq/realestate/types/offer.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import Offer


class OfferNode(OptimizedDjangoObjectType):
    class Meta:
        model = Offer
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "property": ["exact"],
            "buyer": ["exact"],

            # ---- Traversals into the listing ----------------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],
            "property__owner": ["exact"],

            # ---- Traversals into the buyer (Client) ---------------------
            # Adjust to whatever Client declares. Most likely candidates:
            "buyer__user": ["exact"],
            "buyer__user__email": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "status": ["exact", "in"],
            "offer_price": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Timestamps --------------------------------------------
            "expiration_date": ["exact", "gte", "lte", "lt", "gt"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }