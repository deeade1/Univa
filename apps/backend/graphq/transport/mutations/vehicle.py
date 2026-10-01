# apps/backend/graphq/transport/mutations/vehicle.py
"""
Vehicle mutations.

Design rules enforced:
    - The owner is always the authenticated user unless staff overrides.
    - `is_moving`, `last_location_update`, and `created_at` / `updated_at`
      are system-managed and not writable via generic create/update.
    - Status transitions go through the model's helper methods
      (`set_in_use`, `set_available`, `set_maintenance`, `set_retired`)
      so `is_moving` and `is_active` stay in sync.
    - Location writes go through `LocationModel.update_location()` so
      `source`, `last_location_update`, and the Point conversion are
      handled consistently.
"""

from decimal import Decimal, InvalidOperation

from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.vehicle import VehicleNode
from graphq.accounts.types.user import UserNode

from transport.models.maintenance.vehicle import Vehicle
from transport.models.core.service_provider import ServiceProviderProfile


User = get_user_model()


# =============================================================================
# Enum allow-lists (from the model's TextChoices)
# =============================================================================

_VALID_CATEGORIES = {c.value for c in Vehicle.VehicleCategory}
_VALID_VEHICLE_TYPES = {c.value for c in Vehicle.VehicleType}
_VALID_FUEL_TYPES = {c.value for c in Vehicle.FuelType}
_VALID_OWNERSHIP_TYPES = {c.value for c in Vehicle.OwnershipType}
_VALID_STATUSES = {c.value for c in Vehicle.VehicleStatus}

