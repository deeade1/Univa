# apps/backend/graphq/transport/mutations/maintenance.py
"""
MaintenanceSchedule and MaintenanceLog mutations.

Model facts that shape these mutations:
    - MaintenanceSchedule.estimated_duration is a DurationField — clients
      send an Int (minutes) and we convert to timedelta.
    - Multiple DateFields (last_service_date, next_service_date,
      service_date) — inputs are Date, not DateTime.
    - DecimalField for cost — inputs are Decimal.
    - MaintenanceLog.receipts is a FileField — input is a storage
      reference string, not a list.
    - is_verified / verified_by are audit fields — staff-only.
    - Status transitions have meaning (SCHEDULED → IN_PROGRESS →
      COMPLETED, or CANCELLED). The COMPLETED transition also fills in
      completed_date; a dedicated mutation handles that.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.maintenance_schedule import (
    MaintenanceScheduleNode,
    MaintenanceLogNode,
)
from graphq.transport.types.vehicle import VehicleNode
from graphq.accounts.types.user import UserNode

from transport.models.maintenance.maintenance_schedule import (
    MaintenanceSchedule,
    MaintenanceLog,
)
from transport.models.maintenance.vehicle import Vehicle


User = get_user_model()

_MAINTENANCE_TYPES = {c.value for c in MaintenanceSchedule.MaintenanceType}
_SCHEDULE_STATUSES = {c.value for c in MaintenanceSchedule.Status}
_LOG_TYPES = {c.value for c in MaintenanceLog.LogType}

_TERMINAL_SCHEDULE_STATUSES = {
    MaintenanceSchedule.Status.COMPLETED,
    MaintenanceSchedule.Status.CANCELLED,
}


# =============================================================================
# Helpers
# =============================================================================

def _assert_can_manage(vehicle, user, *, staff_only=False):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if staff_only:
        if not user.is_staff:
            raise GraphQLError("Staff permission required.")
        return
    if user.is_staff:
        return
    if getattr(vehicle, "owner_id", None) == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and getattr(vehicle, "provider_id", None) == provider.pk:
        return
    raise GraphQLError("Not authorized to manage maintenance for this vehicle.")


def _resolve_vehicle(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid vehicle_id.")
    try:
        return Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        raise GraphQLError("Vehicle not found.")


def _resolve_schedule(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid maintenance_schedule_id.")
    qs = MaintenanceSchedule.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except MaintenanceSchedule.DoesNotExist:
        raise GraphQLError("Maintenance schedule not found.")


def _resolve_log(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid maintenance_log_id.")
    qs = MaintenanceLog.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except MaintenanceLog.DoesNotExist:
        raise GraphQLError("Maintenance log not found.")


def _resolve_user(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


def _validate_enum(value, allowed, field):
    if value is None:
        return
    if value not in allowed:
        raise GraphQLError(
            f"{field} must be one of: {', '.join(sorted(allowed))}."
        )


def _minutes_to_delta(minutes):
    if minutes is None:
        return None
    if minutes < 0:
        raise GraphQLError("estimated_duration cannot be negative.")
    return timedelta(minutes=minutes)


def _parse_json_list(value, field):
    if value is None:
        return None
    if not isinstance(value, list):
        raise GraphQLError(f"{field} must be a list.")
    return value


# =============================================================================
# MaintenanceSchedule
# =============================================================================

class CreateMaintenanceSchedule(relay.ClientIDMutation):
    """
    Create a MaintenanceSchedule.

    Vehicle owner, assigned provider, or staff. New schedules start
    SCHEDULED by default; `status` may be set but COMPLETED / CANCELLED
    should go through the dedicated mutations.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)

        maintenance_type = graphene.String(required=True)
        status = graphene.String()
        scheduled_date = graphene.DateTime(required=True)
        estimated_duration = graphene.Int(
            description="Estimated duration in minutes."
        )

        last_service_date = graphene.Date()
        last_service_odometer = graphene.Int()
        next_service_date = graphene.Date()
        next_service_odometer = graphene.Int()

        time_interval_days = graphene.Int()
        distance_interval_km = graphene.Int()

        description = graphene.String(required=True)
        cost = graphene.Decimal()
        parts_used = graphene.JSONString()
        mileage_at_service = graphene.Int()
        service_center = graphene.String()
        technician_notes = graphene.String()

        is_urgent = graphene.Boolean()
        is_recurring = graphene.Boolean()
        recurrence_interval = graphene.Int()

        is_verified = graphene.Boolean()     # staff-only
        verified_by_id = graphene.ID()       # staff-only

    vehicle = graphene.Field(VehicleNode)
    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, **input):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id)
        _assert_can_manage(vehicle, me)

        _validate_enum(input["maintenance_type"], _MAINTENANCE_TYPES, "maintenance_type")
        _validate_enum(input.get("status"), _SCHEDULE_STATUSES, "status")

        if (
            input.get("status") in _TERMINAL_SCHEDULE_STATUSES
            and not me.is_staff
        ):
            raise GraphQLError(
                "Only staff may create a schedule in a terminal state."
            )

        # Staff-only fields.
        if not me.is_staff:
            for field in ("is_verified", "verified_by_id"):
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may set {field}.")

        verified_by = None
        if input.get("verified_by_id"):
            verified_by = _resolve_user(input["verified_by_id"])

        payload = {
            "vehicle": vehicle,
            "maintenance_type": input["maintenance_type"],
            "status": input.get("status") or MaintenanceSchedule.Status.SCHEDULED,
            "scheduled_date": input["scheduled_date"],
            "estimated_duration": _minutes_to_delta(input.get("estimated_duration")),
            "last_service_date": input.get("last_service_date"),
            "last_service_odometer": input.get("last_service_odometer"),
            "next_service_date": input.get("next_service_date"),
            "next_service_odometer": input.get("next_service_odometer"),
            "time_interval_days": input.get("time_interval_days"),
            "distance_interval_km": input.get("distance_interval_km"),
            "description": input["description"],
            "cost": _parse_decimal(input.get("cost"), "cost"),
            "parts_used": _parse_json_list(input.get("parts_used"), "parts_used") or [],
            "mileage_at_service": input.get("mileage_at_service"),
            "service_center": input.get("service_center") or "",
            "technician_notes": input.get("technician_notes") or "",
            "is_urgent": bool(input.get("is_urgent")),
            "is_recurring": bool(input.get("is_recurring")),
            "recurrence_interval": input.get("recurrence_interval"),
            "is_verified": bool(input.get("is_verified")) if me.is_staff else False,
            "verified_by": verified_by,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            schedule = MaintenanceSchedule.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            maintenance_schedule=schedule,
            success=True,
            message="Maintenance schedule created.",
        )


