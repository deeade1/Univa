# apps/backend/graphq/banking/mutations/payments.py

"""
GraphQL mutations for Banking payments models.

Architecture
------------

All money movement is delegated to:

    banking.services.payment_service.PaymentService

PaymentService posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - mutate Wallet.balance directly
    - call Wallet.debit() or Wallet.credit()  (they no longer exist)
    - post LedgerEntry rows itself
    - call Account.balance.available_balance
    - call Account.balance.debit() or .credit()

Notifications are emitted via:

    banking.services.notification_service

which is a thin wrapper over:

    notifications.events.emitter.emit_notification_event
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
    String,
    relay,
)
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.accounting import AccountingJournal
from banking.models.core import Account
from banking.models.payments import (
    Transaction,
    PaymentStat,
    MoneyTransfer,
    Wallet,
)
from banking.services.payment_service import PaymentService
from graphq.banking.types.payments import (
    TransactionNode,
    PaymentStatNode,
    MoneyTransferNode,
    WalletNode,
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


# ============================================================================
# WALLET — LIFECYCLE
# ============================================================================

class CreateWalletMutation(relay.ClientIDMutation):
    """
    Create a wallet backed by an existing ledger account.

    A wallet is a presentation object. Its balance is derived from
    the linked Account's LedgerEntry rows.
    """

    class Input:
        account_id = ID(required=True)
        wallet_reference = String()
        daily_transaction_limit = GrapheneDecimal()
        single_transaction_limit = GrapheneDecimal()

    wallet = Field(WalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        account = _by_gid(input["account_id"], Account, "Account")

        if account.user_id != user.pk:
            raise GraphQLError("Account does not belong to you.")
        if account.is_system_account:
            raise GraphQLError("Cannot create a wallet over a system account.")
        if hasattr(account, "wallet"):
            raise GraphQLError("This account already has a wallet.")

        reference = (
            input.get("wallet_reference")
            or f"WAL-{timezone.now().strftime('%Y%m%d')}-"
               f"{uuid.uuid4().hex[:6].upper()}"
        )

        wallet = _wrap(
            Wallet.objects.create,
            user=user,
            account=account,
            wallet_reference=reference,
            daily_transaction_limit=Decimal(
                str(input.get("daily_transaction_limit", "500000.00"))
            ),
            single_transaction_limit=Decimal(
                str(input.get("single_transaction_limit", "100000.00"))
            ),
            status="ACTIVE",
        )

        return cls(wallet=wallet, success=True, message="Wallet created.")


class UpdateWalletMutation(relay.ClientIDMutation):
    """
    Update wallet limits and verification.

    The linked account cannot be changed after creation.
    """

    class Input:
        wallet_id = ID(required=True)
        is_verified = Boolean()
        daily_transaction_limit = GrapheneDecimal()
        single_transaction_limit = GrapheneDecimal()
        status = String()

    wallet = Field(WalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        if input.get("is_verified") is not None:
            _staff(user)
            wallet.is_verified = input["is_verified"]

        if input.get("daily_transaction_limit") is not None:
            wallet.daily_transaction_limit = Decimal(
                str(input["daily_transaction_limit"])
            )

        if input.get("single_transaction_limit") is not None:
            wallet.single_transaction_limit = Decimal(
                str(input["single_transaction_limit"])
            )

        if input.get("status"):
            if input["status"] not in dict(Wallet.WALLET_STATUS_CHOICES):
                raise GraphQLError("Invalid wallet status.")
            if input["status"] == "CLOSED" and wallet.balance != Decimal("0.00"):
                raise GraphQLError(
                    "Cannot close a wallet with non-zero balance."
                )
            wallet.status = input["status"]

        _wrap(wallet.full_clean)
        wallet.save()

        return cls(wallet=wallet, success=True, message="Wallet updated.")


class CloseWalletMutation(relay.ClientIDMutation):
    """
    Close a wallet. Deletion is not exposed — Wallet is referenced by
    many models, and closing is the correct lifecycle end.
    """

    class Input:
        wallet_id = ID(required=True)

    wallet = Field(WalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        if wallet.balance != Decimal("0.00"):
            raise GraphQLError(
                "Cannot close a wallet with a non-zero ledger balance."
            )

        wallet.status = "CLOSED"
        wallet.save(update_fields=["status", "updated_at"])

        return cls(wallet=wallet, success=True, message="Wallet closed.")


# ============================================================================
# WALLET — MONEY MOVEMENT
# ============================================================================

class DebitWalletMutation(relay.ClientIDMutation):
    """Debit a wallet. Posts a balanced journal from wallet.account to SETTLEMENT."""

    class Input:
        wallet_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        narration = String()

    wallet = Field(WalletNode)
    transaction = Field(TransactionNode)
    balance_after = GrapheneDecimal()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        service = PaymentService()
        txn = _wrap(
            service.withdraw_from_wallet,
            wallet=wallet,
            amount=Decimal(str(input["amount"])),
            narration=input.get("narration", ""),
        )

        wallet.refresh_from_db()

        return cls(
            wallet=wallet,
            transaction=txn,
            balance_after=wallet.balance,
            success=True,
            message=f"Wallet debited by ₦{txn.amount:,.2f}.",
        )


class CreditWalletMutation(relay.ClientIDMutation):
    """Credit a wallet. Posts a balanced journal from SETTLEMENT to wallet.account."""

    class Input:
        wallet_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        source = String()
        narration = String()

    wallet = Field(WalletNode)
    transaction = Field(TransactionNode)
    balance_after = GrapheneDecimal()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        service = PaymentService()
        txn = _wrap(
            service.fund_wallet,
            wallet=wallet,
            amount=Decimal(str(input["amount"])),
            source=input.get("source", ""),
            narration=input.get("narration", ""),
        )

        wallet.refresh_from_db()

        return cls(
            wallet=wallet,
            transaction=txn,
            balance_after=wallet.balance,
            success=True,
            message=f"Wallet credited by ₦{txn.amount:,.2f}.",
        )


class ValidateWalletTransactionMutation(relay.ClientIDMutation):
    """Dry-run validation. Does not mutate anything."""

    class Input:
        wallet_id = ID(required=True)
        amount = GrapheneDecimal(required=True)

    can_transact = Boolean()
    success = Boolean()
    message = String()
    available_balance = GrapheneDecimal()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")
        _owner(user, wallet, "wallet")

        amount = Decimal(str(input["amount"]))
        balance = wallet.balance

        try:
            wallet.can_transact(amount)
        except ValidationError as exc:
            return cls(
                can_transact=False,
                success=False,
                message=str(exc),
                available_balance=balance,
            )

        if balance < amount:
            return cls(
                can_transact=False,
                success=False,
                message="Insufficient wallet balance.",
                available_balance=balance,
            )

        return cls(
            can_transact=True,
            success=True,
            message="Transaction is allowed.",
            available_balance=balance,
        )


class ResetWalletDailyLimitsMutation(relay.ClientIDMutation):
    """Reset the wallet's daily transaction counters. Staff only."""

    class Input:
        wallet_id = ID(required=True)

    wallet = Field(WalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        wallet = _by_gid(input["wallet_id"], Wallet, "Wallet")

        wallet.daily_transaction_count = 0
        wallet.daily_transaction_amount = Decimal("0.00")
        wallet.last_reset_date = timezone.localdate()
        wallet.save(update_fields=[
            "daily_transaction_count",
            "daily_transaction_amount",
            "last_reset_date",
            "updated_at",
        ])

        return cls(wallet=wallet, success=True, message="Daily limits reset.")


# ============================================================================
# MONEY TRANSFERS
# ============================================================================

class CreateMoneyTransferMutation(relay.ClientIDMutation):
    """
    Create a money transfer.

    Internal: set receiver_id and receiver_account_id.
    External: set recipient_account_number, recipient_bank_code, recipient_name.
    """

    class Input:
        sender_account_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        narration = String()

        receiver_id = ID()
        receiver_account_id = ID()

        recipient_account_number = String()
        recipient_bank_code = String()
        recipient_name = String()

    money_transfer = Field(MoneyTransferNode)
    journal = Field("graphq.banking.types.accounting.AccountingJournalNode")
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        sender_account = _by_gid(
            input["sender_account_id"], Account, "Sender account"
        )
        if sender_account.user_id != user.pk:
            raise GraphQLError("Sender account does not belong to you.")

        amount = Decimal(str(input["amount"]))
        service = PaymentService()

        is_external = bool(input.get("recipient_account_number"))

        if is_external:
            if not (input.get("recipient_bank_code") and input.get("recipient_name")):
                raise GraphQLError(
                    "External transfer requires recipient_bank_code "
                    "and recipient_name."
                )

            transfer = _wrap(
                service.transfer_funds_external,
                sender=user,
                sender_account=sender_account,
                recipient_account_number=input["recipient_account_number"],
                recipient_bank_code=input["recipient_bank_code"],
                recipient_name=input["recipient_name"],
                amount=amount,
                narration=input.get("narration", ""),
            )
        else:
            if not (input.get("receiver_id") and input.get("receiver_account_id")):
                raise GraphQLError(
                    "Internal transfer requires receiver_id "
                    "and receiver_account_id."
                )

            receiver = _by_gid(input["receiver_id"], User, "Receiver")
            receiver_account = _by_gid(
                input["receiver_account_id"], Account, "Receiver account"
            )

            transfer = _wrap(
                service.transfer_funds_internal,
                sender=user,
                recipient=receiver,
                sender_account=sender_account,
                recipient_account=receiver_account,
                amount=amount,
                narration=input.get("narration", ""),
            )

        return cls(
            money_transfer=transfer,
            journal=transfer.journal,
            success=True,
            message="Transfer completed.",
        )


class UpdateMoneyTransferMutation(relay.ClientIDMutation):
    """Update a MoneyTransfer. Staff only."""

    class Input:
        money_transfer_id = ID(required=True)
        status = String()
        bank_reference = String()

    money_transfer = Field(MoneyTransferNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        mt = _by_gid(
            input["money_transfer_id"], MoneyTransfer, "Money transfer"
        )

        if input.get("status"):
            if input["status"] not in dict(Transaction.STATUS_CHOICES):
                raise GraphQLError("Invalid status.")
            mt.status = input["status"]

        if input.get("bank_reference") is not None:
            mt.bank_reference = input["bank_reference"]

        mt.save()

        return cls(
            money_transfer=mt,
            success=True,
            message="Money transfer updated.",
        )


class ReverseMoneyTransferMutation(relay.ClientIDMutation):
    """Reverse a completed transfer. Staff only. Posts a reversal journal."""

    class Input:
        money_transfer_id = ID(required=True)
        reason = String()

    money_transfer = Field(MoneyTransferNode)
    journal = Field("graphq.banking.types.accounting.AccountingJournalNode")
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        mt = _by_gid(
            input["money_transfer_id"], MoneyTransfer, "Money transfer"
        )

        if mt.journal is None:
            raise GraphQLError(
                "Cannot reverse: transfer has no linked journal."
            )
        if mt.status == Transaction.REVERSED:
            raise GraphQLError("Transfer is already reversed.")

        reversal = _wrap(
            PaymentService._reverse_journal,
            mt.journal,
            sender=user,
        )

        mt.status = Transaction.REVERSED
        reason = input.get("reason", "")
        mt.narration = (
            f"{mt.narration} — Reversed: {reason}".strip(" —")
            if reason
            else f"{mt.narration} — Reversed".strip(" —")
        )
        mt.save(update_fields=["status", "narration"])

        return cls(
            money_transfer=mt,
            journal=reversal,
            success=True,
            message="Transfer reversed.",
        )


# ============================================================================
# TRANSACTIONS
# ============================================================================

class UpdateTransactionMutation(relay.ClientIDMutation):
    """Update a Transaction. Staff only. No client-supplied balance_after."""

    class Input:
        transaction_id = ID(required=True)
        status = String()
        provider_reference = String()

    transaction = Field(TransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        txn = _by_gid(input["transaction_id"], Transaction, "Transaction")

        if input.get("status"):
            if input["status"] not in dict(Transaction.STATUS_CHOICES):
                raise GraphQLError("Invalid status.")
            txn.status = input["status"]

        if input.get("provider_reference") is not None:
            txn.provider_reference = input["provider_reference"]

        txn.save()

        return cls(
            transaction=txn,
            success=True,
            message="Transaction updated.",
        )


# ============================================================================
# PAYMENT STATISTICS
# ============================================================================

class UpdatePaymentStatMutation(relay.ClientIDMutation):
    """Update a user's daily/monthly payment limits. Owner or staff only."""

    class Input:
        payment_stat_id = ID(required=True)
        daily_limit = GrapheneDecimal()
        monthly_limit = GrapheneDecimal()

    payment_stat = Field(PaymentStatNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        stat = _by_gid(input["payment_stat_id"], PaymentStat, "Payment stat")
        _owner(user, stat, "payment statistic")

        if input.get("daily_limit") is not None:
            stat.daily_limit = Decimal(str(input["daily_limit"]))

        if input.get("monthly_limit") is not None:
            stat.monthly_limit = Decimal(str(input["monthly_limit"]))

        stat.save()

        return cls(
            payment_stat=stat,
            success=True,
            message="Payment limits updated.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class PaymentsMutations(graphene.ObjectType):
    # Wallet — lifecycle
    create_wallet = CreateWalletMutation.Field()
    update_wallet = UpdateWalletMutation.Field()
    close_wallet = CloseWalletMutation.Field()

    # Wallet — money movement
    debit_wallet = DebitWalletMutation.Field()
    credit_wallet = CreditWalletMutation.Field()
    validate_wallet_transaction = ValidateWalletTransactionMutation.Field()
    reset_wallet_daily_limits = ResetWalletDailyLimitsMutation.Field()

    # Money transfers
    create_money_transfer = CreateMoneyTransferMutation.Field()
    update_money_transfer = UpdateMoneyTransferMutation.Field()
    reverse_money_transfer = ReverseMoneyTransferMutation.Field()

    # Transaction
    update_transaction = UpdateTransactionMutation.Field()

    # Payment statistics
    update_payment_stat = UpdatePaymentStatMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateWalletMutation",
    "UpdateWalletMutation",
    "CloseWalletMutation",
    "DebitWalletMutation",
    "CreditWalletMutation",
    "ValidateWalletTransactionMutation",
    "ResetWalletDailyLimitsMutation",
    "CreateMoneyTransferMutation",
    "UpdateMoneyTransferMutation",
    "ReverseMoneyTransferMutation",
    "UpdateTransactionMutation",
    "UpdatePaymentStatMutation",
    "PaymentsMutations",
]