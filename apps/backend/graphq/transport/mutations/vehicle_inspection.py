# apps/backend/graphq/transport/mutations/vehicle_inspection.py
"""
VehicleInspection mutations.

Design rules enforced:
    - An inspection is always attached to an existing vehicle; creation
      requires ownership, provider assignment, or staff.
    - The inspector is derived from `info.context.user` (staff may
      override for data imports).
    - Result transitions go through the model's helper methods so the
      vehicle's `last_inspection_date` / `next_inspection_date` stay in
      sync (`_update_vehicle_inspection_date`).
    - Checklist and photos are validated structurally before save.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.vehicle_inspection import VehicleInspectionNode

from graphq.transport.types.vehicle import VehicleNode


from transport.models.maintenance.vehicle_inspection import VehicleInspection
from transport.models.maintenance.vehicle import Vehicle  


# =============================================================================
# Constants
# =============================================================================

_ALLOWED_INSPECTION_TYPES = {
    choice[0] for choice in VehicleInspection.InspectionType.choices
}
_ALLOWED_RESULTS = {
    choice[0] for choice in VehicleInspection.InspectionResult.choices
}
_FOLLOW_UP_TERMINAL_RESULTS = {
    VehicleInspection.InspectionResult.PASSED,
    VehicleInspection.InspectionResult.FAILED,
    VehicleInspection.InspectionResult.CONDITIONAL,
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


def _resolve_inspection(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid inspection_id.")
    qs = VehicleInspection.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except VehicleInspection.DoesNotExist:
        raise GraphQLError("Vehicle inspection not found.")


def _assert_can_write_inspection(vehicle, user):
    """
    A user may write an inspection for a vehicle they own, are the
    assigned provider for, or (staff). Inspectors are typically the
    provider's mechanic — we deliberately allow staff as an escape hatch.
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
        "Not authorized to record inspections for this vehicle."
    )


def _validate_inspection_type(value):
    if value not in _ALLOWED_INSPECTION_TYPES:
        raise GraphQLError(
            f"inspection_type must be one of: "
            f"{', '.join(sorted(_ALLOWED_INSPECTION_TYPES))}."
        )


def _validate_result(value):
    if value is None:
        return
    if value not in _ALLOWED_RESULTS:
        raise GraphQLError(
            f"result must be one of: {', '.join(sorted(_ALLOWED_RESULTS))}."
        )


