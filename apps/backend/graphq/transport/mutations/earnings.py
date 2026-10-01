# apps/backend/graphq/transport/mutations/driver_earning.py
"""
DriverEarning and IncentiveProgram mutations.

Model facts that shape these mutations:
    - DriverEarning.driver FK → ServiceProviderProfile (not User).
    - DriverEarning.save() calls calculate_earnings() then full_clean().
      Any field the caller supplies that overlaps with the computed
      set (total_earnings, net_earnings, payout_amount) is overwritten.
      Only `commission` is preserved when explicitly set.
    - Payout lifecycle: PENDING → PROCESSING → PAID, or → FAILED / CANCELLED.
      The model enforces "cannot leave PAID". Its helpers
      (mark_as_paid, mark_as_failed, cancel_payout) wrap the transition.
    - IncentiveProgram is global config; staff-only.
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.service_provider import ServiceProviderProfileNode
from graphq.transport.types.earnings import (
    DriverEarningNode,
    IncentiveProgramNode,
)
from graphq.accounts.types.user import UserNode

from transport.models.financial.earnings import DriverEarning, IncentiveProgram
from transport.models.core.service_provider import ServiceProviderProfile


User = get_user_model()

_PERIOD_TYPES = {c.value for c in DriverEarning.PeriodType}
_PAYOUT_STATUSES = {c.value for c in DriverEarning.PayoutStatus}
_INCENTIVE_TYPES = {c.value for c in IncentiveProgram.IncentiveType}
_REWARD_TYPES = {"fixed", "percentage", "multiplier"}


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_earning(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid driver_earning_id.")
    qs = DriverEarning.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except DriverEarning.DoesNotExist:
        raise GraphQLError("Driver earning not found.")


def _resolve_program(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid incentive_program_id.")
    qs = IncentiveProgram.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except IncentiveProgram.DoesNotExist:
        raise GraphQLError("Incentive program not found.")


def _resolve_provider(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid driver_id.")
    try:
        return ServiceProviderProfile.objects.get(pk=pk)
    except ServiceProviderProfile.DoesNotExist:
        raise GraphQLError("Service provider not found.")


def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


def _non_negative(value, field):
    if value is not None and Decimal(str(value)) < 0:
        raise GraphQLError(f"{field} cannot be negative.")


def _validate_commission_rate(value):
    if value is None:
        return
    try:
        rate = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError("commission_rate must be a valid decimal.")
    if not 0 <= rate <= 100:
        raise GraphQLError("commission_rate must be between 0 and 100.")


# =============================================================================
# DriverEarning — Create
# =============================================================================

class CreateDriverEarning(relay.ClientIDMutation):
    """
    Create a DriverEarning record.

    Staff-only. Only the *source* figures are accepted; the totals
    (total_earnings, commission when not overridden, net_earnings,
    payout_amount) are computed by the model.
    """

    class Input:
        driver_id = graphene.ID(required=True)
        period = graphene.String(required=True)
        period_start = graphene.DateTime(required=True)
        period_end = graphene.DateTime(required=True)

        # Source figures
        ride_earnings = graphene.Decimal()
        delivery_earnings = graphene.Decimal()
        cancellation_fees = graphene.Decimal()
        tips = graphene.Decimal()
        bonuses = graphene.Decimal()

        # Deductions / adjustments
        commission = graphene.Decimal()      # if omitted, computed from rate
        commission_rate = graphene.Decimal()
        fees = graphene.Decimal()
        adjustments = graphene.Decimal()

        # Metrics (optional, informational)
        total_rides = graphene.Int()
        completed_rides = graphene.Int()
        total_deliveries = graphene.Int()
        completed_deliveries = graphene.Int()
        total_distance = graphene.Float()
        online_hours = graphene.Float()

        metadata = graphene.JSONString()

    driver_earning = graphene.Field(DriverEarningNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, driver_id, period, period_start, period_end, **input
    ):
        _assert_staff(info.context.user)

        if period not in _PERIOD_TYPES:
            raise GraphQLError(
                f"period must be one of: {', '.join(sorted(_PERIOD_TYPES))}."
            )

        if period_end <= period_start:
            raise GraphQLError("period_end must be after period_start.")

        driver = _resolve_provider(driver_id)
        _validate_commission_rate(input.get("commission_rate"))

        for field in (
            "ride_earnings",
            "delivery_earnings",
            "cancellation_fees",
            "tips",
            "bonuses",
            "commission",
            "fees",
        ):
            _non_negative(input.get(field), field)

        if DriverEarning.objects.filter(
            driver=driver, period_start=period_start, period_end=period_end
        ).exists():
            raise GraphQLError(
                "An earning record already exists for this driver and period."
            )

        payload = {
            "driver": driver,
            "period": period,
            "period_start": period_start,
            "period_end": period_end,
            "ride_earnings": _parse_decimal(input.get("ride_earnings"), "ride_earnings") or Decimal("0"),
            "delivery_earnings": _parse_decimal(input.get("delivery_earnings"), "delivery_earnings") or Decimal("0"),
            "cancellation_fees": _parse_decimal(input.get("cancellation_fees"), "cancellation_fees") or Decimal("0"),
            "tips": _parse_decimal(input.get("tips"), "tips") or Decimal("0"),
            "bonuses": _parse_decimal(input.get("bonuses"), "bonuses") or Decimal("0"),
            "commission": _parse_decimal(input.get("commission"), "commission") or Decimal("0"),
            "commission_rate": _parse_decimal(input.get("commission_rate"), "commission_rate") or Decimal("20.00"),
            "fees": _parse_decimal(input.get("fees"), "fees") or Decimal("0"),
            "adjustments": _parse_decimal(input.get("adjustments"), "adjustments") or Decimal("0"),
            "total_rides": input.get("total_rides") or 0,
            "completed_rides": input.get("completed_rides") or 0,
            "total_deliveries": input.get("total_deliveries") or 0,
            "completed_deliveries": input.get("completed_deliveries") or 0,
            "total_distance": input.get("total_distance") or 0.0,
            "online_hours": input.get("online_hours") or 0.0,
            "metadata": input.get("metadata") or {},
        }

        try:
            earning = DriverEarning(**payload)
            # save() runs calculate_earnings() then full_clean().
            earning.save()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        return cls(
            driver_earning=earning,
            success=True,
            message="Driver earning created.",
        )


# =============================================================================
# DriverEarning — Update
# =============================================================================

class UpdateDriverEarning(relay.ClientIDMutation):
    """
    Update the source figures / metrics on a DriverEarning.

    Staff-only. Only permitted while payout is not PAID. Totals are
    recomputed by the model on save().
    """

    class Input:
        driver_earning_id = graphene.ID(required=True)

        ride_earnings = graphene.Decimal()
        delivery_earnings = graphene.Decimal()
        cancellation_fees = graphene.Decimal()
        tips = graphene.Decimal()
        bonuses = graphene.Decimal()

        commission = graphene.Decimal()
        commission_rate = graphene.Decimal()
        fees = graphene.Decimal()
        adjustments = graphene.Decimal()

        total_rides = graphene.Int()
        completed_rides = graphene.Int()
        total_deliveries = graphene.Int()
        completed_deliveries = graphene.Int()
        total_distance = graphene.Float()
        online_hours = graphene.Float()

        metadata = graphene.JSONString()

    driver_earning = graphene.Field(DriverEarningNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_earning_id, **input):
        _assert_staff(info.context.user)

        earning = _resolve_earning(driver_earning_id, lock=True)

        if earning.payout_status == DriverEarning.PayoutStatus.PAID:
            raise GraphQLError("Cannot edit an earning record that has been paid.")

        _validate_commission_rate(input.get("commission_rate"))

        for field in (
            "ride_earnings",
            "delivery_earnings",
            "cancellation_fees",
            "tips",
            "bonuses",
            "commission",
            "fees",
        ):
            _non_negative(input.get(field), field)

        decimal_fields = {
            "ride_earnings": "ride_earnings",
            "delivery_earnings": "delivery_earnings",
            "cancellation_fees": "cancellation_fees",
            "tips": "tips",
            "bonuses": "bonuses",
            "commission": "commission",
            "commission_rate": "commission_rate",
            "fees": "fees",
            "adjustments": "adjustments",
        }
        for input_key, model_field in decimal_fields.items():
            if input_key in input and input[input_key] is not None:
                setattr(earning, model_field, _parse_decimal(input[input_key], input_key))

        for field in (
            "total_rides",
            "completed_rides",
            "total_deliveries",
            "completed_deliveries",
            "total_distance",
            "online_hours",
        ):
            if field in input and input[field] is not None:
                setattr(earning, field, input[field])

        if "metadata" in input and input["metadata"] is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            earning.metadata = {**(earning.metadata or {}), **input["metadata"]}

        try:
            earning.save()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            driver_earning=earning,
            success=True,
            message="Driver earning updated.",
        )


# =============================================================================
# Payout lifecycle
# =============================================================================

class MarkDriverEarningPaid(relay.ClientIDMutation):
    """Transition a DriverEarning to PAID. Staff-only."""

    class Input:
        driver_earning_id = graphene.ID(required=True)
        payout_reference = graphene.String()
        payout_method = graphene.String()

    driver_earning = graphene.Field(DriverEarningNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, driver_earning_id, payout_reference=None, payout_method=None
    ):
        _assert_staff(info.context.user)
        earning = _resolve_earning(driver_earning_id, lock=True)

        if payout_method is not None:
            from payment.models import PaymentMethod as PM
            valid_methods = {c.value for c in PM.PaymentType}
            if payout_method not in valid_methods:
                raise GraphQLError(
                    f"payout_method must be one of: "
                    f"{', '.join(sorted(valid_methods))}."
                )
            earning.payout_method = payout_method

        try:
            earning.mark_as_paid(reference=payout_reference)
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            driver_earning=earning,
            success=True,
            message="Earning marked as paid.",
        )


class MarkDriverEarningFailed(relay.ClientIDMutation):
    """Transition a DriverEarning to FAILED. Staff-only."""

    class Input:
        driver_earning_id = graphene.ID(required=True)
        reason = graphene.String()

    driver_earning = graphene.Field(DriverEarningNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_earning_id, reason=None):
        _assert_staff(info.context.user)
        earning = _resolve_earning(driver_earning_id, lock=True)

        try:
            earning.mark_as_failed(reason=reason)
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            driver_earning=earning,
            success=True,
            message="Earning marked as failed.",
        )


class CancelDriverEarningPayout(relay.ClientIDMutation):
    """Transition a DriverEarning to CANCELLED. Staff-only."""

    class Input:
        driver_earning_id = graphene.ID(required=True)

    driver_earning = graphene.Field(DriverEarningNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_earning_id):
        _assert_staff(info.context.user)
        earning = _resolve_earning(driver_earning_id, lock=True)

        try:
            earning.cancel_payout()
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            driver_earning=earning,
            success=True,
            message="Payout cancelled.",
        )


class DeleteDriverEarning(relay.ClientIDMutation):
    """
    Delete a DriverEarning. Staff-only.

    Refuses to delete a PAID earning — that row is a financial audit
    record. Use `CancelDriverEarningPayout` for non-paid corrections.
    """

    class Input:
        driver_earning_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, driver_earning_id):
        _assert_staff(info.context.user)
        earning = _resolve_earning(driver_earning_id, lock=True)

        if earning.payout_status == DriverEarning.PayoutStatus.PAID:
            raise GraphQLError(
                "Cannot delete a PAID earning record. It is a financial "
                "audit record."
            )

        earning.delete()
        return cls(success=True, message="Driver earning deleted.")


# =============================================================================
# IncentiveProgram
# =============================================================================

class CreateIncentiveProgram(relay.ClientIDMutation):
    """Create an IncentiveProgram. Staff-only."""

    class Input:
        name = graphene.String(required=True)
        incentive_type = graphene.String(required=True)
        description = graphene.String(required=True)

        min_rating = graphene.Float()
        min_completion_rate = graphene.Float()
        min_rides = graphene.Int()
        service_types = graphene.List(graphene.String)

        reward_amount = graphene.Decimal(required=True)
        reward_type = graphene.String()

        start_date = graphene.DateTime(required=True)
        end_date = graphene.DateTime(required=True)
        is_active = graphene.Boolean()

    incentive_program = graphene.Field(IncentiveProgramNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        _assert_staff(info.context.user)

        if input["incentive_type"] not in _INCENTIVE_TYPES:
            raise GraphQLError(
                f"incentive_type must be one of: "
                f"{', '.join(sorted(_INCENTIVE_TYPES))}."
            )

        reward_type = input.get("reward_type") or "fixed"
        if reward_type not in _REWARD_TYPES:
            raise GraphQLError(
                f"reward_type must be one of: {', '.join(sorted(_REWARD_TYPES))}."
            )

        if input["end_date"] <= input["start_date"]:
            raise GraphQLError("end_date must be after start_date.")

        min_rating = input.get("min_rating")
        if min_rating is not None and not 0 <= min_rating <= 5:
            raise GraphQLError("min_rating must be between 0 and 5.")

        min_completion = input.get("min_completion_rate")
        if min_completion is not None and not 0 <= min_completion <= 100:
            raise GraphQLError("min_completion_rate must be between 0 and 100.")

        reward_amount = _parse_decimal(input["reward_amount"], "reward_amount")
        if reward_amount is None or reward_amount < 0:
            raise GraphQLError("reward_amount must be >= 0.")

        try:
            program = IncentiveProgram.objects.create(
                name=input["name"],
                incentive_type=input["incentive_type"],
                description=input["description"],
                min_rating=min_rating,
                min_completion_rate=min_completion,
                min_rides=input.get("min_rides"),
                service_types=input.get("service_types") or [],
                reward_amount=reward_amount,
                reward_type=reward_type,
                start_date=input["start_date"],
                end_date=input["end_date"],
                is_active=(
                    input["is_active"]
                    if input.get("is_active") is not None
                    else True
                ),
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            incentive_program=program,
            success=True,
            message="Incentive program created.",
        )


class UpdateIncentiveProgram(relay.ClientIDMutation):
    """Update an IncentiveProgram. Staff-only."""

    class Input:
        incentive_program_id = graphene.ID(required=True)

        name = graphene.String()
        incentive_type = graphene.String()
        description = graphene.String()

        min_rating = graphene.Float()
        min_completion_rate = graphene.Float()
        min_rides = graphene.Int()
        service_types = graphene.List(graphene.String)

        reward_amount = graphene.Decimal()
        reward_type = graphene.String()

        start_date = graphene.DateTime()
        end_date = graphene.DateTime()
        is_active = graphene.Boolean()

    incentive_program = graphene.Field(IncentiveProgramNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, incentive_program_id, **input):
        _assert_staff(info.context.user)
        program = _resolve_program(incentive_program_id, lock=True)

        if (
            "incentive_type" in input
            and input["incentive_type"] is not None
            and input["incentive_type"] not in _INCENTIVE_TYPES
        ):
            raise GraphQLError(
                f"incentive_type must be one of: "
                f"{', '.join(sorted(_INCENTIVE_TYPES))}."
            )

        if (
            "reward_type" in input
            and input["reward_type"] is not None
            and input["reward_type"] not in _REWARD_TYPES
        ):
            raise GraphQLError(
                f"reward_type must be one of: "
                f"{', '.join(sorted(_REWARD_TYPES))}."
            )

        update_fields = []

        simple_map = {
            "name": "name",
            "incentive_type": "incentive_type",
            "description": "description",
            "min_rating": "min_rating",
            "min_completion_rate": "min_completion_rate",
            "min_rides": "min_rides",
            "service_types": "service_types",
            "reward_type": "reward_type",
            "start_date": "start_date",
            "end_date": "end_date",
            "is_active": "is_active",
        }
        for input_key, model_field in simple_map.items():
            if input_key in input and input[input_key] is not None:
                if input_key == "min_rating" and not 0 <= input[input_key] <= 5:
                    raise GraphQLError("min_rating must be between 0 and 5.")
                if input_key == "min_completion_rate" and not 0 <= input[input_key] <= 100:
                    raise GraphQLError("min_completion_rate must be between 0 and 100.")
                setattr(program, model_field, input[input_key])
                update_fields.append(model_field)

        if "reward_amount" in input and input["reward_amount"] is not None:
            amount = _parse_decimal(input["reward_amount"], "reward_amount")
            if amount < 0:
                raise GraphQLError("reward_amount must be >= 0.")
            program.reward_amount = amount
            update_fields.append("reward_amount")

        if program.end_date <= program.start_date:
            raise GraphQLError("end_date must be after start_date.")

        if not update_fields:
            return cls(
                incentive_program=program,
                success=True,
                message="Nothing to update.",
            )

        try:
            program.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        program.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            incentive_program=program,
            success=True,
            message="Incentive program updated.",
        )


class DeleteIncentiveProgram(relay.ClientIDMutation):
    """
    Delete an IncentiveProgram. Staff-only.

    Prefer `UpdateIncentiveProgram(is_active: false)` — deleting is
    irreversible and drops the historical link to drivers who earned
    under the program.
    """

    class Input:
        incentive_program_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, incentive_program_id):
        _assert_staff(info.context.user)
        program = _resolve_program(incentive_program_id, lock=True)
        program.delete()
        return cls(success=True, message="Incentive program deleted.")


# =============================================================================
# Registration
# =============================================================================

class DriverEarningMutations(graphene.ObjectType):
    create_driver_earning = CreateDriverEarning.Field()
    update_driver_earning = UpdateDriverEarning.Field()
    mark_driver_earning_paid = MarkDriverEarningPaid.Field()
    mark_driver_earning_failed = MarkDriverEarningFailed.Field()
    cancel_driver_earning_payout = CancelDriverEarningPayout.Field()
    delete_driver_earning = DeleteDriverEarning.Field()

    create_incentive_program = CreateIncentiveProgram.Field()
    update_incentive_program = UpdateIncentiveProgram.Field()
    delete_incentive_program = DeleteIncentiveProgram.Field()