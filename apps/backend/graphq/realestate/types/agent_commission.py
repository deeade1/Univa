# apps/backend/graphq/realestate/types/commission.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import  AgentCommission


class AgentCommissionNode(OptimizedDjangoObjectType):
    class Meta:
        model = AgentCommission
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "agent": ["exact"],
            "transaction": ["exact"],
            "commission_plan": ["exact"],

            # ---- Traversals into the agent ------------------------------
            "agent__agent_profile__user": ["exact"],
            "agent__agent_profile__user__email": ["exact", "icontains"],

            # ---- Traversals into the transaction ------------------------
            # Adjust these to whatever Transaction actually declares.
            # These two are the most likely candidates.
            "transaction__status": ["exact"],
            "transaction__property": ["exact"],

            # ---- Traversals into the plan -------------------------------
            "commission_plan__plan_type": ["exact"],
            "commission_plan__is_active": ["exact"],

            # ---- Scalar filters ----------------------------------------
            "calculated_amount": ["exact", "gte", "lte", "lt", "gt"],
            "paid_amount": ["exact", "gte", "lte", "lt", "gt"],
            "paid_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
        }