# apps/backend/graphq/transport/mutations/cancellation.py
"""
Cancellation mutations.

Two related concerns:

1. CancellationPolicy — global per-service-type config. Staff-only CRUD.

2. CancellationRecord — a per-ServiceRequest snapshot of what was
   cancelled, by whom, and at what cost. Normally created as a side
   effect of cancelling a ServiceRequest, via
   `CancelServiceRequestWithPolicy`. A staff-only raw upsert is also
   provided for backfills and corrections.

Design rules enforced:
    - Policies are staff-only (they affect every customer).
    - Records are always owned by the canceller; the client cannot
      forge `cancelled_by`.
    - Fees/refunds/compensation are computed from the active policy,
      not from client-supplied numbers.
"""

from decimal import Decimal

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.cancellation import (
    CancellationPolicyNode,
    CancellationRecordNode,
)
from graphq.transport.types.trip import TripNode
from graphq.accounts.types.user import UserNode

from transport.models.financial.cancellation import (
    CancellationPolicy,
    CancellationRecord,
)
from transport.models.core.service_request import ServiceRequest


User = get_user_model()

_VALID_SERVICE_TYPES = {c.value for c in CancellationPolicy.ServiceType}
_VALID_PARTIES = {c.value for c in CancellationPolicy.CancellationParty}
_VALID_REASONS = {c.value for c in CancellationRecord.CancellationReason}


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_policy(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid policy id.")
    qs = CancellationPolicy.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except CancellationPolicy.DoesNotExist:
        raise GraphQLError("Cancellation policy not found.")


def _resolve_record(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid cancellation_record id.")
    qs = CancellationRecord.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except CancellationRecord.DoesNotExist:
        raise GraphQLError("Cancellation record not found.")


def _resolve_service_request(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid service_request_id.")
    try:
        return ServiceRequest.objects.get(pk=pk)
    except ServiceRequest.DoesNotExist:
        raise GraphQLError("Service request not found.")


def _resolve_user(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _validate_policy_scalars(data):
    for field in (
        "free_cancellation_minutes",
        "no_penalty_cancellation_minutes",
        "max_cancellations_per_day",
        "suspension_days",
    ):
        if field in data and data[field] is not None and data[field] < 0:
            raise GraphQLError(f"{field} cannot be negative.")

    for field in (
        "cancellation_fee_percentage",
        "refund_percentage",
        "driver_compensation_percentage",
    ):
        if field in data and data[field] is not None:
            value = float(data[field])
            if not 0 <= value <= 100:
                raise GraphQLError(f"{field} must be between 0 and 100.")

    for field in ("cancellation_fee", "min_refund_amount"):
        if field in data and data[field] is not None:
            if Decimal(str(data[field])) < 0:
                raise GraphQLError(f"{field} cannot be negative.")


def _active_policy_for(service_request):
    """
    Return the currently applicable CancellationPolicy for the given
    ServiceRequest, or None if there isn't one.
    """
    now = timezone.now()
    return (
        CancellationPolicy.objects.filter(
            service_type=service_request.service_type,
            is_active=True,
            effective_from__lte=now,
        )
        .filter(models_Q_effective_to(now))
        .order_by("-effective_from")
        .first()
    )


def models_Q_effective_to(now):
    """Small helper so the queryset filter stays readable."""
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gt=now)


def _compute_cancellation_figures(policy, service_request, minutes_after_acceptance):
    """
    Return (fee, refund, compensation) based on the policy and the
    elapsed minutes since acceptance.

    Rules (matching the model's semantics):
        - Within `free_cancellation_minutes` of booking: no fee.
        - Within `no_penalty_cancellation_minutes` of acceptance: no fee.
        - Otherwise: fee = max(fixed_fee, fare * fee_percentage / 100),
          capped at the ride fare.
        - Refund = (fare - fee) * refund_percentage / 100, floored at
          `min_refund_amount`.
        - Driver compensation = fee * driver_compensation_percentage / 100.
    """
    fare = Decimal(str(service_request.total_fare or 0))

    if policy is None:
        return Decimal("0.00"), fare, Decimal("0.00")

    # Free window (from booking).
    if service_request.created_at:
        minutes_since_booking = (
            timezone.now() - service_request.created_at
        ).total_seconds() / 60
        if minutes_since_booking <= policy.free_cancellation_minutes:
            return Decimal("0.00"), fare, Decimal("0.00")

    # No-penalty window (from acceptance).
    if (
        minutes_after_acceptance is not None
        and minutes_after_acceptance <= policy.no_penalty_cancellation_minutes
    ):
        return Decimal("0.00"), fare, Decimal("0.00")

    fixed_fee = Decimal(str(policy.cancellation_fee or 0))
    percent_fee = fare * Decimal(str(policy.cancellation_fee_percentage or 0)) / Decimal("100")
    fee = max(fixed_fee, percent_fee)
    if fare > 0:
        fee = min(fee, fare)

    net_after_fee = max(fare - fee, Decimal("0.00"))
    refund = net_after_fee * Decimal(str(policy.refund_percentage or 0)) / Decimal("100")
    refund = max(refund, Decimal(str(policy.min_refund_amount or 0)))
    refund = min(refund, net_after_fee)

    compensation = fee * Decimal(str(policy.driver_compensation_percentage or 0)) / Decimal("100")

    return (
        fee.quantize(Decimal("0.01")),
        refund.quantize(Decimal("0.01")),
        compensation.quantize(Decimal("0.01")),
    )


# =============================================================================
# CancellationPolicy
# =============================================================================

class UpsertCancellationPolicy(relay.ClientIDMutation):
    """
    Create or update the policy for a service_type.

    Staff-only. `service_type` is `unique=True` on the model, so upsert
    is keyed on it. Timestamps are left to auto_now_add / auto_now.
    """

    class Input:
        service_type = graphene.String(required=True)
        name = graphene.String(required=True)
        description = graphene.String()

        free_cancellation_minutes = graphene.Int()
        no_penalty_cancellation_minutes = graphene.Int()

        cancellation_fee = graphene.Decimal()
        cancellation_fee_percentage = graphene.Decimal()

        refund_percentage = graphene.Decimal()
        min_refund_amount = graphene.Decimal()

        driver_compensation_percentage = graphene.Decimal()
        max_cancellations_per_day = graphene.Int()
        suspension_days = graphene.Int()

        is_active = graphene.Boolean()
        effective_from = graphene.DateTime()
        effective_to = graphene.DateTime()

    cancellation_policy = graphene.Field(CancellationPolicyNode)
    created = graphene.Boolean()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_type, **input):
        _assert_staff(info.context.user)

        if service_type not in _VALID_SERVICE_TYPES:
            raise GraphQLError(
                f"service_type must be one of: "
                f"{', '.join(sorted(_VALID_SERVICE_TYPES))}."
            )

        _validate_policy_scalars(input)

        defaults = {"name": input["name"]}
        for field in (
            "description",
            "free_cancellation_minutes",
            "no_penalty_cancellation_minutes",
            "cancellation_fee",
            "cancellation_fee_percentage",
            "refund_percentage",
            "min_refund_amount",
            "driver_compensation_percentage",
            "max_cancellations_per_day",
            "suspension_days",
            "is_active",
            "effective_from",
            "effective_to",
        ):
            if field in input and input[field] is not None:
                defaults[field] = input[field]

        policy, created = CancellationPolicy.objects.get_or_create(
            service_type=service_type,
            defaults=defaults,
        )

        if not created:
            for field, value in defaults.items():
                setattr(policy, field, value)
            try:
                policy.full_clean()
            except ValidationError as exc:
                raise GraphQLError(f"Validation failed: {exc.message_dict}")
            policy.save()

        return cls(
            cancellation_policy=policy,
            created=created,
            success=True,
            message="Cancellation policy saved.",
        )


class DeleteCancellationPolicy(relay.ClientIDMutation):
    """
    Delete a CancellationPolicy.

    Staff-only. Prefer `is_active=False` for temporary deactivation —
    historical CancellationRecords keep a FK to the policy
    (`on_delete=SET_NULL`), so deletion isn't fatal but loses the audit
    link.
    """

    class Input:
        cancellation_policy_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, cancellation_policy_id):
        _assert_staff(info.context.user)
        policy = _resolve_policy(cancellation_policy_id, lock=True)
        policy.delete()
        return cls(success=True, message="Cancellation policy deleted.")


# =============================================================================
# CancellationRecord — derived (recommended path)
# =============================================================================

class CancelServiceRequestWithPolicy(relay.ClientIDMutation):
    """
    Cancel a ServiceRequest and record a CancellationRecord.

    This is the correct way to cancel: the record is a snapshot that
    captures the applicable policy and the computed fees/refunds.
    Owner, assigned provider, or staff may cancel.

    All monetary values are computed server-side from the active policy;
    clients cannot supply them.
    """

    class Input:
        service_request_id = graphene.ID(required=True)
        cancellation_party = graphene.String(required=True)
        reason = graphene.String(required=True)
        reason_description = graphene.String()

    cancellation_record = graphene.Field(CancellationRecordNode)
    service_request = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        service_request_id,
        cancellation_party,
        reason,
        reason_description=None,
    ):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        if cancellation_party not in _VALID_PARTIES:
            raise GraphQLError(
                f"cancellation_party must be one of: "
                f"{', '.join(sorted(_VALID_PARTIES))}."
            )
        if reason not in _VALID_REASONS:
            raise GraphQLError(
                f"reason must be one of: {', '.join(sorted(_VALID_REASONS))}."
            )

        service_request = _resolve_service_request(service_request_id)

        # Ownership: caller must be the customer, assigned provider, or staff.
        is_customer = service_request.customer_id == me.pk
        provider = getattr(me, "service_provider", None)
        is_provider = (
            provider is not None
            and service_request.provider_id == provider.pk
        )
        if not (is_customer or is_provider or me.is_staff):
            raise GraphQLError("Not authorized to cancel this service request.")

        if service_request.status in (
            ServiceRequest.Status.COMPLETED,
            ServiceRequest.Status.CANCELLED,
        ):
            raise GraphQLError(
                f"Cannot cancel a request in status '{service_request.status}'."
            )

        # Duplicate guard (OneToOneField would raise IntegrityError anyway).
        if CancellationRecord.objects.filter(service_request=service_request).exists():
            raise GraphQLError(
                "A cancellation record already exists for this service request."
            )

        # Snapshot the policy and compute figures.
        policy = _active_policy_for(service_request)

        minutes_after_acceptance = None
        if service_request.started_at:
            minutes_after_acceptance = (
                timezone.now() - service_request.started_at
            ).total_seconds() / 60

        fee, refund, compensation = _compute_cancellation_figures(
            policy, service_request, minutes_after_acceptance
        )

        # Create the record.
        try:
            record = CancellationRecord.objects.create(
                service_request=service_request,
                cancelled_by=me,
                cancellation_party=cancellation_party,
                reason=reason,
                reason_description=reason_description or "",
                accepted_at=service_request.started_at,
                minutes_after_acceptance=minutes_after_acceptance,
                ride_fare=service_request.total_fare,
                cancellation_fee=fee,
                refund_amount=refund,
                driver_compensation=compensation,
                policy=policy,
                penalty_applied=fee > 0,
                penalty_details={
                    "policy_id": str(policy.pk) if policy else None,
                    "policy_service_type": policy.service_type if policy else None,
                    "computed_at": timezone.now().isoformat(),
                },
            )
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        # Mark the request cancelled.
        service_request.status = ServiceRequest.Status.CANCELLED
        try:
            service_request.save(update_fields=["status", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            cancellation_record=record,
            service_request=service_request,
            success=True,
            message="Service request cancelled.",
        )


# =============================================================================
# CancellationRecord — raw CRUD (staff-only)
# =============================================================================

class UpsertCancellationRecord(relay.ClientIDMutation):
    """
    Raw upsert of a CancellationRecord.

    Staff-only. Use `CancelServiceRequestWithPolicy` for the standard
    cancel flow. This mutation exists for backfills, migrations, and
    corrections where the historical numbers need to be set explicitly.
    """

    class Input:
        service_request_id = graphene.ID(required=True)
        cancelled_by_id = graphene.ID()  # staff-only override
        cancellation_party = graphene.String(required=True)
        reason = graphene.String(required=True)
        reason_description = graphene.String()

        accepted_at = graphene.DateTime()
        cancelled_at = graphene.DateTime()
        minutes_after_acceptance = graphene.Float()

        ride_fare = graphene.Decimal()
        cancellation_fee = graphene.Decimal()
        refund_amount = graphene.Decimal()
        driver_compensation = graphene.Decimal()

        policy_id = graphene.ID()
        penalty_applied = graphene.Boolean()
        penalty_details = graphene.JSONString()

    cancellation_record = graphene.Field(CancellationRecordNode)
    created = graphene.Boolean()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_request_id, **input):
        me = info.context.user
        _assert_staff(me)

        if input["cancellation_party"] not in _VALID_PARTIES:
            raise GraphQLError(
                f"cancellation_party must be one of: "
                f"{', '.join(sorted(_VALID_PARTIES))}."
            )
        if input["reason"] not in _VALID_REASONS:
            raise GraphQLError(
                f"reason must be one of: {', '.join(sorted(_VALID_REASONS))}."
            )

        service_request = _resolve_service_request(service_request_id)

        cancelled_by = me
        if input.get("cancelled_by_id"):
            cancelled_by = _resolve_user(input["cancelled_by_id"])

        policy = None
        if input.get("policy_id"):
            policy = _resolve_policy(input["policy_id"])

        defaults = {
            "cancelled_by": cancelled_by,
            "cancellation_party": input["cancellation_party"],
            "reason": input["reason"],
            "reason_description": input.get("reason_description") or "",
            "policy": policy,
        }
        for field in (
            "accepted_at",
            "cancelled_at",
            "minutes_after_acceptance",
            "ride_fare",
            "cancellation_fee",
            "refund_amount",
            "driver_compensation",
            "penalty_applied",
            "penalty_details",
        ):
            if field in input and input[field] is not None:
                defaults[field] = input[field]

        try:
            record, created = CancellationRecord.objects.update_or_create(
                service_request=service_request,
                defaults=defaults,
            )
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            cancellation_record=record,
            created=created,
            success=True,
            message="Cancellation record saved.",
        )


class DeleteCancellationRecord(relay.ClientIDMutation):
    """
    Delete a CancellationRecord.

    Staff-only. The record is the audit trail of who cancelled what;
    deleting it is destructive and should be rare.
    """

    class Input:
        cancellation_record_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, cancellation_record_id):
        _assert_staff(info.context.user)
        record = _resolve_record(cancellation_record_id, lock=True)
        record.delete()
        return cls(success=True, message="Cancellation record deleted.")


# =============================================================================
# Registration
# =============================================================================

class CancellationMutations(graphene.ObjectType):
    upsert_cancellation_policy = UpsertCancellationPolicy.Field()
    delete_cancellation_policy = DeleteCancellationPolicy.Field()

    cancel_service_request_with_policy = CancelServiceRequestWithPolicy.Field()
    upsert_cancellation_record = UpsertCancellationRecord.Field()
    delete_cancellation_record = DeleteCancellationRecord.Field()