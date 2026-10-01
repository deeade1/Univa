# apps/backend/graphq/transport/mutations/service_request.py
"""
ServiceRequest mutations.

Aligned against transport/models/core/service_request.py.

Key facts about the model that shape these mutations:

    - `pickup_location` and `dropoff_location` are FKs to `StopPoint`,
      not raw Point fields. The client sends lat/lng and we resolve or
      create a StopPoint.
    - There is no `pickup_address` / `dropoff_address` on ServiceRequest;
      those are properties of StopPoint.
    - There is no `scheduled_time`; the field is `scheduled_at`.
    - `save()` calls `full_clean()` internally and triggers dispatch on
      create. Mutations must not double-trigger dispatch.
    - Terminal statuses are 'completed' and 'cancelled'.
"""

from datetime import timedelta
from decimal import Decimal

import graphene
from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.service_request import ServiceRequestNode
from transport.models import ServiceRequest


User = get_user_model()

# Provider-visible status transitions. Status is a free string in the
# model but we constrain what a mutation may set.
_ALLOWED_STATUSES = {
    ServiceRequest.Status.REQUESTED,
    ServiceRequest.Status.ACCEPTED,
    ServiceRequest.Status.IN_PROGRESS,
    ServiceRequest.Status.SCHEDULED,
    ServiceRequest.Status.DEPARTED,
    ServiceRequest.Status.IN_TRANSIT,
    ServiceRequest.Status.ARRIVED,
    ServiceRequest.Status.COMPLETED,
    ServiceRequest.Status.CANCELLED,
}

_TERMINAL_STATUSES = {
    ServiceRequest.Status.COMPLETED,
    ServiceRequest.Status.CANCELLED,
}

_ALLOWED_SERVICE_TYPES = {
    ServiceRequest.ServiceType.TAXI,
    ServiceRequest.ServiceType.DELIVERY,
    ServiceRequest.ServiceType.SHARED,
    ServiceRequest.ServiceType.FOOD,
    ServiceRequest.ServiceType.CARGO,
    ServiceRequest.ServiceType.INTERSTATE,
}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_or_create_stop_point(lat, lng, *, address="", label=""):
    """
    Resolve an existing StopPoint at (lat, lng) or create one.

    `StopPoint` is assumed to have `coordinates` (PointField) and
    optionally `address` / `label`. Adjust the field names here if
    your StopPoint model differs.
    """
    from transport.models import StopPoint

    if lat is None or lng is None:
        return None

    if not (-90 <= lat <= 90):
        raise GraphQLError("Latitude must be between -90 and 90.")
    if not (-180 <= lng <= 180):
        raise GraphQLError("Longitude must be between -180 and 180.")

    point = Point(float(lng), float(lat), srid=4326)

    # Best-effort reuse: match within a tiny tolerance.
    existing = StopPoint.objects.filter(
        coordinates__distance_lte=(point, 0.0001)  # degrees, ~11m
    ).first()
    if existing:
        return existing

    create_kwargs = {"coordinates": point}
    # Only pass address/label if the StopPoint model actually has them.
    stop_field_names = {f.name for f in StopPoint._meta.get_fields()}
    if "address" in stop_field_names and address:
        create_kwargs["address"] = address
    if "label" in stop_field_names and label:
        create_kwargs["label"] = label

    return StopPoint.objects.create(**create_kwargs)


def _haversine_km(lat1, lng1, lat2, lng2):
    from math import radians, cos, sin, asin, sqrt

    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    dlon = lng2 - lng1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371