def _validate_checklist(value):
    """
    Accept a dict of {item_name: {passed: bool, notes?: str}}.

    The model's own `add_checklist_item()` writes `checked_at`, but
    accepting it from the client is fine — it just overwrites. We
    require `passed` to be present and boolean.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise GraphQLError("checklist must be an object.")

    for name, item in value.items():
        if not isinstance(item, dict):
            raise GraphQLError(
                f"checklist['{name}'] must be an object."
            )
        if "passed" not in item:
            raise GraphQLError(
                f"checklist['{name}'] must include 'passed'."
            )
        if not isinstance(item["passed"], bool):
            raise GraphQLError(
                f"checklist['{name}']['passed'] must be a boolean."
            )
    return value


def _normalize_photos(photos):
    """
    Accept a list of strings (URLs) or dicts with `url` and normalize
    into the model's expected `[{url, uploaded_at}]` structure.
    """
    if not photos:
        return []
    now = timezone.now().isoformat()
    result = []
    for entry in photos:
        if isinstance(entry, str):
            result.append({"url": entry, "uploaded_at": now})
        elif isinstance(entry, dict) and entry.get("url"):
            result.append({
                "url": entry["url"],
                "uploaded_at": entry.get("uploaded_at") or now,
            })
        else:
            raise GraphQLError(
                "Each photo must be a URL string or {url, uploaded_at} object."
            )
    return result


# =============================================================================
# Create
# =============================================================================

class CreateVehicleInspection(relay.ClientIDMutation):
    """
    Create a VehicleInspection.

    `inspected_by` defaults to the authenticated user. Only staff may
    backdate `inspection_date` or supply a different `inspected_by_id`.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)

        inspection_type = graphene.String(required=True)
        result = graphene.String()  # optional; default = PENDING

        inspected_by_id = graphene.ID()  # staff-only
        inspection_date = graphene.DateTime()  # staff-only
        next_inspection_date = graphene.DateTime()

        checklist = graphene.JSONString()
        findings = graphene.String()
        recommendations = graphene.String()
        notes = graphene.String()

        follow_up_required = graphene.Boolean()
        follow_up_date = graphene.DateTime()

        inspector_signature = graphene.String()
        photos = graphene.List(graphene.String)
        metadata = graphene.JSONString()

    vehicle = graphene.Field(VehicleNode)
    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, inspection_type, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        vehicle = _resolve_vehicle(vehicle_id)
        _assert_can_write_inspection(vehicle, me)

        _validate_inspection_type(inspection_type)
        result = input.get("result") or VehicleInspection.InspectionResult.PENDING
        _validate_result(result)

        checklist = _validate_checklist(input.get("checklist"))
        photos = _normalize_photos(input.get("photos"))

        # Inspector: caller by default; staff may override.
        inspected_by = me
        if input.get("inspected_by_id"):
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may set inspected_by_id explicitly."
                )
            try:
                _, inspector_pk = from_global_id(input["inspected_by_id"])
            except Exception:
                raise GraphQLError("Invalid inspected_by_id.")
            try:
                inspected_by = type(me).objects.get(pk=inspector_pk)
            except type(me).DoesNotExist:
                raise GraphQLError("Inspector not found.")

        # inspection_date: staff-only override, otherwise let the model
        # default to now.
        inspection_date = None
        if input.get("inspection_date"):
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may backdate inspection_date."
                )
            inspection_date = input["inspection_date"]

        payload = {
            "vehicle": vehicle,
            "inspection_type": inspection_type,
            "result": result,
            "inspected_by": inspected_by,
            "next_inspection_date": input.get("next_inspection_date"),
            "checklist": checklist,
            "findings": input.get("findings") or "",
            "recommendations": input.get("recommendations") or "",
            "notes": input.get("notes") or "",
            "follow_up_required": bool(input.get("follow_up_required")),
            "follow_up_date": input.get("follow_up_date"),
            "inspector_signature": input.get("inspector_signature") or "",
            "photos": photos,
            "metadata": input.get("metadata") or {},
        }
        if inspection_date is not None:
            payload["inspection_date"] = inspection_date

        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            inspection = VehicleInspection.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Sync the vehicle's cached inspection dates.
        try:
            inspection._update_vehicle_inspection_date()
        except Exception:
            # Non-fatal: the inspection is already recorded.
            pass

        return cls(
            vehicle=vehicle,
            vehicle_inspection=inspection,
            success=True,
            message="Vehicle inspection created.",
        )


# =============================================================================
# Update (metadata-level fields, not result)
# =============================================================================

class UpdateVehicleInspection(relay.ClientIDMutation):
    """
    Update metadata-level fields of an inspection.

    `result` is NOT updated here — use `RecordInspectionResult`. This
    keeps the result transition going through the model's helper
    methods, which also keep the vehicle's cached dates in sync.
    """

    class Input:
        inspection_id = graphene.ID(required=True)

        inspection_type = graphene.String()
        next_inspection_date = graphene.DateTime()

        findings = graphene.String()
        recommendations = graphene.String()
        notes = graphene.String()

        follow_up_required = graphene.Boolean()
        follow_up_date = graphene.DateTime()

        inspector_signature = graphene.String()
        checklist = graphene.JSONString()  # merge, not replace
        metadata = graphene.JSONString()

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id, **input):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        update_fields = []

        if "inspection_type" in input and input["inspection_type"] is not None:
            _validate_inspection_type(input["inspection_type"])
            inspection.inspection_type = input["inspection_type"]
            update_fields.append("inspection_type")

        simple_map = {
            "next_inspection_date": "next_inspection_date",
            "findings": "findings",
            "recommendations": "recommendations",
            "notes": "notes",
            "follow_up_date": "follow_up_date",
            "inspector_signature": "inspector_signature",
        }
        for input_key, model_field in simple_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(inspection, model_field, input[input_key])
                update_fields.append(model_field)

        if "follow_up_required" in input and input["follow_up_required"] is not None:
            inspection.follow_up_required = bool(input["follow_up_required"])
            update_fields.append("follow_up_required")

        if "checklist" in input and input["checklist"] is not None:
            new_items = _validate_checklist(input["checklist"])
            merged = {**(inspection.checklist or {}), **new_items}
            inspection.checklist = merged
            update_fields.append("checklist")

        if "metadata" in input and input["metadata"] is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            inspection.metadata = {**(inspection.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if not update_fields:
            return cls(
                vehicle_inspection=inspection,
                success=True,
                message="Nothing to update.",
            )

        try:
            inspection.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        inspection.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message="Inspection updated.",
        )


# =============================================================================
# Record result (uses model helpers)
# =============================================================================

class RecordInspectionResult(relay.ClientIDMutation):
    """
    Transition the inspection result.

    Delegates to the model's `pass_inspection()`, `fail_inspection()`,
    and `mark_conditional()` so the vehicle's cached dates get updated.
    """

    class Input:
        inspection_id = graphene.ID(required=True)
        result = graphene.String(required=True)
        notes = graphene.String()

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id, result, notes=None):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        _validate_result(result)

        try:
            if result == VehicleInspection.InspectionResult.PASSED:
                inspection.pass_inspection(notes=notes)
            elif result == VehicleInspection.InspectionResult.FAILED:
                inspection.fail_inspection(notes=notes)
            elif result == VehicleInspection.InspectionResult.CONDITIONAL:
                inspection.mark_conditional(notes=notes)
            else:
                # DEFERRED / PENDING / other — direct field write is fine.
                inspection.result = result
                if notes is not None:
                    inspection.notes = notes
                inspection.save(update_fields=["result", "notes", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message=f"Inspection result set to '{result}'.",
        )


# =============================================================================
# Follow-up
# =============================================================================

class ScheduleInspectionFollowUp(relay.ClientIDMutation):
    """Schedule a follow-up inspection."""

    class Input:
        inspection_id = graphene.ID(required=True)
        follow_up_date = graphene.DateTime(required=True)

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id, follow_up_date):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        if follow_up_date <= timezone.now():
            raise GraphQLError("follow_up_date must be in the future.")

        inspection.schedule_follow_up(follow_up_date)

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message="Follow-up scheduled.",
        )


