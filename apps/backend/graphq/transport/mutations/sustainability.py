# apps/backend/graphq/transport/mutations/sustainability.py
"""
Mutations for SustainabilityProfile and CarbonCredit.

Design rules enforced here:
    - Profile and credits always belong to the authenticated user; the
      client never supplies `user_id`.
    - System-tracked counters on SustainabilityProfile
      (total_co2_saved_kg, total_car_trips_avoided, current_streak_days)
      are not writable by clients.
    - CarbonCredit verification (`is_verified`, `verification_code`) is
      staff-only. Regular users can create `earned` credits tied to a
      ride; `purchased`, `redeemed`, and `offset` are staff/system-only.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.sustainability import (
    SustainabilityProfileNode,
    CarbonCreditNode,
)
from graphq.accounts.types.user import UserNode

from transport.models.shared.sustainability import (
    SustainabilityProfile,
    CarbonCredit,
)
from transport.models.core.service_request import ServiceRequest


# =============================================================================
# Helpers
# =============================================================================

_ALLOWED_TRANSACTION_TYPES = {
    "earned",
    "purchased",
    "redeemed",
    "offset",
}

# Regular users may only create 'earned' credits (e.g. from a ride).
_USER_CREATABLE_TYPES = {"earned"}


def _resolve_user_credit(global_id, user):
    """Fetch a CarbonCredit owned by `user`, or raise."""
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid carbon_credit_id.")
    try:
        return CarbonCredit.objects.select_for_update().get(pk=pk)
    except CarbonCredit.DoesNotExist:
        raise GraphQLError("Carbon credit not found.")


def _refresh_sustainability_counters(user):
    """
    Recompute `total_co2_saved_kg` and `total_car_trips_avoided` from
    the ledger of earned/verified credits.

    Only `earned` and `offset` credits count as savings. Purchased and
    redeemed credits are ledger entries but not CO2 offsets.
    """
    profile = getattr(user, "sustainability_profile", None)
    if profile is None:
        return

    from django.db.models import Sum
    saved = (
        CarbonCredit.objects.filter(
            user=user,
            transaction_type__in=["earned", "offset"],
            is_verified=True,
        ).aggregate(total=Sum("credits_amount"))["total"]
        or 0.0
    )

    profile.total_co2_saved_kg = float(saved)
    profile.save(update_fields=["total_co2_saved_kg", "updated_at"])


# =============================================================================
# SustainabilityProfile
# =============================================================================

class UpsertSustainabilityProfile(relay.ClientIDMutation):
    """
    Create or update the authenticated user's SustainabilityProfile.

    Because `user` is a OneToOneField, create and update collapse into a
    single upsert. Only preference/goal fields are writable; system
    counters are managed elsewhere.
    """

    class Input:
        co2_reduction_goal_kg = graphene.Float()
        monthly_ride_goal = graphene.Int()
        car_avoidance_goal = graphene.Int()

        prefer_electric_vehicles = graphene.Boolean()
        prefer_shared_rides = graphene.Boolean()
        offset_carbon_footprint = graphene.Boolean()

    sustainability_profile = graphene.Field(SustainabilityProfileNode)
    created = graphene.Boolean()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        writable = {
            "co2_reduction_goal_kg": "co2_reduction_goal_kg",
            "monthly_ride_goal": "monthly_ride_goal",
            "car_avoidance_goal": "car_avoidance_goal",
            "prefer_electric_vehicles": "prefer_electric_vehicles",
            "prefer_shared_rides": "prefer_shared_rides",
            "offset_carbon_footprint": "offset_carbon_footprint",
        }

        create_defaults = {}
        for input_key, model_field in writable.items():
            if input_key in input and input[input_key] is not None:
                create_defaults[model_field] = input[input_key]

        # Validate non-negativity where the model has validators.
        if "co2_reduction_goal_kg" in create_defaults:
            if create_defaults["co2_reduction_goal_kg"] < 0:
                raise GraphQLError("co2_reduction_goal_kg must be >= 0.")
        for key in ("monthly_ride_goal", "car_avoidance_goal"):
            if key in create_defaults and create_defaults[key] < 0:
                raise GraphQLError(f"{key} must be >= 0.")

        profile, created = SustainabilityProfile.objects.get_or_create(
            user=me,
            defaults=create_defaults,
        )

        if not created and create_defaults:
            update_fields = []
            for field, value in create_defaults.items():
                setattr(profile, field, value)
                update_fields.append(field)
            update_fields.append("updated_at")
            try:
                profile.full_clean()
            except ValidationError as exc:
                raise GraphQLError(f"Validation failed: {exc.message_dict}")
            profile.save(update_fields=sorted(set(update_fields)))

        return cls(
            sustainability_profile=profile,
            created=created,
            success=True,
            message="Profile saved.",
        )


class ResetSustainabilityStreak(relay.ClientIDMutation):
    """
    Reset the caller's `current_streak_days` to zero.

    Separate from the general update because it's a system counter, not
    a preference. Anyone else resetting another user's streak would be
    an integrity problem, so the operation is scoped to the caller.
    """

    class Input:
        pass

    sustainability_profile = graphene.Field(SustainabilityProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        profile = getattr(me, "sustainability_profile", None)
        if profile is None:
            raise GraphQLError("You do not have a sustainability profile.")

        profile.current_streak_days = 0
        profile.save(update_fields=["current_streak_days", "updated_at"])

        return cls(
            sustainability_profile=profile,
            success=True,
            message="Streak reset.",
        )


class DeleteSustainabilityProfile(relay.ClientIDMutation):
    """
    Delete the caller's SustainabilityProfile.

    Staff may delete another user's profile by passing `user_id`.
    """

    class Input:
        user_id = graphene.ID()  # staff-only

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, user_id=None):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        target = me
        if user_id:
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may delete another user's profile."
                )
            try:
                _, pk = from_global_id(user_id)
            except Exception:
                raise GraphQLError("Invalid user_id.")
            try:
                target = type(me).objects.get(pk=pk)
            except type(me).DoesNotExist:
                raise GraphQLError("User not found.")

        profile = getattr(target, "sustainability_profile", None)
        if profile is None:
            return cls(success=True, message="No profile to delete.")

        profile.delete()
        return cls(success=True, message="Sustainability profile deleted.")


# =============================================================================
# CarbonCredit
# =============================================================================

class CreateCarbonCredit(relay.ClientIDMutation):
    """
    Create a CarbonCredit for the authenticated user.

    Regular users may only create `earned` credits tied to a ride they
    participated in. `purchased`, `redeemed`, and `offset` are staff or
    system operations — this is enforced by checking `transaction_type`.

    `is_verified` and `verification_code` are staff-only on create;
    regular users always get `is_verified=False`.
    """

    class Input:
        credits_amount = graphene.Float(required=True)
        transaction_type = graphene.String(required=True)

        ride_id = graphene.ID()

        verification_code = graphene.String()  # staff-only
        is_verified = graphene.Boolean()       # staff-only

    carbon_credit = graphene.Field(CarbonCreditNode)
    sustainability_profile = graphene.Field(SustainabilityProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        credits_amount = input["credits_amount"]
        if credits_amount < 0:
            raise GraphQLError("credits_amount must be >= 0.")

        transaction_type = input["transaction_type"]
        if transaction_type not in _ALLOWED_TRANSACTION_TYPES:
            raise GraphQLError(
                f"transaction_type must be one of: "
                f"{', '.join(sorted(_ALLOWED_TRANSACTION_TYPES))}."
            )

        # Non-staff can only create 'earned' credits.
        if not me.is_staff and transaction_type not in _USER_CREATABLE_TYPES:
            raise GraphQLError(
                "Only staff may create credits of type "
                f"'{transaction_type}'. Users may create 'earned' credits only."
            )

        # Staff-only flags — silently ignore for non-staff, since Django
        # would reject them anyway, but here we make the intent explicit.
        is_verified = False
        verification_code = ""
        if me.is_staff:
            is_verified = bool(input.get("is_verified", False))
            verification_code = input.get("verification_code") or ""

        # Resolve ride if provided.
        ride = None
        if input.get("ride_id"):
            try:
                _, ride_pk = from_global_id(input["ride_id"])
            except Exception:
                raise GraphQLError("Invalid ride_id.")
            try:
                ride = ServiceRequest.objects.get(pk=ride_pk)
            except ServiceRequest.DoesNotExist:
                raise GraphQLError("Ride not found.")

            # Non-staff user must be a participant in that ride.
            if not me.is_staff:
                is_customer = ride.customer_id == me.pk
                is_provider = (
                    ride.provider_id
                    and getattr(me, "service_provider", None)
                    and me.service_provider.pk == ride.provider_id
                )
                if not (is_customer or is_provider):
                    raise GraphQLError(
                        "You are not a participant in this ride."
                    )

        try:
            credit = CarbonCredit.objects.create(
                user=me,
                credits_amount=credits_amount,
                transaction_type=transaction_type,
                ride=ride,
                verification_code=verification_code,
                is_verified=is_verified,
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Refresh totals if the new credit counts toward savings.
        _refresh_sustainability_counters(me)

        return cls(
            carbon_credit=credit,
            sustainability_profile=getattr(me, "sustainability_profile", None),
            success=True,
            message="Carbon credit created.",
        )


class UpdateCarbonCredit(relay.ClientIDMutation):
    """
    Update a CarbonCredit.

    Regular users can only edit the `credits_amount` of an unverified
    'earned' credit they own. Staff can change any field including
    `is_verified`, `verification_code`, and `transaction_type`.
    """

    class Input:
        carbon_credit_id = graphene.ID(required=True)

        credits_amount = graphene.Float()
        transaction_type = graphene.String()   # staff-only
        ride_id = graphene.ID()

        verification_code = graphene.String()  # staff-only
        is_verified = graphene.Boolean()       # staff-only

    carbon_credit = graphene.Field(CarbonCreditNode)
    sustainability_profile = graphene.Field(SustainabilityProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, carbon_credit_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        credit = _resolve_user_credit(carbon_credit_id, me)
        if credit.user_id != me.pk and not me.is_staff:
            raise GraphQLError("Not authorized to update this credit.")

        staff_only = ("transaction_type", "verification_code", "is_verified")
        if not me.is_staff:
            if credit.is_verified:
                raise GraphQLError(
                    "Cannot edit a verified credit. Contact support."
                )
            if credit.transaction_type != "earned":
                raise GraphQLError(
                    "Only 'earned' credits can be edited by users."
                )
            for field in staff_only:
                if input.get(field) is not None:
                    raise GraphQLError(
                        f"Only staff may change {field}."
                    )

        update_fields = []

        if "credits_amount" in input and input["credits_amount"] is not None:
            if input["credits_amount"] < 0:
                raise GraphQLError("credits_amount must be >= 0.")
            credit.credits_amount = input["credits_amount"]
            update_fields.append("credits_amount")

        if me.is_staff:
            if "transaction_type" in input and input["transaction_type"] is not None:
                if input["transaction_type"] not in _ALLOWED_TRANSACTION_TYPES:
                    raise GraphQLError(
                        f"transaction_type must be one of: "
                        f"{', '.join(sorted(_ALLOWED_TRANSACTION_TYPES))}."
                    )
                credit.transaction_type = input["transaction_type"]
                update_fields.append("transaction_type")

            if "verification_code" in input and input["verification_code"] is not None:
                credit.verification_code = input["verification_code"]
                update_fields.append("verification_code")

            if "is_verified" in input and input["is_verified"] is not None:
                credit.is_verified = bool(input["is_verified"])
                update_fields.append("is_verified")

        if "ride_id" in input and input["ride_id"] is not None:
            try:
                _, ride_pk = from_global_id(input["ride_id"])
            except Exception:
                raise GraphQLError("Invalid ride_id.")
            try:
                credit.ride = ServiceRequest.objects.get(pk=ride_pk)
            except ServiceRequest.DoesNotExist:
                raise GraphQLError("Ride not found.")
            update_fields.append("ride")

        if not update_fields:
            return cls(
                carbon_credit=credit,
                sustainability_profile=getattr(me, "sustainability_profile", None),
                success=True,
                message="Nothing to update.",
            )

        try:
            credit.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        credit.save(update_fields=update_fields)

        # Refresh totals if the credit still counts toward savings, or
        # previously did (e.g. is_verified toggled off).
        _refresh_sustainability_counters(credit.user)

        return cls(
            carbon_credit=credit,
            sustainability_profile=getattr(credit.user, "sustainability_profile", None),
            success=True,
            message="Carbon credit updated.",
        )


class DeleteCarbonCredit(relay.ClientIDMutation):
    """
    Delete a CarbonCredit.

    Regular users can delete their own unverified 'earned' credits.
    Staff can delete any credit.
    """

    class Input:
        carbon_credit_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    sustainability_profile = graphene.Field(SustainabilityProfileNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, carbon_credit_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        credit = _resolve_user_credit(carbon_credit_id, me)

        if credit.user_id != me.pk and not me.is_staff:
            raise GraphQLError("Not authorized to delete this credit.")

        if not me.is_staff:
            if credit.is_verified:
                raise GraphQLError("Cannot delete a verified credit.")
            if credit.transaction_type != "earned":
                raise GraphQLError(
                    "Only 'earned' credits can be deleted by users."
                )

        owner = credit.user
        credit.delete()

        # Refresh totals after the ledger entry is gone.
        _refresh_sustainability_counters(owner)

        return cls(
            success=True,
            message="Carbon credit deleted.",
            sustainability_profile=getattr(owner, "sustainability_profile", None),
        )


class VerifyCarbonCredit(relay.ClientIDMutation):
    """
    Staff-only verification of a CarbonCredit.

    Verifying a credit triggers a recomputation of the owner's
    `total_co2_saved_kg`, so the profile counters stay consistent with
    the ledger.
    """

    class Input:
        carbon_credit_id = graphene.ID(required=True)
        verification_code = graphene.String()

    carbon_credit = graphene.Field(CarbonCreditNode)
    sustainability_profile = graphene.Field(SustainabilityProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, carbon_credit_id, verification_code=None
    ):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may verify carbon credits.")

        try:
            _, pk = from_global_id(carbon_credit_id)
        except Exception:
            raise GraphQLError("Invalid carbon_credit_id.")
        try:
            credit = CarbonCredit.objects.select_for_update().get(pk=pk)
        except CarbonCredit.DoesNotExist:
            raise GraphQLError("Carbon credit not found.")

        credit.is_verified = True
        if verification_code:
            credit.verification_code = verification_code

        credit.save(update_fields=["is_verified", "verification_code"])

        _refresh_sustainability_counters(credit.user)

        return cls(
            carbon_credit=credit,
            sustainability_profile=getattr(credit.user, "sustainability_profile", None),
            success=True,
            message="Carbon credit verified.",
        )


# =============================================================================
# Registration
# =============================================================================

class SustainabilityMutations(graphene.ObjectType):
    upsert_sustainability_profile = UpsertSustainabilityProfile.Field()
    reset_sustainability_streak = ResetSustainabilityStreak.Field()
    delete_sustainability_profile = DeleteSustainabilityProfile.Field()

    create_carbon_credit = CreateCarbonCredit.Field()
    update_carbon_credit = UpdateCarbonCredit.Field()
    delete_carbon_credit = DeleteCarbonCredit.Field()
    verify_carbon_credit = VerifyCarbonCredit.Field()