# apps/backend/graphq/transport/mutations/delivery.py
"""
Delivery mutations.

`Delivery` is a proxy over `ServiceRequest`. Creation must go through
`Delivery.objects.create_delivery(...)`, not `Delivery.objects.create(...)`
— the manager is what wires `service_type='delivery'` and normalizes
`delivery_data`.

Ownership rules enforced here:
    - The customer who owns the underlying ServiceRequest may manage
      the delivery and its packages while status is still mutable.
    - Staff may manage any delivery.
    - Terminal statuses (completed / cancelled) reject further edits.
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphene import relay
from graphq.transport.types.delivery import  DeliveryNode
from graphq.transport.types.package import PackageNode
from transport.models.core.service_request import ServiceRequest
from transport.models.delivery.delivery import Delivery
from transport.models.delivery.package import Package


# =============================================================================
# Terminal statuses — no edits allowed once reached
# =============================================================================

_TERMINAL_STATUSES = {"completed", "cancelled"}


# =============================================================================
# Input types
# =============================================================================

class GeoPointInput(graphene.InputObjectType):
    """Lat/lng pair. SRID is assumed 4326."""
    lat = graphene.Float(required=True)
    lng = graphene.Float(required=True)


class PackageInput(graphene.InputObjectType):
    """Writable fields for a Package row."""

    name = graphene.String(required=True)
    package_type = graphene.String(default_value="parcel")
    weight = graphene.Float(required=True)
    weight_unit = graphene.String(default_value="kg")
    length = graphene.Float()
    width = graphene.Float()
    height = graphene.Float()
    dimension_unit = graphene.String(default_value="cm")

    declared_value = graphene.Float()
    is_insured = graphene.Boolean()
    insurance_value = graphene.Float()

    is_fragile = graphene.Boolean()
    is_perishable = graphene.Boolean()
    is_dangerous = graphene.Boolean()
    requires_signature = graphene.Boolean()
    requires_refrigeration = graphene.Boolean()

    priority = graphene.String(default_value="standard")

    sender_name = graphene.String(required=True)
    sender_phone = graphene.String(required=True)
    sender_email = graphene.String()

    receiver_name = graphene.String(required=True)
    receiver_phone = graphene.String(required=True)
    receiver_email = graphene.String()

    tracking_number = graphene.String()
    notes = graphene.String()

    metadata = graphene.JSONString()


class DeliveryCreateInput(graphene.InputObjectType):
    """Fields used when creating a Delivery (i.e. a ServiceRequest)."""

    pickup_location = GeoPointInput(required=True)
    dropoff_location = GeoPointInput(required=True)

    pickup_address = graphene.String()
    dropoff_address = graphene.String()

    scheduled_pickup_time = graphene.DateTime()
    estimated_arrival_time = graphene.DateTime()

    surge_multiplier = graphene.Float(default_value=1.0)

    # Optional initial packages
    packages = graphene.List(PackageInput)

    # Free-form extras passed through to ServiceRequest
    metadata = graphene.JSONString()


class DeliveryUpdateInput(graphene.InputObjectType):
    """Partial update on mutable delivery-level fields."""

    pickup_location = GeoPointInput()
    dropoff_location = GeoPointInput()
    pickup_address = graphene.String()
    dropoff_address = graphene.String()

    scheduled_pickup_time = graphene.DateTime()
    estimated_arrival_time = graphene.DateTime()

    surge_multiplier = graphene.Float()

    metadata = graphene.JSONString()


class PackageUpdateInput(graphene.InputObjectType):
    """Partial update on a Package row."""

    name = graphene.String()
    package_type = graphene.String()
    weight = graphene.Float()
    weight_unit = graphene.String()
    length = graphene.Float()
    width = graphene.Float()
    height = graphene.Float()
    dimension_unit = graphene.String()

    declared_value = graphene.Float()
    is_insured = graphene.Boolean()
    insurance_value = graphene.Float()

    is_fragile = graphene.Boolean()
    is_perishable = graphene.Boolean()
    is_dangerous = graphene.Boolean()
    requires_signature = graphene.Boolean()
    requires_refrigeration = graphene.Boolean()

    priority = graphene.String()

    sender_name = graphene.String()
    sender_phone = graphene.String()
    sender_email = graphene.String()

    receiver_name = graphene.String()
    receiver_phone = graphene.String()
    receiver_email = graphene.String()

    status = graphene.String()
    notes = graphene.String()
    metadata = graphene.JSONString()


# =============================================================================
# Helpers
# =============================================================================

def _point_from_input(payload):
    """Convert GeoPointInput into a GEOS Point (SRID 4326)."""
    if payload is None:
        return None
    return Point(payload.lng, payload.lat, srid=4326)


def _resolve_delivery(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid delivery id.")

    qs = Delivery.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Delivery.DoesNotExist:
        raise GraphQLError("Delivery not found.")


def _resolve_package(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid package id.")

    qs = Package.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Package.DoesNotExist:
        raise GraphQLError("Package not found.")


def _assert_can_edit(delivery, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if delivery.customer_id != user.pk and not user.is_staff:
        raise GraphQLError("Not authorized to manage this delivery.")
    if delivery.status in _TERMINAL_STATUSES:
        raise GraphQLError(
            f"Cannot modify a delivery with status '{delivery.status}'."
        )


def _apply_package_input(package, data, *, partial):
    """Write provided keys onto a Package instance."""
    field_map = {
        "name": "name",
        "package_type": "package_type",
        "weight": "weight",
        "weight_unit": "weight_unit",
        "length": "length",
        "width": "width",
        "height": "height",
        "dimension_unit": "dimension_unit",
        "declared_value": "declared_value",
        "is_insured": "is_insured",
        "insurance_value": "insurance_value",
        "is_fragile": "is_fragile",
        "is_perishable": "is_perishable",
        "is_dangerous": "is_dangerous",
        "requires_signature": "requires_signature",
        "requires_refrigeration": "requires_refrigeration",
        "priority": "priority",
        "sender_name": "sender_name",
        "sender_phone": "sender_phone",
        "sender_email": "sender_email",
        "receiver_name": "receiver_name",
        "receiver_phone": "receiver_phone",
        "receiver_email": "receiver_email",
        "tracking_number": "tracking_number",
        "status": "status",
        "notes": "notes",
        "metadata": "metadata",
    }

    for input_key, model_field in field_map.items():
        if input_key not in data:
            continue
        value = data[input_key]
        if value is None and partial:
            continue
        setattr(package, model_field, value)


# =============================================================================
# Create Delivery
# =============================================================================

class CreateDelivery(relay.ClientIDMutation):
    """
    Create a Delivery (and its underlying ServiceRequest).

    Optionally seeds it with one or more packages in the same
    transaction.
    """

    class Input:
        delivery_data = DeliveryCreateInput(required=True)

    delivery = graphene.Field(DeliveryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_data):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        pickup = _point_from_input(delivery_data.get("pickup_location"))
        dropoff = _point_from_input(delivery_data.get("dropoff_location"))
        if pickup is None or dropoff is None:
            raise GraphQLError("pickup_location and dropoff_location are required.")

        surge = delivery_data.get("surge_multiplier", 1.0)
        try:
            Decimal(str(surge))
        except (InvalidOperation, TypeError):
            raise GraphQLError("surge_multiplier must be a valid decimal.")

        # ServiceRequest manager kwargs
        service_kwargs = {
            "customer": user,
            "pickup_location": pickup,
            "dropoff_location": dropoff,
            "pickup_address": delivery_data.get("pickup_address", "") or "",
            "dropoff_address": delivery_data.get("dropoff_address", "") or "",
            "scheduled_pickup_time": delivery_data.get("scheduled_pickup_time"),
            "estimated_arrival_time": delivery_data.get("estimated_arrival_time"),
            "surge_multiplier": surge,
            "metadata": delivery_data.get("metadata") or {},
        }

        # Drop Nones so ServiceRequest defaults apply
        service_kwargs = {k: v for k, v in service_kwargs.items() if v is not None}

        try:
            delivery = Delivery.objects.create_delivery(**service_kwargs)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except Exception as exc:
            raise GraphQLError(f"Delivery creation failed: {exc}")

        # Optional initial packages
        packages_input = delivery_data.get("packages") or []
        if packages_input:
            try:
                package_dicts = [
                    {k: v for k, v in pkg.items() if v is not None}
                    for pkg in packages_input
                ]
                delivery.add_packages(package_dicts)
            except ValueError as exc:
                # Roll back the outer transaction so we don't leave a
                # half-created delivery behind.
                raise GraphQLError(f"Package creation failed: {exc}")
            except ValidationError as exc:
                raise GraphQLError(f"Package validation failed: {exc}")

        return cls(
            delivery=delivery,
            success=True,
            message="Delivery created.",
        )


# =============================================================================
# Update Delivery
# =============================================================================

class UpdateDelivery(relay.ClientIDMutation):
    """Update mutable, delivery-level fields (not packages)."""

    class Input:
        delivery_id = graphene.ID(required=True)
        delivery_data = DeliveryUpdateInput(required=True)

    delivery = graphene.Field(DeliveryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_id, delivery_data):
        user = info.context.user
        delivery = _resolve_delivery(delivery_id, lock=True)
        _assert_can_edit(delivery, user)

        update_fields = []

        simple_map = {
            "pickup_address": "pickup_address",
            "dropoff_address": "dropoff_address",
            "scheduled_pickup_time": "scheduled_pickup_time",
            "estimated_arrival_time": "estimated_arrival_time",
            "metadata": "metadata",
        }

        for input_key, model_field in simple_map.items():
            if input_key in delivery_data and delivery_data[input_key] is not None:
                setattr(delivery, model_field, delivery_data[input_key])
                update_fields.append(model_field)

        if "pickup_location" in delivery_data and delivery_data["pickup_location"]:
            delivery.pickup_location = _point_from_input(delivery_data["pickup_location"])
            update_fields.append("pickup_location")

        if "dropoff_location" in delivery_data and delivery_data["dropoff_location"]:
            delivery.dropoff_location = _point_from_input(delivery_data["dropoff_location"])
            update_fields.append("dropoff_location")

        if "surge_multiplier" in delivery_data and delivery_data["surge_multiplier"] is not None:
            # Property setter writes into delivery_data JSON
            try:
                delivery.surge_multiplier = Decimal(str(delivery_data["surge_multiplier"]))
            except (InvalidOperation, TypeError):
                raise GraphQLError("surge_multiplier must be a valid decimal.")
            # The save() override re-serializes _delivery_data for us.
            update_fields.append("delivery_data")

        if not update_fields:
            return cls(
                delivery=delivery,
                success=True,
                message="Nothing to update.",
            )

        try:
            delivery.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        delivery.save(update_fields=list(set(update_fields)))

        return cls(
            delivery=delivery,
            success=True,
            message="Delivery updated.",
        )


# =============================================================================
# Add / Update / Remove Package
# =============================================================================

class AddPackageToDelivery(relay.ClientIDMutation):
    """Add a single package to an existing delivery."""

    class Input:
        delivery_id = graphene.ID(required=True)
        package_data = PackageInput(required=True)

    delivery = graphene.Field(DeliveryNode)
    package = graphene.Field(PackageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_id, package_data):
        user = info.context.user
        delivery = _resolve_delivery(delivery_id, lock=True)
        _assert_can_edit(delivery, user)

        data = {k: v for k, v in package_data.items() if v is not None}
        try:
            package = delivery.add_package(**data)
        except ValueError as exc:
            raise GraphQLError(str(exc))
        except ValidationError as exc:
            raise GraphQLError(f"Package validation failed: {exc.message_dict}")

        return cls(
            delivery=delivery,
            package=package,
            success=True,
            message="Package added.",
        )


class UpdatePackage(relay.ClientIDMutation):
    """Update a single package. Ownership via its parent delivery."""

    class Input:
        package_id = graphene.ID(required=True)
        package_data = PackageUpdateInput(required=True)

    package = graphene.Field(PackageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, package_id, package_data):
        user = info.context.user
        package = _resolve_package(package_id, lock=True)
        delivery = package.delivery
        _assert_can_edit(delivery, user)

        _apply_package_input(package, package_data, partial=True)

        try:
            package.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        package.save()

        return cls(
            package=package,
            success=True,
            message="Package updated.",
        )


class RemovePackageFromDelivery(relay.ClientIDMutation):
    """Remove a package from its delivery."""

    class Input:
        package_id = graphene.ID(required=True)

    delivery = graphene.Field(DeliveryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, package_id):
        user = info.context.user
        package = _resolve_package(package_id, lock=True)
        delivery = _resolve_delivery(str(package.delivery_id), lock=True)
        _assert_can_edit(delivery, user)

        package.delete()

        return cls(
            delivery=delivery,
            success=True,
            message="Package removed.",
        )


# =============================================================================
# Cancel / Delete
# =============================================================================

class CancelDelivery(relay.ClientIDMutation):
    """
    Cancel a delivery and all its packages.

    Uses the model's `cancel_delivery(reason)` so `delivery_data` is
    updated consistently and packages are cascaded to 'cancelled'.
    """

    class Input:
        delivery_id = graphene.ID(required=True)
        reason = graphene.String(default_value="")

    delivery = graphene.Field(DeliveryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_id, reason=""):
        user = info.context.user
        delivery = _resolve_delivery(delivery_id, lock=True)

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        if delivery.customer_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to cancel this delivery.")

        try:
            delivery.cancel_delivery(reason=reason or "")
        except ValueError as exc:
            raise GraphQLError(str(exc))

        return cls(
            delivery=delivery,
            success=True,
            message="Delivery cancelled.",
        )


class DeleteDelivery(relay.ClientIDMutation):
    """
    Delete a Delivery.

    This deletes the underlying ServiceRequest row (proxy — no separate
    table). Refuses while the delivery is in an active state; cancel it
    first.
    """

    class Input:
        delivery_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, delivery_id):
        user = info.context.user
        delivery = _resolve_delivery(delivery_id, lock=True)

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        if delivery.customer_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to delete this delivery.")

        if delivery.status not in _TERMINAL_STATUSES:
            raise GraphQLError(
                "Cannot delete an active delivery. Cancel it first."
            )

        delivery.delete()

        return cls(success=True, message="Delivery deleted.")


# =============================================================================
# Registration
# =============================================================================

class DeliveryMutations(graphene.ObjectType):
    create_delivery = CreateDelivery.Field()
    update_delivery = UpdateDelivery.Field()
    add_package_to_delivery = AddPackageToDelivery.Field()
    update_package = UpdatePackage.Field()
    remove_package_from_delivery = RemovePackageFromDelivery.Field()
    cancel_delivery = CancelDelivery.Field()
    delete_delivery = DeleteDelivery.Field()