class UpdateMaintenanceSchedule(relay.ClientIDMutation):
    """
    Update metadata on a MaintenanceSchedule.

    Status transitions have dedicated mutations (`CompleteMaintenanceSchedule`,
    `CancelMaintenanceSchedule`, `StartMaintenanceSchedule`).
    """

    class Input:
        maintenance_schedule_id = graphene.ID(required=True)

        maintenance_type = graphene.String()
        scheduled_date = graphene.DateTime()
        estimated_duration = graphene.Int()

        last_service_date = graphene.Date()
        last_service_odometer = graphene.Int()
        next_service_date = graphene.Date()
        next_service_odometer = graphene.Int()

        time_interval_days = graphene.Int()
        distance_interval_km = graphene.Int()

        description = graphene.String()
        cost = graphene.Decimal()
        parts_used = graphene.JSONString()
        mileage_at_service = graphene.Int()
        service_center = graphene.String()
        technician_notes = graphene.String()

        is_urgent = graphene.Boolean()
        is_recurring = graphene.Boolean()
        recurrence_interval = graphene.Int()

        is_verified = graphene.Boolean()   # staff-only
        verified_by_id = graphene.ID()     # staff-only

    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_schedule_id, **input):
        me = info.context.user
        schedule = _resolve_schedule(maintenance_schedule_id, lock=True)
        _assert_can_manage(schedule.vehicle, me)

        if schedule.status in _TERMINAL_SCHEDULE_STATUSES and not me.is_staff:
            raise GraphQLError(
                f"Cannot update a schedule in terminal state '{schedule.status}'."
            )

        _validate_enum(input.get("maintenance_type"), _MAINTENANCE_TYPES, "maintenance_type")

        if not me.is_staff:
            for field in ("is_verified", "verified_by_id"):
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may set {field}.")

        update_fields = []

        # Duration
        if "estimated_duration" in input and input["estimated_duration"] is not None:
            schedule.estimated_duration = _minutes_to_delta(input["estimated_duration"])
            update_fields.append("estimated_duration")

        # Cost
        if "cost" in input and input["cost"] is not None:
            schedule.cost = _parse_decimal(input["cost"], "cost")
            update_fields.append("cost")

        # parts_used — merge by index is ambiguous; replace if provided.
        if "parts_used" in input and input["parts_used"] is not None:
            schedule.parts_used = _parse_json_list(input["parts_used"], "parts_used")
            update_fields.append("parts_used")

        # Simple scalar passthrough
        for field in (
            "maintenance_type",
            "scheduled_date",
            "last_service_date",
            "last_service_odometer",
            "next_service_date",
            "next_service_odometer",
            "time_interval_days",
            "distance_interval_km",
            "description",
            "mileage_at_service",
            "service_center",
            "technician_notes",
            "is_urgent",
            "is_recurring",
            "recurrence_interval",
        ):
            if field in input and input[field] is not None:
                setattr(schedule, field, input[field])
                update_fields.append(field)

        # Staff-only flags
        if me.is_staff:
            if "is_verified" in input and input["is_verified"] is not None:
                schedule.is_verified = bool(input["is_verified"])
                update_fields.append("is_verified")
            if input.get("verified_by_id"):
                schedule.verified_by = _resolve_user(input["verified_by_id"])
                update_fields.append("verified_by")

        if not update_fields:
            return cls(
                maintenance_schedule=schedule,
                success=True,
                message="Nothing to update.",
            )

        try:
            schedule.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        schedule.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            maintenance_schedule=schedule,
            success=True,
            message="Maintenance schedule updated.",
        )


