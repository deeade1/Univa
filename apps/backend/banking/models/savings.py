"""
Savings goal models.

Architecture
------------

SavingsGoal is a savings bucket whose balance is derived from its own
SavingsTransaction rows.

The authoritative balance is:

    sum(DEPOSIT, INTEREST, AUTO_SAVE)
  - sum(WITHDRAWAL, PENALTY)

across the goal's SavingsTransaction rows where status='COMPLETED'.

SavingsGoal.current_amount is a read-only property. It is NOT stored
on the model.

SavingsGoal.interest_earned is a read-only property that sums
SavingsTransaction rows of type INTEREST. It is NOT stored.

Each SavingsTransaction links to the ledger journal that posted it.
The ledger remains the authoritative source of financial truth; each
SavingsTransaction carries a `journal` FK pointing at the specific
AccountingJournal that recorded the corresponding money movement.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from banking.models.core import Account


# ============================================================================
# SAVINGS GOAL
# ============================================================================


class SavingsGoal(models.Model):
    """A savings goal whose balance is derived from its own transactions."""

    GOAL_TYPES = [
        ('SHORT_TERM', 'Short Term (0-3 months)'),
        ('MEDIUM_TERM', 'Medium Term (3-12 months)'),
        ('LONG_TERM', 'Long Term (1+ years)'),
        ('EMERGENCY', 'Emergency Fund'),
        ('SPECIFIC', 'Specific Purchase'),
    ]

    SAVINGS_METHODS = [
        ('FIXED_AMOUNT', 'Fixed Amount'),
        ('PERCENTAGE', 'Percentage of Income'),
        ('ROUND_UP', 'Round-up Savings'),
        ('FREQUENCY', 'Regular Frequency'),
    ]

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    goal_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='savings_goals',
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)

    # ------------------------------------------------------------------
    # Target & timing
    # ------------------------------------------------------------------

    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    target_date = models.DateField()

    # ------------------------------------------------------------------
    # Method configuration
    # ------------------------------------------------------------------

    savings_method = models.CharField(
        max_length=20,
        choices=SAVINGS_METHODS,
    )

    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    round_up_multiplier = models.IntegerField(
        default=1,
        choices=[
            (1, 'Nearest ₦10'),
            (2, 'Nearest ₦50'),
            (3, 'Nearest ₦100'),
        ],
    )

    frequency = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('BIWEEKLY', 'Bi-weekly'),
            ('MONTHLY', 'Monthly'),
        ],
        blank=True,
    )

    # ------------------------------------------------------------------
    # Funding account
    # ------------------------------------------------------------------

    source_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='funded_savings',
        help_text="Customer account that funds this goal.",
    )

    # ------------------------------------------------------------------
    # Ledger linkage
    # ------------------------------------------------------------------

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='savings_goals',
        help_text="Opening journal for the goal (if pre-funded).",
    )

    # ------------------------------------------------------------------
    # Auto-save settings
    # ------------------------------------------------------------------

    is_auto_save = models.BooleanField(default=False)
    next_auto_save = models.DateTimeField(null=True, blank=True)
    last_auto_save = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    is_locked = models.BooleanField(default=False, db_index=True)
    locked_until = models.DateField(null=True, blank=True)
    lock_reason = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Interest (informational; actual interest paid via ledger)
    # ------------------------------------------------------------------

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    last_interest_calculated = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(default=True, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    total_deposits = models.IntegerField(default=0)
    total_withdrawals = models.IntegerField(default=0)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['goal_type', 'is_active']),
            models.Index(fields=['target_date']),
        ]

    def __str__(self):
        return f"{self.name} - ₦{self.current_amount}/{self.target_amount}"

    # ------------------------------------------------------------------
    # Clean
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        errors = {}

        if self.source_account_id is not None:
            if self.source_account.is_system_account:
                errors['source_account'] = (
                    "Source account cannot be a system account."
                )
            elif self.source_account.user_id != self.user_id:
                errors['source_account'] = (
                    "Source account must belong to the goal's owner."
                )

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        if not self.goal_id:
            self.goal_id = f"GOAL{uuid.uuid4().hex[:8].upper()}"

        self.full_clean()

        super().save(*args, **kwargs)

        # Completion is detected after save so the transaction history
        # has had a chance to reflect the latest deposit.
        if (
            not self.is_completed
            and self.target_amount
            and self.current_amount >= self.target_amount
        ):
            self.is_completed = True
            self.completed_at = timezone.now()
            type(self).objects.filter(pk=self.pk).update(
                is_completed=True,
                completed_at=self.completed_at,
            )

    # ------------------------------------------------------------------
    # Derived money fields
    # ------------------------------------------------------------------

    @property
    def current_amount(self) -> Decimal:
        """
        Balance derived from the goal's own SavingsTransaction rows.

        Credits: DEPOSIT, INTEREST, AUTO_SAVE
        Debits:  WITHDRAWAL, PENALTY

        Only transactions with status='COMPLETED' are counted.
        """
        completed = self.transactions.filter(status='COMPLETED')

        credits = (
            completed
            .filter(transaction_type__in=['DEPOSIT', 'INTEREST', 'AUTO_SAVE'])
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        debits = (
            completed
            .filter(transaction_type__in=['WITHDRAWAL', 'PENALTY'])
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        return (Decimal(credits) - Decimal(debits)).quantize(Decimal('0.01'))

    @property
    def interest_earned(self) -> Decimal:
        """
        Sum of all interest-type SavingsTransaction rows.
        """
        result = self.transactions.filter(
            transaction_type='INTEREST',
            status='COMPLETED',
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')

    @property
    def progress_percentage(self) -> float:
        if not self.target_amount:
            return 0.0
        return float(
            (self.current_amount / self.target_amount) * Decimal('100')
        )

    @property
    def days_remaining(self) -> int:
        from datetime import date
        today = date.today()
        remaining = (self.target_date - today).days
        return max(remaining, 0)

    @property
    def daily_savings_needed(self) -> Decimal:
        remaining_days = self.days_remaining
        if remaining_days == 0:
            return Decimal('0.00')
        remaining_amount = self.target_amount - self.current_amount
        if remaining_amount <= Decimal('0.00'):
            return Decimal('0.00')
        return (remaining_amount / remaining_days).quantize(
            Decimal('0.01')
        )


# ============================================================================
# SAVINGS TRANSACTION
# ============================================================================


class SavingsTransaction(models.Model):
    """Business-event log for a savings goal. Each row links to a journal."""

    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('INTEREST', 'Interest Earned'),
        ('AUTO_SAVE', 'Auto-save'),
        ('PENALTY', 'Early Withdrawal Penalty'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]

    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='transactions',
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)

    # Historical snapshots captured at posting time. These are NOT
    # the source of truth — the ledger is. They exist for statements
    # and audit convenience.
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='COMPLETED',
    )

    is_auto_save = models.BooleanField(default=False)

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='savings_transactions',
        help_text="Ledger journal that posted this transaction.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['goal', 'transaction_type']),
            models.Index(fields=['goal', 'created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - ₦{self.amount} - {self.goal.name}"


# ============================================================================
# AUTO SAVE RULE
# ============================================================================


class AutoSaveRule(models.Model):
    """Rule for automatically funding a savings goal."""

    RULE_TYPES = [
        ('ROUND_UP', 'Round-up Transactions'),
        ('RECURRING', 'Recurring Transfer'),
        ('INCOME_PERCENTAGE', 'Percentage of Income'),
        ('SPENDING_TRIGGER', 'Spending Trigger'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auto_save_rules',
    )

    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='auto_save_rules',
    )

    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    is_active = models.BooleanField(default=True)

    parameters = models.JSONField(default=dict)

    last_executed = models.DateTimeField(null=True, blank=True)
    total_executions = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_rule_type_display()} - {self.goal.name}"

    @property
    def total_amount_saved(self) -> Decimal:
        """
        Sum of auto-save transactions attached to this goal.
        """
        result = self.goal.transactions.filter(
            transaction_type='AUTO_SAVE',
            is_auto_save=True,
            status='COMPLETED',
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')