# apps/backend/banking/services/savings_service.py

"""
Savings orchestration service.

Money movement flows through:

    SavingsService
        -> AccountingManager.create_double_entry
            -> AccountingJournal
            -> LedgerEntry (debit)
            -> LedgerEntry (credit)

Account model uses Univa's convention:

    balance = SUM(CREDIT) - SUM(DEBIT)
    DEBIT  decreases an account balance
    CREDIT increases an account balance

Savings does not create a dedicated ledger Account per goal. Instead
all savings float lives in the SUSPENSE system account. Each goal's
authoritative balance is derived from the sum of its own
SavingsTransaction rows:

    credits: DEPOSIT, INTEREST, AUTO_SAVE
    debits:  WITHDRAWAL, PENALTY

Journals posted by this service:

    deposit:   source_account -> SUSPENSE
    withdrawal: SUSPENSE       -> source_account
    interest:   REVENUE        -> SUSPENSE

Each SavingsTransaction carries a journal FK so any balance can be
traced back to the underlying ledger entry.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import (
    AccountingJournal,
    AccountingManager,
)
from banking.models.core import Account
from banking.models.payments import Transaction
from banking.models.savings import (
    AutoSaveRule,
    SavingsGoal,
    SavingsTransaction,
)
from banking.services import notification_service as notify


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class SavingsService:
    """
    Orchestration service for ledger-backed savings operations.
    """

    # ------------------------------------------------------------------
    # GOAL LIFECYCLE
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def create_savings_goal(
        self,
        *,
        user,
        source_account: Account,
        name: str,
        target_amount,
        target_date,
        goal_type: str,
        savings_method: str = "FIXED_AMOUNT",
        description: str = "",
        fixed_amount=None,
        percentage=None,
        round_up_multiplier: int = 1,
        frequency: str = "",
        is_auto_save: bool = False,
        is_locked: bool = False,
        locked_until=None,
        lock_reason: str = "",
        interest_rate=None,
    ) -> SavingsGoal:
        """
        Create a SavingsGoal.

        No ledger journal is posted at creation time. Money moves
        only when the goal is funded via `deposit_to_goal`.
        """
        self._validate_user_source_account(user, source_account)

        target_amount = self._validate_amount(target_amount)

        goal = SavingsGoal.objects.create(
            user=user,
            name=name,
            description=description,
            goal_type=goal_type,
            target_amount=target_amount,
            start_date=timezone.localdate(),
            target_date=target_date,
            savings_method=savings_method,
            fixed_amount=(
                self._validate_amount(fixed_amount)
                if fixed_amount is not None
                else None
            ),
            percentage=(
                Decimal(str(percentage))
                if percentage is not None
                else None
            ),
            round_up_multiplier=round_up_multiplier,
            frequency=frequency,
            source_account=source_account,
            is_auto_save=is_auto_save,
            is_locked=is_locked,
            locked_until=locked_until,
            lock_reason=lock_reason,
            interest_rate=(
                Decimal(str(interest_rate))
                if interest_rate is not None
                else Decimal("0.00")
            ),
            is_active=True,
        )

        notify.emit_savings_goal_created(user=user, goal=goal)

        return goal

    # ------------------------------------------------------------------
    # DEPOSIT
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def deposit_to_goal(
        self,
        *,
        goal: SavingsGoal,
        amount,
        description: str = "",
        is_auto_save: bool = False,
    ) -> SavingsTransaction:
        """
        Deposit into a goal.

        Journal: source_account -> SUSPENSE
        """
        amount = self._validate_amount(amount)
        self._validate_goal_active_and_unlocked(goal)

        user = goal.user
        source_account = goal.source_account

        if source_account.get_balance() < amount:
            raise ValidationError("Insufficient funds in source account.")

        balance_before = goal.current_amount

        transaction = Transaction.objects.create(
            account=source_account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=description or f"Savings deposit to {goal.name}",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=source_account,
            credit_account=AccountingManager.get_suspense_account(),
            amount=amount,
            description=description or f"Savings deposit to {goal.name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = source_account.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        savings_tx = SavingsTransaction.objects.create(
            goal=goal,
            transaction_type="AUTO_SAVE" if is_auto_save else "DEPOSIT",
            amount=amount,
            description=description or f"Deposit to {goal.name}",
            balance_before=balance_before,
            balance_after=balance_before + amount,
            status="COMPLETED",
            is_auto_save=is_auto_save,
            journal=journal,
        )

        type(goal).objects.filter(pk=goal.pk).update(
            total_deposits=goal.total_deposits + 1,
            updated_at=timezone.now(),
        )

        goal.refresh_from_db()

        self._mark_completed_if_reached(goal)

        notify.emit_savings_deposit(
            user=user,
            goal=goal,
            savings_transaction=savings_tx,
        )

        return savings_tx

    # ------------------------------------------------------------------
    # WITHDRAWAL
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def withdraw_from_goal(
        self,
        *,
        goal: SavingsGoal,
        amount,
        description: str = "",
    ) -> SavingsTransaction:
        """
        Withdraw from a goal.

        Journal: SUSPENSE -> source_account
        """
        amount = self._validate_amount(amount)
        self._validate_goal_active(goal)

        if goal.is_locked:
            if goal.locked_until and timezone.localdate() < goal.locked_until:
                raise ValidationError(
                    f"Goal is locked until {goal.locked_until}."
                )

        user = goal.user
        source_account = goal.source_account

        balance_before = goal.current_amount
        if balance_before < amount:
            raise ValidationError("Insufficient funds in savings goal.")

        transaction = Transaction.objects.create(
            account=source_account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=description or f"Savings withdrawal from {goal.name}",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=AccountingManager.get_suspense_account(),
            credit_account=source_account,
            amount=amount,
            description=description or f"Savings withdrawal from {goal.name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = source_account.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        savings_tx = SavingsTransaction.objects.create(
            goal=goal,
            transaction_type="WITHDRAWAL",
            amount=amount,
            description=description or f"Withdrawal from {goal.name}",
            balance_before=balance_before,
            balance_after=balance_before - amount,
            status="COMPLETED",
            journal=journal,
        )

        type(goal).objects.filter(pk=goal.pk).update(
            total_withdrawals=goal.total_withdrawals + 1,
            updated_at=timezone.now(),
        )

        goal.refresh_from_db()

        notify.emit_savings_withdrawal(
            user=user,
            goal=goal,
            savings_transaction=savings_tx,
        )

        return savings_tx

    # ------------------------------------------------------------------
    # INTEREST
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def pay_interest(
        self,
        *,
        goal: SavingsGoal,
        amount,
        description: str = "",
    ) -> SavingsTransaction:
        """
        Pay interest into a savings goal.

        Journal: REVENUE -> SUSPENSE
        """
        amount = self._validate_amount(amount)
        self._validate_goal_active(goal)

        user = goal.user
        revenue = AccountingManager.get_revenue_account()
        suspense = AccountingManager.get_suspense_account()

        balance_before = goal.current_amount

        transaction = Transaction.objects.create(
            account=suspense,
            amount=amount,
            type=Transaction.DEPOSIT,
            narration=description or f"Savings interest for {goal.name}",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction,
            debit_account=revenue,
            credit_account=suspense,
            amount=amount,
            description=description or f"Savings interest for {goal.name}",
            journal_type=AccountingJournal.INTEREST,
            created_by=user,
        )

        transaction.journal = journal
        transaction.status = Transaction.SUCCESS
        transaction.balance_after = suspense.get_balance()
        transaction.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        savings_tx = SavingsTransaction.objects.create(
            goal=goal,
            transaction_type="INTEREST",
            amount=amount,
            description=description or f"Interest on {goal.name}",
            balance_before=balance_before,
            balance_after=balance_before + amount,
            status="COMPLETED",
            journal=journal,
        )

        type(goal).objects.filter(pk=goal.pk).update(
            last_interest_calculated=timezone.now(),
            updated_at=timezone.now(),
        )

        goal.refresh_from_db()

        self._mark_completed_if_reached(goal)

        notify.emit_savings_interest_paid(
            user=user,
            goal=goal,
            savings_transaction=savings_tx,
        )

        return savings_tx

    # ------------------------------------------------------------------
    # AUTO-SAVE EXECUTION
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def execute_auto_save(
        self,
        *,
        rule: AutoSaveRule,
        amount,
        description: str = "",
    ) -> SavingsTransaction:
        """
        Execute a single auto-save cycle against the rule's goal.
        """
        if not rule.is_active:
            raise ValidationError("Auto-save rule is not active.")

        goal = rule.goal
        self._validate_goal_active(goal)

        savings_tx = self.deposit_to_goal(
            goal=goal,
            amount=amount,
            description=description or f"Auto-save: {rule.get_rule_type_display()}",
            is_auto_save=True,
        )

        type(rule).objects.filter(pk=rule.pk).update(
            last_executed=timezone.now(),
            total_executions=rule.total_executions + 1,
            updated_at=timezone.now(),
        )

        return savings_tx

    # ------------------------------------------------------------------
    # GOAL COMPLETION
    # ------------------------------------------------------------------

    def _mark_completed_if_reached(self, goal: SavingsGoal) -> None:
        """
        Set is_completed when the transaction-derived balance meets the
        target.
        """
        if goal.is_completed:
            return

        if goal.target_amount <= Decimal("0.00"):
            return

        if goal.current_amount < goal.target_amount:
            return

        completed_at = timezone.now()
        type(goal).objects.filter(pk=goal.pk).update(
            is_completed=True,
            completed_at=completed_at,
            updated_at=completed_at,
        )
        goal.is_completed = True
        goal.completed_at = completed_at

        notify.emit_savings_goal_completed(user=goal.user, goal=goal)

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
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

    @staticmethod
    def _validate_user_source_account(user, source_account: Account) -> None:
        if source_account is None:
            raise ValidationError("Source account is required.")
        if source_account.pk is None:
            raise ValidationError("Source account must be persisted.")
        if source_account.is_system_account:
            raise ValidationError("Source account cannot be a system account.")
        if source_account.user_id != user.pk:
            raise ValidationError(
                "Source account does not belong to this user."
            )
        if source_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Source account is not active.")

    @staticmethod
    def _validate_goal_active(goal: SavingsGoal) -> None:
        if goal is None:
            raise ValidationError("Savings goal is required.")
        if not goal.is_active:
            raise ValidationError("Savings goal is not active.")

    @staticmethod
    def _validate_goal_active_and_unlocked(goal: SavingsGoal) -> None:
        SavingsService._validate_goal_active(goal)
        if goal.is_locked:
            if goal.locked_until and timezone.localdate() < goal.locked_until:
                raise ValidationError(
                    f"Goal is locked until {goal.locked_until}."
                )