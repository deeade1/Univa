# apps/backend/graphq/banking/mutations/merchant.py

"""
GraphQL mutations for Banking merchant models.

Money movement
--------------

Sale, refund, and settlement all delegate to:

    banking.services.merchant_service.MerchantService

which posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - post LedgerEntry rows
    - create Transaction rows for money movement
    - compute fees
    - update merchant aggregates directly

Merchant profile CRUD and verification are metadata operations.
"""

import logging
from datetime import timedelta
from decimal import Decimal
import uuid

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import ID, Boolean, Decimal as GrapheneDecimal, Field, String, relay
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.core import Account, Bank
from banking.models.merchant import Merchant, MerchantTransaction
from banking.services.merchant_service import MerchantService
from graphq.banking.types.merchant import (
    MerchantNode,
    MerchantTransactionNode,
)
from univa_jwt.decorators import login_required

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    """Return the authenticated Django user."""
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _get_model_by_global_id(global_id, model, model_name):
    """Get a model instance by Relay global ID."""
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc


def _clean_message(exc):
    """Return a clean single-line message from a ValidationError."""
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _wrap(fn, *args, **kwargs):
    """Convert service-layer ValidationError into GraphQLError."""
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(_clean_message(exc)) from exc


def _require_staff(user):
    """Raise if the authenticated user is not staff."""
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


# ============================================================================
# MERCHANT MUTATIONS (metadata)
# ============================================================================

class CreateMerchantMutation(relay.ClientIDMutation):
    """Create a merchant account for the authenticated user."""

    class Input:
        business_name = String(required=True)
        business_type = String(required=True)
        business_email = String(required=True)
        business_phone = String(required=True)
        business_address = String(required=True)
        business_state = String(required=True)
        business_city = String(required=True)
        settlement_account_id = ID(required=True)
        settlement_bank_id = ID(required=True)
        business_registration_number = String()
        tax_id = String()
        transaction_fee_percentage = GrapheneDecimal()
        daily_transaction_limit = GrapheneDecimal()
        monthly_transaction_limit = GrapheneDecimal()
        settlement_schedule = String()

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        settlement_account = _get_model_by_global_id(
            input["settlement_account_id"], Account, "Settlement account"
        )
        settlement_bank = _get_model_by_global_id(
            input["settlement_bank_id"], Bank, "Settlement bank"
        )

        valid_types = [choice[0] for choice in Merchant.MERCHANT_TYPES]
        if input["business_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid business type. Must be one of: {', '.join(valid_types)}"
            )

        valid_schedules = ["DAILY", "WEEKLY", "MONTHLY", "INSTANT"]
        settlement_schedule = input.get("settlement_schedule", "DAILY")
        if settlement_schedule not in valid_schedules:
            raise GraphQLError("Invalid settlement schedule.")

        if Merchant.objects.filter(user=user).exists():
            raise GraphQLError("You already have a merchant profile.")

        if Merchant.objects.filter(
            business_name=input["business_name"]
        ).exists():
            raise GraphQLError("Business name is already registered.")

        if settlement_account.user_id != user.pk:
            raise GraphQLError("Settlement account does not belong to you.")

        if settlement_account.is_system_account:
            raise GraphQLError(
                "Settlement account cannot be a system account."
            )

        next_settlement_at = timezone.now()
        if settlement_schedule == "DAILY":
            next_settlement_at = timezone.now() + timedelta(days=1)
        elif settlement_schedule == "WEEKLY":
            next_settlement_at = timezone.now() + timedelta(days=7)
        elif settlement_schedule == "MONTHLY":
            next_settlement_at = timezone.now() + timedelta(days=30)

        try:
            merchant = Merchant.objects.create(
                user=user,
                business_name=input["business_name"],
                business_type=input["business_type"],
                business_email=input["business_email"],
                business_phone=input["business_phone"],
                business_address=input["business_address"],
                business_state=input["business_state"],
                business_city=input["business_city"],
                settlement_account=settlement_account,
                settlement_bank=settlement_bank,
                business_registration_number=input.get(
                    "business_registration_number", ""
                ),
                tax_id=input.get("tax_id", ""),
                transaction_fee_percentage=Decimal(
                    str(input.get("transaction_fee_percentage", "1.5"))
                ),
                daily_transaction_limit=Decimal(
                    str(input.get("daily_transaction_limit", "1000000.00"))
                ),
                monthly_transaction_limit=Decimal(
                    str(input.get("monthly_transaction_limit", "5000000.00"))
                ),
                settlement_schedule=settlement_schedule,
                next_settlement_at=next_settlement_at,
                verification_status="PENDING",
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        from banking.services import notification_service as notify
        notify.emit_merchant_created(user=user, merchant=merchant)

        return cls(
            merchant=merchant,
            success=True,
            message="Merchant account created successfully.",
        )


class UpdateMerchantMutation(relay.ClientIDMutation):
    """Update the authenticated user's merchant account."""

    class Input:
        merchant_id = ID(required=True)
        business_name = String()
        business_email = String()
        business_phone = String()
        business_address = String()
        business_state = String()
        business_city = String()
        business_registration_number = String()
        tax_id = String()
        transaction_fee_percentage = GrapheneDecimal()
        daily_transaction_limit = GrapheneDecimal()
        monthly_transaction_limit = GrapheneDecimal()
        settlement_schedule = String()
        settlement_account_id = ID()
        is_active = Boolean()

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        if merchant.user_id != user.pk:
            raise GraphQLError("You do not own this merchant account.")

        if input.get("business_name"):
            if (
                Merchant.objects
                .filter(business_name=input["business_name"])
                .exclude(pk=merchant.pk)
                .exists()
            ):
                raise GraphQLError("Business name is already registered.")
            merchant.business_name = input["business_name"]

        if input.get("business_email"):
            merchant.business_email = input["business_email"]

        if input.get("business_phone"):
            merchant.business_phone = input["business_phone"]

        if input.get("business_address"):
            merchant.business_address = input["business_address"]

        if input.get("business_state"):
            merchant.business_state = input["business_state"]

        if input.get("business_city"):
            merchant.business_city = input["business_city"]

        if input.get("business_registration_number") is not None:
            merchant.business_registration_number = input[
                "business_registration_number"
            ]

        if input.get("tax_id") is not None:
            merchant.tax_id = input["tax_id"]

        if input.get("transaction_fee_percentage") is not None:
            merchant.transaction_fee_percentage = Decimal(
                str(input["transaction_fee_percentage"])
            )

        if input.get("daily_transaction_limit") is not None:
            merchant.daily_transaction_limit = Decimal(
                str(input["daily_transaction_limit"])
            )

        if input.get("monthly_transaction_limit") is not None:
            merchant.monthly_transaction_limit = Decimal(
                str(input["monthly_transaction_limit"])
            )

        if input.get("settlement_schedule"):
            valid_schedules = ["DAILY", "WEEKLY", "MONTHLY", "INSTANT"]
            if input["settlement_schedule"] not in valid_schedules:
                raise GraphQLError("Invalid settlement schedule.")
            merchant.settlement_schedule = input["settlement_schedule"]

        if input.get("settlement_account_id"):
            settlement_account = _get_model_by_global_id(
                input["settlement_account_id"],
                Account,
                "Settlement account",
            )
            if settlement_account.user_id != merchant.user_id:
                raise GraphQLError(
                    "Settlement account does not belong to this user."
                )
            merchant.settlement_account = settlement_account

        if input.get("is_active") is not None:
            merchant.is_active = input["is_active"]

        try:
            merchant.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            merchant=merchant,
            success=True,
            message="Merchant account updated successfully.",
        )


