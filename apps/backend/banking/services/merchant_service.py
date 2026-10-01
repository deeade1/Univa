"""
Merchant service: orchestrates merchant sale, refund, and settlement.

Money movement paths
--------------------

    Sale:        customer_account -> merchant_suspense   (principal)
                 customer_account -> FEE                  (merchant fee)

    Refund:      merchant_suspense -> customer_account   (reversal)

    Settlement:  merchant_suspense -> merchant_settlement_account

Every path posts through AccountingManager.create_double_entry.

The merchant settlement account is a customer account. The "suspense"
side for a pending sale is the platform's SUSPENSE system account
until the settlement clears. In a full implementation this might be
a merchant-specific holding account, but for now we route through
SUSPENSE so the ledger stays balanced and the merchant's settlement
account is only credited at settlement time.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.core import Account
from banking.models.merchant import Merchant, MerchantTransaction
from banking.models.payments import Transaction
from banking.services import notification_service as notify


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class MerchantService:

    # ------------------------------------------------------------------
    # SALE
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def record_sale(
        *,
        merchant: Merchant,
        customer,
        customer_account: Account,
        amount,
        items: list | None = None,
        reference: str | None = None,
    ) -> MerchantTransaction:
        """
        Record a merchant sale.

        Posts two journals:

            principal: customer_account -> SUSPENSE   (amount - fee)
            fee:       customer_account -> FEE        (fee)

        Wait — this splits the amount between merchant-suspense and
        the platform fee. The merchant's settlement account is only
        credited when SettlementService settles the transaction.
        """
        amount = MerchantService._validate_amount(amount)

        if not merchant.is_active:
            raise ValidationError("Merchant is not active.")

        if merchant.user_id == customer.pk:
            raise ValidationError("Cannot transact with yourself.")

        if customer_account.user_id != customer.pk:
            raise ValidationError(
                "Customer account does not belong to this customer."
            )

        if customer_account.is_system_account:
            raise ValidationError("Customer account cannot be a system account.")

        if customer_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Customer account is not active.")

        fee = merchant.calculate_fee(amount).quantize(MONEY_QUANTUM)
        net_amount = (amount - fee).quantize(MONEY_QUANTUM)

        if net_amount <= Decimal("0.00"):
            raise ValidationError(
                "Merchant fee exceeds the sale amount."
            )

        if customer_account.get_balance() < amount:
            raise ValidationError("Insufficient funds in customer account.")

        reference = reference or (
            f"MER-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        suspense_account = AccountingManager.get_suspense_account()
        fee_account = AccountingManager.get_fee_account()

        # --------------------------------------------------------------
        # Principal journal: customer -> suspense (net amount)
        # --------------------------------------------------------------
        principal_txn = Transaction.objects.create(
            account=customer_account,
            amount=net_amount,
            type=Transaction.TRANSFER,
            narration=f"Merchant sale: {merchant.business_name}",
            recipient_name=merchant.business_name,
            recipient_account_number=merchant.settlement_account.nuban_number,
            status=Transaction.PENDING,
        )
        
        principal_journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=customer_account,
            credit_account=suspense_account,
            amount=net_amount,
            description=f"Merchant sale {reference}: {merchant.business_name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=customer,
        )

        principal_txn.journal = principal_journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = customer_account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Fee journal: customer -> fee account
        # --------------------------------------------------------------
        fee_txn = Transaction.objects.create(
            account=customer_account,
            amount=fee,
            type=Transaction.FEE,
            narration=f"Merchant fee: {merchant.business_name}",
            fee=fee,
            status=Transaction.PENDING,
        )

        fee_journal = AccountingManager.create_double_entry(
            transaction=fee_txn,
            debit_account=customer_account,
            credit_account=fee_account,
            amount=fee,
            description=f"Merchant fee {reference}: {merchant.business_name}",
            journal_type=AccountingJournal.FEE,
            created_by=customer,
        )

        fee_txn.journal = fee_journal
        fee_txn.status = Transaction.SUCCESS
        fee_txn.balance_after = customer_account.get_balance()
        fee_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Business record
        # --------------------------------------------------------------
        merchant_transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference=reference,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            items=items or [],
            status="COMPLETED",
            is_settled=False,
            journal=principal_journal,
        )

        notify.emit_merchant_sale(
            merchant_user=merchant.user,
            customer=customer,
            merchant_transaction=merchant_transaction,
        )

        return merchant_transaction

    # ------------------------------------------------------------------
    # REFUND
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def refund(
        *,
        merchant_transaction: MerchantTransaction,
        reason: str = "",
    ) -> MerchantTransaction:
        """
        Refund a completed sale.

        Posts:
            refund:  SUSPENSE -> customer_account     (net amount)
            fee back: FEE      -> customer_account    (fee)

        Marks MerchantTransaction.status = "REFUNDED".
        """
        if merchant_transaction.status != "COMPLETED":
            raise ValidationError("Only completed sales can be refunded.")

        if merchant_transaction.is_settled:
            raise ValidationError(
                "Settled transactions cannot be refunded. Reverse the "
                "settlement instead."
            )

        customer_account = Account.objects.filter(
            user=merchant_transaction.customer
        ).first()
        if customer_account is None:
            raise ValidationError("Customer no longer has an account.")

        suspense_account = AccountingManager.get_suspense_account()
        fee_account = AccountingManager.get_fee_account()

        # ------------------------------------------------------------------
        # Refund principal
        # ------------------------------------------------------------------
        refund_txn = Transaction.objects.create(
            account=suspense_account,
            amount=merchant_transaction.net_amount,
            type=Transaction.TRANSFER,
            narration=f"Refund: {merchant_transaction.merchant.business_name}",
            recipient_name=merchant_transaction.customer.email,
            recipient_account_number=customer_account.nuban_number,
            status=Transaction.PENDING,
        )

        refund_journal = AccountingManager.create_double_entry(
            transaction=refund_txn,
            debit_account=suspense_account,
            credit_account=customer_account,
            amount=merchant_transaction.net_amount,
            description=(
                f"Merchant refund {merchant_transaction.reference}: "
                f"{merchant_transaction.merchant.business_name}"
            ),
            journal_type=AccountingJournal.REVERSAL,
            created_by=merchant_transaction.merchant.user,
        )

        refund_txn.journal = refund_journal
        refund_txn.status = Transaction.SUCCESS
        refund_txn.balance_after = suspense_account.get_balance()
        refund_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # ------------------------------------------------------------------
        # Refund fee
        # ------------------------------------------------------------------
        if merchant_transaction.fee > Decimal("0.00"):
            fee_back_txn = Transaction.objects.create(
                account=fee_account,
                amount=merchant_transaction.fee,
                type=Transaction.FEE,
                narration=f"Fee refund: {merchant_transaction.merchant.business_name}",
                fee=merchant_transaction.fee,
                status=Transaction.PENDING,
            )

            AccountingManager.create_double_entry(
                transaction=fee_back_txn,
                debit_account=fee_account,
                credit_account=customer_account,
                amount=merchant_transaction.fee,
                description=(
                    f"Merchant fee refund {merchant_transaction.reference}"
                ),
                journal_type=AccountingJournal.REVERSAL,
                created_by=merchant_transaction.merchant.user,
            )

            fee_back_txn.status = Transaction.SUCCESS
            fee_back_txn.save(update_fields=["status", "updated_at"])

        merchant_transaction.status = "REFUNDED"
        merchant_transaction.save(update_fields=["status", "updated_at"])

        notify.emit_merchant_refund(
            merchant_user=merchant_transaction.merchant.user,
            merchant_transaction=merchant_transaction,
        )

        return merchant_transaction

    # ------------------------------------------------------------------
    # SETTLEMENT
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def process_settlements(
        *,
        merchant: Merchant,
    ) -> dict:
        """
        Settle all unsettled completed sales for a merchant.

        Posts one journal per merchant transaction:

            SUSPENSE -> merchant.settlement_account    (net_amount)

        Marks the transaction is_settled=True.
        """
        pending = MerchantTransaction.objects.filter(
            merchant=merchant,
            status="COMPLETED",
            is_settled=False,
        )

        if not pending.exists():
            return {"count": 0, "total_amount": Decimal("0.00")}

        suspense_account = AccountingManager.get_suspense_account()
        settlement_account = merchant.settlement_account

        total_settled = Decimal("0.00")
        settled_count = 0

        for mt in pending:
            settlement_txn = Transaction.objects.create(
                account=suspense_account,
                amount=mt.net_amount,
                type=Transaction.TRANSFER,
                narration=f"Settlement: {merchant.business_name}",
                recipient_name=merchant.business_name,
                recipient_account_number=settlement_account.nuban_number,
                status=Transaction.PENDING,
            )

            settlement_journal = AccountingManager.create_double_entry(
                transaction=settlement_txn,
                debit_account=suspense_account,
                credit_account=settlement_account,
                amount=mt.net_amount,
                description=f"Merchant settlement {mt.reference}",
                journal_type=AccountingJournal.SETTLEMENT,
                created_by=merchant.user,
            )

            settlement_txn.journal = settlement_journal
            settlement_txn.status = Transaction.SUCCESS
            settlement_txn.balance_after = suspense_account.get_balance()
            settlement_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

            mt.is_settled = True
            mt.settled_at = timezone.now()
            mt.settled_journal = settlement_journal
            mt.save(update_fields=[
                "is_settled", "settled_at", "settled_journal", "updated_at",
            ])

            total_settled += mt.net_amount
            settled_count += 1

        merchant.last_settlement_at = timezone.now()
        merchant.save(update_fields=["last_settlement_at", "updated_at"])

        notify.emit_merchant_settlement(
            user=merchant.user,
            merchant=merchant,
            count=settled_count,
            total_amount=total_settled,
        )

        return {"count": settled_count, "total_amount": total_settled}

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        if amount is None:
            raise ValidationError("Amount is required.")
        try:
            value = Decimal(str(amount))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid amount.") from exc
        if not value.is_finite():
            raise ValidationError("Amount must be finite.")
        if value <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")
        return value.quantize(MONEY_QUANTUM)