class CompleteInspectionFollowUp(relay.ClientIDMutation):
    """Complete a follow-up inspection with a result."""

    class Input:
        inspection_id = graphene.ID(required=True)
        result = graphene.String(required=True)
        notes = graphene.String()

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id, result, notes=None):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        if result not in _FOLLOW_UP_TERMINAL_RESULTS:
            raise GraphQLError(
                f"follow-up result must be one of: "
                f"{', '.join(sorted(_FOLLOW_UP_TERMINAL_RESULTS))}."
            )

        inspection.complete_follow_up(result, notes=notes)

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message="Follow-up completed.",
        )


# =============================================================================
# Checklist & photos (incremental)
# =============================================================================

class AddInspectionChecklistItem(relay.ClientIDMutation):
    """Add or replace a single checklist item on an inspection."""

    class Input:
        inspection_id = graphene.ID(required=True)
        item_name = graphene.String(required=True)
        passed = graphene.Boolean(required=True)
        notes = graphene.String()

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, inspection_id, item_name, passed, notes=None
    ):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        if not item_name.strip():
            raise GraphQLError("item_name cannot be empty.")

        inspection.add_checklist_item(item_name, passed, notes=notes)

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message=f"Checklist item '{item_name}' saved.",
        )


class AddInspectionPhoto(relay.ClientIDMutation):
    """Attach a photo URL to an inspection."""

    class Input:
        inspection_id = graphene.ID(required=True)
        photo_url = graphene.String(required=True)

    vehicle_inspection = graphene.Field(VehicleInspectionNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id, photo_url):
        me = info.context.user
        inspection = _resolve_inspection(inspection_id, lock=True)
        _assert_can_write_inspection(inspection.vehicle, me)

        if not photo_url.strip():
            raise GraphQLError("photo_url cannot be empty.")

        inspection.add_photo(photo_url)

        return cls(
            vehicle_inspection=inspection,
            success=True,
            message="Photo attached.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteVehicleInspection(relay.ClientIDMutation):
    """
    Delete a VehicleInspection.

    Staff-only. Inspections are compliance records; a regular user (or
    even the vehicle owner) should not be able to erase one.
    """

    class Input:
        inspection_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, inspection_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete vehicle inspections.")

        inspection = _resolve_inspection(inspection_id, lock=True)
        inspection.delete()

        return cls(success=True, message="Inspection deleted.")


# =============================================================================
# Registration
# =============================================================================

class VehicleInspectionMutations(graphene.ObjectType):
    create_vehicle_inspection = CreateVehicleInspection.Field()
    update_vehicle_inspection = UpdateVehicleInspection.Field()
    record_inspection_result = RecordInspectionResult.Field()
    schedule_inspection_follow_up = ScheduleInspectionFollowUp.Field()
    complete_inspection_follow_up = CompleteInspectionFollowUp.Field()
    add_inspection_checklist_item = AddInspectionChecklistItem.Field()
    add_inspection_photo = AddInspectionPhoto.Field()
    delete_vehicle_inspection = DeleteVehicleInspection.Field()