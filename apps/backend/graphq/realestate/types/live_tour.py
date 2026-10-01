# apps/backend/graphq/realestate/types/live_tour.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import LiveTourSchedule


class LiveTourScheduleNode(OptimizedDjangoObjectType):
    class Meta:
        model = LiveTourSchedule
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "property": ["exact"],
            "agent": ["exact"],

            # ---- Traversals into the parent listing ---------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],

            # ---- Traversals into the agent ------------------------------
            "agent__agent_profile__user": ["exact"],
            "agent__agent_profile__user__email": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "scheduled_time": ["exact", "gte", "lte", "lt", "gt"],
            "duration_minutes": ["exact", "gte", "lte"],
            "max_attendees": ["exact", "gte", "lte"],
        }