class VerifyMerchantMutation(relay.ClientIDMutation):
    """Verify a merchant account. Staff only."""

    class Input:
        merchant_id = ID(required=True)

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        merchant.verification_status = "VERIFIED"
        merchant.verified_at = timezone.now()
        merchant.verified_by = user
        merchant.save()

        from banking.services import notification_service as notify
        notify.emit_merchant_verified(user=merchant.user, merchant=merchant)

        return cls(
            merchant=merchant,
            success=True,
            message="Merchant verified successfully.",
        )


class RejectMerchantMutation(relay.ClientIDMutation):
    """Reject a merchant account. Staff only."""

    class Input:
        merchant_id = ID(required=True)
        reason = String(required=True)

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        merchant.verification_status = "REJECTED"
        merchant.is_active = False
        merchant.save()

        from banking.services import notification_service as notify
        notify.emit_merchant_rejected(
            user=merchant.user,
            merchant=merchant,
            reason=input["reason"],
        )

        return cls(
            merchant=merchant,
            success=True,
            message=f"Merchant rejected. Reason: {input['reason']}",
        )


class SuspendMerchantMutation(relay.ClientIDMutation):
    """Suspend a merchant account. Staff only."""

    class Input:
        merchant_id = ID(required=True)
        reason = String(required=True)

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        merchant.verification_status = "SUSPENDED"
        merchant.is_active = False
        merchant.save()

        from banking.services import notification_service as notify
        notify.emit_merchant_suspended(
            user=merchant.user,
            merchant=merchant,
            reason=input["reason"],
        )

        return cls(
            merchant=merchant,
            success=True,
            message=f"Merchant suspended. Reason: {input['reason']}",
        )


class DeleteMerchantMutation(relay.ClientIDMutation):
    """Delete the authenticated user's merchant account."""

    class Input:
        merchant_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        if merchant.user_id != user.pk:
            raise GraphQLError("You do not own this merchant account.")

        if merchant.verification_status == "VERIFIED":
            raise GraphQLError(
                "Cannot delete a verified merchant. Please contact support."
            )

        merchant.delete()

        return cls(
            success=True,
            message="Merchant account deleted successfully.",
        )


