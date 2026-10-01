# apps/backend/graphq/realestate/types/agent.py

from graphene import Node
from graphene_django import DjangoObjectType

from realestate.models import Agent


class AgentNode(DjangoObjectType):
    """
    GraphQL type for Agent — operational/backend data.
    """

    class Meta:
        model = Agent
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward OneToOne (the correct name) -------------------
            "agent_profile": ["exact"],

            # ---- Scalar fields ----------------------------------------
            "license_number": ["exact", "icontains"],

            # ---- Boolean flags ----------------------------------------
            "is_verified": ["exact"],
            "is_active": ["exact"],

            # ---- Performance metrics ----------------------------------
            "total_listings": ["exact", "gte", "lte"],
            "total_sales": ["exact", "gte", "lte"],
            "agent_rating": ["exact", "gte", "lte"],
            "total_reviews": ["exact", "gte", "lte"],

            # ---- Timestamps (from TimeStampedModel) -------------------
            "created": ["exact", "gte", "lte", "lt", "gt"],
            "updated": ["exact", "gte", "lte", "lt", "gt"],
        }