# apps/backend/graphq/transport/mutations/promo.py
"""
PromoCode and PromoUsage mutations.

Model facts that shape these mutations:
    - PromoCode.usage_count is a running counter; it is incremented
      server-side whenever a successful PromoUsage is recorded and
      decremented when one is reversed. Clients never set it.
    - PromoCode.is_deleted is a soft-delete flag. Deleting via the API
      sets it True. Hard delete is staff-only and rare.
    - PromoCode.calculate_discount() applies the min_order_value,
      max_discount_amount, and percentage / fixed / free_delivery rules.
      PromoUsage figures come from this, never from client input.
    - PromoCode.can_user_use() counts successful PromoUsages against
      max_uses_per_user. The mutation checks this before recording.

Ownership / staff rules:
    - PromoCode CRUD: staff-only (they affect revenue globally).
    - PromoUsage create: owner only (caller). Staff may create on
      behalf of a user for backfills.
    - Reverse PromoUsage: staff-only (it's a financial correction).
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.promo import (
    PromoCodeNode,
    PromoUsageNode,
)
from graphq.transport.types.service_request import ServiceRequestNode
from graphq.accounts.types.user import UserNode

from transport.models.financial.promo import PromoCode, PromoUsage
from transport.models.core.service_request import ServiceRequest


User = get_user_model()

_VALID_DISCOUNT_TYPES = {c.value for c in PromoCode.DiscountType}
_VALID_APPLICABLE_TO = {c.value for c in PromoCode.ApplicableTo}


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_promo(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid promo_code_id.")
    qs = PromoCode.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except PromoCode.DoesNotExist:
        raise GraphQLError("Promo code not found.")


def _resolve_usage(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid promo_usage_id.")
    qs = PromoUsage.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except PromoUsage.DoesNotExist:
        raise GraphQLError("Promo usage record not found.")


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


def _normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


def _validate_enum(value, allowed, field):
    if value is None:
        return
    if value not in allowed:
        raise GraphQLError(
            f"{field} must be one of: {', '.join(sorted(allowed))}."
        )


def _validate_discount_config(discount_type, discount_value):
    if discount_type == PromoCode.DiscountType.PERCENTAGE:
        if discount_value is None:
            raise GraphQLError("discount_value is required for percentage discounts.")
        if not (0 <= discount_value <= 100):
            raise GraphQLError("discount_value must be between 0 and 100 for percentage discounts.")
    elif discount_type == PromoCode.DiscountType.FIXED:
        if discount_value is None or discount_value < 0:
            raise GraphQLError("discount_value must be >= 0 for fixed discounts.")
    elif discount_type == PromoCode.DiscountType.FREE_DELIVERY:
        # Value is ignored but must still be present in the column.
        pass


def _validate_date_window(start_date, end_date):
    if start_date is None or end_date is None:
        raise GraphQLError("start_date and end_date are required.")
    if end_date <= start_date:
        raise GraphQLError("end_date must be after start_date.")


# =============================================================================
# PromoCode — Create
# =============================================================================

class CreatePromoCode(relay.ClientIDMutation):
    """
    Create a PromoCode. Staff-only.

    `created_by` is the caller. `usage_count` is initialised to 0 and
    incremented only by PromoUsage creation.
    """

    class Input:
        code = graphene.String(required=True)
        description = graphene.String(required=True)
        discount_type = graphene.String(required=True)
        discount_value = graphene.Decimal(required=True)

        min_order_value = graphene.Decimal()
        max_discount_amount = graphene.Decimal()
        applicable_to = graphene.String()

        max_uses_total = graphene.Int()
        max_uses_per_user = graphene.Int()

        start_date = graphene.DateTime()
        end_date = graphene.DateTime(required=True)

        is_active = graphene.Boolean()
        metadata = graphene.JSONString()

    promo_code = graphene.Field(PromoCodeNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        _assert_staff(me)

        _validate_enum(input["discount_type"], _VALID_DISCOUNT_TYPES, "discount_type")
        _validate_enum(input.get("applicable_to"), _VALID_APPLICABLE_TO, "applicable_to")

        discount_value = _parse_decimal(input["discount_value"], "discount_value")
        _validate_discount_config(input["discount_type"], discount_value)

        min_order = _parse_decimal(input.get("min_order_value"), "min_order_value")
        max_discount = _parse_decimal(input.get("max_discount_amount"), "max_discount_amount")
        if min_order is not None and min_order < 0:
            raise GraphQLError("min_order_value cannot be negative.")
        if max_discount is not None and max_discount < 0:
            raise GraphQLError("max_discount_amount cannot be negative.")

        if input.get("max_uses_total") is not None and input["max_uses_total"] < 0:
            raise GraphQLError("max_uses_total cannot be negative.")
        if input.get("max_uses_per_user") is not None and input["max_uses_per_user"] < 1:
            raise GraphQLError("max_uses_per_user must be at least 1.")

        start_date = input.get("start_date") or timezone.now()
        end_date = input["end_date"]
        _validate_date_window(start_date, end_date)

        code = _normalize_code(input["code"])
        if not code:
            raise GraphQLError("code cannot be empty.")
        if PromoCode.objects.filter(code=code).exists():
            raise GraphQLError(f"Promo code '{code}' already exists.")

        payload = {
            "code": code,
            "description": input["description"],
            "discount_type": input["discount_type"],
            "discount_value": discount_value,
            "min_order_value": min_order,
            "max_discount_amount": max_discount,
            "applicable_to": input.get("applicable_to") or PromoCode.ApplicableTo.ALL,
            "max_uses_total": input.get("max_uses_total"),
            "max_uses_per_user": (
                input["max_uses_per_user"]
                if input.get("max_uses_per_user") is not None
                else 1
            ),
            "usage_count": 0,
            "start_date": start_date,
            "end_date": end_date,
            "is_active": (
                input["is_active"] if input.get("is_active") is not None else True
            ),
            "is_deleted": False,
            "created_by": me,
            "metadata": input.get("metadata") or {},
        }

        try:
            promo = PromoCode(**payload)
            promo.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        promo.save()

        return cls(
            promo_code=promo,
            success=True,
            message="Promo code created.",
        )


# =============================================================================
# PromoCode — Update
# =============================================================================

class UpdatePromoCode(relay.ClientIDMutation):
    """
    Update a PromoCode. Staff-only.

    `code` and `usage_count` are not editable — the code is the public
    identifier and the usage count is derived from PromoUsage rows.
    """

    class Input:
        promo_code_id = graphene.ID(required=True)

        description = graphene.String()
        discount_type = graphene.String()
        discount_value = graphene.Decimal()

        min_order_value = graphene.Decimal()
        max_discount_amount = graphene.Decimal()
        applicable_to = graphene.String()

        max_uses_total = graphene.Int()
        max_uses_per_user = graphene.Int()

        start_date = graphene.DateTime()
        end_date = graphene.DateTime()

        is_active = graphene.Boolean()
        metadata = graphene.JSONString()

    promo_code = graphene.Field(PromoCodeNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_code_id, **input):
        _assert_staff(info.context.user)
        promo = _resolve_promo(promo_code_id, lock=True)

        if promo.is_deleted:
            raise GraphQLError("Cannot update a deleted promo code.")

        if input.get("discount_type") is not None:
            _validate_enum(input["discount_type"], _VALID_DISCOUNT_TYPES, "discount_type")
        if input.get("applicable_to") is not None:
            _validate_enum(input["applicable_to"], _VALID_APPLICABLE_TO, "applicable_to")

        # Determine effective values for validation.
        new_discount_type = input.get("discount_type") or promo.discount_type
        new_discount_value = (
            _parse_decimal(input["discount_value"], "discount_value")
            if input.get("discount_value") is not None
            else promo.discount_value
        )
        _validate_discount_config(new_discount_type, new_discount_value)

        if input.get("min_order_value") is not None:
            if _parse_decimal(input["min_order_value"], "min_order_value") < 0:
                raise GraphQLError("min_order_value cannot be negative.")
        if input.get("max_discount_amount") is not None:
            if _parse_decimal(input["max_discount_amount"], "max_discount_amount") < 0:
                raise GraphQLError("max_discount_amount cannot be negative.")
        if input.get("max_uses_total") is not None and input["max_uses_total"] < 0:
            raise GraphQLError("max_uses_total cannot be negative.")
        if input.get("max_uses_per_user") is not None and input["max_uses_per_user"] < 1:
            raise GraphQLError("max_uses_per_user must be at least 1.")

        new_start = input.get("start_date") or promo.start_date
        new_end = input.get("end_date") or promo.end_date
        _validate_date_window(new_start, new_end)

        update_fields = []

        scalar_map = {
            "description": "description",
            "discount_type": "discount_type",
            "applicable_to": "applicable_to",
            "max_uses_total": "max_uses_total",
            "max_uses_per_user": "max_uses_per_user",
            "start_date": "start_date",
            "end_date": "end_date",
            "is_active": "is_active",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(promo, model_field, input[input_key])
                update_fields.append(model_field)

        for input_key, model_field in (
            ("discount_value", "discount_value"),
            ("min_order_value", "min_order_value"),
            ("max_discount_amount", "max_discount_amount"),
        ):
            if input_key in input and input[input_key] is not None:
                setattr(promo, model_field, _parse_decimal(input[input_key], input_key))
                update_fields.append(model_field)

        if "metadata" in input and input["metadata"] is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            promo.metadata = {**(promo.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        if not update_fields:
            return cls(promo_code=promo, success=True, message="Nothing to update.")

        try:
            promo.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        promo.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            promo_code=promo,
            success=True,
            message="Promo code updated.",
        )


# =============================================================================
# PromoCode — Soft delete / Restore / Hard delete
# =============================================================================

class DeletePromoCode(relay.ClientIDMutation):
    """
    Soft-delete a PromoCode. Staff-only.

    Sets `is_deleted=True` and `is_active=False`. Existing PromoUsage
    rows remain attached for audit. Use `RestorePromoCode` to undo.
    """

    class Input:
        promo_code_id = graphene.ID(required=True)

    promo_code = graphene.Field(PromoCodeNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_code_id):
        _assert_staff(info.context.user)
        promo = _resolve_promo(promo_code_id, lock=True)

        if promo.is_deleted:
            return cls(
                promo_code=promo,
                success=True,
                message="Promo code is already deleted.",
            )

        promo.is_deleted = True
        promo.is_active = False
        promo.save(update_fields=["is_deleted", "is_active", "updated_at"])

        return cls(
            promo_code=promo,
            success=True,
            message="Promo code deleted (soft).",
        )


class RestorePromoCode(relay.ClientIDMutation):
    """Undo a soft-delete. Staff-only."""

    class Input:
        promo_code_id = graphene.ID(required=True)
        is_active = graphene.Boolean(default_value=True)

    promo_code = graphene.Field(PromoCodeNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_code_id, is_active=True):
        _assert_staff(info.context.user)
        promo = _resolve_promo(promo_code_id, lock=True)

        promo.is_deleted = False
        promo.is_active = bool(is_active)
        promo.save(update_fields=["is_deleted", "is_active", "updated_at"])

        return cls(
            promo_code=promo,
            success=True,
            message="Promo code restored.",
        )


class HardDeletePromoCode(relay.ClientIDMutation):
    """
    Permanently delete a PromoCode.

    Staff-only. Refuses if any PromoUsage rows reference it — the
    `PromoUsage.promo` FK is CASCADE, so a raw delete would wipe the
    usage history. Reverse those first via `ReversePromoUsage`.
    """

    class Input:
        promo_code_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_code_id):
        _assert_staff(info.context.user)
        promo = _resolve_promo(promo_code_id, lock=True)

        if PromoUsage.objects.filter(promo=promo).exists():
            raise GraphQLError(
                "Cannot hard-delete a promo code with usage history. "
                "Use soft-delete instead, or reverse the usages first."
            )

        promo.delete()
        return cls(success=True, message="Promo code permanently deleted.")


# =============================================================================
# PromoUsage — Apply
# =============================================================================

class ApplyPromoCode(relay.ClientIDMutation):
    """
    Apply a promo code to a service request.

    This is the client-facing operation. The discount and final amount
    are computed server-side from `PromoCode.calculate_discount()` and
    the request's `total_fare` — the client never supplies them.

    Caller must own the ServiceRequest (or be staff).
    A request can only have one successful promo applied.
    """

    class Input:
        promo_code = graphene.String(required=True)
        service_request_id = graphene.ID(required=True)
        user_id = graphene.ID()   # staff-only override

    promo_code = graphene.Field(PromoCodeNode)
    promo_usage = graphene.Field(PromoUsageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_code, service_request_id, user_id=None):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        service_request = _resolve_service_request(service_request_id)

        # Ownership: caller must own the request unless staff.
        if not me.is_staff and service_request.customer_id != me.pk:
            raise GraphQLError("Not authorized to apply a promo to this request.")

        # Target user for the usage record.
        target_user = me
        if user_id:
            if not me.is_staff:
                raise GraphQLError("Only staff may apply on behalf of another user.")
            target_user = _resolve_user(user_id)

        code = _normalize_code(promo_code)
        if not code:
            raise GraphQLError("promo_code cannot be empty.")

        try:
            promo = PromoCode.objects.select_for_update().get(code=code)
        except PromoCode.DoesNotExist:
            raise GraphQLError("Promo code not found.")

        if promo.is_deleted:
            raise GraphQLError("This promo code has been deleted.")
        if not promo.is_valid:
            raise GraphQLError("This promo code is not currently valid.")
        if not promo.can_user_use(target_user):
            raise GraphQLError("You have reached the usage limit for this promo.")

        if PromoUsage.objects.filter(
            service_request=service_request, is_successful=True
        ).exists():
            raise GraphQLError("A promo has already been applied to this request.")

        original_amount = Decimal(str(service_request.total_fare or 0))
        if original_amount <= 0:
            raise GraphQLError("Cannot apply a promo to a zero-fare request.")

        # Optional: compute delivery_fee from the request if this is a
        # free_delivery promo. Callers should extend this when the fee
        # is a distinct line item.
        delivery_fee = Decimal("0.00")

        discount = promo.calculate_discount(original_amount, delivery_fee=delivery_fee)
        if discount <= 0:
            raise GraphQLError(
                "Promo is not applicable to this request "
                "(min order value not met, or discount evaluates to zero)."
            )
        discount = min(discount, original_amount)
        final_amount = (original_amount - discount).quantize(Decimal("0.01"))

        try:
            usage = PromoUsage.objects.create(
                promo=promo,
                user=target_user,
                service_request=service_request,
                discount_amount=discount,
                original_amount=original_amount,
                final_amount=final_amount,
                is_successful=True,
                failure_reason="",
            )
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        # Bump the counter atomically.
        PromoCode.objects.filter(pk=promo.pk).update(
            usage_count=F("usage_count") + 1
        )
        promo.refresh_from_db(fields=["usage_count"])

        # Reflect the discount on the request.
        service_request.total_fare = final_amount
        try:
            service_request.save(update_fields=["total_fare", "updated_at"])
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            promo_code=promo,
            promo_usage=usage,
            success=True,
            message=f"Promo applied. Discount: {discount}.",
        )


class ReversePromoUsage(relay.ClientIDMutation):
    """
    Reverse a previously-applied promo.

    Staff-only — this is a financial correction. Marks the usage as
    unsuccessful, decrements `PromoCode.usage_count`, and restores the
    request's `total_fare` to `original_amount`.
    """

    class Input:
        promo_usage_id = graphene.ID(required=True)
        reason = graphene.String()

    promo_usage = graphene.Field(PromoUsageNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_usage_id, reason=None):
        _assert_staff(info.context.user)
        usage = _resolve_usage(promo_usage_id, lock=True)

        if not usage.is_successful:
            return cls(
                promo_usage=usage,
                success=True,
                message="Usage is already reversed.",
            )

        usage.is_successful = False
        usage.failure_reason = (reason or "Reversed by staff").strip()
        usage.save(update_fields=["is_successful", "failure_reason"])

        PromoCode.objects.filter(pk=usage.promo_id).update(
            usage_count=F("usage_count") - 1
        )

        # Restore the request's fare to the pre-discount amount.
        if usage.service_request_id:
            try:
                service_request = ServiceRequest.objects.select_for_update().get(
                    pk=usage.service_request_id
                )
                service_request.total_fare = usage.original_amount
                service_request.save(update_fields=["total_fare", "updated_at"])
            except ServiceRequest.DoesNotExist:
                pass

        return cls(
            promo_usage=usage,
            success=True,
            message="Promo usage reversed.",
        )


class DeletePromoUsage(relay.ClientIDMutation):
    """
    Hard-delete a PromoUsage row.

    Staff-only, and discouraged. Prefer `ReversePromoUsage` — a hard
    delete silently drifts `PromoCode.usage_count` out of sync unless
    you also decrement it. If you truly need a hard delete, this
    mutation handles the decrement too.
    """

    class Input:
        promo_usage_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, promo_usage_id):
        _assert_staff(info.context.user)
        usage = _resolve_usage(promo_usage_id, lock=True)

        was_successful = usage.is_successful
        promo_id = usage.promo_id
        usage.delete()

        if was_successful:
            PromoCode.objects.filter(pk=promo_id).update(
                usage_count=F("usage_count") - 1
            )

        return cls(success=True, message="Promo usage deleted.")


# =============================================================================
# Registration
# =============================================================================

class PromoMutations(graphene.ObjectType):
    create_promo_code = CreatePromoCode.Field()
    update_promo_code = UpdatePromoCode.Field()
    delete_promo_code = DeletePromoCode.Field()
    restore_promo_code = RestorePromoCode.Field()
    hard_delete_promo_code = HardDeletePromoCode.Field()

    apply_promo_code = ApplyPromoCode.Field()
    reverse_promo_usage = ReversePromoUsage.Field()
    delete_promo_usage = DeletePromoUsage.Field()