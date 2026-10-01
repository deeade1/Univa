# apps/backend/graphq/realestate/types/agent_rating.py

from graphene_django import DjangoObjectType
from graphene import Node

from realestate.models import AgentRating


class AgentRatingNode(DjangoObjectType):
    """
    GraphQL type for AgentRating — client reviews of agents.
    """

    class Meta:
        model = AgentRating
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "agent": ["exact"],
            "user": ["exact"],

            # ---- Traversals into the agent ------------------------------
            # Agent has no direct `user` field — it exposes one as a
            # property that walks through `agent_profile`. Two-hop the
            # FK path to reach the underlying user.
            "agent__agent_profile__user": ["exact"],
            "agent__agent_profile__user__email": ["exact", "icontains"],
            "agent__is_verified": ["exact"],
            "agent__is_active": ["exact"],

            # ---- Traversals into the rater ------------------------------
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "rating": ["exact", "gte", "lte", "lt", "gt"],
            "review": ["exact", "icontains"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
        }