def _estimate_fare(service_type, input_data):
    """
    Cheap heuristic estimator. Replace with the real pricing service
    when available (`ServiceRequest.calculate_fare()` calls into
    `transport.services.base.ServiceFactory`).
    """
    base_fares = {
        ServiceRequest.ServiceType.TAXI: 15.00,
        ServiceRequest.ServiceType.DELIVERY: 8.00,
        ServiceRequest.ServiceType.SHARED: 5.00,
        ServiceRequest.ServiceType.FOOD: 6.00,
        ServiceRequest.ServiceType.CARGO: 20.00,
        ServiceRequest.ServiceType.INTERSTATE: 50.00,
    }
    fare = base_fares.get(service_type, 10.00)
    wait_minutes = 5

    if input_data.get("dropoff_lat") and input_data.get("dropoff_lng"):
        distance_km = _haversine_km(
            input_data["pickup_lat"],
            input_data["pickup_lng"],
            input_data["dropoff_lat"],
            input_data["dropoff_lng"],
        )
        fare += distance_km * 0.5

        if distance_km > 20:
            wait_minutes = 15
        elif distance_km > 10:
            wait_minutes = 10
    else:
        distance_km = None

    if service_type == ServiceRequest.ServiceType.TAXI:
        if input_data.get("rider_count", 1) > 3:
            fare *= 1.2
        if input_data.get("special_requests"):
            fare += 2.00

    elif service_type == ServiceRequest.ServiceType.DELIVERY:
        weight = input_data.get("package_weight", 0.1)
        fare += weight * 0.5
        if input_data.get("requires_signature"):
            fare += 3.00
        if input_data.get("insurance_required"):
            fare += 5.00

    if input_data.get("vehicle_preference") in {"premium", "luxury", "suv"}:
        fare *= 1.3

    return {
        "estimated_fare": round(fare, 2),
        "estimated_wait_time": wait_minutes,
        "distance_km": distance_km,
    }


# =============================================================================
# Create
# =============================================================================

