# apps/backend/graphq/realestate/types/transaction.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import Transaction


class TransactionNode(OptimizedDjangoObjectType):
    class Meta:
        model = Transaction
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "property": ["exact"],
            "buyer": ["exact"],
            "seller": ["exact"],

            # ---- Traversals into the listing ----------------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__property_status": ["exact"],

            # ---- Traversals into the buyer (Client) ---------------------
            "buyer__user": ["exact"],
            "buyer__user__email": ["exact", "icontains"],

            # ---- Traversals into the seller (User) ----------------------
            "seller__email": ["exact", "icontains"],
            "seller__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "status": ["exact", "in"],
            "offer_price": ["exact", "gte", "lte", "lt", "gt"],
            "agreed_price": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "escrow_number": ["exact", "icontains"],

            # ---- Dates -------------------------------------------------
            "target_close_date": ["exact", "gte", "lte", "lt", "gt"],
            "actual_close_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }