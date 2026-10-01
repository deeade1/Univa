# apps/backend/graphq/banking/mutations/investments.py

"""
GraphQL mutations for Banking investments models.

Architecture
------------

All money movement is delegated to:

    banking.services.investment_service.InvestmentService

InvestmentService posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - mutate Investment money fields directly (they are properties)
    - mutate InvestmentProduct aggregates directly (they are properties)
    - post LedgerEntry rows itself
    - allow clients to set arbitrary Investment.status
    - allow clients to supply actual_return, total_return, etc.

Mutation surface
----------------

Product (staff only):
    create_investment_product
    update_investment_product
    delete_investment_product

Investment:
    create_investment        (owner)
    mature_investment        (staff)
    withdraw_investment      (owner)
    cancel_investment        (owner, PENDING only)

Earnings (staff only):
    pay_investment_earnings
"""

import logging
import uuid
from decimal import Decimal

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import (
    ID,
    Boolean,
    Decimal as GrapheneDecimal,
    Field,
    Int,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.core import Account
from banking.models.investments import (
    Investment,
    InvestmentEarnings,
    InvestmentProduct,
)
from banking.models.payments import Wallet
from banking.services.investment_service import InvestmentService
from graphq.banking.types.investments import (
    InvestmentEarningsNode,
    InvestmentNode,
    InvestmentProductNode,
)
from univa_jwt.decorators import login_required


User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _by_gid(global_id, model, label):
    if not global_id:
        raise GraphQLError(f"{label} ID is required.")
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{label} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {label} ID.") from exc


def _owner(user, obj, label, field="user"):
    owner = getattr(obj, field, None)
    owner_id = getattr(owner, "pk", None)
    if owner_id != user.pk and not user.is_staff:
        raise GraphQLError(f"You do not own this {label}.")


def _staff(user):
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(str(exc)) from exc


def _parse_datetime(value):
    if value is None:
        return None
    if hasattr(value, "tzinfo"):
        return value
    try:
        return timezone.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise GraphQLError(f"Invalid datetime: {value!r}.") from exc


# ============================================================================
# INVESTMENT PRODUCT MUTATIONS (staff only)
# ============================================================================

class CreateInvestmentProductMutation(relay.ClientIDMutation):
    """Create an investment product. Staff only."""

    class Input:
        name = String(required=True)
        slug = String(required=True)
        product_type = String(required=True)
        description = String(required=True)
        risk_level = String(required=True)
        min_investment = GrapheneDecimal(required=True)
        max_investment = GrapheneDecimal()
        min_tenure_days = Int(required=True)
        max_tenure_days = Int(required=True)
        default_tenure_days = Int(required=True)
        interest_rate = GrapheneDecimal(required=True)
        interest_frequency = String()
        compounding = Boolean()
        compounding_frequency = String()
        management_fee = GrapheneDecimal()
        early_withdrawal_fee = GrapheneDecimal()
        is_active = Boolean()
        is_available = Boolean()
        max_capacity = GrapheneDecimal()
        available_from = String(required=True)
        available_until = String()

    product = Field(InvestmentProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        valid_types = [c[0] for c in InvestmentProduct.PRODUCT_TYPES]
        if input["product_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid product_type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        valid_risks = [c[0] for c in InvestmentProduct.RISK_LEVELS]
        if input["risk_level"] not in valid_risks:
            raise GraphQLError(
                f"Invalid risk_level. Must be one of: "
                f"{', '.join(valid_risks)}"
            )

        valid_frequencies = [c[0] for c in InvestmentProduct.FREQUENCY_CHOICES]
        interest_frequency = input.get("interest_frequency", "AT_MATURITY")
        if interest_frequency not in valid_frequencies:
            raise GraphQLError("Invalid interest_frequency.")

        compounding = bool(input.get("compounding", False))
        compounding_frequency = input.get("compounding_frequency")
        if compounding and compounding_frequency:
            if compounding_frequency not in valid_frequencies:
                raise GraphQLError("Invalid compounding_frequency.")

        if InvestmentProduct.objects.filter(slug=input["slug"]).exists():
            raise GraphQLError("A product with this slug already exists.")

        if input["min_tenure_days"] > input["max_tenure_days"]:
            raise GraphQLError(
                "min_tenure_days cannot exceed max_tenure_days."
            )
        if not (
            input["min_tenure_days"]
            <= input["default_tenure_days"]
            <= input["max_tenure_days"]
        ):
            raise GraphQLError(
                "default_tenure_days must be between "
                "min_tenure_days and max_tenure_days."
            )

        available_from = _parse_datetime(input["available_from"])
        if not available_from:
            raise GraphQLError("available_from is required.")
        if available_from.date() < timezone.localdate():
            raise GraphQLError("available_from cannot be in the past.")

        available_until = None
        if input.get("available_until"):
            available_until = _parse_datetime(input["available_until"])
            if available_until <= available_from:
                raise GraphQLError(
                    "available_until must be after available_from."
                )

        min_amount = _wrap(
            lambda v: InvestmentService._validate_amount(v),
            input["min_investment"],
        )
        max_amount = None
        if input.get("max_investment"):
            max_amount = _wrap(
                lambda v: InvestmentService._validate_amount(v),
                input["max_investment"],
            )
            if max_amount < min_amount:
                raise GraphQLError(
                    "max_investment cannot be less than min_investment."
                )

        product = _wrap(
            InvestmentProduct.objects.create,
            name=input["name"],
            slug=input["slug"],
            product_type=input["product_type"],
            description=input["description"],
            risk_level=input["risk_level"],
            min_investment=min_amount,
            max_investment=max_amount,
            min_tenure_days=input["min_tenure_days"],
            max_tenure_days=input["max_tenure_days"],
            default_tenure_days=input["default_tenure_days"],
            interest_rate=Decimal(str(input["interest_rate"])),
            interest_frequency=interest_frequency,
            compounding=compounding,
            compounding_frequency=compounding_frequency,
            management_fee=Decimal(str(input.get("management_fee", "0.00"))),
            early_withdrawal_fee=Decimal(
                str(input.get("early_withdrawal_fee", "0.00"))
            ),
            is_active=input.get("is_active", True),
            is_available=input.get("is_available", True),
            max_capacity=(
                Decimal(str(input["max_capacity"]))
                if input.get("max_capacity")
                else None
            ),
            available_from=available_from,
            available_until=available_until,
        )

        return cls(
            product=product,
            success=True,
            message="Investment product created.",
        )


class UpdateInvestmentProductMutation(relay.ClientIDMutation):
    """Update an investment product. Staff only."""

    class Input:
        product_id = ID(required=True)
        name = String()
        description = String()
        risk_level = String()
        min_investment = GrapheneDecimal()
        max_investment = GrapheneDecimal()
        min_tenure_days = Int()
        max_tenure_days = Int()
        default_tenure_days = Int()
        interest_rate = GrapheneDecimal()
        interest_frequency = String()
        compounding = Boolean()
        compounding_frequency = String()
        management_fee = GrapheneDecimal()
        early_withdrawal_fee = GrapheneDecimal()
        is_active = Boolean()
        is_available = Boolean()
        max_capacity = GrapheneDecimal()
        available_from = String()
        available_until = String()

    product = Field(InvestmentProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        product = _by_gid(
            input["product_id"], InvestmentProduct, "Product"
        )

        if input.get("name"):
            product.name = input["name"]

        if input.get("description") is not None:
            product.description = input["description"]

        if input.get("risk_level"):
            valid_risks = [c[0] for c in InvestmentProduct.RISK_LEVELS]
            if input["risk_level"] not in valid_risks:
                raise GraphQLError("Invalid risk_level.")
            product.risk_level = input["risk_level"]

        if input.get("min_investment") is not None:
            product.min_investment = _wrap(
                InvestmentService._validate_amount,
                input["min_investment"],
            )

        if input.get("max_investment") is not None:
            product.max_investment = (
                _wrap(
                    InvestmentService._validate_amount,
                    input["max_investment"],
                )
                if input["max_investment"]
                else None
            )

        if input.get("min_tenure_days") is not None:
            product.min_tenure_days = input["min_tenure_days"]
        if input.get("max_tenure_days") is not None:
            product.max_tenure_days = input["max_tenure_days"]
        if input.get("default_tenure_days") is not None:
            product.default_tenure_days = input["default_tenure_days"]

        if product.min_tenure_days > product.max_tenure_days:
            raise GraphQLError(
                "min_tenure_days cannot exceed max_tenure_days."
            )

        if input.get("interest_rate") is not None:
            product.interest_rate = Decimal(str(input["interest_rate"]))

        if input.get("interest_frequency"):
            valid = [c[0] for c in InvestmentProduct.FREQUENCY_CHOICES]
            if input["interest_frequency"] not in valid:
                raise GraphQLError("Invalid interest_frequency.")
            product.interest_frequency = input["interest_frequency"]

        if input.get("compounding") is not None:
            product.compounding = input["compounding"]

        if input.get("compounding_frequency") is not None:
            if input["compounding_frequency"]:
                valid = [c[0] for c in InvestmentProduct.FREQUENCY_CHOICES]
                if input["compounding_frequency"] not in valid:
                    raise GraphQLError("Invalid compounding_frequency.")
            product.compounding_frequency = input["compounding_frequency"]

        if input.get("management_fee") is not None:
            product.management_fee = Decimal(str(input["management_fee"]))

        if input.get("early_withdrawal_fee") is not None:
            product.early_withdrawal_fee = Decimal(
                str(input["early_withdrawal_fee"])
            )

        if input.get("is_active") is not None:
            product.is_active = input["is_active"]

        if input.get("is_available") is not None:
            product.is_available = input["is_available"]

        if input.get("max_capacity") is not None:
            product.max_capacity = (
                Decimal(str(input["max_capacity"]))
                if input["max_capacity"]
                else None
            )

        if input.get("available_from"):
            product.available_from = _parse_datetime(input["available_from"])

        if input.get("available_until") is not None:
            product.available_until = (
                _parse_datetime(input["available_until"])
                if input["available_until"]
                else None
            )

        _wrap(product.full_clean)
        product.save()

        return cls(
            product=product,
            success=True,
            message="Investment product updated.",
        )


class DeleteInvestmentProductMutation(relay.ClientIDMutation):
    """Delete an investment product. Staff only."""

    class Input:
        product_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        product = _by_gid(
            input["product_id"], InvestmentProduct, "Product"
        )

        if product.investments.exists():
            raise GraphQLError(
                "Cannot delete a product with existing investments."
            )

        product.delete()

        return cls(
            success=True,
            message="Investment product deleted.",
        )


# ============================================================================
# INVESTMENT MUTATIONS
# ============================================================================

class CreateInvestmentMutation(relay.ClientIDMutation):
    """
    Purchase an investment.

    Delegates entirely to InvestmentService.purchase_investment,
    which posts the ledger journal, creates the Investment row, and
    emits the canonical notification event.
    """

    class Input:
        wallet_id = ID(required=True)
        product_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        tenure_days = Int()

    investment = Field(InvestmentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        product = _by_gid(
            input["product_id"], InvestmentProduct, "Product"
        )

        service = InvestmentService()
        investment = _wrap(
            service.purchase_investment,
            user=user,
            wallet=wallet,
            product=product,
            amount=Decimal(str(input["amount"])),
            tenure_days=input.get("tenure_days"),
        )

        return cls(
            investment=investment,
            success=True,
            message="Investment created.",
        )


class MatureInvestmentMutation(relay.ClientIDMutation):
    """
    Mature an ACTIVE investment. Staff only.

    Delegates to InvestmentService.mature_investment, which posts
    the principal and earnings journals.
    """

    class Input:
        investment_id = ID(required=True)

    investment = Field(InvestmentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        investment = _by_gid(
            input["investment_id"], Investment, "Investment"
        )

        service = InvestmentService()
        investment = _wrap(
            service.mature_investment,
            investment=investment,
        )

        return cls(
            investment=investment,
            success=True,
            message="Investment matured.",
        )


class WithdrawInvestmentMutation(relay.ClientIDMutation):
    """
    Withdraw an ACTIVE investment before maturity.

    Delegates to InvestmentService.withdraw_early, which posts the
    principal + accrued return journal and the fee journal.
    """

    class Input:
        investment_id = ID(required=True)

    investment = Field(InvestmentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        investment = _by_gid(
            input["investment_id"], Investment, "Investment"
        )
        _owner(user, investment, "investment")

        service = InvestmentService()
        investment = _wrap(
            service.withdraw_early,
            investment=investment,
        )

        return cls(
            investment=investment,
            success=True,
            message="Investment withdrawn.",
        )


class CancelInvestmentMutation(relay.ClientIDMutation):
    """
    Cancel a PENDING investment. Only the owner may cancel, and only
    while the investment has not yet been activated.
    """

    class Input:
        investment_id = ID(required=True)
        reason = String()

    investment = Field(InvestmentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        investment = _by_gid(
            input["investment_id"], Investment, "Investment"
        )
        _owner(user, investment, "investment")

        service = InvestmentService()
        investment = _wrap(
            service.cancel_investment,
            investment=investment,
        )

        if input.get("reason"):
            investment.status_reason = input["reason"]
            investment.save(update_fields=["status_reason", "updated_at"])

        return cls(
            investment=investment,
            success=True,
            message="Investment cancelled.",
        )


# ============================================================================
# INVESTMENT EARNINGS MUTATIONS (staff only)
# ============================================================================

class PayInvestmentEarningsMutation(relay.ClientIDMutation):
    """
    Pay an earnings installment to an ACTIVE investment. Staff only.

    Delegates to InvestmentService.pay_earnings, which posts the
    ledger journal from SUSPENSE to the wallet's account and
    creates an InvestmentEarnings row.
    """

    class Input:
        investment_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        period_start = String(required=True)
        period_end = String(required=True)
        earning_type = String()
        description = String()

    earnings = Field(InvestmentEarningsNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        investment = _by_gid(
            input["investment_id"], Investment, "Investment"
        )

        valid_types = [c[0] for c in InvestmentEarnings.EARNING_TYPES]
        earning_type = input.get("earning_type", "INTEREST")
        if earning_type not in valid_types:
            raise GraphQLError(
                f"Invalid earning_type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        period_start = _parse_datetime(input["period_start"])
        period_end = _parse_datetime(input["period_end"])
        if not period_start or not period_end:
            raise GraphQLError("period_start and period_end are required.")
        if period_start > period_end:
            raise GraphQLError("period_start cannot be after period_end.")

        service = InvestmentService()
        earnings = _wrap(
            service.pay_earnings,
            investment=investment,
            amount=Decimal(str(input["amount"])),
            period_start=period_start,
            period_end=period_end,
            earning_type=earning_type,
            description=input.get("description", ""),
        )

        return cls(
            earnings=earnings,
            success=True,
            message="Investment earnings paid.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class InvestmentsMutations(graphene.ObjectType):
    # Product (staff)
    create_investment_product = CreateInvestmentProductMutation.Field()
    update_investment_product = UpdateInvestmentProductMutation.Field()
    delete_investment_product = DeleteInvestmentProductMutation.Field()

    # Investment
    create_investment = CreateInvestmentMutation.Field()
    mature_investment = MatureInvestmentMutation.Field()
    withdraw_investment = WithdrawInvestmentMutation.Field()
    cancel_investment = CancelInvestmentMutation.Field()

    # Earnings (staff)
    pay_investment_earnings = PayInvestmentEarningsMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateInvestmentProductMutation",
    "UpdateInvestmentProductMutation",
    "DeleteInvestmentProductMutation",
    "CreateInvestmentMutation",
    "MatureInvestmentMutation",
    "WithdrawInvestmentMutation",
    "CancelInvestmentMutation",
    "PayInvestmentEarningsMutation",
    "InvestmentsMutations",
]