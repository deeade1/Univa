# apps/backend/graphq/banking/mutations/core.py

"""
GraphQL mutations for Banking core models.

Money movement
--------------

Account creation does NOT move money. It creates an Account, a
BankingSecurity row, and optionally provisions a virtual account
with the chosen partner bank.

Customer self-service
---------------------

    createAccount    — creates an account for the authenticated user

Staff-only
----------

    createAccountForUser   — creates an account for another user
    all Bank mutations      — create / update / delete / metrics
"""

import logging
from decimal import Decimal

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from graphene import (
    Boolean,
    Decimal as GrapheneDecimal,
    Field,
    ID,
    Int,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.core import Account, Bank
from banking.services.account_service import AccountService
from graphq.banking.types.core import AccountNode, BankNode
from univa_jwt.decorators import login_required


logger = logging.getLogger(__name__)

User = get_user_model()


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _require_staff(user):
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


def _get_model_by_global_id(global_id, model, model_name):
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
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(_clean_message(exc)) from exc


# ============================================================================
# BANK MUTATIONS (staff only)
# ============================================================================

class CreateBankMutation(relay.ClientIDMutation):
    class Input:
        name = String(required=True)
        code = String(required=True)
        is_active = Boolean()
        is_virtual_provider = Boolean()
        is_partner_bank = Boolean()
        supports_transfers = Boolean()
        supports_airtime = Boolean()
        supports_bills = Boolean()
        virtual_account_provider = String()
        daily_capacity = Int()
        contact_email = String()
        webhook_url = String()

    bank = Field(BankNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        if Bank.objects.filter(code=input["code"]).exists():
            raise GraphQLError(
                f"Bank with code '{input['code']}' already exists."
            )

        if (
            input.get("is_virtual_provider")
            and not input.get("virtual_account_provider")
        ):
            raise GraphQLError(
                "Virtual account provider is required for virtual banks."
            )

        try:
            bank = Bank.objects.create(
                name=input["name"],
                code=input["code"],
                is_active=input.get("is_active", True),
                is_virtual_provider=input.get(
                    "is_virtual_provider", False
                ),
                is_partner_bank=input.get("is_partner_bank", False),
                supports_transfers=input.get("supports_transfers", True),
                supports_airtime=input.get("supports_airtime", False),
                supports_bills=input.get("supports_bills", False),
                virtual_account_provider=input.get(
                    "virtual_account_provider", ""
                ),
                daily_capacity=input.get("daily_capacity", 0),
                contact_email=input.get("contact_email", ""),
                webhook_url=input.get("webhook_url", ""),
                health_score=100.0,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            bank=bank,
            success=True,
            message=f"Bank '{bank.name}' created successfully.",
        )


class UpdateBankMutation(relay.ClientIDMutation):
    class Input:
        bank_id = ID(required=True)
        name = String()
        code = String()
        is_active = Boolean()
        is_virtual_provider = Boolean()
        is_partner_bank = Boolean()
        supports_transfers = Boolean()
        supports_airtime = Boolean()
        supports_bills = Boolean()
        virtual_account_provider = String()
        daily_capacity = Int()
        contact_email = String()
        webhook_url = String()

    bank = Field(BankNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        bank = _get_model_by_global_id(input["bank_id"], Bank, "Bank")

        if input.get("name"):
            bank.name = input["name"]

        if input.get("code"):
            if (
                Bank.objects
                .filter(code=input["code"])
                .exclude(pk=bank.pk)
                .exists()
            ):
                raise GraphQLError(
                    f"Bank with code '{input['code']}' already exists."
                )
            bank.code = input["code"]

        for field in [
            "is_active",
            "is_virtual_provider",
            "is_partner_bank",
            "supports_transfers",
            "supports_airtime",
            "supports_bills",
            "daily_capacity",
        ]:
            if input.get(field) is not None:
                setattr(bank, field, input[field])

        for field in [
            "virtual_account_provider",
            "contact_email",
            "webhook_url",
        ]:
            if input.get(field) is not None:
                setattr(bank, field, input[field])

        try:
            bank.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            bank=bank,
            success=True,
            message=f"Bank '{bank.name}' updated successfully.",
        )


class DeleteBankMutation(relay.ClientIDMutation):
    class Input:
        bank_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        bank = _get_model_by_global_id(input["bank_id"], Bank, "Bank")

        if bank.accounts.exists():
            bank.is_active = False
            bank.save(update_fields=["is_active", "updated_at"])
            return cls(
                success=True,
                message=(
                    f"Bank '{bank.name}' deactivated. "
                    "It has existing accounts."
                ),
            )

        bank.delete()

        return cls(
            success=True,
            message=f"Bank '{bank.name}' deleted successfully.",
        )


class RecordBankSuccessMutation(relay.ClientIDMutation):
    class Input:
        bank_id = ID(required=True)

    bank = Field(BankNode)
    success = Boolean()
    message = String()
    health_score = GrapheneDecimal()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        bank = _get_model_by_global_id(input["bank_id"], Bank, "Bank")
        bank.record_success()
        bank.refresh_from_db()

        return cls(
            bank=bank,
            success=True,
            message="Bank success recorded.",
            health_score=Decimal(str(bank.health_score)),
        )


class RecordBankFailureMutation(relay.ClientIDMutation):
    class Input:
        bank_id = ID(required=True)

    bank = Field(BankNode)
    success = Boolean()
    message = String()
    health_score = GrapheneDecimal()
    is_disabled = Boolean()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        bank = _get_model_by_global_id(input["bank_id"], Bank, "Bank")
        bank.record_failure()
        bank.refresh_from_db()

        return cls(
            bank=bank,
            success=True,
            message="Bank failure recorded.",
            health_score=Decimal(str(bank.health_score)),
            is_disabled=bank.is_temporarily_disabled,
        )


class ResetBankHealthMutation(relay.ClientIDMutation):
    class Input:
        bank_id = ID(required=True)

    bank = Field(BankNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        bank = _get_model_by_global_id(input["bank_id"], Bank, "Bank")

        bank.health_score = 100.0
        bank.consecutive_failures = 0
        bank.is_temporarily_disabled = False
        bank.disabled_until = None
        bank.save(update_fields=[
            "health_score",
            "consecutive_failures",
            "is_temporarily_disabled",
            "disabled_until",
            "updated_at",
        ])
        bank.refresh_from_db()

        return cls(
            bank=bank,
            success=True,
            message="Bank health reset successfully.",
        )


# ============================================================================
# ACCOUNT MUTATIONS
# ============================================================================

class CreateAccountMutation(relay.ClientIDMutation):
    """
    Create a banking account for the authenticated user.

    The account number is the user's phone number with the leading
    zero stripped. This mirrors OPay, Moniepoint, and PalmPay.
    """

    class Input:
        bank_id = ID()
        account_name = String()
        daily_limit = GrapheneDecimal()
        single_transaction_limit = GrapheneDecimal()
        create_virtual_account = Boolean()

    account = Field(AccountNode)
    virtual_account_data = GenericScalar()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        bank = None
        if input.get("bank_id"):
            bank = _get_model_by_global_id(
                input["bank_id"], Bank, "Bank"
            )

        account = _wrap(
            AccountService.create_account,
            user=user,
            bank=bank,
            account_name=input.get("account_name"),
            daily_limit=input.get("daily_limit"),
            single_transaction_limit=input.get(
                "single_transaction_limit"
            ),
            created_by=user,
            provision_virtual_account=bool(
                input.get("create_virtual_account", False)
            ),
        )

        virtual_account_data = None
        if input.get("create_virtual_account"):
            virtual_account_data = {
                "provider_reference": account.provider_reference,
                "nuban_number": account.nuban_number,
            }

        return cls(
            account=account,
            virtual_account_data=virtual_account_data,
            success=True,
            message="Account created successfully.",
        )


class CreateAccountForUserMutation(relay.ClientIDMutation):
    """
    Create a banking account for another user. Staff only.

    Used for provisioning and back-office workflows. Customer
    self-service uses CreateAccountMutation instead.
    """

    class Input:
        user_id = ID(required=True)
        bank_id = ID()
        account_name = String()
        daily_limit = GrapheneDecimal()
        single_transaction_limit = GrapheneDecimal()
        create_virtual_account = Boolean()

    account = Field(AccountNode)
    virtual_account_data = GenericScalar()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        actor = _get_authenticated_user(info)
        _require_staff(actor)

        target_user = _get_model_by_global_id(
            input["user_id"], User, "User"
        )

        bank = None
        if input.get("bank_id"):
            bank = _get_model_by_global_id(
                input["bank_id"], Bank, "Bank"
            )

        account = _wrap(
            AccountService.create_account,
            user=target_user,
            bank=bank,
            account_name=input.get("account_name"),
            daily_limit=input.get("daily_limit"),
            single_transaction_limit=input.get(
                "single_transaction_limit"
            ),
            created_by=actor,
            provision_virtual_account=bool(
                input.get("create_virtual_account", False)
            ),
        )

        virtual_account_data = None
        if input.get("create_virtual_account"):
            virtual_account_data = {
                "provider_reference": account.provider_reference,
                "nuban_number": account.nuban_number,
            }

        return cls(
            account=account,
            virtual_account_data=virtual_account_data,
            success=True,
            message=(
                f"Account created successfully for {target_user.email}."
            ),
        )


class UpdateAccountMutation(relay.ClientIDMutation):
    class Input:
        account_id = ID(required=True)
        account_name = String()
        phone_number = String()
        daily_limit = GrapheneDecimal()
        single_transaction_limit = GrapheneDecimal()
        status = String()
        can_send_external = Boolean()
        can_receive_external = Boolean()

    account = Field(AccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )

        if account.user_id != user.pk and not user.is_staff:
            raise GraphQLError("You do not own this account.")

        if input.get("account_name"):
            account.account_name = input["account_name"]

        if input.get("phone_number"):
            if (
                Account.objects
                .filter(phone_number=input["phone_number"])
                .exclude(pk=account.pk)
                .exists()
            ):
                raise GraphQLError("Phone number already in use.")
            account.phone_number = input["phone_number"]

        if input.get("daily_limit"):
            daily_limit = Decimal(str(input["daily_limit"]))
            if daily_limit < Decimal("0.00"):
                raise GraphQLError("Daily limit cannot be negative.")
            account.daily_limit = daily_limit

        if input.get("single_transaction_limit"):
            single_limit = Decimal(
                str(input["single_transaction_limit"])
            )
            if single_limit < Decimal("0.00"):
                raise GraphQLError(
                    "Single transaction limit cannot be negative."
                )
            if single_limit > account.daily_limit:
                raise GraphQLError(
                    "Single transaction limit cannot exceed "
                    "daily limit."
                )
            account.single_transaction_limit = single_limit

        if input.get("status"):
            valid_statuses = [
                choice[0] for choice in Account.STATUS_CHOICES
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError(
                    f"Invalid status. Must be one of: "
                    f"{', '.join(valid_statuses)}"
                )
            account.status = input["status"]

        if input.get("can_send_external") is not None:
            if account.is_system_account:
                raise GraphQLError(
                    "System accounts cannot send external transfers."
                )
            account.can_send_external = input["can_send_external"]

        if input.get("can_receive_external") is not None:
            if account.is_system_account:
                raise GraphQLError(
                    "System accounts cannot receive external transfers."
                )
            account.can_receive_external = input["can_receive_external"]

        try:
            account.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            account=account,
            success=True,
            message="Account updated successfully.",
        )


class DeleteAccountMutation(relay.ClientIDMutation):
    class Input:
        account_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )

        if account.user_id != user.pk and not user.is_staff:
            raise GraphQLError("You do not own this account.")

        if account.is_system_account:
            raise GraphQLError("Cannot delete system account.")

        if account.get_balance() != Decimal("0.00"):
            raise GraphQLError(
                "Cannot delete account with non-zero balance."
            )

        if account.ledger_entries.exists():
            raise GraphQLError(
                "Cannot delete account with ledger history."
            )

        account.delete()

        return cls(
            success=True,
            message="Account deleted successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class CoreMutations(graphene.ObjectType):
    # Bank (staff)
    create_bank = CreateBankMutation.Field()
    update_bank = UpdateBankMutation.Field()
    delete_bank = DeleteBankMutation.Field()
    record_bank_success = RecordBankSuccessMutation.Field()
    record_bank_failure = RecordBankFailureMutation.Field()
    reset_bank_health = ResetBankHealthMutation.Field()

    # Account (customer self-service)
    create_account = CreateAccountMutation.Field()
    create_account_for_user = CreateAccountForUserMutation.Field()
    update_account = UpdateAccountMutation.Field()
    delete_account = DeleteAccountMutation.Field()


__all__ = [
    "CreateBankMutation",
    "UpdateBankMutation",
    "DeleteBankMutation",
    "RecordBankSuccessMutation",
    "RecordBankFailureMutation",
    "ResetBankHealthMutation",
    "CreateAccountMutation",
    "CreateAccountForUserMutation",
    "UpdateAccountMutation",
    "DeleteAccountMutation",
    "CoreMutations",
]