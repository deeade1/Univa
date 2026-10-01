# apps/backend/graphq/transport/mutations/maintenance.py
"""
Mutations for VehicleTelemetry and PredictiveAlert.

Design rules enforced:
    - Telemetry may only be ingested for a vehicle the caller controls
      (owner, assigned provider, or staff).
    - PredictiveAlert is always created in the unresolved state; the
      resolved/unresolved transition is a separate, audited operation.
    - Enum-valued fields (alert_type, severity) are validated before
      reaching the DB so errors surface as GraphQLErrors, not IntegrityErrors.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.telemetry import (
    VehicleTelemetryNode,
    PredictiveAlertNode,
)
from graphq.transport.types.vehicle import VehicleNode
from transport.models.maintenance import (
    VehicleTelemetry as VehicleTelemetryModel,
    PredictiveAlert as PredictiveAlertModel,
)
from transport.models.maintenance.vehicle import Vehicle  # adjust path if needed


# =============================================================================
# Enums / bounds
# =============================================================================

_ALERT_TYPES = {
    "maintenance_due",
    "component_failure",
    "performance_degradation",
    "safety_concern",
}

_ALERT_SEVERITIES = {"low", "medium", "high", "critical"}

_PERCENT_FIELDS = ("oil_level", "fuel_level")


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


def _assert_can_write_telemetry(vehicle, user):
    """
    A user may push telemetry for a vehicle they own, are the assigned
    provider for, or (staff).
    """
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return

    if getattr(vehicle, "owner_id", None) == user.pk:
        return

    provider = getattr(user, "service_provider", None)
    if provider is not None and getattr(vehicle, "provider_id", None) == provider.pk:
        return

    raise GraphQLError(
        "Not authorized to write telemetry for this vehicle."
    )


def _validate_percent(value, field):
    if value is None:
        return
    if not 0 <= value <= 100:
        raise GraphQLError(f"{field} must be between 0 and 100.")


# =============================================================================
# VehicleTelemetry
# =============================================================================

class CreateVehicleTelemetry(relay.ClientIDMutation):
    """Ingest a telemetry reading for a vehicle."""

    class Input:
        vehicle_id = graphene.ID(required=True)

        engine_temperature = graphene.Float()
        oil_pressure = graphene.Float()
        oil_level = graphene.Float()
        battery_voltage = graphene.Float()

        tire_pressure_front_left = graphene.Float()
        tire_pressure_front_right = graphene.Float()
        tire_pressure_rear_left = graphene.Float()
        tire_pressure_rear_right = graphene.Float()
        tire_tread_depth = graphene.Float()

        fuel_level = graphene.Float()
        odometer_reading = graphene.Int(required=True)
        average_fuel_consumption = graphene.Float()

        diagnostic_trouble_codes = graphene.List(graphene.String)

    vehicle = graphene.Field(VehicleNode)
    vehicle_telemetry = graphene.Field(VehicleTelemetryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, **input):
        me = info.context.user

        vehicle = _resolve_vehicle(vehicle_id)
        _assert_can_write_telemetry(vehicle, me)

        # Bounds checks that mirror the model validators.
        _validate_percent(input.get("oil_level"), "oil_level")
        _validate_percent(input.get("fuel_level"), "fuel_level")

        odometer = input.get("odometer_reading")
        if odometer is None or odometer < 0:
            raise GraphQLError("odometer_reading must be a non-negative integer.")

        try:
            telemetry = VehicleTelemetryModel.objects.create(
                vehicle=vehicle,
                engine_temperature=input.get("engine_temperature"),
                oil_pressure=input.get("oil_pressure"),
                oil_level=input.get("oil_level"),
                battery_voltage=input.get("battery_voltage"),
                tire_pressure_front_left=input.get("tire_pressure_front_left"),
                tire_pressure_front_right=input.get("tire_pressure_front_right"),
                tire_pressure_rear_left=input.get("tire_pressure_rear_left"),
                tire_pressure_rear_right=input.get("tire_pressure_rear_right"),
                tire_tread_depth=input.get("tire_tread_depth"),
                fuel_level=input.get("fuel_level"),
                odometer_reading=odometer,
                average_fuel_consumption=input.get("average_fuel_consumption"),
                diagnostic_trouble_codes=input.get("diagnostic_trouble_codes") or [],
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            vehicle_telemetry=telemetry,
            success=True,
            message="Telemetry recorded.",
        )


class UpdateVehicleTelemetry(relay.ClientIDMutation):
    """
    Correct a previously recorded telemetry reading.

    Telemetry is normally append-only. This mutation exists for the
    legitimate case of fixing a corrupted reading (sensor glitch,
    bad ingest). It does not change `recorded_at` — the original
    timestamp is preserved.
    """

    class Input:
        telemetry_id = graphene.ID(required=True)

        engine_temperature = graphene.Float()
        oil_pressure = graphene.Float()
        oil_level = graphene.Float()
        battery_voltage = graphene.Float()

        tire_pressure_front_left = graphene.Float()
        tire_pressure_front_right = graphene.Float()
        tire_pressure_rear_left = graphene.Float()
        tire_pressure_rear_right = graphene.Float()
        tire_tread_depth = graphene.Float()

        fuel_level = graphene.Float()
        odometer_reading = graphene.Int()
        average_fuel_consumption = graphene.Float()

        diagnostic_trouble_codes = graphene.List(graphene.String)

    vehicle_telemetry = graphene.Field(VehicleTelemetryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, telemetry_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(telemetry_id)
        except Exception:
            raise GraphQLError("Invalid telemetry_id.")

        try:
            telemetry = VehicleTelemetryModel.objects.select_for_update().get(pk=pk)
        except VehicleTelemetryModel.DoesNotExist:
            raise GraphQLError("Telemetry record not found.")

        _assert_can_write_telemetry(telemetry.vehicle, me)

        _validate_percent(input.get("oil_level"), "oil_level")
        _validate_percent(input.get("fuel_level"), "fuel_level")

        scalar_map = {
            "engine_temperature": "engine_temperature",
            "oil_pressure": "oil_pressure",
            "oil_level": "oil_level",
            "battery_voltage": "battery_voltage",
            "tire_pressure_front_left": "tire_pressure_front_left",
            "tire_pressure_front_right": "tire_pressure_front_right",
            "tire_pressure_rear_left": "tire_pressure_rear_left",
            "tire_pressure_rear_right": "tire_pressure_rear_right",
            "tire_tread_depth": "tire_tread_depth",
            "fuel_level": "fuel_level",
            "odometer_reading": "odometer_reading",
            "average_fuel_consumption": "average_fuel_consumption",
        }

        update_fields = []
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                if model_field == "odometer_reading" and input[input_key] < 0:
                    raise GraphQLError("odometer_reading must be >= 0.")
                setattr(telemetry, model_field, input[input_key])
                update_fields.append(model_field)

        if "diagnostic_trouble_codes" in input and input["diagnostic_trouble_codes"] is not None:
            telemetry.diagnostic_trouble_codes = input["diagnostic_trouble_codes"]
            update_fields.append("diagnostic_trouble_codes")

        if not update_fields:
            return cls(
                vehicle_telemetry=telemetry,
                success=True,
                message="Nothing to update.",
            )

        try:
            telemetry.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        telemetry.save(update_fields=update_fields)

        return cls(
            vehicle_telemetry=telemetry,
            success=True,
            message="Telemetry updated.",
        )


class DeleteVehicleTelemetry(relay.ClientIDMutation):
    """
    Delete a telemetry record.

    Restricted to staff or the vehicle owner. Telemetry is usually
    retained for a long time; delete only for GDPR-style requests or
    to purge genuinely corrupt data.
    """

    class Input:
        telemetry_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, telemetry_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(telemetry_id)
        except Exception:
            raise GraphQLError("Invalid telemetry_id.")

        try:
            telemetry = VehicleTelemetryModel.objects.select_for_update().get(pk=pk)
        except VehicleTelemetryModel.DoesNotExist:
            raise GraphQLError("Telemetry record not found.")

        _assert_can_write_telemetry(telemetry.vehicle, me)

        telemetry.delete()
        return cls(success=True, message="Telemetry deleted.")


# =============================================================================
# PredictiveAlert
# =============================================================================

class CreatePredictiveAlert(relay.ClientIDMutation):
    """
    Create a predictive-maintenance alert.

    Alerts are always created unresolved. Resolving is a separate,
    audited operation. `confidence_score` is validated against the
    model's 0-100 range, and `recommended_action_date` is required
    because the model has no default.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)

        alert_type = graphene.String(required=True)
        severity = graphene.String(required=True)

        title = graphene.String(required=True)
        description = graphene.String()
        predicted_issue = graphene.String()

        confidence_score = graphene.Float(required=True)

        predicted_failure_date = graphene.Date()
        recommended_action_date = graphene.Date(required=True)

    vehicle = graphene.Field(VehicleNode)
    predictive_alert = graphene.Field(PredictiveAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        if input["alert_type"] not in _ALERT_TYPES:
            raise GraphQLError(
                f"alert_type must be one of: {', '.join(sorted(_ALERT_TYPES))}."
            )
        if input["severity"] not in _ALERT_SEVERITIES:
            raise GraphQLError(
                f"severity must be one of: {', '.join(sorted(_ALERT_SEVERITIES))}."
            )

        confidence = input["confidence_score"]
        if not 0 <= confidence <= 100:
            raise GraphQLError("confidence_score must be between 0 and 100.")

        vehicle = _resolve_vehicle(vehicle_id)

        # Only staff or the vehicle's provider/owner may create alerts on it.
        # System-generated alerts typically run as staff.
        if not me.is_staff:
            provider = getattr(me, "service_provider", None)
            is_provider = (
                provider is not None
                and getattr(vehicle, "provider_id", None) == provider.pk
            )
            is_owner = getattr(vehicle, "owner_id", None) == me.pk
            if not (is_provider or is_owner):
                raise GraphQLError(
                    "Not authorized to create alerts for this vehicle."
                )

        try:
            alert = PredictiveAlertModel.objects.create(
                vehicle=vehicle,
                alert_type=input["alert_type"],
                severity=input["severity"],
                title=input["title"],
                description=input.get("description") or "",
                predicted_issue=input.get("predicted_issue") or "",
                confidence_score=confidence,
                predicted_failure_date=input.get("predicted_failure_date"),
                recommended_action_date=input["recommended_action_date"],
                is_resolved=False,
                resolved_at=None,
                resolution_notes="",
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            predictive_alert=alert,
            success=True,
            message="Predictive alert created.",
        )


class UpdatePredictiveAlert(relay.ClientIDMutation):
    """
    Update the descriptive fields of an unresolved alert.

    Resolution fields (`is_resolved`, `resolved_at`, `resolution_notes`)
    are not exposed here — use `ResolvePredictiveAlert` /
    `UnresolvePredictiveAlert` for that transition.
    """

    class Input:
        alert_id = graphene.ID(required=True)

        alert_type = graphene.String()
        severity = graphene.String()

        title = graphene.String()
        description = graphene.String()
        predicted_issue = graphene.String()

        confidence_score = graphene.Float()
        predicted_failure_date = graphene.Date()
        recommended_action_date = graphene.Date()

    predictive_alert = graphene.Field(PredictiveAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, alert_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(alert_id)
        except Exception:
            raise GraphQLError("Invalid alert_id.")

        try:
            alert = PredictiveAlertModel.objects.select_for_update().get(pk=pk)
        except PredictiveAlertModel.DoesNotExist:
            raise GraphQLError("Predictive alert not found.")

        # Permission mirrors create.
        if not me.is_staff:
            provider = getattr(me, "service_provider", None)
            is_provider = (
                provider is not None
                and getattr(alert.vehicle, "provider_id", None) == provider.pk
            )
            is_owner = getattr(alert.vehicle, "owner_id", None) == me.pk
            if not (is_provider or is_owner):
                raise GraphQLError(
                    "Not authorized to update alerts for this vehicle."
                )

        # Resolved alerts are frozen for non-staff.
        if alert.is_resolved and not me.is_staff:
            raise GraphQLError(
                "Cannot edit a resolved alert. Unresolve it first."
            )

        if "alert_type" in input and input["alert_type"] is not None:
            if input["alert_type"] not in _ALERT_TYPES:
                raise GraphQLError(
                    f"alert_type must be one of: "
                    f"{', '.join(sorted(_ALERT_TYPES))}."
                )
            alert.alert_type = input["alert_type"]

        if "severity" in input and input["severity"] is not None:
            if input["severity"] not in _ALERT_SEVERITIES:
                raise GraphQLError(
                    f"severity must be one of: "
                    f"{', '.join(sorted(_ALERT_SEVERITIES))}."
                )
            alert.severity = input["severity"]

        if "confidence_score" in input and input["confidence_score"] is not None:
            if not 0 <= input["confidence_score"] <= 100:
                raise GraphQLError("confidence_score must be between 0 and 100.")
            alert.confidence_score = input["confidence_score"]

        simple_map = {
            "title": "title",
            "description": "description",
            "predicted_issue": "predicted_issue",
            "predicted_failure_date": "predicted_failure_date",
            "recommended_action_date": "recommended_action_date",
        }
        for input_key, model_field in simple_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(alert, model_field, input[input_key])

        try:
            alert.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        alert.save()

        return cls(
            predictive_alert=alert,
            success=True,
            message="Predictive alert updated.",
        )


class ResolvePredictiveAlert(relay.ClientIDMutation):
    """
    Mark an alert as resolved.

    The transition is idempotent: resolving an already-resolved alert
    returns success without altering timestamps.
    """

    class Input:
        alert_id = graphene.ID(required=True)
        resolution_notes = graphene.String()

    predictive_alert = graphene.Field(PredictiveAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, alert_id, resolution_notes=None):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(alert_id)
        except Exception:
            raise GraphQLError("Invalid alert_id.")

        try:
            alert = PredictiveAlertModel.objects.select_for_update().get(pk=pk)
        except PredictiveAlertModel.DoesNotExist:
            raise GraphQLError("Predictive alert not found.")

        if not me.is_staff:
            provider = getattr(me, "service_provider", None)
            is_provider = (
                provider is not None
                and getattr(alert.vehicle, "provider_id", None) == provider.pk
            )
            is_owner = getattr(alert.vehicle, "owner_id", None) == me.pk
            if not (is_provider or is_owner):
                raise GraphQLError(
                    "Not authorized to resolve alerts for this vehicle."
                )

        if alert.is_resolved:
            return cls(
                predictive_alert=alert,
                success=True,
                message="Alert is already resolved.",
            )

        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        if resolution_notes is not None:
            alert.resolution_notes = resolution_notes

        alert.save(update_fields=[
            "is_resolved", "resolved_at", "resolution_notes", "updated_at",
        ])

        return cls(
            predictive_alert=alert,
            success=True,
            message="Alert resolved.",
        )


class UnresolvePredictiveAlert(relay.ClientIDMutation):
    """Reopen a previously resolved alert. Staff-only."""

    class Input:
        alert_id = graphene.ID(required=True)

    predictive_alert = graphene.Field(PredictiveAlertNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, alert_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may reopen resolved alerts.")

        try:
            _, pk = from_global_id(alert_id)
        except Exception:
            raise GraphQLError("Invalid alert_id.")

        try:
            alert = PredictiveAlertModel.objects.select_for_update().get(pk=pk)
        except PredictiveAlertModel.DoesNotExist:
            raise GraphQLError("Predictive alert not found.")

        if not alert.is_resolved:
            return cls(
                predictive_alert=alert,
                success=True,
                message="Alert is already open.",
            )

        alert.is_resolved = False
        alert.resolved_at = None
        alert.resolution_notes = ""

        alert.save(update_fields=[
            "is_resolved", "resolved_at", "resolution_notes", "updated_at",
        ])

        return cls(
            predictive_alert=alert,
            success=True,
            message="Alert reopened.",
        )


class DeletePredictiveAlert(relay.ClientIDMutation):
    """
    Delete a predictive alert.

    Staff-only. Alerts are audit records; a regular user should not be
    able to erase one, even their own.
    """

    class Input:
        alert_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, alert_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete predictive alerts.")

        try:
            _, pk = from_global_id(alert_id)
        except Exception:
            raise GraphQLError("Invalid alert_id.")

        try:
            alert = PredictiveAlertModel.objects.select_for_update().get(pk=pk)
        except PredictiveAlertModel.DoesNotExist:
            raise GraphQLError("Predictive alert not found.")

        alert.delete()
        return cls(success=True, message="Predictive alert deleted.")


# =============================================================================
# Registration
# =============================================================================

class TelemetryMutations(graphene.ObjectType):
    create_vehicle_telemetry = CreateVehicleTelemetry.Field()
    update_vehicle_telemetry = UpdateVehicleTelemetry.Field()
    delete_vehicle_telemetry = DeleteVehicleTelemetry.Field()

    create_predictive_alert = CreatePredictiveAlert.Field()
    update_predictive_alert = UpdatePredictiveAlert.Field()
    resolve_predictive_alert = ResolvePredictiveAlert.Field()
    unresolve_predictive_alert = UnresolvePredictiveAlert.Field()
    delete_predictive_alert = DeletePredictiveAlert.Field()