class CreateRequestService(relay.ClientIDMutation):
    """Create a new ServiceRequest (ride, delivery, or shared)."""

    class Input:
        service_type = graphene.String(required=True)

        pickup_lat = graphene.Float(required=True)
        pickup_lng = graphene.Float(required=True)
        pickup_address = graphene.String()

        dropoff_lat = graphene.Float()
        dropoff_lng = graphene.Float()
        dropoff_address = graphene.String()

        # Trip-specific
        rider_count = graphene.Int()
        special_requests = graphene.String()

        # Delivery-specific
        package_description = graphene.String()
        package_weight = graphene.Float()
        package_dimensions = graphene.JSONString()
        recipient_name = graphene.String()
        recipient_phone = graphene.String()
        requires_signature = graphene.Boolean()
        insurance_required = graphene.Boolean()

        # Common
        scheduled_at = graphene.DateTime()
        vehicle_preference = graphene.String()
        payment_method = graphene.String()
        promo_code = graphene.String()

    service_request = graphene.Field(ServiceRequestNode)
    estimated_fare = graphene.Decimal()
    estimated_wait_time = graphene.Int()
    success = graphene.Boolean()
    message = graphene.String()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @classmethod
    def validate_user_can_request(cls, user):
        if not user.is_active:
            raise GraphQLError("User account is not active.")

        if hasattr(user, "has_outstanding_balance") and user.has_outstanding_balance():
            raise GraphQLError(
                "Please clear outstanding balance before requesting services."
            )

        recent_requests = ServiceRequest.objects.filter(
            customer=user,
            created_at__gte=timezone.now() - timedelta(hours=1),
        ).count()
        if recent_requests >= 10:
            raise GraphQLError("Too many requests. Please try again later.")

    @classmethod
    def validate_service_type(cls, service_type, data):
        if service_type not in _ALLOWED_SERVICE_TYPES:
            raise GraphQLError(
                f"Unsupported service type: {service_type}."
            )

        if service_type == ServiceRequest.ServiceType.TAXI:
            rider_count = data.get("rider_count") or 1
            if not 1 <= rider_count <= 10:
                raise GraphQLError("rider_count must be between 1 and 10.")

        elif service_type == ServiceRequest.ServiceType.DELIVERY:
            if not data.get("package_description"):
                raise GraphQLError(
                    "package_description is required for deliveries."
                )
            weight = data.get("package_weight") or 0.1
            if weight <= 0:
                raise GraphQLError("package_weight must be greater than 0.")
            if weight > 50:
                raise GraphQLError("package_weight cannot exceed 50kg.")

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    @classmethod
    def _build_service_specific_data(cls, service_type, data):
        """Return the value to store on the appropriate JSON field."""
        if service_type == ServiceRequest.ServiceType.DELIVERY:
            return {
                "package_description": data.get("package_description", ""),
                "package_weight": float(data.get("package_weight") or 0.1),
                "package_dimensions": data.get("package_dimensions") or {},
                "recipient_name": data.get("recipient_name", "") or "",
                "recipient_phone": data.get("recipient_phone", "") or "",
                "requires_signature": bool(data.get("requires_signature")),
                "insurance_required": bool(data.get("insurance_required")),
            }

        if service_type in {
            ServiceRequest.ServiceType.SHARED,
            ServiceRequest.ServiceType.INTERSTATE,
        }:
            return {
                "rider_count": data.get("rider_count") or 1,
                "shared": True,
                "available_seats": data.get("rider_count") or 1,
            }

        if service_type in {
            ServiceRequest.ServiceType.TAXI,
        }:
            return {
                "rider_count": data.get("rider_count") or 1,
                "special_requests": data.get("special_requests", "") or "",
            }

        # cargo / food — treat as delivery-like
        return {
            "rider_count": data.get("rider_count") or 1,
        }

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            cls.validate_user_can_request(user)

            service_type = input["service_type"]
            cls.validate_service_type(service_type, input)

            # Resolve / create StopPoints
            pickup_stop = _resolve_or_create_stop_point(
                input["pickup_lat"],
                input["pickup_lng"],
                address=input.get("pickup_address", "") or "",
                label="pickup",
            )

            dropoff_stop = None
            if input.get("dropoff_lat") is not None and input.get("dropoff_lng") is not None:
                dropoff_stop = _resolve_or_create_stop_point(
                    input["dropoff_lat"],
                    input["dropoff_lng"],
                    address=input.get("dropoff_address", "") or "",
                    label="dropoff",
                )

            # Estimate fare
            fare_info = _estimate_fare(service_type, input)
            estimated_fare = Decimal(str(fare_info["estimated_fare"]))

            # Compute estimated distance / duration from the two coords
            estimated_distance = fare_info.get("distance_km")
            estimated_duration = None
            if estimated_distance is not None:
                estimated_duration = max(1, int(estimated_distance / 40 * 60))

            # Base ServiceRequest payload
            payload = {
                "customer": user,
                "service_type": service_type,
                "status": (
                    ServiceRequest.Status.SCHEDULED
                    if input.get("scheduled_at")
                    else ServiceRequest.Status.REQUESTED
                ),
                "pickup_location": pickup_stop,
                "dropoff_location": dropoff_stop,
                "estimated_distance": estimated_distance,
                "estimated_duration": estimated_duration,
                "base_fare": estimated_fare,
                "total_fare": estimated_fare,
                "scheduled_at": input.get("scheduled_at"),
                "insurance_required": bool(input.get("insurance_required")),
            }

            # Strip None so model defaults apply
            payload = {k: v for k, v in payload.items() if v is not None}

            # Service-type-specific JSON
            service_data = cls._build_service_specific_data(service_type, input)

            if service_type in {
                ServiceRequest.ServiceType.TAXI,
                ServiceRequest.ServiceType.SHARED,
                ServiceRequest.ServiceType.INTERSTATE,
            }:
                payload["trip_data"] = service_data
                if service_type == ServiceRequest.ServiceType.SHARED:
                    payload["shared_trip_data"] = service_data
            else:
                payload["delivery_data"] = service_data

            # Create. NOTE: ServiceRequest.save() calls full_clean() and
            # runs dispatch on create — do not duplicate that here.
            try:
                request = ServiceRequest.objects.create(**payload)
            except ValidationError as exc:
                raise GraphQLError(f"Validation failed: {exc.message_dict}")

            # Trigger subscription if available
            try:
                from graphq.transport.subscriptions import (
                    ServiceRequestUpdatedSubscription,
                )
                ServiceRequestUpdatedSubscription.trigger(request)
            except ImportError:
                pass
            except Exception:
                # Never let a subscription failure break the mutation.
                pass

            return CreateRequestService(
                service_request=request,
                estimated_fare=estimated_fare,
                estimated_wait_time=fare_info["estimated_wait_time"],
                success=True,
                message="Service request created.",
            )

        except GraphQLError:
            raise
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except Exception as exc:
            raise GraphQLError(f"Failed to create service request: {exc}")


