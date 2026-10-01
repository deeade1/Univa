# apps/backend/graphq/banking/mutations/savings.py

"""
GraphQL mutations for Banking savings models.

Architecture
------------

All money movement is delegated to:

    banking.services.savings_service.SavingsService

SavingsService posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - mutate SavingsGoal.current_amount directly (it is a property)
    - mutate SavingsGoal.interest_earned directly (it is a property)
    - mutate AutoSaveRule.total_amount_saved directly (property)
    - post LedgerEntry rows itself
    - allow clients to set arbitrary savings balances

Mutation surface
----------------

SavingsGoal:
    create_savings_goal       (owner)
    update_savings_goal       (owner, metadata only)
    delete_savings_goal       (owner, only if balance is zero)

SavingsTransaction:
    deposit_to_savings_goal   (owner) -- delegates to SavingsService
    withdraw_from_savings_goal (owner) -- delegates to SavingsService

AutoSaveRule:
    create_auto_save_rule     (owner)
    update_auto_save_rule     (owner)
    delete_auto_save_rule     (owner)
    execute_auto_save_rule    (owner) -- delegates to SavingsService
"""

import logging
from decimal import Decimal

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
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
from banking.models.savings import (
    AutoSaveRule,
    SavingsGoal,
    SavingsTransaction,
)
from banking.services.savings_service import SavingsService
from graphq.banking.types.savings import (
    AutoSaveRuleNode,
    SavingsGoalNode,
    SavingsTransactionNode,
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


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(str(exc)) from exc


def _parse_date(value):
    if value is None:
        return None
    if hasattr(value, "year"):
        return value
    try:
        return __import__("datetime").date.fromisoformat(str(value))
    except ValueError as exc:
        raise GraphQLError(f"Invalid date: {value!r}.") from exc


# ============================================================================
# SAVINGS GOAL MUTATIONS
# ============================================================================

class CreateSavingsGoalMutation(relay.ClientIDMutation):
    """
    Create a savings goal and its ledger-backed account.

    Delegates to SavingsService.create_savings_goal, which creates
    the Account, the SavingsGoal, and links them atomically.
    """

    class Input:
        name = String(required=True)
        description = String()
        goal_type = String(required=True)
        target_amount = GrapheneDecimal(required=True)
        target_date = String(required=True)
        savings_method = String()
        fixed_amount = GrapheneDecimal()
        percentage = GrapheneDecimal()
        round_up_multiplier = Int()
        frequency = String()
        source_account_id = ID(required=True)
        is_auto_save = Boolean()
        is_locked = Boolean()
        locked_until = String()
        lock_reason = String()
        interest_rate = GrapheneDecimal()

    savings_goal = Field(SavingsGoalNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        valid_types = [c[0] for c in SavingsGoal.GOAL_TYPES]
        if input["goal_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid goal_type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        valid_methods = [c[0] for c in SavingsGoal.SAVINGS_METHODS]
        savings_method = input.get("savings_method", "FIXED_AMOUNT")
        if savings_method not in valid_methods:
            raise GraphQLError(
                f"Invalid savings_method. Must be one of: "
                f"{', '.join(valid_methods)}"
            )

        target_date = _parse_date(input["target_date"])
        if not target_date:
            raise GraphQLError("target_date is required.")

        locked_until = None
        if input.get("locked_until"):
            locked_until = _parse_date(input["locked_until"])

        source_account = _by_gid(
            input["source_account_id"], Account, "Source account"
        )

        service = SavingsService()
        goal = _wrap(
            service.create_savings_goal,
            user=user,
            source_account=source_account,
            name=input["name"],
            target_amount=Decimal(str(input["target_amount"])),
            target_date=target_date,
            goal_type=input["goal_type"],
            savings_method=savings_method,
            description=input.get("description", ""),
            fixed_amount=(
                Decimal(str(input["fixed_amount"]))
                if input.get("fixed_amount")
                else None
            ),
            percentage=(
                Decimal(str(input["percentage"]))
                if input.get("percentage")
                else None
            ),
            round_up_multiplier=input.get("round_up_multiplier", 1),
            frequency=input.get("frequency", ""),
            is_auto_save=input.get("is_auto_save", False),
            is_locked=input.get("is_locked", False),
            locked_until=locked_until,
            lock_reason=input.get("lock_reason", ""),
            interest_rate=(
                Decimal(str(input["interest_rate"]))
                if input.get("interest_rate")
                else None
            ),
        )

        return cls(
            savings_goal=goal,
            success=True,
            message="Savings goal created.",
        )


class UpdateSavingsGoalMutation(relay.ClientIDMutation):
    """
    Update a savings goal's metadata. Money movement is NOT permitted
    through this mutation.
    """

    class Input:
        savings_goal_id = ID(required=True)
        name = String()
        description = String()
        target_amount = GrapheneDecimal()
        target_date = String()
        savings_method = String()
        fixed_amount = GrapheneDecimal()
        percentage = GrapheneDecimal()
        round_up_multiplier = Int()
        frequency = String()
        is_auto_save = Boolean()
        is_locked = Boolean()
        locked_until = String()
        lock_reason = String()
        interest_rate = GrapheneDecimal()
        is_active = Boolean()

    savings_goal = Field(SavingsGoalNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        goal = _by_gid(input["savings_goal_id"], SavingsGoal, "Savings goal")
        _owner(user, goal, "savings goal")

        if input.get("name"):
            goal.name = input["name"]

        if input.get("description") is not None:
            goal.description = input["description"]

        if input.get("target_amount"):
            goal.target_amount = Decimal(str(input["target_amount"]))

        if input.get("target_date"):
            goal.target_date = _parse_date(input["target_date"])

        if input.get("savings_method"):
            valid = [c[0] for c in SavingsGoal.SAVINGS_METHODS]
            if input["savings_method"] not in valid:
                raise GraphQLError("Invalid savings_method.")
            goal.savings_method = input["savings_method"]

        if input.get("fixed_amount") is not None:
            goal.fixed_amount = (
                Decimal(str(input["fixed_amount"]))
                if input["fixed_amount"]
                else None
            )

        if input.get("percentage") is not None:
            goal.percentage = (
                Decimal(str(input["percentage"]))
                if input["percentage"]
                else None
            )

        if input.get("round_up_multiplier") is not None:
            goal.round_up_multiplier = input["round_up_multiplier"]

        if input.get("frequency") is not None:
            goal.frequency = input["frequency"] or ""

        if input.get("is_auto_save") is not None:
            goal.is_auto_save = input["is_auto_save"]

        if input.get("is_locked") is not None:
            goal.is_locked = input["is_locked"]

        if input.get("locked_until") is not None:
            goal.locked_until = (
                _parse_date(input["locked_until"])
                if input["locked_until"]
                else None
            )

        if input.get("lock_reason") is not None:
            goal.lock_reason = input["lock_reason"]

        if input.get("interest_rate") is not None:
            goal.interest_rate = Decimal(str(input["interest_rate"]))

        if input.get("is_active") is not None:
            goal.is_active = input["is_active"]

        _wrap(goal.full_clean)
        goal.save()

        return cls(
            savings_goal=goal,
            success=True,
            message="Savings goal updated.",
        )


class DeleteSavingsGoalMutation(relay.ClientIDMutation):
    """
    Delete a savings goal. Refused if the goal still holds funds.
    """

    class Input:
        savings_goal_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        goal = _by_gid(input["savings_goal_id"], SavingsGoal, "Savings goal")
        _owner(user, goal, "savings goal")

        if goal.current_amount != Decimal("0.00"):
            raise GraphQLError(
                "Cannot delete a savings goal with funds. "
                "Withdraw first."
            )

        goal.delete()

        return cls(
            success=True,
            message="Savings goal deleted.",
        )


# ============================================================================
# SAVINGS TRANSACTION MUTATIONS
# ============================================================================

class DepositToSavingsGoalMutation(relay.ClientIDMutation):
    """
    Deposit into a savings goal. Delegates to SavingsService.
    """

    class Input:
        savings_goal_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        description = String()

    savings_goal = Field(SavingsGoalNode)
    savings_transaction = Field(SavingsTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        goal = _by_gid(input["savings_goal_id"], SavingsGoal, "Savings goal")
        _owner(user, goal, "savings goal")

        service = SavingsService()
        savings_tx = _wrap(
            service.deposit_to_goal,
            goal=goal,
            amount=Decimal(str(input["amount"])),
            description=input.get("description", ""),
            is_auto_save=False,
        )

        goal.refresh_from_db()

        return cls(
            savings_goal=goal,
            savings_transaction=savings_tx,
            success=True,
            message=f"Deposited ₦{savings_tx.amount:,.2f}.",
        )


class WithdrawFromSavingsGoalMutation(relay.ClientIDMutation):
    """
    Withdraw from a savings goal. Delegates to SavingsService.
    """

    class Input:
        savings_goal_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        description = String()

    savings_goal = Field(SavingsGoalNode)
    savings_transaction = Field(SavingsTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        goal = _by_gid(input["savings_goal_id"], SavingsGoal, "Savings goal")
        _owner(user, goal, "savings goal")

        service = SavingsService()
        savings_tx = _wrap(
            service.withdraw_from_goal,
            goal=goal,
            amount=Decimal(str(input["amount"])),
            description=input.get("description", ""),
        )

        goal.refresh_from_db()

        return cls(
            savings_goal=goal,
            savings_transaction=savings_tx,
            success=True,
            message=f"Withdrew ₦{savings_tx.amount:,.2f}.",
        )


# ============================================================================
# AUTO SAVE RULE MUTATIONS
# ============================================================================

class CreateAutoSaveRuleMutation(relay.ClientIDMutation):
    """Create an auto-save rule. Metadata only."""

    class Input:
        goal_id = ID(required=True)
        rule_type = String(required=True)
        parameters = GenericScalar()
        is_active = Boolean()

    auto_save_rule = Field(AutoSaveRuleNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        goal = _by_gid(input["goal_id"], SavingsGoal, "Savings goal")
        _owner(user, goal, "savings goal")

        valid_types = [c[0] for c in AutoSaveRule.RULE_TYPES]
        if input["rule_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid rule_type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        rule = _wrap(
            AutoSaveRule.objects.create,
            user=user,
            goal=goal,
            rule_type=input["rule_type"],
            parameters=input.get("parameters", {}),
            is_active=input.get("is_active", True),
        )

        return cls(
            auto_save_rule=rule,
            success=True,
            message="Auto-save rule created.",
        )


class UpdateAutoSaveRuleMutation(relay.ClientIDMutation):
    """Update an auto-save rule."""

    class Input:
        auto_save_rule_id = ID(required=True)
        parameters = GenericScalar()
        is_active = Boolean()

    auto_save_rule = Field(AutoSaveRuleNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        rule = _by_gid(
            input["auto_save_rule_id"], AutoSaveRule, "Auto-save rule"
        )
        _owner(user, rule, "auto-save rule")

        if input.get("parameters") is not None:
            rule.parameters = input["parameters"]

        if input.get("is_active") is not None:
            rule.is_active = input["is_active"]

        _wrap(rule.full_clean)
        rule.save()

        return cls(
            auto_save_rule=rule,
            success=True,
            message="Auto-save rule updated.",
        )


class DeleteAutoSaveRuleMutation(relay.ClientIDMutation):
    """Delete an auto-save rule."""

    class Input:
        auto_save_rule_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        rule = _by_gid(
            input["auto_save_rule_id"], AutoSaveRule, "Auto-save rule"
        )
        _owner(user, rule, "auto-save rule")

        rule.delete()

        return cls(
            success=True,
            message="Auto-save rule deleted.",
        )


class ExecuteAutoSaveRuleMutation(relay.ClientIDMutation):
    """
    Execute an auto-save rule once.

    The amount to save is calculated from the rule's parameters.
    This is intentionally simple: the rule carries a `amount` key
    in its parameters, or we fall back to the goal's `fixed_amount`.
    """

    class Input:
        auto_save_rule_id = ID(required=True)
        amount = GrapheneDecimal()
        description = String()

    savings_goal = Field(SavingsGoalNode)
    savings_transaction = Field(SavingsTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        rule = _by_gid(
            input["auto_save_rule_id"], AutoSaveRule, "Auto-save rule"
        )
        _owner(user, rule, "auto-save rule")

        # Amount precedence: explicit input -> rule.parameters.amount
        # -> goal.fixed_amount.
        if input.get("amount"):
            amount = Decimal(str(input["amount"]))
        elif isinstance(rule.parameters, dict) and rule.parameters.get("amount"):
            amount = Decimal(str(rule.parameters["amount"]))
        elif rule.goal.fixed_amount:
            amount = rule.goal.fixed_amount
        else:
            raise GraphQLError(
                "Auto-save amount is required and could not be derived."
            )

        service = SavingsService()
        savings_tx = _wrap(
            service.execute_auto_save,
            rule=rule,
            amount=amount,
            description=input.get("description", ""),
        )

        rule.goal.refresh_from_db()

        return cls(
            savings_goal=rule.goal,
            savings_transaction=savings_tx,
            success=True,
            message=f"Auto-save executed: ₦{savings_tx.amount:,.2f}.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class SavingsMutations(graphene.ObjectType):
    # Savings Goal
    create_savings_goal = CreateSavingsGoalMutation.Field()
    update_savings_goal = UpdateSavingsGoalMutation.Field()
    delete_savings_goal = DeleteSavingsGoalMutation.Field()

    # Savings Transaction
    deposit_to_savings_goal = DepositToSavingsGoalMutation.Field()
    withdraw_from_savings_goal = WithdrawFromSavingsGoalMutation.Field()

    # Auto Save Rule
    create_auto_save_rule = CreateAutoSaveRuleMutation.Field()
    update_auto_save_rule = UpdateAutoSaveRuleMutation.Field()
    delete_auto_save_rule = DeleteAutoSaveRuleMutation.Field()
    execute_auto_save_rule = ExecuteAutoSaveRuleMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateSavingsGoalMutation",
    "UpdateSavingsGoalMutation",
    "DeleteSavingsGoalMutation",
    "DepositToSavingsGoalMutation",
    "WithdrawFromSavingsGoalMutation",
    "CreateAutoSaveRuleMutation",
    "UpdateAutoSaveRuleMutation",
    "DeleteAutoSaveRuleMutation",
    "ExecuteAutoSaveRuleMutation",
    "SavingsMutations",
]