class StartMaintenanceSchedule(relay.ClientIDMutation):
    """Transition a schedule from SCHEDULED → IN_PROGRESS."""

    class Input:
        maintenance_schedule_id = graphene.ID(required=True)

    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_schedule_id):
        me = info.context.user
        schedule = _resolve_schedule(maintenance_schedule_id, lock=True)
        _assert_can_manage(schedule.vehicle, me)

        if schedule.status == MaintenanceSchedule.Status.IN_PROGRESS:
            return cls(
                maintenance_schedule=schedule,
                success=True,
                message="Schedule is already in progress.",
            )
        if schedule.status != MaintenanceSchedule.Status.SCHEDULED:
            raise GraphQLError(
                f"Cannot start a schedule in status '{schedule.status}'."
            )

        schedule.status = MaintenanceSchedule.Status.IN_PROGRESS
        schedule.save(update_fields=["status", "updated_at"])

        return cls(
            maintenance_schedule=schedule,
            success=True,
            message="Maintenance started.",
        )


class CompleteMaintenanceSchedule(relay.ClientIDMutation):
    """Transition a schedule to COMPLETED and stamp `completed_date`."""

    class Input:
        maintenance_schedule_id = graphene.ID(required=True)
        completed_date = graphene.DateTime()
        mileage_at_service = graphene.Int()
        cost = graphene.Decimal()
        technician_notes = graphene.String()

    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_schedule_id, **input):
        me = info.context.user
        schedule = _resolve_schedule(maintenance_schedule_id, lock=True)
        _assert_can_manage(schedule.vehicle, me)

        if schedule.status == MaintenanceSchedule.Status.COMPLETED:
            return cls(
                maintenance_schedule=schedule,
                success=True,
                message="Schedule is already completed.",
            )
        if schedule.status == MaintenanceSchedule.Status.CANCELLED:
            raise GraphQLError("Cannot complete a cancelled schedule.")

        schedule.status = MaintenanceSchedule.Status.COMPLETED
        schedule.completed_date = input.get("completed_date") or timezone.now()

        update_fields = ["status", "completed_date", "updated_at"]

        if input.get("mileage_at_service") is not None:
            schedule.mileage_at_service = input["mileage_at_service"]
            update_fields.append("mileage_at_service")
        if input.get("cost") is not None:
            schedule.cost = _parse_decimal(input["cost"], "cost")
            update_fields.append("cost")
        if input.get("technician_notes") is not None:
            schedule.technician_notes = input["technician_notes"]
            update_fields.append("technician_notes")

        try:
            schedule.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        schedule.save(update_fields=sorted(set(update_fields)))

        return cls(
            maintenance_schedule=schedule,
            success=True,
            message="Maintenance completed.",
        )


