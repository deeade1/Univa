# apps/backend/graphq/transport/mutations/driver_profile.py
"""
DriverProfile mutations.

Model facts that shape these mutations:
    - The FK to the user is named `profile`, not `user` (OneToOneField).
    - `license_image` is a ResizedImageField; the mutation accepts a
      storage reference string, not binary data. File bytes are handled
      by the file-upload flow (presigned URL / multipart endpoint).
    - All text fields default to blank=True — the create path is
      forgiving, and the update path is a partial merge.

Ownership:
    - The driver owns their own profile.
    - Staff may create / edit / delete anyone's.
    - A regular user can only manage their own profile.
"""

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.driver_profile import DriverProfileNode
from graphq.accounts.types.user import UserNode

from transport.models.driver_profile import DriverProfile  


User = get_user_model()


# =============================================================================
# Helpers
# =============================================================================

def _resolve_profile(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid driver_profile_id.")
    qs = DriverProfile.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except DriverProfile.DoesNotExist:
        raise GraphQLError("Driver profile not found.")


def _resolve_user(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _assert_can_manage(profile, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    # profile.profile is the OneToOneField holding the owning user.
    if profile.profile_id == user.pk:
        return
    raise GraphQLError("Not authorized to manage this driver profile.")


def _validate_year(value):
    if value is None:
        return
    max_year = timezone.now().year + 1
    if not 1900 <= value <= max_year:
        raise GraphQLError(f"vehicle_year must be between 1900 and {max_year}.")


# =============================================================================
# Create
# =============================================================================

class CreateDriverProfile(relay.ClientIDMutation):
    """
    Create a DriverProfile for the authenticated user.

    Staff may pass `user_id` to create for another user. Because the FK
    to the user is a OneToOneField, only one profile per user exists.
    """

    class Input:
        user_id = graphene.ID()  # staff-only override

        license_number = graphene.String()
        license_image = graphene.String(
            description="Storage reference (URL or key), not file bytes."
        )

        vehicle_type = graphene.String()
        vehicle_plate = graphene.String()
        vehicle_make = graphene.String()
        vehicle_model = graphene.String()
        vehicle_year = graphene.Int()

        insurance_provider = graphene.String()
        insurance_expiry = graphene.Date()

    driver_profile = graphene.Field(DriverProfileNode)
    user = graphene.Field(UserNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        # Resolve target user.
        target_user = me
        if input.get("user_id"):
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may create a driver profile for another user."
                )
            target_user = _resolve_user(input["user_id"])

        if DriverProfile.objects.filter(profile=target_user).exists():
            raise GraphQLError(
                "A driver profile already exists for this user. "
                "Use update_driver_profile instead."
            )

        _validate_year(input.get("vehicle_year"))

        payload = {
            "profile": target_user,
            "license_number": input.get("license_number") or "",
            "license_image": input.get("license_image") or None,
            "vehicle_type": input.get("vehicle_type") or "",
            "vehicle_plate": input.get("vehicle_plate") or "",
            "vehicle_make": input.get("vehicle_make") or "",
            "vehicle_model": input.get("vehicle_model") or "",
            "vehicle_year": input.get("vehicle_year"),
            "insurance_provider": input.get("insurance_provider") or "",
            "insurance_expiry": input.get("insurance_expiry"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            profile = DriverProfile.objects.create(**payload)
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return CreateDriverProfile(
            driver_profile=profile,
            user=target_user,
            success=True,
            message="Driver profile created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateDriverProfile(relay.ClientIDMutation):
    """
    Update a DriverProfile.

    All fields are optional. Owner or staff.
    """

    class Input:
        driver_profile_id = graphene.ID(required=True)

        license_number = graphene.String()
        license_image = graphene.String()

        vehicle_type = graphene.String()
        vehicle_plate = graphene.String()
        vehicle_make = graphene.String()
        vehicle_model = graphene.String()
        vehicle_year = graphene.Int()

        insurance_provider = graphene.String()
        insurance_expiry = graphene.Date()

    driver_profile = graphene.Field(DriverProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_profile_id, **input):
        me = info.context.user
        profile = _resolve_profile(driver_profile_id, lock=True)
        _assert_can_manage(profile, me)

        _validate_year(input.get("vehicle_year"))

        update_fields = []
        for field in (
            "license_number",
            "license_image",
            "vehicle_type",
            "vehicle_plate",
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
            "insurance_provider",
            "insurance_expiry",
        ):
            if field in input and input[field] is not None:
                setattr(profile, field, input[field])
                update_fields.append(field)

        if not update_fields:
            return UpdateDriverProfile(
                driver_profile=profile,
                success=True,
                message="Nothing to update.",
            )

        try:
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # `profile` model has no updated_at; no need to include it.
        profile.save(update_fields=update_fields)

        return cls(
            driver_profile=profile,
            success=True,
            message="Driver profile updated.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteDriverProfile(relay.ClientIDMutation):
    """
    Delete a DriverProfile.

    Owner or staff. Prefer clearing fields (`license_number=""`, etc.)
    if you only need to invalidate the driver status — deletion also
    removes the OneToOne link and any downstream assumptions.
    """

    class Input:
        driver_profile_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_profile_id):
        me = info.context.user
        profile = _resolve_profile(driver_profile_id, lock=True)
        _assert_can_manage(profile, me)

        profile.delete()
        return DeleteDriverProfile(success=True, message="Driver profile deleted.")


# =============================================================================
# Registration
# =============================================================================

class DriverProfileMutations(graphene.ObjectType):
    create_driver_profile = CreateDriverProfile.Field()
    update_driver_profile = UpdateDriverProfile.Field()
    delete_driver_profile = DeleteDriverProfile.Field()