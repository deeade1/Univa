# apps/backend/graphq/transport/types/shared_trip.py

"""
GraphQL Nodes for Shared Trip, Waitlist Entry, and User Preference.

`SharedTrip` is a proxy of `ServiceRequest`. Every shared-specific
field lives in the `shared_trip_data` JSONField on the parent row.
`SharedTrip` exposes them as Python properties — but properties are
NOT Django model fields, so they cannot go in `Meta.filter_fields` or
`Meta.ordering`. The `SharedTripFilterSet` bridges that gap with JSON
key lookups.
"""

from django.db.models import IntegerField
from django.db.models.functions import Cast
from django_filters import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    NumberFilter,
)

from graphene import Node, Int, Boolean, String, Field, List, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rides.shared_trip import (
    SharedTrip,
    WaitlistEntry,
    UserPreference,
)


# =============================================================================
# FilterSet for SharedTrip (handles JSON-backed properties)
# =============================================================================

class SharedTripFilterSet(FilterSet):
    """
    Custom FilterSet that translates shared-specific properties into
    lookups on the `shared_trip_data` JSONField.

    Note: `shared_available_seats`, `shared_day_time`, and
    `shared_status` are properties, not columns, so they can't go in
    `Meta.fields` directly. Each is declared as a class-level filter
    with a `field_name` pointing into the JSON field.
    """

    shared_status = CharFilter(
        field_name="shared_trip_data__shared_status",
        lookup_expr="exact",
    )
    shared_day_time = CharFilter(
        field_name="shared_trip_data__day_time",
        lookup_expr="exact",
    )

    # Three variants so callers can do exact / >= / <=.
    shared_available_seats = NumberFilter(
        field_name="shared_trip_data__available_seats",
        lookup_expr="exact",
    )
    shared_available_seats_gte = NumberFilter(
        field_name="shared_trip_data__available_seats",
        lookup_expr="gte",
    )
    shared_available_seats_lte = NumberFilter(
        field_name="shared_trip_data__available_seats",
        lookup_expr="lte",
    )

    # Semantic shortcuts
    is_available = BooleanFilter(method="filter_is_available")
    is_full = BooleanFilter(method="filter_is_full")

    class Meta:
        model = SharedTrip
        interfaces = (Node,)
        fields = {
            # Real columns inherited from ServiceRequest
            "id": ["exact"],
            "customer": ["exact"],
            "customer__email": ["exact", "icontains"],
            "provider": ["exact"],
            "vehicle": ["exact"],
            "service_type": ["exact"],
            "status": ["exact"],
            "created_at": ["exact", "gte", "lte"],
            "updated_at": ["exact", "gte", "lte"],
            "scheduled_at": ["exact", "gte", "lte"],
            "estimated_arrival_time": ["exact", "gte", "lte", "isnull"],
        }

    # ------------------------------------------------------------------
    # Custom method filters
    # ------------------------------------------------------------------

    def filter_is_available(self, queryset, name, value):
        if value:
            return queryset.filter(
                shared_trip_data__shared_status="available",
                shared_trip_data__available_seats__gt=0,
            )
        # "not available" = full OR zero seats
        from django.db.models import Q
        return queryset.filter(
            Q(shared_trip_data__shared_status="full")
            | Q(shared_trip_data__available_seats__lte=0)
        )

    def filter_is_full(self, queryset, name, value):
        if value:
            return queryset.filter(shared_trip_data__shared_status="full")
        return queryset.exclude(shared_trip_data__shared_status="full")


# =============================================================================
# SharedTripNode
# =============================================================================

