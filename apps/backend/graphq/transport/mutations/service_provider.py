# apps/backend/graphq/transport/mutations/service_provider.py
"""
ServiceProviderProfile mutations.

Model facts that shape these mutations:
    - `user` is OneToOneField → one profile per user.
    - `rating`, `total_ratings`, `total_services`, `total_earnings` are
      denormalized aggregates maintained by service-completion flows and
      `update_rating()`. They are NOT client-writable.
    - `is_verified` is an audit flag — staff-only to change.
    - `last_active` is `auto_now=True`; mutations can't set it.
    - `ProviderType.CHOICES` and `LicenseType.choices` are the enums.

Ownership rules:
    - Create: any authenticated user for themselves; staff may create on
      behalf of another user.
    - Update: owner or staff; `is_verified` and `current_service` are
      staff-only.
    - Delete: owner or staff. Refuses if a current_service is assigned.
    - Availability / online toggles: owner or staff.
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphene import relay

from graphq.transport.types.service_provider import ServiceProviderProfileNode
from graphq.accounts.types.user import UserNode

from transport.constants import ProviderType
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.core.service_request import ServiceRequest


User = get_user_model()

_VALID_PROVIDER_TYPES = {choice[0] for choice in ProviderType.CHOICES}
_VALID_LICENSE_TYPES = {
    ServiceProviderProfile.LicenseType.STANDARD,
    ServiceProviderProfile.LicenseType.PROFESSIONAL,
    ServiceProviderProfile.LicenseType.COMMERCIAL,
}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_profile(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid service_provider_profile_id.")
    qs = ServiceProviderProfile.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except ServiceProviderProfile.DoesNotExist:
        raise GraphQLError("Service provider profile not found.")


def _resolve_user(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _resolve_service_request(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid current_service_id.")
    try:
        return ServiceRequest.objects.get(pk=pk)
    except ServiceRequest.DoesNotExist:
        raise GraphQLError("Service request not found.")


def _assert_owner_or_staff(profile, user, *, staff_only=False):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if staff_only:
        if not user.is_staff:
            raise GraphQLError("Staff permission required.")
        return
    if user.is_staff:
        return
    if profile.user_id == user.pk:
        return
    raise GraphQLError("Not authorized to manage this provider profile.")


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


def _validate_allowed_vehicle_types(value):
    if value is None:
        return
    if not isinstance(value, list):
        raise GraphQLError("allowed_vehicle_types must be a list.")
    for entry in value:
        if not isinstance(entry, str):
            raise GraphQLError(
                "allowed_vehicle_types must be a list of strings."
            )


# =============================================================================
# Create
# =============================================================================

class CreateServiceProviderProfile(relay.ClientIDMutation):
    """
    Create a ServiceProviderProfile.

    One profile per user (`OneToOneField`). The owner is the caller by
    default; staff may pass `user_id` for onboarding partners.
    """

    class Input:
        user_id = graphene.ID()  # staff-only override

        provider_type = graphene.String(required=True)

        license_number = graphene.String()
        license_type = graphene.String()
        license_image = graphene.String(
            description="Storage reference (URL or key), not file bytes."
        )

        union_id = graphene.String()
        verified_union_member = graphene.Boolean()

        insurance_policy_number = graphene.String()
        insurance_provider = graphene.String()
        insurance_expiry = graphene.Date()

        allowed_vehicle_types = graphene.List(graphene.String)

        is_available = graphene.Boolean()
        is_online = graphene.Boolean()

        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        metadata = graphene.JSONString()

    service_provider_profile = graphene.Field(ServiceProviderProfileNode)
    user = graphene.Field(UserNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, provider_type, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_enum(provider_type, _VALID_PROVIDER_TYPES, "provider_type")
        _validate_enum(input.get("license_type"), _VALID_LICENSE_TYPES, "license_type")
        _validate_allowed_vehicle_types(input.get("allowed_vehicle_types"))

        # Target user
        target_user = me
        if input.get("user_id"):
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may create a provider profile for another user."
                )
            target_user = _resolve_user(input["user_id"])

        if ServiceProviderProfile.objects.filter(user=target_user).exists():
            raise GraphQLError(
                "This user already has a service provider profile. "
                "Use update_service_provider_profile instead."
            )

        payload = {
            "user": target_user,
            "provider_type": provider_type,
            "license_number": input.get("license_number") or "",
            "license_type": input.get("license_type") or "",
            "license_image": input.get("license_image") or None,
            "union_id": input.get("union_id"),
            "verified_union_member": bool(input.get("verified_union_member")),
            "insurance_policy_number": input.get("insurance_policy_number"),
            "insurance_provider": input.get("insurance_provider"),
            "insurance_expiry": input.get("insurance_expiry"),
            "allowed_vehicle_types": input.get("allowed_vehicle_types") or [],
            "is_available": (
                input["is_available"]
                if input.get("is_available") is not None
                else True
            ),
            "is_online": (
                input["is_online"]
                if input.get("is_online") is not None
                else False
            ),
            # is_verified starts False — staff flips it via update.
            "is_verified": False,
            "emergency_contact_name": input.get("emergency_contact_name"),
            "emergency_contact_phone": input.get("emergency_contact_phone"),
            "metadata": input.get("metadata") or {},
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            profile = ServiceProviderProfile(**payload)
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        profile.save()

        return cls(
            service_provider_profile=profile,
            user=target_user,
            success=True,
            message="Service provider profile created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateServiceProviderProfile(relay.ClientIDMutation):
    """
    Update a ServiceProviderProfile.

    Owner or staff. `is_verified` and `current_service_id` are
    staff-only — verification is an audit action, and service assignment
    is a dispatch decision.
    """

    class Input:
        service_provider_profile_id = graphene.ID(required=True)

        provider_type = graphene.String()

        license_number = graphene.String()
        license_type = graphene.String()
        license_image = graphene.String()

        union_id = graphene.String()
        verified_union_member = graphene.Boolean()

        insurance_policy_number = graphene.String()
        insurance_provider = graphene.String()
        insurance_expiry = graphene.Date()

        allowed_vehicle_types = graphene.List(graphene.String)

        is_available = graphene.Boolean()
        is_online = graphene.Boolean()

        is_verified = graphene.Boolean()            # staff-only
        current_service_id = graphene.ID()          # staff-only

        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        metadata = graphene.JSONString()

    service_provider_profile = graphene.Field(ServiceProviderProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, service_provider_profile_id, **input
    ):
        me = info.context.user
        profile = _resolve_profile(service_provider_profile_id, lock=True)
        _assert_owner_or_staff(profile, me)

        # Staff-only fields
        if not me.is_staff:
            for field in ("is_verified", "current_service_id"):
                if input.get(field) is not None:
                    raise GraphQLError(f"Only staff may change {field}.")

        _validate_enum(input.get("provider_type"), _VALID_PROVIDER_TYPES, "provider_type")
        _validate_enum(input.get("license_type"), _VALID_LICENSE_TYPES, "license_type")
        _validate_allowed_vehicle_types(input.get("allowed_vehicle_types"))

        update_fields = []

        # Simple scalar passthrough
        for field in (
            "provider_type",
            "license_number",
            "license_type",
            "license_image",
            "union_id",
            "verified_union_member",
            "insurance_policy_number",
            "insurance_provider",
            "insurance_expiry",
            "allowed_vehicle_types",
            "is_available",
            "is_online",
            "emergency_contact_name",
            "emergency_contact_phone",
        ):
            if field in input and input[field] is not None:
                setattr(profile, field, input[field])
                update_fields.append(field)

        # Staff-only writes
        if me.is_staff:
            if "is_verified" in input and input["is_verified"] is not None:
                profile.is_verified = bool(input["is_verified"])
                update_fields.append("is_verified")
            if "current_service_id" in input:
                if input["current_service_id"] is None:
                    profile.current_service = None
                else:
                    profile.current_service = _resolve_service_request(
                        input["current_service_id"]
                    )
                update_fields.append("current_service")

        # metadata merge
        if input.get("metadata") is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            profile.metadata = {**(profile.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if not update_fields:
            return cls(
                service_provider_profile=profile,
                success=True,
                message="Nothing to update.",
            )

        try:
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        profile.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            service_provider_profile=profile,
            success=True,
            message="Service provider profile updated.",
        )


# =============================================================================
# Availability / online toggles (thin wrappers over model methods)
# =============================================================================

class SetProviderAvailability(relay.ClientIDMutation):
    """
    Toggle `is_available` on a provider.

    Uses the model's `update_availability()` which also stamps
    `last_active`.
    """

    class Input:
        service_provider_profile_id = graphene.ID(required=True)
        is_available = graphene.Boolean(required=True)

    service_provider_profile = graphene.Field(ServiceProviderProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, service_provider_profile_id, is_available
    ):
        me = info.context.user
        profile = _resolve_profile(service_provider_profile_id, lock=True)
        _assert_owner_or_staff(profile, me)

        try:
            profile.update_availability(is_available=bool(is_available))
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            service_provider_profile=profile,
            success=True,
            message=f"Provider {'available' if is_available else 'unavailable'}.",
        )


class SetProviderOnline(relay.ClientIDMutation):
    """Toggle `is_online` on a provider. Owner or staff."""

    class Input:
        service_provider_profile_id = graphene.ID(required=True)
        is_online = graphene.Boolean(required=True)

    service_provider_profile = graphene.Field(ServiceProviderProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, service_provider_profile_id, is_online
    ):
        me = info.context.user
        profile = _resolve_profile(service_provider_profile_id, lock=True)
        _assert_owner_or_staff(profile, me)

        profile.is_online = bool(is_online)
        profile.save(update_fields=["is_online", "last_active"])

        return cls(
            service_provider_profile=profile,
            success=True,
            message=f"Provider {'online' if is_online else 'offline'}.",
        )


# =============================================================================
# Recompute rating (staff-only — normally called by rating flow)
# =============================================================================

class RecomputeProviderRating(relay.ClientIDMutation):
    """
    Recompute `rating` / `total_ratings` from ProviderRating rows.

    Staff-only escape hatch. The rating flow should call
    `update_provider_rating()` in `transport.models.rating` after each
    rating create / update / delete. This mutation exists for
    corrections and backfills.
    """

    class Input:
        service_provider_profile_id = graphene.ID(required=True)

    service_provider_profile = graphene.Field(ServiceProviderProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_provider_profile_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Staff permission required.")

        profile = _resolve_profile(service_provider_profile_id, lock=True)

        try:
            profile.update_rating()
        except Exception as exc:
            raise GraphQLError(f"Rating recompute failed: {exc}")

        return cls(
            service_provider_profile=profile,
            success=True,
            message="Provider rating recomputed.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteServiceProviderProfile(relay.ClientIDMutation):
    """
    Delete a ServiceProviderProfile.

    Owner or staff. Refuses while a current_service is assigned — the
    provider must be cleared from any active service first, or staff must
    unassign via `UpdateServiceProviderProfile(current_service_id: null)`.
    """

    class Input:
        service_provider_profile_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_provider_profile_id):
        me = info.context.user
        profile = _resolve_profile(service_provider_profile_id, lock=True)
        _assert_owner_or_staff(profile, me)

        if profile.current_service_id is not None:
            raise GraphQLError(
                "Cannot delete a provider profile with an active service. "
                "Complete or unassign the current service first."
            )

        # Optional: also refuse if the provider has any active service
        # requests assigned. The FK on ServiceRequest.provider is
        # SET_NULL so a raw delete wouldn't orphan requests, but the
        # requests would lose their provider silently.
        from transport.models.core.service_request import ServiceRequest

        active_statuses = (
            ServiceRequest.Status.REQUESTED,
            ServiceRequest.Status.ACCEPTED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.SCHEDULED,
            ServiceRequest.Status.DEPARTED,
            ServiceRequest.Status.IN_TRANSIT,
        )
        if ServiceRequest.objects.filter(
            provider=profile, status__in=active_statuses
        ).exists():
            raise GraphQLError(
                "Cannot delete a provider profile with active service requests."
            )

        profile.delete()
        return cls(success=True, message="Service provider profile deleted.")


# =============================================================================
# Registration
# =============================================================================

class ServiceProviderProfileMutations(graphene.ObjectType):
    create_service_provider_profile = CreateServiceProviderProfile.Field()
    update_service_provider_profile = UpdateServiceProviderProfile.Field()
    set_provider_availability = SetProviderAvailability.Field()
    set_provider_online = SetProviderOnline.Field()
    recompute_provider_rating = RecomputeProviderRating.Field()
    delete_service_provider_profile = DeleteServiceProviderProfile.Field()