class CancelMaintenanceSchedule(relay.ClientIDMutation):
    """Transition a schedule to CANCELLED."""

    class Input:
        maintenance_schedule_id = graphene.ID(required=True)
        reason = graphene.String()

    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_schedule_id, reason=None):
        me = info.context.user
        schedule = _resolve_schedule(maintenance_schedule_id, lock=True)
        _assert_can_manage(schedule.vehicle, me)

        if schedule.status == MaintenanceSchedule.Status.CANCELLED:
            return cls(
                maintenance_schedule=schedule,
                success=True,
                message="Schedule is already cancelled.",
            )
        if schedule.status == MaintenanceSchedule.Status.COMPLETED:
            raise GraphQLError("Cannot cancel a completed schedule.")

        schedule.status = MaintenanceSchedule.Status.CANCELLED
        if reason:
            schedule.technician_notes = (
                (schedule.technician_notes or "")
                + ("\n\n" if schedule.technician_notes else "")
                + f"Cancellation reason: {reason}"
            )
            schedule.save(update_fields=["status", "technician_notes", "updated_at"])
        else:
            schedule.save(update_fields=["status", "updated_at"])

        return cls(
            maintenance_schedule=schedule,
            success=True,
            message="Maintenance cancelled.",
        )


class DeleteMaintenanceSchedule(relay.ClientIDMutation):
    """
    Delete a MaintenanceSchedule.

    Staff-only. Schedules are audit records; cancel rather than delete.
    Logs attached via the FK cascade.
    """

    class Input:
        maintenance_schedule_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_schedule_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete maintenance schedules.")

        schedule = _resolve_schedule(maintenance_schedule_id, lock=True)
        schedule.delete()
        return cls(success=True, message="Maintenance schedule deleted.")


# =============================================================================
# MaintenanceLog
# =============================================================================

class CreateMaintenanceLog(relay.ClientIDMutation):
    """
    Create a MaintenanceLog.

    Vehicle owner, assigned provider, or staff. `maintenance_schedule_id`
    is optional (logs can be standalone notes / incidents).
    """

    class Input:
        vehicle_id = graphene.ID(required=True)
        maintenance_schedule_id = graphene.ID()

        log_date = graphene.DateTime()
        service_date = graphene.Date()
        log_type = graphene.String(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)

        mileage = graphene.Int(required=True)
        odometer_reading = graphene.Int()
        cost = graphene.Decimal()

        parts_changed = graphene.JSONString()
        technician = graphene.String()
        service_provider = graphene.String()

        receipts = graphene.String(
            description="Storage reference (URL or key), not a list of files."
        )
        photos = graphene.JSONString()

        is_verified = graphene.Boolean()    # staff-only
        verified_by_id = graphene.ID()      # staff-only

    vehicle = graphene.Field(VehicleNode)
    maintenance_schedule = graphene.Field(MaintenanceScheduleNode)
    maintenance_log = graphene.Field(MaintenanceLogNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, **input):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id)
        _assert_can_manage(vehicle, me)

        _validate_enum(input["log_type"], _LOG_TYPES, "log_type")

        schedule = None
        if input.get("maintenance_schedule_id"):
            schedule = _resolve_schedule(input["maintenance_schedule_id"])
            if schedule.vehicle_id != vehicle.pk:
                raise GraphQLError(
                    "The schedule does not belong to this vehicle."
                )

        if not me.is_staff:
            for field in ("is_verified", "verified_by_id"):
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may set {field}.")

        verified_by = None
        if input.get("verified_by_id"):
            verified_by = _resolve_user(input["verified_by_id"])

        payload = {
            "vehicle": vehicle,
            "maintenance_schedule": schedule,
            "log_date": input.get("log_date") or timezone.now(),
            "service_date": input.get("service_date"),
            "log_type": input["log_type"],
            "title": input["title"],
            "description": input["description"],
            "mileage": input["mileage"],
            "odometer_reading": input.get("odometer_reading"),
            "cost": _parse_decimal(input.get("cost"), "cost"),
            "parts_changed": _parse_json_list(
                input.get("parts_changed"), "parts_changed"
            ) or [],
            "technician": input.get("technician") or "",
            "service_provider": input.get("service_provider") or "",
            "receipts": input.get("receipts") or None,
            "photos": _parse_json_list(input.get("photos"), "photos") or [],
            "is_verified": bool(input.get("is_verified")) if me.is_staff else False,
            "verified_by": verified_by,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            log = MaintenanceLog.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            maintenance_schedule=schedule,
            maintenance_log=log,
            success=True,
            message="Maintenance log created.",
        )