class SharedTripNode(OptimizedDjangoObjectType):
    """GraphQL node for a shared trip (proxy over ServiceRequest)."""

    # Properties exposed as scalar fields — must be declared ABOVE Meta
    waitlist_count = Int(description="Number of active waitlist entries")
    is_available = Boolean(description="Whether the trip has seats left")
    is_full = Boolean(description="Whether the trip is fully booked")
    day_time_display = String(description="Human-readable day/night value")
    shared_status_display = String(description="Human-readable shared status")
    available_seats = Int(description="Current number of available seats")

    user_position = Field(
        Int,
        user_id=Int(required=True, description="User ID to check on the waitlist"),
        description="Current waitlist position of a user",
    )

    class Meta:
        model = SharedTrip
        interfaces = (Node,)
        fields = "__all__"
        # `filterset_class` supersedes `filter_fields`. Do NOT keep
        # `filter_fields` alongside it — it's ignored when both are set.
        filterset_class = SharedTripFilterSet
        # `ordering` can only reference real columns. JSON-backed
        # ordering requires an annotation (see `resolve_available_seats`
        # for how to sort on demand at the resolver level).
       

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------

    def resolve_waitlist_count(self, info):
        return self.waitlist_count

    def resolve_is_available(self, info):
        return self.is_available

    def resolve_is_full(self, info):
        return self.is_full

    def resolve_day_time_display(self, info):
        return self.day_time_display

    def resolve_shared_status_display(self, info):
        return self.shared_status_display

    def resolve_available_seats(self, info):
        return self.shared_available_seats

    def resolve_user_position(self, info, user_id):
        """
        `user_id` is a raw integer here, not a global Relay ID, because
        the field argument is `Int`. If you want to pass a Relay global
        ID instead, change `user_id=Int(...)` to `user_id=ID(...)` and
        call `from_global_id` inside the resolver.
        """
        return self.get_position_for_user(user_id)


# =============================================================================
# WaitlistEntryNode
# =============================================================================

class WaitlistEntryNode(OptimizedDjangoObjectType):
    wait_time_hours = Float(description="Estimated wait time in hours")
    is_active = Boolean(description="Whether the entry is still active")
    priority_score = Int(description="Priority score for the waitlist")
    position_display = String(description="Human-readable position display")
    status = String(description="Current status of the waitlist entry")

    class Meta:
        model = WaitlistEntry
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "shared_trip": ["exact"],
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "notified": ["exact"],
            "expired": ["exact"],
            "position": ["exact", "gte", "lte"],
            "joined_at": ["exact", "gte", "lte"],
            "notified_at": ["exact", "gte", "lte", "isnull"],
            "expired_at": ["exact", "gte", "lte", "isnull"],
            "created_at": ["gte", "lte"],
            "updated_at": ["gte", "lte"],
        }
        

    def resolve_wait_time_hours(self, info):
        return self.wait_time_hours

    def resolve_is_active(self, info):
        return self.is_active

    def resolve_priority_score(self, info):
        return self.priority_score

    def resolve_position_display(self, info):
        return self.get_position_display()

    def resolve_status(self, info):
        if self.expired:
            return "expired"
        if self.notified:
            return "notified"
        return "waiting"


# =============================================================================
# UserPreferenceNode
# =============================================================================

class UserPreferenceNode(OptimizedDjangoObjectType):
    music_preference_display = String()
    conversation_level_display = String()
    temperature_preference_display = String()

    class Meta:
        model = UserPreference
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "music_preference": ["exact"],
            "conversation_level": ["exact", "gte", "lte"],
            "temperature_preference": ["exact"],
            "created_at": ["gte", "lte"],
            "updated_at": ["gte", "lte"],
        }
        

    def resolve_music_preference_display(self, info):
        return dict(UserPreference.MusicPreference.choices).get(
            self.music_preference, self.music_preference
        )

    def resolve_conversation_level_display(self, info):
        return dict(UserPreference.ConversationLevel.choices).get(
            self.conversation_level, str(self.conversation_level)
        )

    def resolve_temperature_preference_display(self, info):
        return dict(UserPreference.TemperaturePreference.choices).get(
            self.temperature_preference, str(self.temperature_preference)
        )