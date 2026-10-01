# apps/backend/graphq/transport/mutations/package.py
"""
Package mutations.

Model facts that shape these mutations:
    - `Package.delivery` is a null=False FK to Delivery (a proxy of
      ServiceRequest).
    - `tracking_number` is unique, not auto-generated — the caller or
      staff must supply it. A duplicate is rejected before hitting the DB.
    - `Package.clean()` enforces:
        * positive dimensions where present
        * insurance_value required when is_insured=True
        * insurance_value <= declared_value
    - `Package.save()` calls full_clean() — every save is validated.
    - The model has NO sender FK (the bare `models.OneToOneField(...)`
      call in the model file is a no-op — see the note after this file).
      Mutations therefore work off `receiver_*` and the delivery chain.
    - `Package.tracking` is a reverse OneToOne from Tracking; not
      writable here. Use the Tracking mutations module.

Ownership:
    - Caller must be the customer of the parent Delivery, the assigned
      provider, or staff.
    - Status transitions go through `UpdatePackageStatus`, which delegates
      to the tracking flow when a Tracking row exists.
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.package import PackageNode 
from graphq.transport.types.delivery import DeliveryNode

from transport.models.delivery.package import Package
from transport.models.delivery.delivery import Delivery


User = get_user_model()

_PACKAGE_TYPES = {c.value for c in Package.PackageType}
_PACKAGE_STATUSES = {c.value for c in Package.PackageStatus}
_WEIGHT_UNITS = {c.value for c in Package.WeightUnit}
_DIMENSION_UNITS = {c.value for c in Package.DimensionUnit}

_TERMINAL_STATUSES = {
    Package.PackageStatus.DELIVERED,
    Package.PackageStatus.RETURNED,
    Package.PackageStatus.CANCELLED,
}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_package(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid package_id.")
    qs = Package.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Package.DoesNotExist:
        raise GraphQLError("Package not found.")


def _resolve_delivery(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid delivery_id.")
    qs = Delivery.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Delivery.DoesNotExist:
        raise GraphQLError("Delivery not found.")


def _assert_can_manage(delivery, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if delivery.customer_id == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and delivery.provider_id == provider.pk:
        return
    raise GraphQLError("Not authorized to manage packages for this delivery.")


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


def _validate_weight(weight):
    if weight is None or weight <= 0:
        raise GraphQLError("weight must be greater than 0.")


def _validate_dimension(value, field):
    if value is None:
        return
    if value <= 0:
        raise GraphQLError(f"{field} must be greater than 0.")


def _validate_insurance(is_insured, insurance_value, declared_value):
    if is_insured and insurance_value is None:
        raise GraphQLError("insurance_value is required when is_insured is True.")
    if (
        is_insured
        and insurance_value is not None
        and declared_value is not None
        and insurance_value > declared_value
    ):
        raise GraphQLError("insurance_value cannot exceed declared_value.")


# =============================================================================
# Create
# =============================================================================

class CreatePackage(relay.ClientIDMutation):
    """Add a Package to a Delivery."""

    class Input:
        delivery_id = graphene.ID(required=True)

        tracking_number = graphene.String(required=True)
        name = graphene.String(required=True)
        description = graphene.String()
        package_type = graphene.String()

        weight = graphene.Decimal(required=True)
        weight_unit = graphene.String()

        length = graphene.Decimal()
        width = graphene.Decimal()
        height = graphene.Decimal()
        dimension_unit = graphene.String()

        declared_value = graphene.Decimal()
        currency = graphene.String()
        is_insured = graphene.Boolean()
        insurance_value = graphene.Decimal()

        requires_signature = graphene.Boolean()
        is_fragile = graphene.Boolean()
        is_perishable = graphene.Boolean()
        is_dangerous = graphene.Boolean()
        requires_refrigeration = graphene.Boolean()

        handling_instructions = graphene.String()
        temperature_min = graphene.Decimal()
        temperature_max = graphene.Decimal()

        receiver_name = graphene.String(required=True)
        receiver_phone = graphene.String(required=True)
        receiver_email = graphene.String()

        notes = graphene.String()

    package = graphene.Field(PackageNode)
    delivery = graphene.Field(DeliveryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_id, **input):
        me = info.context.user
        delivery = _resolve_delivery(delivery_id)
        _assert_can_manage(delivery, me)

        if delivery.status in ("completed", "cancelled") and not me.is_staff:
            raise GraphQLError(
                f"Cannot add a package to a delivery in status "
                f"'{delivery.status}'."
            )

        _validate_enum(input.get("package_type"), _PACKAGE_TYPES, "package_type")
        _validate_enum(input.get("weight_unit"), _WEIGHT_UNITS, "weight_unit")
        _validate_enum(input.get("dimension_unit"), _DIMENSION_UNITS, "dimension_unit")

        weight = _parse_decimal(input["weight"], "weight")
        _validate_weight(weight)

        length = _parse_decimal(input.get("length"), "length")
        width = _parse_decimal(input.get("width"), "width")
        height = _parse_decimal(input.get("height"), "height")
        _validate_dimension(length, "length")
        _validate_dimension(width, "width")
        _validate_dimension(height, "height")

        declared_value = _parse_decimal(input.get("declared_value"), "declared_value")
        insurance_value = _parse_decimal(input.get("insurance_value"), "insurance_value")
        _validate_insurance(
            bool(input.get("is_insured")), insurance_value, declared_value
        )

        temp_min = _parse_decimal(input.get("temperature_min"), "temperature_min")
        temp_max = _parse_decimal(input.get("temperature_max"), "temperature_max")
        if temp_min is not None and temp_max is not None and temp_min > temp_max:
            raise GraphQLError("temperature_min cannot exceed temperature_max.")

        tracking_number = (input["tracking_number"] or "").strip().upper()
        if not tracking_number:
            raise GraphQLError("tracking_number cannot be empty.")
        if Package.objects.filter(tracking_number=tracking_number).exists():
            raise GraphQLError(
                f"A package with tracking number '{tracking_number}' already exists."
            )

        payload = {
            "delivery": delivery,
            "tracking_number": tracking_number,
            "status": Package.PackageStatus.PENDING,
            "name": input["name"],
            "description": input.get("description") or "",
            "package_type": input.get("package_type") or Package.PackageType.PARCEL,
            "weight": weight,
            "weight_unit": input.get("weight_unit") or Package.WeightUnit.KG,
            "length": length,
            "width": width,
            "height": height,
            "dimension_unit": input.get("dimension_unit") or Package.DimensionUnit.CM,
            "declared_value": declared_value,
            "currency": (input.get("currency") or "USD").upper()[:3],
            "is_insured": bool(input.get("is_insured")),
            "insurance_value": insurance_value,
            "requires_signature": bool(input.get("requires_signature")),
            "is_fragile": bool(input.get("is_fragile")),
            "is_perishable": bool(input.get("is_perishable")),
            "is_dangerous": bool(input.get("is_dangerous")),
            "requires_refrigeration": bool(input.get("requires_refrigeration")),
            "handling_instructions": input.get("handling_instructions") or "",
            "temperature_min": temp_min,
            "temperature_max": temp_max,
            "receiver_name": input["receiver_name"],
            "receiver_phone": input["receiver_phone"],
            "receiver_email": input.get("receiver_email") or "",
            "notes": input.get("notes") or "",
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            package = Package(**payload)
            # save() calls full_clean() internally.
            package.save()
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            package=package,
            delivery=delivery,
            success=True,
            message="Package created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdatePackage(relay.ClientIDMutation):
    """
    Update a Package's metadata.

    `status` is NOT editable here — use `UpdatePackageStatus`.
    `tracking_number` is editable only by staff (it's an identifier
    referenced by couriers and customers).
    """

    class Input:
        package_id = graphene.ID(required=True)

        tracking_number = graphene.String()   # staff-only change
        name = graphene.String()
        description = graphene.String()
        package_type = graphene.String()

        weight = graphene.Decimal()
        weight_unit = graphene.String()

        length = graphene.Decimal()
        width = graphene.Decimal()
        height = graphene.Decimal()
        dimension_unit = graphene.String()

        declared_value = graphene.Decimal()
        currency = graphene.String()
        is_insured = graphene.Boolean()
        insurance_value = graphene.Decimal()

        requires_signature = graphene.Boolean()
        is_fragile = graphene.Boolean()
        is_perishable = graphene.Boolean()
        is_dangerous = graphene.Boolean()
        requires_refrigeration = graphene.Boolean()

        handling_instructions = graphene.String()
        temperature_min = graphene.Decimal()
        temperature_max = graphene.Decimal()

        receiver_name = graphene.String()
        receiver_phone = graphene.String()
        receiver_email = graphene.String()

        notes = graphene.String()

    package = graphene.Field(PackageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, package_id, **input):
        me = info.context.user
        package = _resolve_package(package_id, lock=True)
        _assert_can_manage(package.delivery, me)

        if package.status in _TERMINAL_STATUSES and not me.is_staff:
            raise GraphQLError(
                f"Cannot edit a package in terminal status '{package.status}'."
            )

        _validate_enum(input.get("package_type"), _PACKAGE_TYPES, "package_type")
        _validate_enum(input.get("weight_unit"), _WEIGHT_UNITS, "weight_unit")
        _validate_enum(input.get("dimension_unit"), _DIMENSION_UNITS, "dimension_unit")

        if input.get("tracking_number") and not me.is_staff:
            new_tn = input["tracking_number"].strip().upper()
            if new_tn != package.tracking_number:
                raise GraphQLError(
                    "Only staff may change an existing tracking number."
                )

        update_fields = []

        # tracking_number (staff)
        if input.get("tracking_number"):
            new_tn = input["tracking_number"].strip().upper()
            if new_tn != package.tracking_number:
                if Package.objects.filter(tracking_number=new_tn).exclude(
                    pk=package.pk
                ).exists():
                    raise GraphQLError(
                        f"Tracking number '{new_tn}' is already in use."
                    )
                package.tracking_number = new_tn
                update_fields.append("tracking_number")

        # scalar fields
        for field in (
            "name",
            "description",
            "package_type",
            "weight_unit",
            "dimension_unit",
            "currency",
            "requires_signature",
            "is_fragile",
            "is_perishable",
            "is_dangerous",
            "requires_refrigeration",
            "handling_instructions",
            "receiver_name",
            "receiver_phone",
            "receiver_email",
            "notes",
        ):
            if field in input and input[field] is not None:
                setattr(package, field, input[field])
                update_fields.append(field)

        # decimal fields
        for input_key, model_field in (
            ("weight", "weight"),
            ("length", "length"),
            ("width", "width"),
            ("height", "height"),
            ("declared_value", "declared_value"),
            ("insurance_value", "insurance_value"),
            ("temperature_min", "temperature_min"),
            ("temperature_max", "temperature_max"),
        ):
            if input_key in input and input[input_key] is not None:
                value = _parse_decimal(input[input_key], input_key)
                if model_field in ("weight", "length", "width", "height") and value <= 0:
                    raise GraphQLError(f"{model_field} must be greater than 0.")
                setattr(package, model_field, value)
                update_fields.append(model_field)

        # is_insured toggle — validate with the post-update values
        if "is_insured" in input and input["is_insured"] is not None:
            package.is_insured = bool(input["is_insured"])
            update_fields.append("is_insured")

        # temperature range
        if (
            package.temperature_min is not None
            and package.temperature_max is not None
            and package.temperature_min > package.temperature_max
        ):
            raise GraphQLError("temperature_min cannot exceed temperature_max.")

        _validate_insurance(
            package.is_insured, package.insurance_value, package.declared_value
        )

        if not update_fields:
            return cls(package=package, success=True, message="Nothing to update.")

        try:
            package.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        package.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            package=package,
            success=True,
            message="Package updated.",
        )


# =============================================================================
# Status transition
# =============================================================================

class UpdatePackageStatus(relay.ClientIDMutation):
    """
    Transition a Package's status.

    If a Tracking row exists for this package, the transition is routed
    through `Tracking.update_status()`, which creates a TrackingEvent
    and cascades to the parent Delivery when appropriate. Otherwise the
    status is set directly (useful for packages without tracking set up
    yet).

    Terminal transitions (DELIVERED / RETURNED / CANCELLED) are refused
    for non-staff once reached.
    """

    class Input:
        package_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        description = graphene.String()
        lat = graphene.Float()
        lng = graphene.Float()
        address = graphene.String()

    package = graphene.Field(PackageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, package_id, status, **input):
        me = info.context.user
        package = _resolve_package(package_id, lock=True)
        _assert_can_manage(package.delivery, me)

        _validate_enum(status, _PACKAGE_STATUSES, "status")

        if package.status in _TERMINAL_STATUSES and not me.is_staff:
            raise GraphQLError(
                f"Cannot change status from terminal state '{package.status}'."
            )

        if (input.get("lat") is None) ^ (input.get("lng") is None):
            raise GraphQLError("Provide both lat and lng, or neither.")

        # Route through Tracking if one exists.
        tracking = getattr(package, "tracking", None)
        if tracking is not None:
            # Tracking.Status has a superset of Package statuses. Map.
            _TRACKING_STATUS_MAP = {
                Package.PackageStatus.PENDING: "label_created",
                Package.PackageStatus.PICKED_UP: "picked_up",
                Package.PackageStatus.IN_TRANSIT: "in_transit",
                Package.PackageStatus.OUT_FOR_DELIVERY: "out_for_delivery",
                Package.PackageStatus.DELIVERED: "delivered",
                Package.PackageStatus.EXCEPTION: "exception",
                Package.PackageStatus.RETURNED: "returned",
                Package.PackageStatus.CANCELLED: "cancelled",
            }
            tracking_status = _TRACKING_STATUS_MAP.get(status)
            if tracking_status is None:
                raise GraphQLError(f"Cannot map package status '{status}' to tracking.")

            try:
                tracking.update_status(
                    new_status=tracking_status,
                    description=input.get("description"),
                    lat=input.get("lat"),
                    lng=input.get("lng"),
                    address=input.get("address"),
                )
            except (ValidationError, ValueError) as exc:
                raise GraphQLError(str(exc))

            package.refresh_from_db()
            return cls(
                package=package,
                success=True,
                message=f"Status updated via tracking to '{status}'.",
            )

        # No tracking — direct write.
        package.status = status
        try:
            package.save(update_fields=["status", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            package=package,
            success=True,
            message=f"Status set to '{status}'.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeletePackage(relay.ClientIDMutation):
    """
    Delete a Package.

    Customer of the parent delivery or staff. Refuses while the package
    is in transit or delivered — cancel via `UpdatePackageStatus` instead.
    """

    class Input:
        package_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, package_id):
        me = info.context.user
        package = _resolve_package(package_id, lock=True)
        _assert_can_manage(package.delivery, me)

        if package.status in {
            Package.PackageStatus.IN_TRANSIT,
            Package.PackageStatus.OUT_FOR_DELIVERY,
            Package.PackageStatus.DELIVERED,
        } and not me.is_staff:
            raise GraphQLError(
                f"Cannot delete a package in status '{package.status}'. "
                "Cancel it via update_package_status instead."
            )

        # Refuse if a Tracking row is linked — the FK cascades, silently
        # dropping the tracking history.
        if hasattr(package, "tracking"):
            raise GraphQLError(
                "Cannot delete a package with tracking history. "
                "Cancel it via update_package_status instead."
            )

        package.delete()
        return cls(success=True, message="Package deleted.")


# =============================================================================
# Registration
# =============================================================================

class PackageMutations(graphene.ObjectType):
    create_package = CreatePackage.Field()
    update_package = UpdatePackage.Field()
    update_package_status = UpdatePackageStatus.Field()
    delete_package = DeletePackage.Field()