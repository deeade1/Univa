# apps/backend/graphq/realestate/types/live_tour_registration.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import LiveTourRegistration


class LiveTourRegistrationNode(OptimizedDjangoObjectType):
    class Meta:
        model = LiveTourRegistration
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "user": ["exact"],
            "tour": ["exact"],

            # ---- Traversals into the user -------------------------------
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Traversals into the tour -------------------------------
            "tour__property": ["exact"],
            "tour__property__title": ["exact", "icontains"],
            "tour__property__city": ["exact", "icontains"],
            "tour__agent": ["exact"],
            "tour__scheduled_time": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Scalar filters ----------------------------------------
            "attended": ["exact"],
            "registered_at": ["exact", "gte", "lte", "lt", "gt"],
        }