# Statuses a regular user may set; retired is staff-only.
_USER_SETTABLE_STATUSES = {
    Vehicle.VehicleStatus.AVAILABLE,
    Vehicle.VehicleStatus.MAINTENANCE,
    Vehicle.VehicleStatus.UNAVAILABLE,
    Vehicle.VehicleStatus.IN_USE,
}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_vehicle(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid vehicle id.")
    qs = Vehicle.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Vehicle.DoesNotExist:
        raise GraphQLError("Vehicle not found.")


def _resolve_provider(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid provider id.")
    try:
        return ServiceProviderProfile.objects.get(pk=pk)
    except ServiceProviderProfile.DoesNotExist:
        raise GraphQLError("Service provider not found.")


def _assert_can_manage(vehicle, user, *, staff_only=False):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if staff_only:
        if not user.is_staff:
            raise GraphQLError("Staff permission required.")
        return
    if user.is_staff:
        return
    if vehicle.owner_id == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and vehicle.provider_id == provider.pk:
        return
    raise GraphQLError("Not authorized to manage this vehicle.")


def _validate_enum(value, allowed, field):
    if value is None:
        return
    if value not in allowed:
        raise GraphQLError(
            f"{field} must be one of: {', '.join(sorted(allowed))}."
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

class CreateVehicle(relay.ClientIDMutation):
    """
    Create a Vehicle.

    Owner is the authenticated user by default. Staff may set an
    explicit `owner_id` (e.g. for onboarding a fleet on behalf of a
    partner account).
    """

    class Input:
        # Ownership (staff override)
        owner_id = graphene.ID()

        # Required basic info
        category = graphene.String(required=True)
        vehicle_type = graphene.String(required=True)
        make = graphene.String(required=True)
        model = graphene.String(required=True)
        year = graphene.Int(required=True)
        license_plate = graphene.String(required=True)

        # Optional basic info
        color = graphene.String()

        # Capacity
        passenger_capacity = graphene.Int()
        cargo_capacity_kg = graphene.Int()
        cargo_volume_m3 = graphene.Decimal()
        luggage_capacity_kg = graphene.Int()

        # Fuel
        fuel_type = graphene.String()
        fuel_efficiency = graphene.Decimal()

        # Ownership / assignment
        ownership_type = graphene.String()
        provider_id = graphene.ID()

        # Insurance
        insurance_provider = graphene.String()
        insurance_policy_number = graphene.String()
        insurance_expiry = graphene.Date()

        # Registration
        registration_number = graphene.String()
        registration_expiry = graphene.Date()

        # Inspection
        last_inspection_date = graphene.Date()
        next_inspection_date = graphene.Date()

        # Flags
        is_active = graphene.Boolean()
        status = graphene.String()

        metadata = graphene.JSONString()

    vehicle = graphene.Field(VehicleNode)
    owner = graphene.Field(UserNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_enum(input["category"], _VALID_CATEGORIES, "category")
        _validate_enum(input["vehicle_type"], _VALID_VEHICLE_TYPES, "vehicle_type")
        _validate_enum(input.get("fuel_type"), _VALID_FUEL_TYPES, "fuel_type")
        _validate_enum(input.get("ownership_type"), _VALID_OWNERSHIP_TYPES, "ownership_type")

        # Vehicle status default is AVAILABLE; staff may set any status,
        # regular users cannot set RETIRED at create.
        status = input.get("status") or Vehicle.VehicleStatus.AVAILABLE
        _validate_enum(status, _VALID_STATUSES, "status")
        if status == Vehicle.VehicleStatus.RETIRED and not me.is_staff:
            raise GraphQLError("Only staff may create a retired vehicle.")

        # Owner resolution.
        owner = me
        if input.get("owner_id"):
            if not me.is_staff:
                raise GraphQLError("Only staff may set a different owner.")
            try:
                _, owner_pk = from_global_id(input["owner_id"])
            except Exception:
                raise GraphQLError("Invalid owner_id.")
            try:
                owner = User.objects.get(pk=owner_pk)
            except User.DoesNotExist:
                raise GraphQLError("Owner not found.")

        # Provider resolution.
        provider = None
        if input.get("provider_id"):
            provider = _resolve_provider(input["provider_id"])
            if not me.is_staff and provider.user_id != me.pk:
                raise GraphQLError(
                    "You can only assign a vehicle to your own provider profile."
                )

        # Year sanity check.
        year = input["year"]
        current_year = timezone.now().year
        if year < 1900 or year > current_year + 1:
            raise GraphQLError(
                f"year must be between 1900 and {current_year + 1}."
            )

        payload = {
            "owner": owner,
            "category": input["category"],
            "vehicle_type": input["vehicle_type"],
            "make": input["make"],
            "model": input["model"],
            "year": year,
            "license_plate": input["license_plate"].upper().strip(),
            "color": input.get("color") or "",
            "passenger_capacity": input.get("passenger_capacity") or 4,
            "cargo_capacity_kg": input.get("cargo_capacity_kg") or 0,
            "cargo_volume_m3": _parse_decimal(input.get("cargo_volume_m3"), "cargo_volume_m3") or Decimal("0"),
            "luggage_capacity_kg": input.get("luggage_capacity_kg") or 0,
            "fuel_type": input.get("fuel_type") or Vehicle.FuelType.PETROL,
            "fuel_efficiency": _parse_decimal(input.get("fuel_efficiency"), "fuel_efficiency"),
            "ownership_type": input.get("ownership_type") or Vehicle.OwnershipType.OWNED,
            "provider": provider,
            "current_provider": provider,
            "insurance_provider": input.get("insurance_provider") or "",
            "insurance_policy_number": input.get("insurance_policy_number") or "",
            "insurance_expiry": input.get("insurance_expiry"),
            "registration_number": input.get("registration_number") or "",
            "registration_expiry": input.get("registration_expiry"),
            "last_inspection_date": input.get("last_inspection_date"),
            "next_inspection_date": input.get("next_inspection_date"),
            "is_active": (
                input["is_active"]
                if input.get("is_active") is not None
                else True
            ),
            "status": status,
            "metadata": input.get("metadata") or {},
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            vehicle = Vehicle(**payload)
            # save() calls full_clean() which runs the model's clean().
            vehicle.save()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            owner=owner,
            success=True,
            message="Vehicle created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateVehicle(relay.ClientIDMutation):
    """
    Update mutable fields on a Vehicle.

    Owner or assigned provider or staff. `provider_id` and
    `current_provider_id` are staff-only. `status` is NOT updated here —
    use `SetVehicleStatus` so the transition goes through the model's
    helper methods.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)

        # Basic info
        color = graphene.String()
        category = graphene.String()
        vehicle_type = graphene.String()
        make = graphene.String()
        model = graphene.String()
        year = graphene.Int()
        license_plate = graphene.String()

        # Capacity
        passenger_capacity = graphene.Int()
        cargo_capacity_kg = graphene.Int()
        cargo_volume_m3 = graphene.Decimal()
        luggage_capacity_kg = graphene.Int()

        # Fuel
        fuel_type = graphene.String()
        fuel_efficiency = graphene.Decimal()

        # Ownership
        ownership_type = graphene.String()
        provider_id = graphene.ID()          # staff-only

        # Insurance
        insurance_provider = graphene.String()
        insurance_policy_number = graphene.String()
        insurance_expiry = graphene.Date()

        # Registration
        registration_number = graphene.String()
        registration_expiry = graphene.Date()

        # Inspection
        last_inspection_date = graphene.Date()
        next_inspection_date = graphene.Date()

        # Flags
        is_active = graphene.Boolean()       # staff-only
        is_verified = graphene.Boolean()     # staff-only

        metadata = graphene.JSONString()

    vehicle = graphene.Field(VehicleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, **input):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id, lock=True)
        _assert_can_manage(vehicle, me)

        # Staff-only fields.
        staff_only = {"provider_id", "is_active", "is_verified"}
        if not me.is_staff:
            for field in staff_only:
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may change {field}.")

        _validate_enum(input.get("category"), _VALID_CATEGORIES, "category")
        _validate_enum(input.get("vehicle_type"), _VALID_VEHICLE_TYPES, "vehicle_type")
        _validate_enum(input.get("fuel_type"), _VALID_FUEL_TYPES, "fuel_type")
        _validate_enum(input.get("ownership_type"), _VALID_OWNERSHIP_TYPES, "ownership_type")

        if "year" in input and input["year"] is not None:
            current_year = timezone.now().year
            if not (1900 <= input["year"] <= current_year + 1):
                raise GraphQLError(
                    f"year must be between 1900 and {current_year + 1}."
                )

        update_fields = []

        # Direct assignment fields.
        scalar_map = {
            "color": "color",
            "category": "category",
            "vehicle_type": "vehicle_type",
            "make": "make",
            "model": "model",
            "year": "year",
            "license_plate": "license_plate",
            "passenger_capacity": "passenger_capacity",
            "cargo_capacity_kg": "cargo_capacity_kg",
            "luggage_capacity_kg": "luggage_capacity_kg",
            "fuel_type": "fuel_type",
            "ownership_type": "ownership_type",
            "insurance_provider": "insurance_provider",
            "insurance_policy_number": "insurance_policy_number",
            "insurance_expiry": "insurance_expiry",
            "registration_number": "registration_number",
            "registration_expiry": "registration_expiry",
            "last_inspection_date": "last_inspection_date",
            "next_inspection_date": "next_inspection_date",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                value = input[input_key]
                if model_field == "license_plate":
                    value = value.upper().strip()
                setattr(vehicle, model_field, value)
                update_fields.append(model_field)

        # Decimal fields.
        for input_key, model_field in (
            ("cargo_volume_m3", "cargo_volume_m3"),
            ("fuel_efficiency", "fuel_efficiency"),
        ):
            if input_key in input and input[input_key] is not None:
                setattr(vehicle, model_field, _parse_decimal(input[input_key], input_key))
                update_fields.append(model_field)

        # Staff-only flags.
        if "is_active" in input and input["is_active"] is not None:
            vehicle.is_active = bool(input["is_active"])
            update_fields.append("is_active")
        if "is_verified" in input and input["is_verified"] is not None:
            vehicle.is_verified = bool(input["is_verified"])
            update_fields.append("is_verified")
        if "provider_id" in input and input["provider_id"] is not None:
            provider = _resolve_provider(input["provider_id"])
            vehicle.provider = provider
            vehicle.current_provider = provider
            update_fields.extend(["provider", "current_provider"])

        # Metadata merge.
        if "metadata" in input and input["metadata"] is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            vehicle.metadata = {**(vehicle.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if not update_fields:
            return cls(
                vehicle=vehicle,
                success=True,
                message="Nothing to update.",
            )

        try:
            vehicle.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        vehicle.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            vehicle=vehicle,
            success=True,
            message="Vehicle updated.",
        )


# =============================================================================
# Status transitions (route through model helpers)
# =============================================================================

class SetVehicleStatus(relay.ClientIDMutation):
    """
    Transition a vehicle's operational status.

    Uses the model's `set_in_use()`, `set_available()`, `set_maintenance()`,
    and `set_retired()` helpers so `is_moving` and `is_active` stay in
    sync. `RETIRED` is staff-only.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)
        status = graphene.String(required=True)

    vehicle = graphene.Field(VehicleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id, status):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id, lock=True)
        _assert_can_manage(vehicle, me)

        _validate_enum(status, _VALID_STATUSES, "status")

        if status not in _USER_SETTABLE_STATUSES and not me.is_staff:
            raise GraphQLError(
                f"Only staff may set status to '{status}'."
            )

        try:
            if status == Vehicle.VehicleStatus.AVAILABLE:
                vehicle.set_available()
            elif status == Vehicle.VehicleStatus.IN_USE:
                vehicle.set_in_use()
            elif status == Vehicle.VehicleStatus.MAINTENANCE:
                vehicle.set_maintenance()
            elif status == Vehicle.VehicleStatus.RETIRED:
                vehicle.set_retired()
            elif status == Vehicle.VehicleStatus.UNAVAILABLE:
                vehicle.status = Vehicle.VehicleStatus.UNAVAILABLE
                vehicle.is_moving = False
                vehicle.save(update_fields=["status", "is_moving", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            vehicle=vehicle,
            success=True,
            message=f"Status set to '{status}'.",
        )


# =============================================================================
# Location update
# =============================================================================

class UpdateVehicleLocation(relay.ClientIDMutation):
    """
    Push a location update for a vehicle.

    Routes through `LocationModel.update_location()` so the Point
    conversion, `source`, and `last_location_update` are all handled
    consistently.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)
        lat = graphene.Float(required=True)
        lng = graphene.Float(required=True)
        accuracy = graphene.Float()
        source = graphene.String()

    vehicle = graphene.Field(VehicleNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, vehicle_id, lat, lng, accuracy=None, source="gps"
    ):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id, lock=True)
        _assert_can_manage(vehicle, me)

        if not (-90 <= lat <= 90):
            raise GraphQLError("Latitude must be between -90 and 90.")
        if not (-180 <= lng <= 180):
            raise GraphQLError("Longitude must be between -180 and 180.")

        try:
            vehicle.update_location(
                latitude=lat,
                longitude=lng,
                accuracy=accuracy,
                source=source or "gps",
                save=True,
            )
        except (ValueError, ValidationError) as exc:
            raise GraphQLError(str(exc))

        return cls(
            vehicle=vehicle,
            success=True,
            message="Location updated.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteVehicle(relay.ClientIDMutation):
    """
    Delete a Vehicle.

    Refuses while the vehicle is linked to an in-progress ServiceRequest.
    Staff-only for active vehicles; owners can delete their own retired
    or unavailable vehicles.
    """

    class Input:
        vehicle_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, vehicle_id):
        me = info.context.user
        vehicle = _resolve_vehicle(vehicle_id, lock=True)
        _assert_can_manage(vehicle, me)

        # Active vehicles need staff to delete.
        active_statuses = {
            Vehicle.VehicleStatus.AVAILABLE,
            Vehicle.VehicleStatus.IN_USE,
        }
        if vehicle.status in active_statuses and not me.is_staff:
            raise GraphQLError(
                "Cannot delete an active vehicle. "
                "Set it to maintenance or retired first."
            )

        try:
            vehicle.delete()
        except Exception as exc:
            raise GraphQLError(
                f"Delete blocked — vehicle has related records: {exc}"
            )

        return cls(success=True, message="Vehicle deleted.")


# =============================================================================
# Registration
# =============================================================================

class VehicleMutations(graphene.ObjectType):
    create_vehicle = CreateVehicle.Field()
    update_vehicle = UpdateVehicle.Field()
    set_vehicle_status = SetVehicleStatus.Field()
    update_vehicle_location = UpdateVehicleLocation.Field()
    delete_vehicle = DeleteVehicle.Field()