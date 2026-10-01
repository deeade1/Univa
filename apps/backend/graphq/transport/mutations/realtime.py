# apps/backend/graphq/transport/mutations/realtime.py
"""
RealTimeTracking / TrafficConditions / EmergencyAlert mutations.

Model facts that shape these mutations:
    - All three inherit LocationModel. Coordinates are set through
      `update_location()`, not by assigning `location_point` directly.
    - Auto-managed timestamps (`timestamp` on RTT, `recorded_at` on
      TrafficConditions, `created_at`/`updated_at` on EmergencyAlert)
      are not client-settable.
    - Enum-valued fields (traffic_level, alert_type, severity, status,
      platform, source) are TextChoices, not ints.
    - EmergencyAlert.acknowledged_by is M2M to ServiceProviderProfile,
      not User.
    - EmergencyAlert uses `status`, not `is_active`.

Ownership / staff rules:
    - RTT: vehicle owner, assigned provider, or staff.
    - TrafficConditions: any authenticated user (user reports) or staff.
    - EmergencyAlert create: any authenticated user (reporters).
    - Acknowledge: provider profile owners or staff.
    - Resolve / cancel / delete: reporter, assigned provider, or staff.
"""

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.realtime import (
    RealTimeTrackingNode,
    TrafficConditionsNode,
    EmergencyAlertNode
)
from graphq.transport.types.vehicle import VehicleNode
from graphq.transport.types.service_request import ServiceRequestNode
from graphq.transport.types.service_provider import   ServiceProviderProfileNode

from graphq.accounts.types.user import UserNode

from transport.models.shared.realtime import (
    RealTimeTracking,
    TrafficConditions,
    EmergencyAlert,
)
from transport.models.maintenance.vehicle import Vehicle
from transport.models.core.service_request import ServiceRequest
from transport.models.core.service_provider import ServiceProviderProfile


# =============================================================================
# Constants (from the model TextChoices)
# =============================================================================

_RTT_PLATFORMS = {c.value for c in RealTimeTracking.Platform}

_TRAFFIC_LEVELS = {c.value for c in TrafficConditions.TrafficLevel}
_TRAFFIC_SOURCES = {c.value for c in TrafficConditions.Source}

_ALERT_TYPES = {c.value for c in EmergencyAlert.AlertType}
_ALERT_SEVERITIES = {c.value for c in EmergencyAlert.Severity}
_ALERT_STATUSES = {c.value for c in EmergencyAlert.AlertStatus}

