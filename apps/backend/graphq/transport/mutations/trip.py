# apps/backend/graphq/transport/mutations/trip.py
"""
Trip mutations.

Trip is a proxy over ServiceRequest. All shared/trip-specific state is
stored in the `trip_data` JSON field, exposed via properties with
setters for `shared` and `surge_multiplier` only. Other trip fields
(rider_count, available_seats, day_time, special_requests,
safety_incidents) live only in `_trip_data` and must be written there
before calling save().

`save()` calls `full_clean()`, which invokes the model's `clean()`.
The model's clean() references `self.rider_count` / `self.shared`
which are NOT attributes — see the note at the bottom of this file.
The mutations here do not rely on that clean(); validation is explicit.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.trip import TripNode
from transport.models.rides.trip import Trip
from transport.models.core.service_request import ServiceRequest


# =============================================================================
# Constants
# =============================================================================

_TERMINAL_STATUSES = {
    ServiceRequest.Status.COMPLETED,
    ServiceRequest.Status.CANCELLED,
}

_VALID_DAY_TIMES = {"day", "night"}

_MAX_RIDERS = 10
_MIN_RIDERS = 1


# =============================================================================
# Helpers
# =============================================================================

def _resolve_trip(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid trip id.")
    qs = Trip.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Trip.DoesNotExist:
        raise GraphQLError("Trip not found.")


def _resolve_or_create_stop_point(lat, lng, *, address="", label="stop"):
    """
    Resolve an existing StopPoint at (lat, lng) within a tiny tolerance,
    or create one. Shared with ServiceRequest mutations; duplicated here
    to keep this file self-contained.
    """
    from transport.models import StopPoint

    if lat is None or lng is None:
        return None

    if not (-90 <= lat <= 90):
        raise GraphQLError("Latitude must be between -90 and 90.")
    if not (-180 <= lng <= 180):
        raise GraphQLError("Longitude must be between -180 and 180.")

    point = Point(float(lng), float(lat), srid=4326)

    existing = StopPoint.objects.filter(
        coordinates__distance_lte=(point, 0.0001)
    ).first()
    if existing:
        return existing

    create_kwargs = {"coordinates": point}
    stop_field_names = {f.name for f in StopPoint._meta.get_fields()}
    if "address" in stop_field_names and address:
        create_kwargs["address"] = address
    if "label" in stop_field_names and label:
        create_kwargs["label"] = label

    return StopPoint.objects.create(**create_kwargs)


def _assert_can_manage(trip, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return

    if trip.customer_id == user.pk:
        return

    provider = getattr(user, "service_provider", None)
    if provider is not None and trip.provider_id == provider.pk:
        return

    raise GraphQLError("Not authorized to manage this trip.")


def _refresh_trip_data(trip):
    """
    Ensure `_trip_data` reflects what's persisted on the row.

    The model caches `_trip_data` on __init__ but doesn't refresh it
    after a DB write. After `select_for_update()`, we must sync it or
    subsequent property setters will clobber unrelated keys.
    """
    trip._trip_data = dict(trip.trip_data or {})


def _apply_trip_data(trip, data):
    """Write provided keys into `_trip_data`. Returns keys touched."""
    touched = []
    for key, value in data.items():
        if value is None:
            continue
        trip._trip_data[key] = value
        touched.append(key)
    return touched


def _validate_rider_count(value):
    if value is None:
        return
    if not _MIN_RIDERS <= value <= _MAX_RIDERS:
        raise GraphQLError(
            f"rider_count must be between {_MIN_RIDERS} and {_MAX_RIDERS}."
        )


def _validate_seats(value):
    if value is None:
        return
    if value < 0:
        raise GraphQLError("available_seats cannot be negative.")


def _validate_day_time(value):
    if value is None:
        return
    if value not in _VALID_DAY_TIMES:
        raise GraphQLError(
            f"day_time must be one of: {', '.join(sorted(_VALID_DAY_TIMES))}."
        )


def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


# =============================================================================
# Create
# =============================================================================

class CreateTrip(relay.ClientIDMutation):
    """
    Create a Trip (i.e. a ServiceRequest with service_type='taxi').

    Trip-specific fields (shared, available_seats, rider_count,
    day_time, special_requests, safety_incidents) are stored in the
    trip_data JSON blob.
    """

    class Input:
        pickup_lat = graphene.Float(required=True)
        pickup_lng = graphene.Float(required=True)
        pickup_address = graphene.String()

        dropoff_lat = graphene.Float()
        dropoff_lng = graphene.Float()
        dropoff_address = graphene.String()

        scheduled_at = graphene.DateTime()

        # Trip-specific
        shared = graphene.Boolean(default_value=False)
        available_seats = graphene.Int(default_value=1)
        rider_count = graphene.Int(default_value=1)
        special_requests = graphene.String()
        day_time = graphene.String(default_value="day")
        surge_multiplier = graphene.Decimal(default_value=Decimal("1.0"))
        safety_incidents = graphene.Int(default_value=0)

        luggage_capacity_kg = graphene.Int()
        luggage_price_per_kg = graphene.Decimal()
        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        metadata = graphene.JSONString()

    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        # Validate trip-specific fields before touching the DB.
        _validate_rider_count(input.get("rider_count"))
        _validate_seats(input.get("available_seats"))
        _validate_day_time(input.get("day_time"))

        surge = _parse_decimal(input.get("surge_multiplier"), "surge_multiplier")
        if surge is not None and surge <= 0:
            raise GraphQLError("surge_multiplier must be greater than 0.")

        # Resolve StopPoints
        pickup_stop = _resolve_or_create_stop_point(
            input["pickup_lat"],
            input["pickup_lng"],
            address=input.get("pickup_address") or "",
            label="pickup",
        )

        dropoff_stop = None
        if (
            input.get("dropoff_lat") is not None
            and input.get("dropoff_lng") is not None
        ):
            dropoff_stop = _resolve_or_create_stop_point(
                input["dropoff_lat"],
                input["dropoff_lng"],
                address=input.get("dropoff_address") or "",
                label="dropoff",
            )

        # Build the ServiceRequest kwargs. TripManager.create_trip pulls
        # the trip-specific keys out before forwarding the rest to
        # ServiceRequest.objects.create(). We pass only real model fields
        # via kwargs and stuff the trip-specific stuff into trip_data
        # afterwards.
        service_kwargs = {
            "customer": me,
            "pickup_location": pickup_stop,
            "dropoff_location": dropoff_stop,
            "scheduled_at": input.get("scheduled_at"),
            "luggage_capacity_kg": input.get("luggage_capacity_kg") or 0,
            "luggage_price_per_kg": _parse_decimal(
                input.get("luggage_price_per_kg"), "luggage_price_per_kg"
            ),
            "emergency_contact_name": input.get("emergency_contact_name") or "",
            "emergency_contact_phone": input.get("emergency_contact_phone") or "",
            "metadata": input.get("metadata") or {},
            # TripManager picks these up.
            "shared": bool(input.get("shared", False)),
            "available_seats": input.get("available_seats") or 1,
            "rider_count": input.get("rider_count") or 1,
            "special_requests": input.get("special_requests") or "",
            "day_time": input.get("day_time") or "day",
            "surge_multiplier": float(surge) if surge is not None else 1.0,
            "safety_incidents": input.get("safety_incidents") or 0,
        }
        service_kwargs = {k: v for k, v in service_kwargs.items() if v is not None}

        try:
            trip = Trip.objects.create_trip(**service_kwargs)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except Exception as exc:
            raise GraphQLError(f"Trip creation failed: {exc}")

        # Refresh cached _trip_data so the response reflects reality.
        _refresh_trip_data(trip)

        return cls(
            trip=trip,
            success=True,
            message="Trip created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateTrip(relay.ClientIDMutation):
    """
    Update mutable fields on a Trip.

    Location fields are not editable here — changing pickup/dropoff
    invalidates the dispatch, route, and fare. Use the create flow or
    a dedicated re-route mutation for that.
    """

    class Input:
        trip_id = graphene.ID(required=True)

        scheduled_at = graphene.DateTime()

        # Trip-specific
        shared = graphene.Boolean()
        available_seats = graphene.Int()
        rider_count = graphene.Int()
        special_requests = graphene.String()
        day_time = graphene.String()
        surge_multiplier = graphene.Decimal()
        safety_incidents = graphene.Int()

        luggage_capacity_kg = graphene.Int()
        luggage_price_per_kg = graphene.Decimal()
        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        metadata = graphene.JSONString()

    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_id, **input):
        me = info.context.user
        trip = _resolve_trip(trip_id, lock=True)
        _assert_can_manage(trip, me)

        if trip.status in _TERMINAL_STATUSES and not me.is_staff:
            raise GraphQLError(
                f"Cannot update a trip in terminal state '{trip.status}'."
            )

        _refresh_trip_data(trip)

        # Validate provided values
        _validate_rider_count(input.get("rider_count"))
        _validate_seats(input.get("available_seats"))
        _validate_day_time(input.get("day_time"))

        if "surge_multiplier" in input and input["surge_multiplier"] is not None:
            surge = _parse_decimal(input["surge_multiplier"], "surge_multiplier")
            if surge is not None and surge <= 0:
                raise GraphQLError("surge_multiplier must be greater than 0.")

        update_fields = []

        # ServiceRequest-level scalars
        scalar_map = {
            "scheduled_at": "scheduled_at",
            "luggage_capacity_kg": "luggage_capacity_kg",
            "luggage_price_per_kg": "luggage_price_per_kg",
            "emergency_contact_name": "emergency_contact_name",
            "emergency_contact_phone": "emergency_contact_phone",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                if model_field == "luggage_price_per_kg":
                    setattr(
                        trip,
                        model_field,
                        _parse_decimal(input[input_key], input_key),
                    )
                else:
                    setattr(trip, model_field, input[input_key])
                update_fields.append(model_field)

        # metadata merge
        if "metadata" in input and input["metadata"] is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            trip.metadata = {**(trip.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        # Trip-specific fields go through _trip_data. `shared` and
        # `surge_multiplier` have property setters that also write
        # trip_data via JSON serialization. Others need direct writes.
        trip_data_updates = {}

        if "shared" in input and input["shared"] is not None:
            trip.shared = bool(input["shared"])  # property setter

        if "surge_multiplier" in input and input["surge_multiplier"] is not None:
            trip.surge_multiplier = Decimal(str(input["surge_multiplier"]))  # property setter

        for key in (
            "available_seats",
            "rider_count",
            "special_requests",
            "day_time",
            "safety_incidents",
        ):
            if key in input and input[key] is not None:
                trip_data_updates[key] = input[key]

        if trip_data_updates:
            _apply_trip_data(trip, trip_data_updates)
            # Explicitly include trip_data so save() persists the merged blob.
            update_fields.append("trip_data")

        if not update_fields:
            return cls(
                trip=trip,
                success=True,
                message="Nothing to update.",
            )

        try:
            trip.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        trip.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            trip=trip,
            success=True,
            message="Trip updated.",
        )


# =============================================================================
# Cancel
# =============================================================================

class CancelTrip(relay.ClientIDMutation):
    """
    Cancel a Trip.

    Sets status='cancelled' and records the reason plus who cancelled
    it inside `trip_data`. Preserves the row for audit.
    """

    class Input:
        trip_id = graphene.ID(required=True)
        reason = graphene.String()

    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_id, reason=None):
        me = info.context.user
        trip = _resolve_trip(trip_id, lock=True)
        _assert_can_manage(trip, me)

        if trip.status == ServiceRequest.Status.CANCELLED:
            return cls(
                trip=trip,
                success=True,
                message="Trip is already cancelled.",
            )
        if trip.status == ServiceRequest.Status.COMPLETED:
            raise GraphQLError("Cannot cancel a completed trip.")

        _refresh_trip_data(trip)

        trip._trip_data["cancelled"] = True
        trip._trip_data["cancellation_reason"] = reason or ""
        trip._trip_data["cancelled_at"] = timezone.now().isoformat()
        trip._trip_data["cancelled_by_id"] = me.pk

        trip.status = ServiceRequest.Status.CANCELLED

        try:
            trip.save(update_fields=["status", "trip_data", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            trip=trip,
            success=True,
            message="Trip cancelled.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteTrip(relay.ClientIDMutation):
    """
    Delete a Trip.

    Hard delete of the underlying ServiceRequest row. Refuses while the
    trip is still active — cancel first.
    """

    class Input:
        trip_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_id):
        me = info.context.user
        trip = _resolve_trip(trip_id, lock=True)
        _assert_can_manage(trip, me)

        if trip.status not in _TERMINAL_STATUSES:
            raise GraphQLError(
                "Cannot delete an active trip. Cancel it first."
            )

        try:
            trip.delete()
        except Exception as exc:
            raise GraphQLError(
                f"Delete blocked — trip has related records: {exc}"
            )

        return cls(success=True, message="Trip deleted.")


# =============================================================================
# Registration
# =============================================================================

class TripMutations(graphene.ObjectType):
    create_trip = CreateTrip.Field()
    update_trip = UpdateTrip.Field()
    cancel_trip = CancelTrip.Field()
    delete_trip = DeleteTrip.Field()