class FlagMerchantMutation(relay.ClientIDMutation):
    """Flag a merchant. Staff only."""

    class Input:
        merchant_id = ID(required=True)
        reason = String(required=True)

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        merchant.is_flagged = True
        merchant.save()

        return cls(
            merchant=merchant,
            success=True,
            message=f"Merchant flagged. Reason: {input['reason']}",
        )


class UnflagMerchantMutation(relay.ClientIDMutation):
    """Unflag a merchant. Staff only."""

    class Input:
        merchant_id = ID(required=True)

    merchant = Field(MerchantNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        merchant.is_flagged = False
        merchant.save()

        return cls(
            merchant=merchant,
            success=True,
            message="Merchant unflagged successfully.",
        )


# ============================================================================
# MERCHANT TRANSACTION MUTATIONS (money movement)
# ============================================================================

class RecordMerchantSaleMutation(relay.ClientIDMutation):
    """
    Record a merchant sale.

    Delegates to MerchantService.record_sale, which posts the principal
    journal (customer -> SUSPENSE) and the fee journal (customer -> FEE),
    creates the Transaction and MerchantTransaction rows, and emits a
    notification to the merchant.
    """

    class Input:
        merchant_id = ID(required=True)
        source_account_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        items = GenericScalar()
        reference = String()

    merchant_transaction = Field(MerchantTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )
        source_account = _get_model_by_global_id(
            input["source_account_id"], Account, "Source account"
        )

        if source_account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        merchant_transaction = _wrap(
            MerchantService.record_sale,
            merchant=merchant,
            customer=user,
            customer_account=source_account,
            amount=input["amount"],
            items=input.get("items") or [],
            reference=input.get("reference"),
        )

        return cls(
            merchant_transaction=merchant_transaction,
            success=True,
            message="Merchant sale recorded successfully.",
        )


class RefundMerchantTransactionMutation(relay.ClientIDMutation):
    """
    Refund a merchant sale.

    Delegates to MerchantService.refund, which reverses the principal
    journal (SUSPENSE -> customer) and the fee journal (FEE -> customer).
    """

    class Input:
        merchant_transaction_id = ID(required=True)
        reason = String()

    merchant_transaction = Field(MerchantTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant_transaction = _get_model_by_global_id(
            input["merchant_transaction_id"],
            MerchantTransaction,
            "Merchant transaction",
        )

        if merchant_transaction.merchant.user_id != user.pk:
            raise GraphQLError(
                "You do not own this merchant transaction."
            )

        merchant_transaction = _wrap(
            MerchantService.refund,
            merchant_transaction=merchant_transaction,
            reason=input.get("reason", ""),
        )

        return cls(
            merchant_transaction=merchant_transaction,
            success=True,
            message="Merchant transaction refunded successfully.",
        )


class ProcessMerchantSettlementMutation(relay.ClientIDMutation):
    """
    Settle all unsettled completed sales for a merchant.

    Delegates to MerchantService.process_settlements, which posts one
    settlement journal per transaction (SUSPENSE -> merchant settlement).
    """

    class Input:
        merchant_id = ID(required=True)

    result = GenericScalar()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        if merchant.user_id != user.pk:
            raise GraphQLError("You do not own this merchant account.")

        result = _wrap(
            MerchantService.process_settlements,
            merchant=merchant,
        )

        count = result["count"]
        total_amount = result["total_amount"]

        if count == 0:
            message = "No pending settlements found."
        else:
            message = (
                f"Settled {count} transactions totaling "
                f"₦{total_amount:,.2f}"
            )

        return cls(
            success=True,
            message=message,
            result={
                "count": count,
                "total_amount": str(total_amount),
            },
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class MerchantMutations(graphene.ObjectType):
    # Merchant
    create_merchant = CreateMerchantMutation.Field()
    update_merchant = UpdateMerchantMutation.Field()
    verify_merchant = VerifyMerchantMutation.Field()
    reject_merchant = RejectMerchantMutation.Field()
    suspend_merchant = SuspendMerchantMutation.Field()
    delete_merchant = DeleteMerchantMutation.Field()
    flag_merchant = FlagMerchantMutation.Field()
    unflag_merchant = UnflagMerchantMutation.Field()

    # Merchant Transaction
    record_merchant_sale = RecordMerchantSaleMutation.Field()
    refund_merchant_transaction = RefundMerchantTransactionMutation.Field()
    process_merchant_settlement = ProcessMerchantSettlementMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Merchant
    "CreateMerchantMutation",
    "UpdateMerchantMutation",
    "VerifyMerchantMutation",
    "RejectMerchantMutation",
    "SuspendMerchantMutation",
    "DeleteMerchantMutation",
    "FlagMerchantMutation",
    "UnflagMerchantMutation",

    # Merchant Transaction
    "RecordMerchantSaleMutation",
    "RefundMerchantTransactionMutation",
    "ProcessMerchantSettlementMutation",

    # Registry
    "MerchantMutations",
]