class UpdateMaintenanceLog(relay.ClientIDMutation):
    """Update a MaintenanceLog. Vehicle owner, provider, or staff."""

    class Input:
        maintenance_log_id = graphene.ID(required=True)
        maintenance_schedule_id = graphene.ID()

        log_date = graphene.DateTime()
        service_date = graphene.Date()
        log_type = graphene.String()
        title = graphene.String()
        description = graphene.String()

        mileage = graphene.Int()
        odometer_reading = graphene.Int()
        cost = graphene.Decimal()

        parts_changed = graphene.JSONString()
        technician = graphene.String()
        service_provider = graphene.String()

        receipts = graphene.String()
        photos = graphene.JSONString()

        is_verified = graphene.Boolean()   # staff-only
        verified_by_id = graphene.ID()     # staff-only

    maintenance_log = graphene.Field(MaintenanceLogNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_log_id, **input):
        me = info.context.user
        log = _resolve_log(maintenance_log_id, lock=True)
        _assert_can_manage(log.vehicle, me)

        _validate_enum(input.get("log_type"), _LOG_TYPES, "log_type")

        if not me.is_staff:
            for field in ("is_verified", "verified_by_id"):
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may set {field}.")

        update_fields = []

        if input.get("maintenance_schedule_id"):
            schedule = _resolve_schedule(input["maintenance_schedule_id"])
            if schedule.vehicle_id != log.vehicle_id:
                raise GraphQLError(
                    "The schedule does not belong to this vehicle."
                )
            log.maintenance_schedule = schedule
            update_fields.append("maintenance_schedule")

        for field in (
            "log_date",
            "service_date",
            "log_type",
            "title",
            "description",
            "mileage",
            "odometer_reading",
            "technician",
            "service_provider",
            "receipts",
        ):
            if field in input and input[field] is not None:
                setattr(log, field, input[field])
                update_fields.append(field)

        if "cost" in input and input["cost"] is not None:
            log.cost = _parse_decimal(input["cost"], "cost")
            update_fields.append("cost")

        if "parts_changed" in input and input["parts_changed"] is not None:
            log.parts_changed = _parse_json_list(input["parts_changed"], "parts_changed")
            update_fields.append("parts_changed")

        if "photos" in input and input["photos"] is not None:
            log.photos = _parse_json_list(input["photos"], "photos")
            update_fields.append("photos")

        if me.is_staff:
            if "is_verified" in input and input["is_verified"] is not None:
                log.is_verified = bool(input["is_verified"])
                update_fields.append("is_verified")
            if input.get("verified_by_id"):
                log.verified_by = _resolve_user(input["verified_by_id"])
                update_fields.append("verified_by")

        if not update_fields:
            return cls(
                maintenance_log=log,
                success=True,
                message="Nothing to update.",
            )

        try:
            log.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        log.save(update_fields=update_fields)

        return cls(
            maintenance_log=log,
            success=True,
            message="Maintenance log updated.",
        )


class DeleteMaintenanceLog(relay.ClientIDMutation):
    """
    Delete a MaintenanceLog.

    Staff-only. Logs are the historical record of what was done; deleting
    is destructive. Prefer editing for corrections.
    """

    class Input:
        maintenance_log_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, maintenance_log_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete maintenance logs.")

        log = _resolve_log(maintenance_log_id, lock=True)
        log.delete()
        return cls(success=True, message="Maintenance log deleted.")


# =============================================================================
# Registration
# =============================================================================

class MaintenanceMutations(graphene.ObjectType):
    create_maintenance_schedule = CreateMaintenanceSchedule.Field()
    update_maintenance_schedule = UpdateMaintenanceSchedule.Field()
    start_maintenance_schedule = StartMaintenanceSchedule.Field()
    complete_maintenance_schedule = CompleteMaintenanceSchedule.Field()
    cancel_maintenance_schedule = CancelMaintenanceSchedule.Field()
    delete_maintenance_schedule = DeleteMaintenanceSchedule.Field()

    create_maintenance_log = CreateMaintenanceLog.Field()
    update_maintenance_log = UpdateMaintenanceLog.Field()
    delete_maintenance_log = DeleteMaintenanceLog.Field()