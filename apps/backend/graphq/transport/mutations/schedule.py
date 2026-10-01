# apps/backend/graphq/transport/mutations/trip_schedule_template.py
"""
TripScheduleTemplate mutations.

Templates are global config — they determine which trips exist on which
days. Every write is staff-only.

The `instantiate` mutation calls the model's `instantiate_for_date()` to
materialise a Trip for a given date. NOTE: the model's current
implementation has two bugs that will make it raise — see the notes
after this file. Until those are fixed, `instantiate` will surface a
clear GraphQLError explaining the failure.
"""

from datetime import datetime, time

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.schedule import TripScheduleTemplateNode
from graphq.transport.types.trip import TripNode

from transport.models.rides.schedule import TripScheduleTemplate  
from transport.models.rides.trip import Trip


_WEEKDAY_RANGE = set(range(7))  # Monday=0 ... Sunday=6


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_template(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid trip_schedule_template_id.")
    qs = TripScheduleTemplate.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except TripScheduleTemplate.DoesNotExist:
        raise GraphQLError("Trip schedule template not found.")


def _validate_days_of_week(value):
    if value is None:
        return
    if not isinstance(value, list):
        raise GraphQLError("days_of_week must be a list of integers.")
    for day in value:
        if not isinstance(day, int) or day not in _WEEKDAY_RANGE:
            raise GraphQLError(
                "days_of_week must contain integers between 0 and 6 (Monday=0)."
            )


def _validate_fare(value):
    if value is None:
        return
    if value < 0:
        raise GraphQLError("base_fare cannot be negative.")


# =============================================================================
# Create
# =============================================================================

class CreateTripScheduleTemplate(relay.ClientIDMutation):
    """Create a TripScheduleTemplate. Staff-only."""

    class Input:
        route_name = graphene.String(required=True)
        departure_state = graphene.String(required=True)
        departure_city = graphene.String(required=True)
        destination_state = graphene.String(required=True)
        destination_city = graphene.String(required=True)
        departure_time = graphene.Time(required=True)
        days_of_week = graphene.List(graphene.Int, required=True)

        vehicle_type = graphene.String()
        base_fare = graphene.Decimal()
        active = graphene.Boolean()

    trip_schedule_template = graphene.Field(TripScheduleTemplateNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        _assert_staff(info.context.user)

        _validate_days_of_week(input["days_of_week"])
        _validate_fare(input.get("base_fare"))

        payload = {
            "route_name": input["route_name"],
            "departure_state": input["departure_state"],
            "departure_city": input["departure_city"],
            "destination_state": input["destination_state"],
            "destination_city": input["destination_city"],
            "departure_time": input["departure_time"],
            "days_of_week": input["days_of_week"],
            "vehicle_type": input.get("vehicle_type"),
            "base_fare": input.get("base_fare") or 0,
            "active": (
                input["active"] if input.get("active") is not None else True
            ),
        }

        try:
            template = TripScheduleTemplate(**payload)
            template.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        template.save()

        return cls(
            trip_schedule_template=template,
            success=True,
            message="Trip schedule template created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateTripScheduleTemplate(relay.ClientIDMutation):
    """Update a TripScheduleTemplate. Staff-only."""

    class Input:
        trip_schedule_template_id = graphene.ID(required=True)

        route_name = graphene.String()
        departure_state = graphene.String()
        departure_city = graphene.String()
        destination_state = graphene.String()
        destination_city = graphene.String()
        departure_time = graphene.Time()
        days_of_week = graphene.List(graphene.Int)

        vehicle_type = graphene.String()
        base_fare = graphene.Decimal()
        active = graphene.Boolean()

    trip_schedule_template = graphene.Field(TripScheduleTemplateNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_schedule_template_id, **input):
        _assert_staff(info.context.user)
        template = _resolve_template(trip_schedule_template_id, lock=True)

        _validate_days_of_week(input.get("days_of_week"))
        _validate_fare(input.get("base_fare"))

        update_fields = []

        scalar_map = {
            "route_name": "route_name",
            "departure_state": "departure_state",
            "departure_city": "departure_city",
            "destination_state": "destination_state",
            "destination_city": "destination_city",
            "departure_time": "departure_time",
            "days_of_week": "days_of_week",
            "vehicle_type": "vehicle_type",
            "base_fare": "base_fare",
            "active": "active",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(template, model_field, input[input_key])
                update_fields.append(model_field)

        if not update_fields:
            return cls(
                trip_schedule_template=template,
                success=True,
                message="Nothing to update.",
            )

        try:
            template.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        template.save(update_fields=update_fields)

        return cls(
            trip_schedule_template=template,
            success=True,
            message="Trip schedule template updated.",
        )


# =============================================================================
# Instantiate
# =============================================================================

class InstantiateTripScheduleTemplate(relay.ClientIDMutation):
    """
    Materialise a Trip from a template for a specific date.

    Delegates to `TripScheduleTemplate.instantiate_for_date()`. That
    model method currently has two bugs (see note after this file); if
    they aren't fixed, this mutation surfaces the error as a
    GraphQLError rather than crashing the resolver.

    Idempotency: creating a Trip twice for the same date would duplicate
    the schedule. Callers should pass `force=true` only for corrections.
    """

    class Input:
        trip_schedule_template_id = graphene.ID(required=True)
        date = graphene.Date(required=True)
        force = graphene.Boolean(default_value=False)

    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, trip_schedule_template_id, date, force=False
    ):
        _assert_staff(info.context.user)
        template = _resolve_template(trip_schedule_template_id, lock=True)

        if not template.active:
            raise GraphQLError("Cannot instantiate an inactive template.")

        weekday = date.weekday()
        if weekday not in (template.days_of_week or []):
            raise GraphQLError(
                f"Template is not scheduled for {date.isoformat()} "
                f"(weekday {weekday})."
            )

        # Duplicate guard — check for an existing trip from this template
        # on the same date. Relies on Trip.metadata["template_id"] being
        # set (see the model note below).
        from django.db.models import Q
        existing = (
            Trip.objects.filter(
                Q(metadata__template_id=str(template.pk))
                & Q(scheduled_at__date=date)
            )
            .only("id")
            .first()
        )
        if existing and not force:
            raise GraphQLError(
                f"A trip from this template already exists on "
                f"{date.isoformat()}. Use force=true to create another."
            )

        try:
            trip = template.instantiate_for_date(date)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except Exception as exc:
            raise GraphQLError(f"Instantiation failed: {exc}")

        # Record provenance so the duplicate guard works and the trip can
        # be traced back to its template.
        metadata = dict(trip.metadata or {})
        metadata["template_id"] = str(template.pk)
        metadata["template_route_name"] = template.route_name
        trip.metadata = metadata
        trip.save(update_fields=["metadata", "updated_at"])

        return cls(
            trip=trip,
            success=True,
            message=f"Trip created for {date.isoformat()}.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteTripScheduleTemplate(relay.ClientIDMutation):
    """
    Delete a TripScheduleTemplate. Staff-only.

    Prefer `active=false` for temporary suspension — deleting loses the
    historical link between already-materialised trips and the template
    that produced them (unless you store that in `Trip.metadata`).
    """

    class Input:
        trip_schedule_template_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_schedule_template_id):
        _assert_staff(info.context.user)
        template = _resolve_template(trip_schedule_template_id, lock=True)
        template.delete()
        return cls(success=True, message="Trip schedule template deleted.")


# =============================================================================
# Registration
# =============================================================================

class TripScheduleTemplateMutations(graphene.ObjectType):
    create_trip_schedule_template = CreateTripScheduleTemplate.Field()
    update_trip_schedule_template = UpdateTripScheduleTemplate.Field()
    instantiate_trip_schedule_template = InstantiateTripScheduleTemplate.Field()
    delete_trip_schedule_template = DeleteTripScheduleTemplate.Field()