# apps/backend/banking/services/investment_service.py

"""
Investment orchestration service.

Every money movement flows through:

    InvestmentService
        -> AccountingManager.create_double_entry
            -> AccountingJournal
            -> LedgerEntry (debit)
            -> LedgerEntry (credit)

Account model uses Univa's convention:

    balance = SUM(CREDIT) - SUM(DEBIT)
    DEBIT  decreases an account balance
    CREDIT increases an account balance

Investment records store only metadata (terms, dates, status).
Money fields are derived properties. The link between an Investment
and its ledger backing is Investment.journal.

Journals posted by this service:

    purchase:      wallet.account  -> SUSPENSE
    maturity:      SUSPENSE        -> wallet.account  (principal)
                   SUSPENSE        -> wallet.account  (earnings)
    early withdraw SUSPENSE        -> wallet.account  (principal + accrued)
                   wallet.account  -> FEE             (fee)
    cancel:        SUSPENSE        -> wallet.account  (reversal of purchase)
    earnings:      SUSPENSE        -> wallet.account  (each installment)
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import (
    AccountingJournal,
    AccountingManager,
)
from banking.models.core import Account
from banking.models.investments import (
    Investment,
    InvestmentEarnings,
    InvestmentProduct,
)
from banking.models.payments import Transaction, Wallet
from banking.services import notification_service as notify
from banking.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")
YEAR_DAYS = Decimal("365")


class InvestmentService:
    """
    Orchestration service for ledger-backed investment operations.
    """

    # ------------------------------------------------------------------
    # PURCHASE
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def purchase_investment(
        self,
        *,
        user,
        wallet: Wallet,
        product: InvestmentProduct,
        amount,
        tenure_days: int | None = None,
    ) -> Investment:
        """
        Create an Investment and post the purchase journal.

        The user's wallet is debited and the SUSPENSE system account
        is credited. This records the platform's custody obligation.
        """
        logger.error("=== P0: purchase_investment start user=%s wallet=%s product=%s ===",
                     getattr(user, 'pk', None), getattr(wallet, 'pk', None), getattr(product, 'pk', None))

        amount = self._validate_amount(amount)
        self._validate_wallet(wallet, user)
        self._validate_product(product, amount, tenure_days)

        logger.error("=== P0.1: validations passed, checking balance ===")

        if wallet.balance < amount:
            raise ValidationError("Insufficient wallet balance.")

        logger.error("=== P0.5: balance OK wallet.balance=%s amount=%s ===",
                     wallet.balance, amount)

        tenure = tenure_days or product.default_tenure_days
        now = timezone.now()

        reference = (
            f"INV-{product.slug.upper()[:12]}-"
            f"{now.strftime('%Y%m')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        logger.error("=== P1: about to create Transaction ===")
        transaction = Transaction.objects.create(
            account=wallet.account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=f"Investment purchase: {product.name}",
            status=Transaction.PENDING,
        )
        logger.error("=== P1.5: Transaction created pk=%s ref=%s ===",
                     transaction.pk, transaction.reference)

        logger.error("=== P2: about to create Investment ===")
        investment = Investment.objects.create(
            user=user,
            product=product,
            wallet=wallet,
            amount=amount,
            tenure_days=tenure,
            interest_rate=product.interest_rate,
            start_date=now,
            maturity_date=now + timedelta(days=tenure),
            interest_payment_date=now + timedelta(days=tenure),
            status="ACTIVE",
            investment_reference=reference,
        )
        logger.error("=== P2.5: Investment created pk=%s ===", investment.pk)

        logger.error("=== P3: about to fetch suspense account ===")
        suspense = AccountingManager.get_suspense_account()
        logger.error("=== P3.5: suspense account pk=%s ===", suspense.pk)

        logger.error("=== P4: about to create_double_entry ===")
        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=wallet.account,
            credit_account=suspense,
            amount=amount,
            description=f"Investment purchase: {product.name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )
        logger.error("=== P4.5: create_double_entry returned journal pk=%s ===", journal.pk)

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = wallet.account.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        investment.journal = journal
        investment.save(update_fields=["journal", "updated_at"])

        wallet.record_transaction(amount)

        logger.error("=== P5: about to emit notification ===")
        notify.emit_investment_purchased(
            user=user,
            investment=investment,
        )
        logger.error("=== P5.5: notification emitted, returning investment ===")

        return investment

    # ------------------------------------------------------------------
    # MATURITY
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def mature_investment(self, *, investment: Investment) -> Investment:
        """
        Mature an ACTIVE investment.

        Two journals are posted:

            principal:  SUSPENSE -> wallet.account
            earnings:   SUSPENSE -> wallet.account

        The earnings amount is `investment.expected_return`.
        """
        self._validate_investment_status(investment, "ACTIVE")

        user = investment.user
        wallet = investment.wallet

        if wallet is None:
            raise ValidationError(
                "Investment has no wallet to credit on maturity."
            )

        principal = Decimal(str(investment.amount))
        earnings = investment.expected_return
        suspense = AccountingManager.get_suspense_account()

        # Principal return
        principal_txn = Transaction.objects.create(
            account=wallet.account,
            amount=principal,
            type=Transaction.DEPOSIT,
            narration=f"Investment matured: {investment.investment_reference}",
            status=Transaction.PENDING,
        )
        principal_journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=suspense,
            credit_account=wallet.account,
            amount=principal,
            description="Investment principal returned on maturity",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )
        principal_txn.journal = principal_journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = wallet.account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # Earnings payout (only if positive)
        if earnings > Decimal("0.00"):
            earnings_txn = Transaction.objects.create(
                account=wallet.account,
                amount=earnings,
                type=Transaction.DEPOSIT,
                narration=f"Investment earnings: {investment.investment_reference}",
                status=Transaction.PENDING,
            )
            earnings_journal = AccountingManager.create_double_entry(
                transaction=earnings_txn,
                debit_account=suspense,
                credit_account=wallet.account,
                amount=earnings,
                description="Investment earnings paid on maturity",
                journal_type=AccountingJournal.INTEREST,
                created_by=user,
            )
            earnings_txn.journal = earnings_journal
            earnings_txn.status = Transaction.SUCCESS
            earnings_txn.balance_after = wallet.account.get_balance()
            earnings_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

            InvestmentEarnings.objects.create(
                investment=investment,
                user=user,
                transaction=earnings_txn,
                earning_type="INTEREST",
                amount=earnings,
                description="Interest on maturity",
                period_start=investment.start_date,
                period_end=investment.maturity_date,
                journal=earnings_journal,
            )

        investment.status = "MATURED"
        investment.withdrawal_date = timezone.now()
        investment.save(update_fields=[
            "status", "withdrawal_date", "updated_at",
        ])

        wallet.record_transaction(principal)

        notify.emit_investment_matured(user=user, investment=investment)

        return investment

    # ------------------------------------------------------------------
    # EARLY WITHDRAWAL
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def withdraw_early(self, *, investment: Investment) -> Investment:
        """
        Withdraw an ACTIVE investment before maturity.

        The user receives principal plus accrued interest (calculated
        by `investment.calculate_return()`), minus an early-withdrawal
        fee computed from the product's `early_withdrawal_fee` percent.

        Journals:

            principal + accrued:  SUSPENSE -> wallet.account
            fee:                  wallet.account -> FEE
        """
        self._validate_investment_status(investment, "ACTIVE")

        user = investment.user
        wallet = investment.wallet
        if wallet is None:
            raise ValidationError(
                "Investment has no wallet to credit on withdrawal."
            )

        principal = Decimal(str(investment.amount))
        accrued = investment.calculate_return()

        product_fee_pct = Decimal(str(investment.product.early_withdrawal_fee))
        fee = (principal * product_fee_pct / Decimal("100")).quantize(MONEY_QUANTUM)

        gross = principal + accrued
        net = (gross - fee).quantize(MONEY_QUANTUM)

        if net < Decimal("0.00"):
            raise ValidationError(
                "Fee exceeds returnable amount; withdrawal not permitted."
            )

        suspense = AccountingManager.get_suspense_account()
        fee_account = AccountingManager.get_fee_account()

        # Gross return: principal + accrued
        gross_txn = Transaction.objects.create(
            account=wallet.account,
            amount=gross,
            type=Transaction.DEPOSIT,
            narration=f"Investment early withdrawal: {investment.investment_reference}",
            status=Transaction.PENDING,
        )
        gross_journal = AccountingManager.create_double_entry(
            transaction=gross_txn,
            debit_account=suspense,
            credit_account=wallet.account,
            amount=gross,
            description="Investment principal and accrued interest returned on early withdrawal",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )
        gross_txn.journal = gross_journal
        gross_txn.status = Transaction.SUCCESS
        gross_txn.balance_after = wallet.account.get_balance()
        gross_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # Fee: wallet back to FEE account
        if fee > Decimal("0.00"):
            fee_txn = Transaction.objects.create(
                account=wallet.account,
                amount=fee,
                type=Transaction.FEE,
                narration="Early withdrawal fee",
                fee=fee,
                status=Transaction.PENDING,
            )
            fee_journal = AccountingManager.create_double_entry(
                transaction=fee_txn,
                debit_account=wallet.account,
                credit_account=fee_account,
                amount=fee,
                description="Early withdrawal fee",
                journal_type=AccountingJournal.FEE,
                created_by=user,
            )
            fee_txn.journal = fee_journal
            fee_txn.status = Transaction.SUCCESS
            fee_txn.balance_after = wallet.account.get_balance()
            fee_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

        investment.status = "WITHDRAWN"
        investment.early_withdrawal = True
        investment.withdrawal_date = timezone.now()
        investment.save(update_fields=[
            "status", "early_withdrawal", "withdrawal_date", "updated_at",
        ])

        wallet.record_transaction(net)

        notify.emit_investment_withdrawn(user=user, investment=investment)

        return investment

    # ------------------------------------------------------------------
    # CANCEL (PENDING only)
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def cancel_investment(self, *, investment: Investment) -> Investment:
        """
        Cancel a PENDING investment.

        Reversal of the original purchase journal. Because the
        original journal is preserved, we post a *new* journal that
        swaps debit and credit for every entry.
        """
        self._validate_investment_status(investment, "PENDING")

        user = investment.user

        if investment.journal is not None:
            PaymentService._reverse_journal(
                investment.journal,
                sender=user,
            )

        investment.status = "CANCELLED"
        investment.status_reason = "Cancelled before activation"
        investment.save(update_fields=[
            "status", "status_reason", "updated_at",
        ])

        notify.emit_investment_cancelled(user=user, investment=investment)

        return investment

    # ------------------------------------------------------------------
    # EARNINGS PAYOUT
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def pay_earnings(
        self,
        *,
        investment: Investment,
        amount,
        period_start,
        period_end,
        earning_type: str = "INTEREST",
        description: str = "",
    ) -> InvestmentEarnings:
        """
        Pay one earnings installment.

        Posts a journal from SUSPENSE to the wallet's account and
        records an `InvestmentEarnings` row linked to the journal.
        """
        self._validate_investment_status(investment, "ACTIVE")

        amount = self._validate_amount(amount)
        user = investment.user
        wallet = investment.wallet

        if wallet is None:
            raise ValidationError(
                "Investment has no wallet to credit earnings to."
            )

        suspense = AccountingManager.get_suspense_account()

        transaction = Transaction.objects.create(
            account=wallet.account,
            amount=amount,
            type=Transaction.DEPOSIT,
            narration=description or "Investment earnings",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=suspense,
            credit_account=wallet.account,
            amount=amount,
            description=description or "Investment earnings",
            journal_type=AccountingJournal.INTEREST,
            created_by=user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = wallet.account.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        earnings = InvestmentEarnings.objects.create(
            investment=investment,
            user=user,
            transaction=transaction,
            earning_type=earning_type,
            amount=amount,
            description=description or "Investment earnings",
            period_start=period_start,
            period_end=period_end,
            journal=journal,
        )

        wallet.record_transaction(amount)

        notify.emit_investment_earnings_paid(
            user=user,
            investment=investment,
            earnings=earnings,
        )

        return earnings

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        try:
            return AccountingManager._validate_amount(amount)
        except ValidationError:
            raise

    @staticmethod
    def _validate_wallet(wallet, user):
        if wallet is None:
            raise ValidationError("Wallet is required.")
        if wallet.user_id != user.pk:
            raise ValidationError("Wallet does not belong to this user.")
        if wallet.status != "ACTIVE":
            raise ValidationError("Wallet is not active.")
        if wallet.account_id is None:
            raise ValidationError("Wallet has no linked ledger account.")

    @staticmethod
    def _validate_product(product, amount, tenure_days):
        if product is None:
            raise ValidationError("Investment product is required.")
        if not product.is_active or not product.is_available:
            raise ValidationError("Product is not available.")

        if amount < product.min_investment:
            raise ValidationError(
                f"Amount must be at least ₦{product.min_investment:,.2f}."
            )
        if product.max_investment and amount > product.max_investment:
            raise ValidationError(
                f"Amount cannot exceed ₦{product.max_investment:,.2f}."
            )

        tenure = tenure_days or product.default_tenure_days
        if not (product.min_tenure_days <= tenure <= product.max_tenure_days):
            raise ValidationError(
                f"Tenure must be between {product.min_tenure_days} "
                f"and {product.max_tenure_days} days."
            )

    @staticmethod
    def _validate_investment_status(investment, expected):
        if investment.status != expected:
            raise ValidationError(
                f"Investment must be {expected}, but is {investment.status}."
            )