_TERMINAL_ALERT_STATUSES = {
    EmergencyAlert.AlertStatus.RESOLVED,
    EmergencyAlert.AlertStatus.CANCELLED,
}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_vehicle(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid vehicle_id.")
    try:
        return Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        raise GraphQLError("Vehicle not found.")


def _resolve_service_request(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid service_request_id.")
    try:
        return ServiceRequest.objects.get(pk=pk)
    except ServiceRequest.DoesNotExist:
        raise GraphQLError("Service request not found.")


def _resolve_provider(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid provider_id.")
    try:
        return ServiceProviderProfile.objects.get(pk=pk)
    except ServiceProviderProfile.DoesNotExist:
        raise GraphQLError("Service provider not found.")


def _resolve_rtt(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid realtime_tracking_id.")
    qs = RealTimeTracking.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except RealTimeTracking.DoesNotExist:
        raise GraphQLError("Real-time tracking record not found.")


def _resolve_traffic(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid traffic_conditions_id.")
    qs = TrafficConditions.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except TrafficConditions.DoesNotExist:
        raise GraphQLError("Traffic conditions record not found.")


def _resolve_alert(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid emergency_alert_id.")
    qs = EmergencyAlert.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except EmergencyAlert.DoesNotExist:
        raise GraphQLError("Emergency alert not found.")


def _validate_enum(value, allowed, field):
    if value is None:
        return
    if value not in allowed:
        raise GraphQLError(
            f"{field} must be one of: {', '.join(sorted(allowed))}."
        )


def _set_location(instance, lat, lng, *, source, address=None):
    """
    Set coordinates on a LocationModel subclass. Prefers `update_location`
    with save=False so the caller controls the final save.
    """
    if lat is None or lng is None:
        return False

    if not (-90 <= lat <= 90):
        raise GraphQLError("Latitude must be between -90 and 90.")
    if not (-180 <= lng <= 180):
        raise GraphQLError("Longitude must be between -180 and 180.")

    if address is not None and hasattr(instance, "location"):
        instance.location = address

    try:
        instance.update_location(latitude=lat, longitude=lng, source=source)
        return True
    except TypeError:
        pass

    if hasattr(instance, "location_point"):
        instance.location_point = Point(lng, lat, srid=4326)
        return True

    if hasattr(instance, "latitude") and hasattr(instance, "longitude"):
        instance.latitude = lat
        instance.longitude = lng
        return True

    raise GraphQLError("LocationModel does not expose a known location API.")


def _assert_vehicle_operator(vehicle, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if getattr(vehicle, "owner_id", None) == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and getattr(vehicle, "provider_id", None) == provider.pk:
        return
    raise GraphQLError("Not authorized for this vehicle.")


# =============================================================================
# RealTimeTracking
# =============================================================================

class CreateRealTimeTracking(relay.ClientIDMutation):
    """Push a real-time tracking ping for a vehicle."""

    class Input:
        vehicle_id = graphene.ID(required=True)
        service_request_id = graphene.ID()

        lat = graphene.Float(required=True)
        lng = graphene.Float(required=True)

        speed = graphene.Float()
        heading = graphene.Float()
        is_moving = graphene.Boolean()

        accuracy = graphene.Float()
        altitude = graphene.Float()
        battery_level = graphene.Int()

        device_id = graphene.String()
        app_version = graphene.String()
        platform = graphene.String()

        metadata = graphene.JSONString()

    vehicle = graphene.Field(VehicleNode)
    service_request = graphene.Field(ServiceRequestNode)
    realtime_tracking = graphene.Field(RealTimeTrackingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, lat, lng, **input):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id)
        _assert_vehicle_operator(vehicle, me)

        _validate_enum(input.get("platform"), _RTT_PLATFORMS, "platform")

        if input.get("speed") is not None and not 0 <= input["speed"] <= 300:
            raise GraphQLError("speed must be between 0 and 300 km/h.")
        if input.get("heading") is not None and not 0 <= input["heading"] <= 360:
            raise GraphQLError("heading must be between 0 and 360 degrees.")
        if input.get("battery_level") is not None and not 0 <= input["battery_level"] <= 100:
            raise GraphQLError("battery_level must be between 0 and 100.")

        sr = None
        if input.get("service_request_id"):
            sr = _resolve_service_request(input["service_request_id"])
            if sr.provider_id and vehicle.provider_id and sr.provider_id != vehicle.provider_id:
                raise GraphQLError("Vehicle is not assigned to this service request.")

        ping = RealTimeTracking(
            vehicle=vehicle,
            service_request=sr,
            speed=input.get("speed") or 0,
            heading=input.get("heading") or 0,
            is_moving=bool(input.get("is_moving")),
            accuracy=input.get("accuracy"),
            altitude=input.get("altitude"),
            battery_level=input.get("battery_level"),
            device_id=input.get("device_id") or "",
            app_version=input.get("app_version") or "",
            platform=input.get("platform") or RealTimeTracking.Platform.ANDROID,
            metadata=input.get("metadata") or {},
        )

        _set_location(ping, lat, lng, source="realtime_tracking")

        try:
            ping.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        ping.save()

        return cls(
            vehicle=vehicle,
            service_request=sr,
            realtime_tracking=ping,
            success=True,
            message="Tracking ping recorded.",
        )


class DeleteRealTimeTracking(relay.ClientIDMutation):
    """Delete a tracking ping. Staff-only — audit cleanup."""

    class Input:
        realtime_tracking_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, realtime_tracking_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete tracking records.")

        ping = _resolve_rtt(realtime_tracking_id, lock=True)
        ping.delete()
        return cls(success=True, message="Tracking record deleted.")


# =============================================================================
# TrafficConditions
# =============================================================================

class CreateTrafficConditions(relay.ClientIDMutation):
    """
    Report traffic conditions for a location.

    Any authenticated user may report (crowd-sourced data); staff may
    also enter system-generated data. The record must have a
    `valid_until` — it's how downstream consumers decide whether to
    trust the row.
    """

    class Input:
        lat = graphene.Float(required=True)
        lng = graphene.Float(required=True)
        address = graphene.String()

        road_name = graphene.String()
        traffic_level = graphene.String(required=True)
        average_speed = graphene.Float(required=True)
        delay_minutes = graphene.Float()

        source = graphene.String()
        confidence = graphene.Float()

        valid_until = graphene.DateTime(required=True)
        metadata = graphene.JSONString()

    traffic_conditions = graphene.Field(TrafficConditionsNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, lat, lng, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_enum(input["traffic_level"], _TRAFFIC_LEVELS, "traffic_level")
        _validate_enum(input.get("source"), _TRAFFIC_SOURCES, "source")

        if not 0 <= input["average_speed"] <= 150:
            raise GraphQLError("average_speed must be between 0 and 150 km/h.")

        if input.get("delay_minutes") is not None and input["delay_minutes"] < 0:
            raise GraphQLError("delay_minutes cannot be negative.")

        if input.get("confidence") is not None and not 0 <= input["confidence"] <= 1:
            raise GraphQLError("confidence must be between 0 and 1.")

        if input["valid_until"] <= timezone.now():
            raise GraphQLError("valid_until must be in the future.")

        record = TrafficConditions(
            road_name=input.get("road_name") or "",
            traffic_level=input["traffic_level"],
            average_speed=input["average_speed"],
            delay_minutes=input.get("delay_minutes") or 0,
            source=input.get("source") or TrafficConditions.Source.GPS,
            confidence=(
                input["confidence"]
                if input.get("confidence") is not None
                else 0.8
            ),
            valid_until=input["valid_until"],
            metadata=input.get("metadata") or {},
        )
        _set_location(
            record, lat, lng, source="traffic_data", address=input.get("address")
        )

        try:
            record.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        record.save()

        return cls(
            traffic_conditions=record,
            success=True,
            message="Traffic conditions recorded.",
        )


class UpdateTrafficConditions(relay.ClientIDMutation):
    """
    Update a TrafficConditions record.

    Reporter (matches by `metadata.reported_by_id` if set), assigned
    provider on the linked service request, or staff.
    """

    class Input:
        traffic_conditions_id = graphene.ID(required=True)

        lat = graphene.Float()
        lng = graphene.Float()
        address = graphene.String()

        road_name = graphene.String()
        traffic_level = graphene.String()
        average_speed = graphene.Float()
        delay_minutes = graphene.Float()

        source = graphene.String()
        confidence = graphene.Float()
        valid_until = graphene.DateTime()
        metadata = graphene.JSONString()

    traffic_conditions = graphene.Field(TrafficConditionsNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, traffic_conditions_id, **input):
        me = info.context.user
        record = _resolve_traffic(traffic_conditions_id, lock=True)

        # No owner FK on the model. Restrict to staff for safety; if you
        # want reporters to edit their own rows, store reporter_id in
        # metadata and check it here.
        if not me.is_staff:
            raise GraphQLError(
                "Only staff may update traffic conditions records."
            )

        _validate_enum(input.get("traffic_level"), _TRAFFIC_LEVELS, "traffic_level")
        _validate_enum(input.get("source"), _TRAFFIC_SOURCES, "source")

        update_fields = []

        if input.get("average_speed") is not None:
            if not 0 <= input["average_speed"] <= 150:
                raise GraphQLError("average_speed must be between 0 and 150.")
            record.average_speed = input["average_speed"]
            update_fields.append("average_speed")

        for field in ("road_name", "traffic_level", "source", "valid_until"):
            if field in input and input[field] is not None:
                setattr(record, field, input[field])
                update_fields.append(field)

        if input.get("delay_minutes") is not None:
            if input["delay_minutes"] < 0:
                raise GraphQLError("delay_minutes cannot be negative.")
            record.delay_minutes = input["delay_minutes"]
            update_fields.append("delay_minutes")

        if input.get("confidence") is not None:
            if not 0 <= input["confidence"] <= 1:
                raise GraphQLError("confidence must be between 0 and 1.")
            record.confidence = input["confidence"]
            update_fields.append("confidence")

        if input.get("metadata") is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            record.metadata = {**(record.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if input.get("lat") is not None or input.get("lng") is not None:
            if input.get("lat") is None or input.get("lng") is None:
                raise GraphQLError("Provide both lat and lng, or neither.")
            _set_location(
                record,
                input["lat"],
                input["lng"],
                source="traffic_data",
                address=input.get("address"),
            )

        if not update_fields:
            return cls(
                traffic_conditions=record,
                success=True,
                message="Nothing to update.",
            )

        try:
            record.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        record.save(update_fields=update_fields)

        return cls(
            traffic_conditions=record,
            success=True,
            message="Traffic conditions updated.",
        )


class DeleteTrafficConditions(relay.ClientIDMutation):
    """Delete a TrafficConditions record. Staff-only."""

    class Input:
        traffic_conditions_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, traffic_conditions_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete traffic records.")

        record = _resolve_traffic(traffic_conditions_id, lock=True)
        record.delete()
        return cls(success=True, message="Traffic conditions deleted.")


# =============================================================================
# EmergencyAlert
# =============================================================================

class CreateEmergencyAlert(relay.ClientIDMutation):
    """
    Report an emergency alert.

    Any authenticated user may create. `reported_by` defaults to the
    caller. New alerts always start in `status=ACTIVE`.
    """

    class Input:
        alert_type = graphene.String(required=True)
        severity = graphene.String()
        title = graphene.String(required=True)
        description = graphene.String(required=True)

        lat = graphene.Float(required=True)
        lng = graphene.Float(required=True)
        location_description = graphene.String()

        service_request_id = graphene.ID()
        reported_by_id = graphene.ID()   # staff-only override
        metadata = graphene.JSONString()

    emergency_alert = graphene.Field(EmergencyAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, lat, lng, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_enum(input["alert_type"], _ALERT_TYPES, "alert_type")
        _validate_enum(input.get("severity"), _ALERT_SEVERITIES, "severity")

        reported_by = me
        if input.get("reported_by_id"):
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may set a different reported_by."
                )
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                _, pk = from_global_id(input["reported_by_id"])
                reported_by = User.objects.get(pk=pk)
            except Exception:
                raise GraphQLError("Invalid reported_by_id.")

        sr = None
        if input.get("service_request_id"):
            sr = _resolve_service_request(input["service_request_id"])

        alert = EmergencyAlert(
            alert_type=input["alert_type"],
            severity=input.get("severity") or EmergencyAlert.Severity.MEDIUM,
            status=EmergencyAlert.AlertStatus.ACTIVE,
            title=input["title"],
            description=input["description"],
            location_description=input.get("location_description") or "",
            service_request=sr,
            reported_by=reported_by,
            metadata=input.get("metadata") or {},
        )
        _set_location(alert, lat, lng, source="emergency_alert")

        try:
            alert.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        alert.save()

        return cls(
            emergency_alert=alert,
            success=True,
            message="Emergency alert created.",
        )


class UpdateEmergencyAlert(relay.ClientIDMutation):
    """
    Update the metadata of an active alert.

    Reporter or staff. Terminal alerts (RESOLVED / CANCELLED) are
    frozen to non-staff.
    """

    class Input:
        emergency_alert_id = graphene.ID(required=True)

        alert_type = graphene.String()
        severity = graphene.String()
        title = graphene.String()
        description = graphene.String()
        location_description = graphene.String()

        lat = graphene.Float()
        lng = graphene.Float()

        metadata = graphene.JSONString()

    emergency_alert = graphene.Field(EmergencyAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, emergency_alert_id, **input):
        me = info.context.user
        alert = _resolve_alert(emergency_alert_id, lock=True)

        if not me.is_staff:
            if alert.reported_by_id != me.pk:
                raise GraphQLError("Not authorized to edit this alert.")
            if alert.status in _TERMINAL_ALERT_STATUSES:
                raise GraphQLError(
                    f"Cannot edit an alert in status '{alert.status}'."
                )

        _validate_enum(input.get("alert_type"), _ALERT_TYPES, "alert_type")
        _validate_enum(input.get("severity"), _ALERT_SEVERITIES, "severity")

        update_fields = []
        for field in (
            "alert_type",
            "severity",
            "title",
            "description",
            "location_description",
        ):
            if field in input and input[field] is not None:
                setattr(alert, field, input[field])
                update_fields.append(field)

        if input.get("metadata") is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            alert.metadata = {**(alert.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if input.get("lat") is not None or input.get("lng") is not None:
            if input.get("lat") is None or input.get("lng") is None:
                raise GraphQLError("Provide both lat and lng, or neither.")
            _set_location(alert, input["lat"], input["lng"], source="emergency_alert")

        if not update_fields:
            return cls(
                emergency_alert=alert,
                success=True,
                message="Nothing to update.",
            )

        try:
            alert.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        alert.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            emergency_alert=alert,
            success=True,
            message="Emergency alert updated.",
        )


class AcknowledgeEmergencyAlert(relay.ClientIDMutation):
    """
    Acknowledge an active alert.

    Caller must own a ServiceProviderProfile (or be staff, in which
    case `provider_id` must be supplied). Uses the model's
    `acknowledge()` helper so the status transition and timestamp are
    consistent.
    """

    class Input:
        emergency_alert_id = graphene.ID(required=True)
        provider_id = graphene.ID()   # staff-only override

    emergency_alert = graphene.Field(EmergencyAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, emergency_alert_id, provider_id=None):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        alert = _resolve_alert(emergency_alert_id, lock=True)

        if alert.status != EmergencyAlert.AlertStatus.ACTIVE:
            raise GraphQLError("Only active alerts can be acknowledged.")

        if provider_id:
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may acknowledge on behalf of another provider."
                )
            provider = _resolve_provider(provider_id)
        else:
            provider = getattr(me, "service_provider", None)
            if provider is None:
                raise GraphQLError(
                    "You must have a service provider profile to acknowledge."
                )

        try:
            alert.acknowledge(provider)
        except (ValidationError, ValueError) as exc:
            raise GraphQLError(str(exc))

        return cls(
            emergency_alert=alert,
            success=True,
            message="Alert acknowledged.",
        )


class ResolveEmergencyAlert(relay.ClientIDMutation):
    """Mark an alert as resolved. Reporter, assigned provider, or staff."""

    class Input:
        emergency_alert_id = graphene.ID(required=True)

    emergency_alert = graphene.Field(EmergencyAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, emergency_alert_id):
        me = info.context.user
        alert = _resolve_alert(emergency_alert_id, lock=True)

        if not me.is_staff:
            is_reporter = alert.reported_by_id == me.pk
            provider = getattr(me, "service_provider", None)
            is_assigned_provider = (
                provider is not None
                and alert.service_request_id
                and alert.service_request.provider_id == provider.pk
            )
            if not (is_reporter or is_assigned_provider):
                raise GraphQLError("Not authorized to resolve this alert.")

        if alert.status == EmergencyAlert.AlertStatus.RESOLVED:
            return cls(
                emergency_alert=alert,
                success=True,
                message="Alert is already resolved.",
            )

        alert.resolve()
        return cls(
            emergency_alert=alert,
            success=True,
            message="Alert resolved.",
        )


class CancelEmergencyAlert(relay.ClientIDMutation):
    """Cancel an alert. Reporter or staff."""

    class Input:
        emergency_alert_id = graphene.ID(required=True)
        reason = graphene.String()

    emergency_alert = graphene.Field(EmergencyAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, emergency_alert_id, reason=None):
        me = info.context.user
        alert = _resolve_alert(emergency_alert_id, lock=True)

        if not me.is_staff and alert.reported_by_id != me.pk:
            raise GraphQLError("Not authorized to cancel this alert.")

        if alert.status == EmergencyAlert.AlertStatus.CANCELLED:
            return cls(
                emergency_alert=alert,
                success=True,
                message="Alert is already cancelled.",
            )
        if alert.status == EmergencyAlert.AlertStatus.RESOLVED:
            raise GraphQLError("Cannot cancel a resolved alert.")

        if reason:
            metadata = dict(alert.metadata or {})
            metadata["cancellation_reason"] = reason
            metadata["cancelled_at"] = timezone.now().isoformat()
            alert.metadata = metadata
            alert.cancel()
            alert.save(update_fields=["metadata"])
        else:
            alert.cancel()

        return cls(
            emergency_alert=alert,
            success=True,
            message="Alert cancelled.",
        )


class DeleteEmergencyAlert(relay.ClientIDMutation):
    """
    Delete an alert. Staff-only.

    Alerts are audit records. Cancel or resolve instead of deleting.
    """

    class Input:
        emergency_alert_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, emergency_alert_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete emergency alerts.")

        alert = _resolve_alert(emergency_alert_id, lock=True)
        alert.delete()
        return cls(success=True, message="Emergency alert deleted.")


# =============================================================================
# Registration
# =============================================================================

class RealTimeTrackingMutations(graphene.ObjectType):
    create_realtime_tracking = CreateRealTimeTracking.Field()
    delete_realtime_tracking = DeleteRealTimeTracking.Field()

    create_traffic_conditions = CreateTrafficConditions.Field()
    update_traffic_conditions = UpdateTrafficConditions.Field()
    delete_traffic_conditions = DeleteTrafficConditions.Field()

    create_emergency_alert = CreateEmergencyAlert.Field()
    update_emergency_alert = UpdateEmergencyAlert.Field()
    acknowledge_emergency_alert = AcknowledgeEmergencyAlert.Field()
    resolve_emergency_alert = ResolveEmergencyAlert.Field()
    cancel_emergency_alert = CancelEmergencyAlert.Field()
    delete_emergency_alert = DeleteEmergencyAlert.Field()