# =============================================================================
# Update (metadata / fare / schedule)
# =============================================================================

class UpdateServiceRequest(relay.ClientIDMutation):
    """
    Update mutable, non-status fields on a ServiceRequest.

    Allowed for:
        - the customer who owns the request, while it is not terminal
        - staff, always

    Only fields explicitly provided in the input are written.
    Pickup / dropoff locations are intentionally NOT updatable here —
    changing them mid-lifecycle invalidates dispatch, routing, and fare.
    Use the create flow or a dedicated re-route mutation instead.
    """

    class Input:
        service_request_id = graphene.ID(required=True)

        # Timing
        scheduled_at = graphene.DateTime()

        # Luggage / capacity
        luggage_capacity_kg = graphene.Int()
        luggage_price_per_kg = graphene.Decimal()

        # Pricing overrides (typically admin-only in production)
        base_fare = graphene.Decimal()
        distance_fare = graphene.Decimal()
        time_fare = graphene.Decimal()
        total_fare = graphene.Decimal()

        # Emergency contact
        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        # Insurance
        insurance_required = graphene.Boolean()
        insurance_details = graphene.JSONString()

        # Recurrence
        is_recurring_daily = graphene.Boolean()

        # JSON blobs (partial merge)
        metadata = graphene.JSONString()
        trip_data = graphene.JSONString()
        delivery_data = graphene.JSONString()
        shared_trip_data = graphene.JSONString()
        stopovers = graphene.List(graphene.JSONString)
        seat_map = graphene.JSONString()

    service_request = graphene.Field(ServiceRequestNode)
    success = graphene.Boolean()
    message = graphene.String()

    # Fields that only staff may change.
    _STAFF_ONLY_FIELDS = {
        "base_fare",
        "distance_fare",
        "time_fare",
        "total_fare",
    }

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_request_id, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(service_request_id)
        except Exception:
            raise GraphQLError("Invalid service_request_id.")

        try:
            request = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            raise GraphQLError("Service request not found.")

        # Ownership check
        if not user.is_staff and request.customer_id != user.pk:
            raise GraphQLError("Not authorized to update this request.")

        # Terminal-state guard (staff may still edit for audit purposes)
        if request.status in _TERMINAL_STATUSES and not user.is_staff:
            raise GraphQLError(
                f"Cannot update a request in terminal state '{request.status}'."
            )

        # Staff-only field guard
        if not user.is_staff:
            touched_staff_fields = [
                f for f in cls._STAFF_ONLY_FIELDS if input.get(f) is not None
            ]
            if touched_staff_fields:
                raise GraphQLError(
                    "Only staff may update fare fields: "
                    + ", ".join(sorted(touched_staff_fields))
                )

        update_fields = []

        # -------- Scalar fields (direct assignment) --------
        scalar_map = {
            "scheduled_at": "scheduled_at",
            "luggage_capacity_kg": "luggage_capacity_kg",
            "luggage_price_per_kg": "luggage_price_per_kg",
            "base_fare": "base_fare",
            "distance_fare": "distance_fare",
            "time_fare": "time_fare",
            "total_fare": "total_fare",
            "emergency_contact_name": "emergency_contact_name",
            "emergency_contact_phone": "emergency_contact_phone",
            "insurance_required": "insurance_required",
            "is_recurring_daily": "is_recurring_daily",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(request, model_field, input[input_key])
                update_fields.append(model_field)

        # -------- JSON blobs --------
        # For `insurance_details` and the `*_data` fields, merge rather
        # than replace when the client sends a partial dict, so callers
        # don't accidentally drop existing keys.
        json_merge_map = {
            "insurance_details": "insurance_details",
            "trip_data": "trip_data",
            "delivery_data": "delivery_data",
            "shared_trip_data": "shared_trip_data",
            "seat_map": "seat_map",
            "metadata": "metadata",
        }
        for input_key, model_field in json_merge_map.items():
            if input_key not in input or input[input_key] is None:
                continue
            incoming = input[input_key]
            if not isinstance(incoming, dict):
                raise GraphQLError(f"{input_key} must be an object.")
            current = getattr(request, model_field) or {}
            merged = {**current, **incoming}
            setattr(request, model_field, merged)
            update_fields.append(model_field)

        # -------- stopovers (list) --------
        if "stopovers" in input and input["stopovers"] is not None:
            stopovers = input["stopovers"]
            if not isinstance(stopovers, list):
                raise GraphQLError("stopovers must be a list.")
            request.stopovers = stopovers
            update_fields.append("stopovers")

        if not update_fields:
            return cls(
                service_request=request,
                success=True,
                message="Nothing to update.",
            )

        # `save()` calls full_clean(); pass update_fields for efficiency.
        # We also need updated_at bumped, which auto_now handles only if
        # the field is included in update_fields — so add it explicitly.
        update_fields = sorted(set(update_fields + ["updated_at"]))

        try:
            request.save(update_fields=update_fields)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Fire subscription (best-effort)
        try:
            from graphq.transport.subscriptions import (
                ServiceRequestUpdatedSubscription,
            )
            ServiceRequestUpdatedSubscription.trigger(request)
        except ImportError:
            pass
        except Exception:
            pass

        return UpdateServiceRequest(
            service_request=request,
            success=True,
            message="Service request updated.",
        )


# =============================================================================
# Cancel (soft delete — preferred)
# =============================================================================

class CancelServiceRequest(relay.ClientIDMutation):
    """
    Soft-cancel a ServiceRequest.

    Sets status to 'cancelled', records the reason in `metadata`, and
    freezes the row from further non-staff edits. This is the correct
    "delete" path for a service request in almost every case — it
    preserves audit history and any downstream references (bookings,
    invoices, delivery packages, tracking rows).

    Allowed for:
        - the customer who owns the request
        - the assigned provider
        - staff
    """

    class Input:
        service_request_id = graphene.ID(required=True)
        reason = graphene.String()

    service_request = graphene.Field(ServiceRequestNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_request_id, reason=None):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(service_request_id)
        except Exception:
            raise GraphQLError("Invalid service_request_id.")

        try:
            request = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            raise GraphQLError("Service request not found.")

        # Ownership check
        is_owner = request.customer_id == user.pk
        is_provider = (
            request.provider_id
            and getattr(user, "service_provider", None)
            and user.service_provider.pk == request.provider_id
        )
        if not (is_owner or is_provider or user.is_staff):
            raise GraphQLError("Not authorized to cancel this request.")

        if request.status == ServiceRequest.Status.CANCELLED:
            return cls(
                service_request=request,
                success=True,
                message="Request is already cancelled.",
            )

        if request.status == ServiceRequest.Status.COMPLETED:
            raise GraphQLError("Cannot cancel a completed request.")

        old_status = request.status
        request.status = ServiceRequest.Status.CANCELLED

        metadata = dict(request.metadata or {})
        metadata["cancellation"] = {
            "reason": reason or "",
            "cancelled_at": timezone.now().isoformat(),
            "cancelled_by_id": user.pk,
            "previous_status": old_status,
        }
        request.metadata = metadata

        try:
            request.save(update_fields=["status", "metadata", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Fire subscription (best-effort)
        try:
            from graphq.transport.subscriptions import (
                ServiceRequestUpdatedSubscription,
            )
            ServiceRequestUpdatedSubscription.trigger(request)
        except ImportError:
            pass
        except Exception:
            pass

        return CancelServiceRequest(
            service_request=request,
            success=True,
            message="Service request cancelled.",
        )


# =============================================================================
# Delete (hard)
# =============================================================================

class DeleteServiceRequest(relay.ClientIDMutation):
    """
    Hard-delete a ServiceRequest.

    This is destructive and irreversible. It is permitted only when:
        - the caller is staff, OR
        - the caller owns the request AND the request is already in a
          terminal state ('completed' or 'cancelled')

    Even then, consider using `cancel_service_request` instead — most
    downstream rows (invoices, bookings, delivery packages, tracking,
    ratings) have `on_delete=PROTECT` or `CASCADE` and will either block
    this delete or disappear with it.
    """

    class Input:
        service_request_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_request_id):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(service_request_id)
        except Exception:
            raise GraphQLError("Invalid service_request_id.")

        try:
            request = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            raise GraphQLError("Service request not found.")

        is_owner = request.customer_id == user.pk

        if not user.is_staff:
            if not is_owner:
                raise GraphQLError("Not authorized to delete this request.")
            if request.status not in _TERMINAL_STATUSES:
                raise GraphQLError(
                    "Cannot delete an active request. Cancel it first."
                )

        # Optional safety net: surface a friendly error before the DB
        # raises ProtectedError from a downstream FK.
        try:
            request.delete()
        except Exception as exc:
            raise GraphQLError(
                f"Delete blocked — request has related records: {exc}"
            )

        return DeleteServiceRequest(success=True, message="Service request deleted.")



# =============================================================================
# Update status
# =============================================================================

class UpdateServiceRequestStatus(relay.ClientIDMutation):
    """Update the status of an existing ServiceRequest."""

    class Input:
        service_request_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        cancellation_reason = graphene.String()

    service_request = graphene.Field(ServiceRequestNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def has_permission(cls, user, request):
        """
        Customer: can cancel or complete their own request.
        Assigned provider: can move through the operational lifecycle.
        Staff: anything.
        """
        if user.is_staff:
            return True

        if user.pk == request.customer_id:
            return True

        if request.provider_id and getattr(user, "service_provider", None):
            if user.service_provider.pk == request.provider_id:
                return True

        return False

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, service_request_id, status, cancellation_reason=None
    ):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        if status not in _ALLOWED_STATUSES:
            raise GraphQLError(f"Invalid status: {status}.")

        try:
            _, pk = from_global_id(service_request_id)
        except Exception:
            raise GraphQLError("Invalid service_request_id.")

        try:
            request = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            raise GraphQLError("Service request not found.")

        if request.status in _TERMINAL_STATUSES and status != request.status:
            raise GraphQLError(
                f"Cannot change status from terminal state '{request.status}'."
            )

        if not cls.has_permission(user, request):
            raise GraphQLError("Permission denied.")

        old_status = request.status
        request.status = status

        # Record the cancellation reason in metadata (no dedicated field).
        if status == ServiceRequest.Status.CANCELLED and cancellation_reason:
            metadata = dict(request.metadata or {})
            metadata["cancellation_reason"] = cancellation_reason
            metadata["cancelled_at"] = timezone.now().isoformat()
            request.metadata = metadata

        try:
            # Model.save() will set started_at / completed_at via clean().
            request.save()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Trigger subscriptions if available.
        try:
            from graphq.transport.subscriptions import (
                ServiceRequestUpdatedSubscription,
            )
            ServiceRequestUpdatedSubscription.trigger(request)
        except ImportError:
            pass
        except Exception:
            pass

        return UpdateServiceRequestStatus(
            service_request=request,
            success=True,
            message=f"Status updated: {old_status} -> {status}.",
        )



class ServiceRequestMutations(graphene.ObjectType):
    create_request_service = CreateRequestService.Field()
    update_service_request = UpdateServiceRequest.Field()
    update_service_request_status = UpdateServiceRequestStatus.Field()
    cancel_service_request = CancelServiceRequest.Field()
    delete_service_request = DeleteServiceRequest.Field()