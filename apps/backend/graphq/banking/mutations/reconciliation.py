# apps/backend/graphq/banking/mutations/reconciliation.py

"""
GraphQL mutations for Banking reconciliation models.

This module contains mutations for:
    - ReconciliationRun: Main reconciliation process run
    - ReconciliationMatch: Matched transactions between internal and external records
    - UnreconciledTransaction: Transactions that couldn't be matched automatically

Money movement
--------------

Reconciliation does NOT move money. It compares internal ledger
records against external bank statements and writes matches and
mismatches. All orchestration is delegated to:

    banking.services.reconciliation_service.ReconciliationService
"""

import logging
from decimal import Decimal
from datetime import datetime
import uuid

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
    Float,
    Int,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.reconciliation import (
    ReconciliationRun,
    ReconciliationMatch,
    UnreconciledTransaction,
)
from banking.models.accounting import FloatAccount
from banking.models.payments import Transaction
from banking.services.reconciliation_service import ReconciliationService
from graphq.accounts.types import UserNode
from graphq.banking.types.reconciliation import (
    ReconciliationRunNode,
    ReconciliationMatchNode,
    UnreconciledTransactionNode,
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
    """Extract a clean single-line message from a ValidationError."""
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _validate_amount(amount):
    """Validate and normalize a monetary amount."""
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")

    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")

    return amount.quantize(Decimal("0.01"))


def _validate_date(date_str):
    """Validate a date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise GraphQLError("Invalid date format. Use YYYY-MM-DD.")


def _validate_datetime(datetime_str):
    """Validate a datetime string."""
    if not datetime_str:
        return None
    try:
        return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    except ValueError:
        raise GraphQLError("Invalid datetime format. Use ISO format.")


# ============================================================================
# RECONCILIATION RUN MUTATIONS
# ============================================================================

class CreateReconciliationRunMutation(relay.ClientIDMutation):
    """Create a new reconciliation run."""

    class Input:
        run_date = String(required=True)
        float_account_ids = graphene.List(ID, required=True)
        date_from = String(required=True)
        date_to = String(required=True)
        config = GenericScalar()

    reconciliation_run = Field(ReconciliationRunNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        run_date = _validate_date(input["run_date"])
        date_from = _validate_date(input["date_from"])
        date_to = _validate_date(input["date_to"])

        if not run_date or not date_from or not date_to:
            raise GraphQLError("Invalid date format.")

        if date_from > date_to:
            raise GraphQLError("date_from cannot be after date_to.")

        float_accounts = []
        for account_id in input["float_account_ids"]:
            fa = _get_model_by_global_id(
                account_id, FloatAccount, "Float account"
            )
            float_accounts.append(fa)

        try:
            reconciliation_run = ReconciliationService.start_run(
                run_date=run_date,
                date_from=date_from,
                date_to=date_to,
                float_accounts=float_accounts,
                created_by=user,
                config=input.get("config") or {},
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            reconciliation_run=reconciliation_run,
            success=True,
            message="Reconciliation run created successfully.",
        )


class RunReconciliationMutation(relay.ClientIDMutation):
    """Execute a reconciliation run."""

    class Input:
        reconciliation_run_id = ID(required=True)

    reconciliation_run = Field(ReconciliationRunNode)
    success = Boolean()
    message = String()
    total_transactions = Int()
    matched_transactions = Int()
    unmatched_transactions = Int()
    total_discrepancy = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        reconciliation_run = _get_model_by_global_id(
            input["reconciliation_run_id"],
            ReconciliationRun,
            "Reconciliation run",
        )

        try:
            reconciliation_run = ReconciliationService.execute_run(
                reconciliation_run=reconciliation_run,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        discrepancy = (
            reconciliation_run.total_discrepancy
            if reconciliation_run.total_discrepancy is not None
            else Decimal("0.00")
        )

        return cls(
            reconciliation_run=reconciliation_run,
            success=True,
            message="Reconciliation completed successfully.",
            total_transactions=reconciliation_run.total_transactions,
            matched_transactions=reconciliation_run.matched_transactions,
            unmatched_transactions=reconciliation_run.unmatched_transactions,
            total_discrepancy=f"{Decimal(discrepancy):.2f}",
        )


class UpdateReconciliationRunMutation(relay.ClientIDMutation):
    """Update a reconciliation run."""

    class Input:
        reconciliation_run_id = ID(required=True)
        config = GenericScalar()
        results = GenericScalar()

    reconciliation_run = Field(ReconciliationRunNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        reconciliation_run = _get_model_by_global_id(
            input["reconciliation_run_id"],
            ReconciliationRun,
            "Reconciliation run",
        )

        if input.get("config") is not None:
            reconciliation_run.config = input["config"]

        if input.get("results") is not None:
            reconciliation_run.results = input["results"]

        try:
            reconciliation_run.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            reconciliation_run=reconciliation_run,
            success=True,
            message="Reconciliation run updated successfully.",
        )


class DeleteReconciliationRunMutation(relay.ClientIDMutation):
    """Delete a reconciliation run."""

    class Input:
        reconciliation_run_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        reconciliation_run = _get_model_by_global_id(
            input["reconciliation_run_id"],
            ReconciliationRun,
            "Reconciliation run",
        )

        if reconciliation_run.matches.exists():
            raise GraphQLError(
                "Cannot delete reconciliation run with existing matches."
            )

        if reconciliation_run.unreconciled_items.exists():
            raise GraphQLError(
                "Cannot delete reconciliation run with existing "
                "unreconciled items."
            )

        reconciliation_run.delete()

        return cls(
            success=True,
            message="Reconciliation run deleted successfully.",
        )


# ============================================================================
# RECONCILIATION MATCH MUTATIONS
# ============================================================================

class CreateReconciliationMatchMutation(relay.ClientIDMutation):
    """Create a manual reconciliation match."""

    class Input:
        reconciliation_run_id = ID(required=True)
        float_account_id = ID(required=True)
        internal_transaction_id = ID()
        internal_amount = GrapheneDecimal(required=True)
        internal_date = String(required=True)
        external_reference = String(required=True)
        external_amount = GrapheneDecimal(required=True)
        external_date = String(required=True)
        external_description = String()
        match_type = String(required=True)
        match_confidence = Float()

    reconciliation_match = Field(ReconciliationMatchNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        reconciliation_run = _get_model_by_global_id(
            input["reconciliation_run_id"],
            ReconciliationRun,
            "Reconciliation run",
        )
        float_account = _get_model_by_global_id(
            input["float_account_id"], FloatAccount, "Float account"
        )

        valid_types = [choice[0] for choice in ReconciliationMatch.MATCH_TYPE]
        if input["match_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid match type. Must be one of: {', '.join(valid_types)}"
            )

        internal_transaction = None
        if input.get("internal_transaction_id"):
            internal_transaction = _get_model_by_global_id(
                input["internal_transaction_id"], Transaction, "Transaction"
            )

        internal_date = _validate_datetime(input["internal_date"])
        external_date = _validate_datetime(input["external_date"])

        if not internal_date or not external_date:
            raise GraphQLError("Invalid date format.")

        internal_amount = _validate_amount(input["internal_amount"])
        external_amount = _validate_amount(input["external_amount"])

        amount_difference = abs(internal_amount - external_amount)
        match_confidence = input.get(
            "match_confidence", 1.0 if amount_difference == 0 else 0.5
        )

        try:
            reconciliation_match = ReconciliationMatch.objects.create(
                reconciliation_run=reconciliation_run,
                float_account=float_account,
                internal_transaction=internal_transaction,
                internal_amount=internal_amount,
                internal_date=internal_date,
                external_reference=input["external_reference"],
                external_amount=external_amount,
                external_date=external_date,
                external_description=input.get("external_description", ""),
                match_type=input["match_type"],
                match_confidence=match_confidence,
                amount_difference=amount_difference,
                matched_by=user,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            reconciliation_match=reconciliation_match,
            success=True,
            message="Reconciliation match created successfully.",
        )


class DeleteReconciliationMatchMutation(relay.ClientIDMutation):
    """Delete a reconciliation match."""

    class Input:
        reconciliation_match_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        reconciliation_match = _get_model_by_global_id(
            input["reconciliation_match_id"],
            ReconciliationMatch,
            "Reconciliation match",
        )

        reconciliation_match.delete()

        return cls(
            success=True,
            message="Reconciliation match deleted successfully.",
        )


# ============================================================================
# UNRECONCILED TRANSACTION MUTATIONS
# ============================================================================

class UpdateUnreconciledTransactionMutation(relay.ClientIDMutation):
    """Update an unreconciled transaction."""

    class Input:
        unreconciled_transaction_id = ID(required=True)
        resolution_status = String(required=True)
        investigation_notes = String()
        assigned_to_id = ID()

    unreconciled_transaction = Field(UnreconciledTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        unreconciled = _get_model_by_global_id(
            input["unreconciled_transaction_id"],
            UnreconciledTransaction,
            "Unreconciled transaction",
        )

        valid_statuses = [
            choice[0] for choice in UnreconciledTransaction.RESOLUTION_STATUS
        ]
        if input["resolution_status"] not in valid_statuses:
            raise GraphQLError(
                f"Invalid resolution status. Must be one of: "
                f"{', '.join(valid_statuses)}"
            )

        unreconciled.resolution_status = input["resolution_status"]

        if input.get("investigation_notes") is not None:
            unreconciled.investigation_notes = input["investigation_notes"]

        if input.get("assigned_to_id"):
            assigned_user = _get_model_by_global_id(
                input["assigned_to_id"], User, "Assigned user"
            )
            unreconciled.assigned_to = assigned_user

        if input["resolution_status"] in ["RESOLVED", "ADJUSTED", "IGNORED"]:
            unreconciled.resolved_at = timezone.now()

        try:
            unreconciled.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            unreconciled_transaction=unreconciled,
            success=True,
            message="Unreconciled transaction updated successfully.",
        )


class AssignUnreconciledTransactionMutation(relay.ClientIDMutation):
    """Assign an unreconciled transaction to a user."""

    class Input:
        unreconciled_transaction_id = ID(required=True)
        assigned_to_id = ID(required=True)

    unreconciled_transaction = Field(UnreconciledTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        unreconciled = _get_model_by_global_id(
            input["unreconciled_transaction_id"],
            UnreconciledTransaction,
            "Unreconciled transaction",
        )
        assigned_user = _get_model_by_global_id(
            input["assigned_to_id"], User, "Assigned user"
        )

        unreconciled.assigned_to = assigned_user
        unreconciled.resolution_status = "INVESTIGATING"

        try:
            unreconciled.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            unreconciled_transaction=unreconciled,
            success=True,
            message="Unreconciled transaction assigned successfully.",
        )


class ResolveUnreconciledTransactionMutation(relay.ClientIDMutation):
    """Resolve an unreconciled transaction."""

    class Input:
        unreconciled_transaction_id = ID(required=True)
        resolution_status = String(required=True)
        investigation_notes = String()

    unreconciled_transaction = Field(UnreconciledTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        unreconciled = _get_model_by_global_id(
            input["unreconciled_transaction_id"],
            UnreconciledTransaction,
            "Unreconciled transaction",
        )

        valid_statuses = ["RESOLVED", "ADJUSTED", "IGNORED"]
        if input["resolution_status"] not in valid_statuses:
            raise GraphQLError(
                f"Resolution status must be one of: "
                f"{', '.join(valid_statuses)}"
            )

        unreconciled.resolution_status = input["resolution_status"]
        unreconciled.resolved_at = timezone.now()

        if input.get("investigation_notes") is not None:
            unreconciled.investigation_notes = input["investigation_notes"]

        try:
            unreconciled.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            unreconciled_transaction=unreconciled,
            success=True,
            message="Unreconciled transaction resolved successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class ReconciliationMutations(graphene.ObjectType):
    # Reconciliation Run
    create_reconciliation_run = CreateReconciliationRunMutation.Field()
    run_reconciliation = RunReconciliationMutation.Field()
    update_reconciliation_run = UpdateReconciliationRunMutation.Field()
    delete_reconciliation_run = DeleteReconciliationRunMutation.Field()

    # Reconciliation Match
    create_reconciliation_match = CreateReconciliationMatchMutation.Field()
    delete_reconciliation_match = DeleteReconciliationMatchMutation.Field()

    # Unreconciled Transaction
    update_unreconciled_transaction = UpdateUnreconciledTransactionMutation.Field()
    assign_unreconciled_transaction = AssignUnreconciledTransactionMutation.Field()
    resolve_unreconciled_transaction = ResolveUnreconciledTransactionMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Reconciliation Run
    "CreateReconciliationRunMutation",
    "RunReconciliationMutation",
    "UpdateReconciliationRunMutation",
    "DeleteReconciliationRunMutation",

    # Reconciliation Match
    "CreateReconciliationMatchMutation",
    "DeleteReconciliationMatchMutation",

    # Unreconciled Transaction
    "UpdateUnreconciledTransactionMutation",
    "AssignUnreconciledTransactionMutation",
    "ResolveUnreconciledTransactionMutation",

    # Registry
    "ReconciliationMutations",
]