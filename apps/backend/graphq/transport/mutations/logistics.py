# apps/backend/graphq/transport/mutations/logistics.py
"""
StopPoint / Route / RouteStop mutations.

Model facts:
    - StopPoint inherits LocationModel (location fields provided by the
      base). Coordinates are set through the location API, not as plain
      model columns.
    - Route.trip FK → ServiceRequest.
    - RouteStop joins Route → StopPoint and carries ordering, distances,
      and arrival/departure timestamps.
    - Route.get_total_distance() / get_total_duration() fill in
      calculated values when the stored columns are empty.
    - Route.optimize() reorders RouteStop rows and updates distance /
      duration using RouteOptimizer.

Ownership:
    - Route belongs to a ServiceRequest — the caller must be the
      customer, the assigned provider, or staff.
    - StopPoints are shared infrastructure: staff-only writes.
"""

from typing import Optional

import graphene
from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.logistics import (
    StopPointNode,
    RouteNode,
    RouteStopNode,
)
from graphq.transport.types.trip import TripNode

from transport.models.delivery.logistics import StopPoint, Route, RouteStop
from transport.models.core.service_request import ServiceRequest


User = get_user_model()

_VALID_STOP_TYPES = {
    "delivery",
    "pickup",
    "transit",
    "warehouse",
    "fuel",
    "rest",
}
_VALID_OPT_PROVIDERS = {"haversine", "google", "osrm", "manual"}


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _assert_trip_participant(trip, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if trip.customer_id == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and trip.provider_id == provider.pk:
        return
    raise GraphQLError("Not authorized for this trip.")


def _resolve_stop(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid stop_point_id.")
    qs = StopPoint.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except StopPoint.DoesNotExist:
        raise GraphQLError("Stop point not found.")


def _resolve_route(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid route_id.")
    qs = Route.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Route.DoesNotExist:
        raise GraphQLError("Route not found.")


def _resolve_route_stop(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid route_stop_id.")
    qs = RouteStop.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except RouteStop.DoesNotExist:
        raise GraphQLError("Route stop not found.")


def _resolve_trip(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid trip_id.")
    try:
        return ServiceRequest.objects.get(pk=pk)
    except ServiceRequest.DoesNotExist:
        raise GraphQLError("Service request not found.")


def _apply_location(instance, latitude, longitude, source="manual"):
    """
    Set location on a LocationModel subclass without depending on the
    exact API surface. Tries `update_location()` first, falls back to
    writing a `location_point` Point.
    """
    if latitude is None or longitude is None:
        return False

    if not (-90 <= latitude <= 90):
        raise GraphQLError("Latitude must be between -90 and 90.")
    if not (-180 <= longitude <= 180):
        raise GraphQLError("Longitude must be between -180 and 180.")

    if hasattr(instance, "update_location"):
        try:
            instance.update_location(
                latitude=latitude,
                longitude=longitude,
                source=source,
                save=False,
            )
            return True
        except TypeError:
            # Signature mismatch; fall through.
            pass

    if hasattr(instance, "location_point"):
        instance.location_point = Point(longitude, latitude, srid=4326)
        return True

    if hasattr(instance, "latitude") and hasattr(instance, "longitude"):
        instance.latitude = latitude
        instance.longitude = longitude
        return True

    raise GraphQLError(
        "LocationModel for this instance does not expose a known location API."
    )


def _validate_stop_type(value):
    if value is None:
        return
    if value not in _VALID_STOP_TYPES:
        raise GraphQLError(
            f"stop_type must be one of: {', '.join(sorted(_VALID_STOP_TYPES))}."
        )


# =============================================================================
# StopPoint
# =============================================================================

class CreateStopPoint(relay.ClientIDMutation):
    """Create a StopPoint. Staff-only — shared infrastructure."""

    class Input:
        name = graphene.String(required=True)
        stop_type = graphene.String()
        latitude = graphene.Float(required=True)
        longitude = graphene.Float(required=True)

        contact_name = graphene.String()
        contact_phone = graphene.String()
        notes = graphene.String()
        is_active = graphene.Boolean()

    stop_point = graphene.Field(StopPointNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        _assert_staff(info.context.user)

        _validate_stop_type(input.get("stop_type"))

        stop = StopPoint(
            name=input["name"],
            stop_type=input.get("stop_type") or "delivery",
            contact_name=input.get("contact_name") or "",
            contact_phone=input.get("contact_phone") or "",
            notes=input.get("notes") or "",
            is_active=(
                input["is_active"] if input.get("is_active") is not None else True
            ),
        )
        _apply_location(stop, input["latitude"], input["longitude"])

        try:
            stop.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        stop.save()

        return cls(
            stop_point=stop,
            success=True,
            message="Stop point created.",
        )


class UpdateStopPoint(relay.ClientIDMutation):
    """Update a StopPoint. Staff-only."""

    class Input:
        stop_point_id = graphene.ID(required=True)

        name = graphene.String()
        stop_type = graphene.String()
        latitude = graphene.Float()
        longitude = graphene.Float()

        contact_name = graphene.String()
        contact_phone = graphene.String()
        notes = graphene.String()
        is_active = graphene.Boolean()

    stop_point = graphene.Field(StopPointNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, stop_point_id, **input):
        _assert_staff(info.context.user)
        stop = _resolve_stop(stop_point_id, lock=True)

        if (
            "stop_type" in input
            and input["stop_type"] is not None
        ):
            _validate_stop_type(input["stop_type"])

        update_fields = []
        for field in (
            "name",
            "stop_type",
            "contact_name",
            "contact_phone",
            "notes",
            "is_active",
        ):
            if field in input and input[field] is not None:
                setattr(stop, field, input[field])
                update_fields.append(field)

        location_touched = False
        if input.get("latitude") is not None or input.get("longitude") is not None:
            if input.get("latitude") is None or input.get("longitude") is None:
                raise GraphQLError(
                    "Provide both latitude and longitude, or neither."
                )
            _apply_location(stop, input["latitude"], input["longitude"])
            location_touched = True

        if not update_fields and not location_touched:
            return cls(
                stop_point=stop,
                success=True,
                message="Nothing to update.",
            )

        try:
            stop.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        if update_fields:
            stop.save(update_fields=sorted(set(update_fields + ["updated_at"])))
        else:
            stop.save()

        return cls(
            stop_point=stop,
            success=True,
            message="Stop point updated.",
        )


class DeleteStopPoint(relay.ClientIDMutation):
    """
    Delete a StopPoint. Staff-only.

    Refuses if the stop is referenced by any RouteStop — reordering or
    removing those first avoids a silent route disruption.
    """

    class Input:
        stop_point_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, stop_point_id):
        _assert_staff(info.context.user)
        stop = _resolve_stop(stop_point_id, lock=True)

        if RouteStop.objects.filter(stop=stop).exists():
            raise GraphQLError(
                "Cannot delete a stop point that is referenced by a route. "
                "Remove it from routes first."
            )

        stop.delete()
        return cls(success=True, message="Stop point deleted.")


# =============================================================================
# Route
# =============================================================================

class CreateRoute(relay.ClientIDMutation):
    """
    Create a Route for a ServiceRequest (Trip).

    Caller must be a participant in the trip. Optionally seeds the
    route with an ordered list of stop ids.
    """

    class Input:
        trip_id = graphene.ID(required=True)

        waypoints = graphene.JSONString()
        traffic_delay_minutes = graphene.Float()
        road_conditions = graphene.JSONString()
        metadata = graphene.JSONString()

        stop_ids = graphene.List(graphene.ID)

    route = graphene.Field(RouteNode)
    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_id, **input):
        me = info.context.user
        trip = _resolve_trip(trip_id)
        _assert_trip_participant(trip, me)

        payload = {
            "trip": trip,
            "waypoints": input.get("waypoints") or [],
            "traffic_delay_minutes": input.get("traffic_delay_minutes") or 0,
            "road_conditions": input.get("road_conditions") or {},
            "metadata": input.get("metadata") or {},
        }

        try:
            route = Route.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Optional seeding of stops.
        stop_ids = input.get("stop_ids") or []
        if stop_ids:
            created = []
            for idx, sid in enumerate(stop_ids):
                stop = _resolve_stop(sid)
                try:
                    rs = RouteStop.objects.create(
                        route=route, stop=stop, order=idx
                    )
                    created.append(rs)
                except IntegrityError:
                    raise GraphQLError(
                        f"Stop {stop.name} is already on this route."
                    )

            # Fill in computed distances/durations from the stops.
            route.distance_km = route.get_total_distance()
            route.duration_minutes = route.get_total_duration()
            route.save(update_fields=["distance_km", "duration_minutes", "updated_at"])

        return cls(
            route=route,
            trip=trip,
            success=True,
            message="Route created.",
        )


class UpdateRoute(relay.ClientIDMutation):
    """Update mutable Route fields. Trip participant or staff."""

    class Input:
        route_id = graphene.ID(required=True)

        waypoints = graphene.JSONString()
        traffic_delay_minutes = graphene.Float()
        road_conditions = graphene.JSONString()
        metadata = graphene.JSONString()

        distance_km = graphene.Float()
        duration_minutes = graphene.Float()

    route = graphene.Field(RouteNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_id, **input):
        me = info.context.user
        route = _resolve_route(route_id, lock=True)
        _assert_trip_participant(route.trip, me)

        update_fields = []

        # JSON blobs merge.
        for input_key, model_field in (
            ("road_conditions", "road_conditions"),
            ("metadata", "metadata"),
        ):
            if input_key in input and input[input_key] is not None:
                if not isinstance(input[input_key], dict):
                    raise GraphQLError(f"{input_key} must be an object.")
                merged = {**(getattr(route, model_field) or {}), **input[input_key]}
                setattr(route, model_field, merged)
                update_fields.append(model_field)

        if "waypoints" in input and input["waypoints"] is not None:
            if not isinstance(input["waypoints"], list):
                raise GraphQLError("waypoints must be a list.")
            route.waypoints = input["waypoints"]
            update_fields.append("waypoints")

        for input_key, model_field in (
            ("traffic_delay_minutes", "traffic_delay_minutes"),
            ("distance_km", "distance_km"),
            ("duration_minutes", "duration_minutes"),
        ):
            if input_key in input and input[input_key] is not None:
                if input[input_key] < 0:
                    raise GraphQLError(f"{input_key} cannot be negative.")
                setattr(route, model_field, input[input_key])
                update_fields.append(model_field)

        if not update_fields:
            return cls(route=route, success=True, message="Nothing to update.")

        try:
            route.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        route.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(route=route, success=True, message="Route updated.")


class OptimizeRoute(relay.ClientIDMutation):
    """
    Run `Route.optimize()` — reorders stops and updates distance/duration.

    Trip participant or staff.
    """

    class Input:
        route_id = graphene.ID(required=True)
        use_google = graphene.Boolean(default_value=False)

    route = graphene.Field(RouteNode)
    optimization_result = graphene.JSONString()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_id, use_google=False):
        me = info.context.user
        route = _resolve_route(route_id, lock=True)
        _assert_trip_participant(route.trip, me)

        try:
            result = route.optimize(use_google=use_google)
        except Exception as exc:
            raise GraphQLError(f"Optimization failed: {exc}")

        if result.get("error"):
            raise GraphQLError(result["error"])

        route.refresh_from_db()

        return cls(
            route=route,
            optimization_result=result,
            success=True,
            message="Route optimized.",
        )


class DeleteRoute(relay.ClientIDMutation):
    """Delete a Route. Trip participant or staff. Cascades RouteStops."""

    class Input:
        route_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_id):
        me = info.context.user
        route = _resolve_route(route_id, lock=True)
        _assert_trip_participant(route.trip, me)

        route.delete()
        return cls(success=True, message="Route deleted.")


# =============================================================================
# RouteStop
# =============================================================================

class AddRouteStop(relay.ClientIDMutation):
    """Add a StopPoint to a Route. Trip participant or staff."""

    class Input:
        route_id = graphene.ID(required=True)
        stop_point_id = graphene.ID(required=True)
        order = graphene.Int()
        notes = graphene.String()

    route_stop = graphene.Field(RouteStopNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, route_id, stop_point_id, order=None, notes=None
    ):
        me = info.context.user
        route = _resolve_route(route_id, lock=True)
        _assert_trip_participant(route.trip, me)

        stop = _resolve_stop(stop_point_id)

        if RouteStop.objects.filter(route=route, stop=stop).exists():
            raise GraphQLError("This stop is already on the route.")

        if order is None:
            last = RouteStop.objects.filter(route=route).order_by("-order").first()
            order = (last.order + 1) if last else 0
        if order < 0:
            raise GraphQLError("order cannot be negative.")

        try:
            route_stop = RouteStop.objects.create(
                route=route, stop=stop, order=order, notes=notes or ""
            )
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        # Refresh derived metrics.
        route.distance_km = route.get_total_distance()
        route.duration_minutes = route.get_total_duration()
        route.save(update_fields=["distance_km", "duration_minutes", "updated_at"])

        return cls(
            route_stop=route_stop,
            success=True,
            message="Stop added to route.",
        )


class UpdateRouteStop(relay.ClientIDMutation):
    """
    Update a RouteStop's ordering / notes / arrival-departure timestamps.

    Reordering is done by setting `order`; if it conflicts with another
    stop's order, callers should reorder the whole route via
    `ReorderRouteStops` instead.
    """

    class Input:
        route_stop_id = graphene.ID(required=True)
        order = graphene.Int()
        notes = graphene.String()
        actual_arrival_time = graphene.DateTime()
        actual_departure_time = graphene.DateTime()

    route_stop = graphene.Field(RouteStopNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_stop_id, **input):
        me = info.context.user
        route_stop = _resolve_route_stop(route_stop_id, lock=True)
        _assert_trip_participant(route_stop.route.trip, me)

        update_fields = []

        for field in (
            "notes",
            "actual_arrival_time",
            "actual_departure_time",
        ):
            if field in input and input[field] is not None:
                setattr(route_stop, field, input[field])
                update_fields.append(field)

        if "order" in input and input["order"] is not None:
            if input["order"] < 0:
                raise GraphQLError("order cannot be negative.")
            route_stop.order = input["order"]
            update_fields.append("order")

        if not update_fields:
            return cls(
                route_stop=route_stop,
                success=True,
                message="Nothing to update.",
            )

        try:
            route_stop.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        route_stop.save(update_fields=update_fields)
        return cls(
            route_stop=route_stop,
            success=True,
            message="Route stop updated.",
        )


class ReorderRouteStops(relay.ClientIDMutation):
    """
    Replace the ordering of a route's stops in one call.

    `ordered_route_stop_ids` must list every existing RouteStop on the
    route exactly once. This avoids transient unique-order conflicts
    that a series of single reorder calls would create.
    """

    class Input:
        route_id = graphene.ID(required=True)
        ordered_route_stop_ids = graphene.List(graphene.ID, required=True)

    route = graphene.Field(RouteNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_id, ordered_route_stop_ids):
        me = info.context.user
        route = _resolve_route(route_id, lock=True)
        _assert_trip_participant(route.trip, me)

        existing_ids = set(
            str(pk)
            for pk in RouteStop.objects.filter(route=route).values_list(
                "pk", flat=True
            )
        )

        provided = []
        for gid in ordered_route_stop_ids:
            try:
                _, pk = from_global_id(gid)
            except Exception:
                raise GraphQLError(f"Invalid route_stop_id: {gid}")
            provided.append(str(pk))

        if set(provided) != existing_ids:
            raise GraphQLError(
                "ordered_route_stop_ids must list each stop on this route exactly once."
            )

        # Two-step: park at a high range, then assign the real order.
        RouteStop.objects.filter(route=route).update(
            order=100000 + models_F("order")
        )
        for idx, pk in enumerate(provided):
            RouteStop.objects.filter(pk=pk).update(order=idx)

        route.distance_km = route.get_total_distance()
        route.duration_minutes = route.get_total_duration()
        route.save(update_fields=["distance_km", "duration_minutes", "updated_at"])

        return cls(
            route=route,
            success=True,
            message="Route stops reordered.",
        )


def models_F(field):
    from django.db.models import F
    return F(field)


class RemoveRouteStop(relay.ClientIDMutation):
    """Remove a stop from a route. Trip participant or staff."""

    class Input:
        route_stop_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, route_stop_id):
        me = info.context.user
        route_stop = _resolve_route_stop(route_stop_id, lock=True)
        route = route_stop.route
        _assert_trip_participant(route.trip, me)

        route_stop.delete()

        route.distance_km = route.get_total_distance()
        route.duration_minutes = route.get_total_duration()
        route.save(update_fields=["distance_km", "duration_minutes", "updated_at"])

        return cls(success=True, message="Stop removed from route.")


# =============================================================================
# Registration
# =============================================================================

class LogisticsMutations(graphene.ObjectType):
    create_stop_point = CreateStopPoint.Field()
    update_stop_point = UpdateStopPoint.Field()
    delete_stop_point = DeleteStopPoint.Field()

    create_route = CreateRoute.Field()
    update_route = UpdateRoute.Field()
    optimize_route = OptimizeRoute.Field()
    delete_route = DeleteRoute.Field()

    add_route_stop = AddRouteStop.Field()
    update_route_stop = UpdateRouteStop.Field()
    reorder_route_stops = ReorderRouteStops.Field()
    remove_route_stop = RemoveRouteStop.Field()