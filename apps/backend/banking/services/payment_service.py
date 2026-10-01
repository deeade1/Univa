# apps/backend/banking/services/payment_service.py

"""
Payment orchestration service.

Every money movement flows through:

    PaymentService
        -> AccountingManager.create_double_entry
            -> AccountingJournal
            -> LedgerEntry (debit)
            -> LedgerEntry (credit)

The service does NOT mutate stored balances. It does NOT call
Account.balance.available_balance, Account.balance.debit(),
Account.balance.credit(), Wallet.debit(), or Wallet.credit().

Transaction records (banking.models.payments.Transaction) are linked to
their journal via Transaction.journal.

Notifications are emitted via the canonical Univa notification system:

    banking.services.notification_service
        -> notifications.events.emitter.emit_notification_event

Fraud checks, limit checks, ledger posting, notification emission, and
webhook dispatch all occur inside the same database transaction, so
that a failure in any step rolls back the entire money movement.
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from banking.models.accounting import (
    AccountingJournal,
    AccountingManager,
)
from banking.models.core import Account
from banking.models.payments import (
    MoneyTransfer,
    PaymentStat,
    Transaction,
)
from banking.services.fraud_service import FraudDetectionService
from banking.services import notification_service as notify
from banking.services.webhook_service import WebhookService


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")
EXTERNAL_FEE_PCT = Decimal("0.015")
EXTERNAL_FEE_MIN = Decimal("50.00")


class PaymentService:

    def __init__(self):
        self.fraud_service = FraudDetectionService()
        self.webhook_service = WebhookService()

    # ---------------------------------------------------------------- internal

    @db_transaction.atomic
    def transfer_funds_internal(
        self,
        *,
        sender,
        recipient,
        sender_account,
        recipient_account,
        amount,
        narration="",
    ) -> MoneyTransfer:
        amount = self._validate_amount(amount)
        self._validate_account(sender_account, "Sender")
        self._validate_account(recipient_account, "Recipient")

        if sender.pk == recipient.pk:
            raise ValidationError("Cannot transfer to yourself.")

        if sender_account.pk == recipient_account.pk:
            raise ValidationError(
                "Sender and recipient accounts must be different."
            )

        self._run_fraud_check(sender, amount, kind="internal_transfer")
        self._check_transaction_limits(sender, amount)

        if sender_account.get_balance() < amount:
            raise ValidationError("Insufficient funds.")

        transaction = Transaction.objects.create(
            account=sender_account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=narration,
            recipient_account_number=recipient_account.nuban_number,
            recipient_bank_code=recipient_account.bank.code,
            recipient_name=recipient_account.account_name,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=sender_account,
            credit_account=recipient_account,
            amount=amount,
            description=narration or "Internal transfer",
            journal_type=AccountingJournal.TRANSFER,
            created_by=sender,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = sender_account.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        money_transfer = MoneyTransfer.objects.create(
            sender=sender,
            receiver=recipient,
            sender_account=sender_account,
            receiver_account=recipient_account,
            amount=amount,
            fee=Decimal("0.00"),
            reference=transaction.reference,
            status=Transaction.SUCCESS,
            narration=narration,
            journal=journal,
        )

        self._update_payment_stats(sender, amount)

        notify.emit_transfer_initiated(sender=sender, money_transfer=money_transfer)
        notify.emit_transfer_succeeded(sender=sender, money_transfer=money_transfer)
        notify.emit_transfer_received(recipient=recipient, money_transfer=money_transfer)

        self.webhook_service.send_webhook(
            event_type="transfer.completed",
            payload={
                "reference": transaction.reference,
                "amount": str(amount),
                "sender_id": sender.pk,
                "recipient_id": recipient.pk,
            },
        )

        return money_transfer

    # ---------------------------------------------------------------- external

    @db_transaction.atomic
    def transfer_funds_external(
        self,
        *,
        sender,
        sender_account,
        recipient_account_number,
        recipient_bank_code,
        recipient_name,
        amount,
        narration="",
    ) -> MoneyTransfer:
        amount = self._validate_amount(amount)
        self._validate_account(sender_account, "Sender")

        if not sender_account.can_send_external:
            raise ValidationError(
                "Account does not support external transfers."
            )

        self._run_fraud_check(sender, amount, kind="external_transfer")
        self._check_transaction_limits(sender, amount)

        fee = self._external_fee(amount)
        total = amount + fee

        if sender_account.get_balance() < total:
            raise ValidationError(
                f"Insufficient funds including ₦{fee:,.2f} fee."
            )

        float_account = AccountingManager.get_settlement_account()
        fee_account = AccountingManager.get_fee_account()

        transaction = Transaction.objects.create(
            account=sender_account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=narration,
            recipient_account_number=recipient_account_number,
            recipient_bank_code=recipient_bank_code,
            recipient_name=recipient_name,
            fee=fee,
            status=Transaction.PENDING,
        )

        principal_journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=sender_account,
            credit_account=float_account,
            amount=amount,
            description=narration or f"External transfer to {recipient_name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=sender,
        )

        fee_journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=sender_account,
            credit_account=fee_account,
            amount=fee,
            description="External transfer fee",
            journal_type=AccountingJournal.FEE,
            created_by=sender,
        )

        transaction.journal = principal_journal
        transaction.save(update_fields=["journal", "updated_at"])

        from banking.services.bank_manager import BankAPIManager
        try:
            bank_result = BankAPIManager.transfer_funds(
                from_account=float_account.nuban_number,
                to_account=recipient_account_number,
                to_bank_code=recipient_bank_code,
                amount=amount,
                narration=narration,
            )
        except Exception as exc:
            logger.exception("External bank call raised.")
            bank_result = {"success": False, "message": str(exc)}

        if not bank_result.get("success"):
            self._reverse_journal(principal_journal, sender=sender)
            self._reverse_journal(fee_journal, sender=sender)
            transaction.status = Transaction.FAILED
            transaction.save(update_fields=["status", "updated_at"])
            notify.emit_external_transfer_failed(
                sender=sender,
                transaction=transaction,
                reason=bank_result.get("message", "External bank failed."),
            )
            raise ValidationError(
                f"External transfer failed: {bank_result.get('message')}"
            )

        transaction.status = Transaction.SUCCESS
        transaction.provider_reference = bank_result.get("reference", "")
        transaction.balance_after = sender_account.get_balance()
        transaction.save(update_fields=[
            "status", "provider_reference", "balance_after", "updated_at",
        ])

        money_transfer = MoneyTransfer.objects.create(
            sender=sender,
            receiver=None,
            sender_account=sender_account,
            receiver_account=None,
            amount=amount,
            fee=fee,
            reference=transaction.reference,
            status=Transaction.SUCCESS,
            narration=narration,
            bank_reference=bank_result.get("reference", ""),
            journal=principal_journal,
        )

        self._update_payment_stats(sender, amount)

        notify.emit_transfer_initiated(sender=sender, money_transfer=money_transfer)
        notify.emit_transfer_succeeded(sender=sender, money_transfer=money_transfer)

        self.webhook_service.send_webhook(
            event_type="transfer.completed",
            payload={
                "reference": transaction.reference,
                "amount": str(amount),
                "fee": str(fee),
                "sender_id": sender.pk,
                "recipient_account": recipient_account_number,
            },
        )

        return money_transfer

    # ---------------------------------------------------------------- wallet

    @db_transaction.atomic
    def fund_wallet(self, *, wallet, amount, source="", narration="") -> Transaction:
        amount = self._validate_amount(amount)

        if wallet.account_id is None:
            raise ValidationError("Wallet has no linked ledger account.")
        if wallet.status != "ACTIVE":
            raise ValidationError("Wallet is not active.")

        settlement = AccountingManager.get_settlement_account()

        transaction = Transaction.objects.create(
            account=wallet.account,
            amount=amount,
            type=Transaction.DEPOSIT,
            narration=narration or f"Wallet funding from {source}",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=settlement,
            credit_account=wallet.account,
            amount=amount,
            description=narration or f"Wallet funding from {source}",
            journal_type=AccountingJournal.DEPOSIT,
            created_by=wallet.user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = wallet.balance
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        wallet.record_transaction(amount)

        notify.emit_wallet_credited(
            wallet=wallet,
            amount=amount,
            reference=transaction.reference,
        )

        return transaction

    @db_transaction.atomic
    def withdraw_from_wallet(
        self, *, wallet, amount, narration=""
    ) -> Transaction:
        amount = self._validate_amount(amount)

        if wallet.account_id is None:
            raise ValidationError("Wallet has no linked ledger account.")

        wallet.can_transact(amount)

        if wallet.balance < amount:
            raise ValidationError("Insufficient wallet balance.")

        settlement = AccountingManager.get_settlement_account()

        transaction = Transaction.objects.create(
            account=wallet.account,
            amount=amount,
            type=Transaction.WITHDRAWAL,
            narration=narration or "Wallet withdrawal",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=wallet.account,
            credit_account=settlement,
            amount=amount,
            description=narration or "Wallet withdrawal",
            journal_type=AccountingJournal.WITHDRAWAL,
            created_by=wallet.user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = wallet.balance
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        wallet.record_transaction(amount)

        notify.emit_wallet_debited(
            wallet=wallet,
            amount=amount,
            reference=transaction.reference,
        )

        return transaction

    # ---------------------------------------------------------------- internals

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        try:
            return AccountingManager._validate_amount(amount)
        except ValidationError:
            raise

    @staticmethod
    def _validate_account(account, label):
        if account is None:
            raise ValidationError(f"{label} account is required.")
        if account.pk is None:
            raise ValidationError(f"{label} account must be persisted.")
        if account.status != Account.STATUS_ACTIVE:
            raise ValidationError(f"{label} account is not active.")

    def _run_fraud_check(self, sender, amount, kind):
        risks = self.fraud_service.analyze_transaction({
            "sender": sender,
            "amount": amount,
            "type": kind,
        })
        if any(r.get("action") == "BLOCK" for r in risks):
            raise ValidationError("Transaction blocked due to fraud risk.")

    def _check_transaction_limits(self, sender, amount):
        stat = PaymentStat.objects.filter(user=sender).first()
        if stat is None:
            return
        if not stat.can_make_transaction(amount):
            raise ValidationError("Transaction limit exceeded.")

    @staticmethod
    def _external_fee(amount: Decimal) -> Decimal:
        return max(
            (amount * EXTERNAL_FEE_PCT).quantize(MONEY_QUANTUM),
            EXTERNAL_FEE_MIN,
        )

    def _update_payment_stats(self, sender, amount):
        stat, _ = PaymentStat.objects.get_or_create(user=sender)
        stat.number_of_payments += 1
        stat.total_payments_amount += amount
        stat.last_transaction_amount = amount
        stat.last_transaction_date = __import__("django.utils.timezone", fromlist=["timezone"]).now()
        stat.save(update_fields=[
            "number_of_payments",
            "total_payments_amount",
            "last_transaction_amount",
            "last_transaction_date",
        ])

    @staticmethod
    def _reverse_journal(original_journal, *, sender=None):
        from banking.models.accounting import LedgerEntry
        reversal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.REVERSAL,
            reference=f"REV-{original_journal.reference}",
            description=f"Reversal of {original_journal.reference}",
            total_amount=original_journal.total_amount,
            is_balanced=False,
            created_by=sender,
        )
        for entry in original_journal.entries.all():
            opposite = (
                LedgerEntry.CREDIT
                if entry.entry_type == LedgerEntry.DEBIT
                else LedgerEntry.DEBIT
            )
            LedgerEntry.objects.create(
                journal=reversal,
                account=entry.account,
                entry_type=opposite,
                amount=entry.amount,
                balance_after=entry.account.get_balance(),
                transaction=entry.transaction,
                reference=(
                    f"{reversal.reference}-"
                    f"{'DEBIT' if opposite == LedgerEntry.DEBIT else 'CREDIT'}"
                ),
                description=f"Reversal of {entry.reference}",
            )
        reversal.mark_balanced()
        return reversal