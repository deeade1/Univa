# apps/backend/banking/models/payments.py

"""
Payment models for the banking domain.

This module contains:
    - Transaction: Payment transactions
    - PaymentStat: User payment statistics
    - MoneyTransfer: Money transfer records
    - Wallet: Ledger-backed wallet (presentation object over an Account)

Architecture
------------

Wallet is NOT a source of truth for money.

The authoritative balance is derived from LedgerEntry:

    banking.models.accounting.AccountingManager.get_account_balance(
        wallet.account
    )

Wallet.balance is a read-only property. Wallet.debit() and
Wallet.credit() do not exist. All money movement flows through:

    banking.models.accounting.AccountingManager.create_double_entry()
"""

import uuid
from decimal import Decimal

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.conf import settings

from banking.models.core import Account, Bank


# ============================================================================
# TRANSACTION
# ============================================================================

class Transaction(models.Model):
    """Unified transaction model."""

    TRANSFER = 'TRANSFER'
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    BILL_PAYMENT = 'BILL_PAYMENT'
    AIRTIME = 'AIRTIME'
    FEE = 'FEE'

    TRANSACTION_TYPES = [
        (TRANSFER, 'Transfer'),
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (BILL_PAYMENT, 'Bill Payment'),
        (AIRTIME, 'Airtime Purchase'),
        (FEE, 'Fee'),
    ]

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (REVERSED, 'Reversed'),
    ]

    reference = models.CharField(max_length=50, unique=True, db_index=True)

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='account_transactions',
        db_index=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    recipient_phone = models.CharField(max_length=15, blank=True, null=True)
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_bank_code = models.CharField(max_length=32, blank=True)
    recipient_account_number = models.CharField(max_length=20, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    narration = models.CharField(max_length=255, blank=True)
    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    provider_reference = models.CharField(max_length=100, blank=True)

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Ledger journal posted for this transaction.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'created_at']),
            models.Index(fields=['reference', 'status']),
            models.Index(fields=['type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.reference}: ₦{self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"TX{timezone.now().strftime('%Y%m%d')}"
                f"{uuid.uuid4().hex[:6].upper()}"
            )
        super().save(*args, **kwargs)


# ============================================================================
# PAYMENT STAT
# ============================================================================

class PaymentStat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_stats',
        db_index=True,
    )
    number_of_payments = models.IntegerField(default=0)
    total_payments_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    last_transaction_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    last_transaction_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    daily_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1000.00'),
    )
    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('5000.00'),
    )

    class Meta:
        ordering = ['-total_payments_amount']
        indexes = [
            models.Index(
                fields=['total_payments_amount'],
                name='paymentstat_total_amount_idx',
            ),
            models.Index(
                fields=['last_transaction_date'],
                name='paymentstat_last_tx_date_idx',
            ),
        ]

    def __str__(self):
        name = (
            self.user.first_name
            if self.user and self.user.first_name
            else 'Unknown'
        )
        return f"{name} Payments"

    def can_make_transaction(self, amount):
        today = timezone.now().date()
        month = timezone.now().month

        today_transactions = (
            Transaction.objects.filter(
                account__user=self.user,
                created_at__date=today,
                status=Transaction.SUCCESS,
            ).aggregate(models.Sum('amount'))['amount__sum']
            or Decimal('0.00')
        )

        month_transactions = (
            Transaction.objects.filter(
                account__user=self.user,
                created_at__month=month,
                status=Transaction.SUCCESS,
            ).aggregate(models.Sum('amount'))['amount__sum']
            or Decimal('0.00')
        )

        return (
            today_transactions + amount <= self.daily_limit
            and month_transactions + amount <= self.monthly_limit
        )


# ============================================================================
# MONEY TRANSFER
# ============================================================================

class MoneyTransfer(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_transfers',
        db_index=True,
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_transfers',
        db_index=True,
        null=True,
        blank=True,
    )
    sender_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_transfers',
        db_index=True,
    )
    receiver_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers',
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        db_index=True,
    )
    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Transaction.STATUS_CHOICES,
        default=Transaction.PENDING,
        db_index=True,
    )
    narration = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    bank_reference = models.CharField(max_length=100, blank=True, null=True)

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="money_transfers",
        help_text="Ledger journal posted for this transfer.",
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['sender', 'receiver'],
                name='transfer_parties_idx',
            ),
            models.Index(
                fields=['amount', 'status'],
                name='transfer_amount_status_idx',
            ),
            models.Index(
                fields=['created_at', 'status'],
                name='transfer_date_status_idx',
            ),
            GinIndex(
                fields=["narration"],
                name="transfer_narration_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        sender_name = (
            self.sender.first_name
            if self.sender and self.sender.first_name
            else "Unknown"
        )
        receiver_name = (
            self.receiver.first_name
            if self.receiver and self.receiver.first_name
            else "External"
        )
        return f"{sender_name} to {receiver_name} - ₦{self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"TF-{timezone.now().strftime('%Y%m%d')}-"
                f"{uuid.uuid4().hex[:6].upper()}"
            )
        super().save(*args, **kwargs)


# ============================================================================
# WALLET
# ============================================================================

class Wallet(models.Model):
    """
    User wallet — a presentation object over a ledger-backed Account.

    Wallet is NOT a source of truth for money. It carries user-facing
    metadata (reference, status, limits) and points to an Account.

    The authoritative balance is:

        banking.models.accounting.AccountingManager.get_account_balance(
            wallet.account
        )

    Wallet.balance is a read-only property that delegates to the ledger.

    Wallet does not own debit()/credit() methods. All money movement
    goes through AccountingManager.create_double_entry().
    """

    WALLET_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('CLOSED', 'Closed'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet',
        help_text="User who owns this wallet.",
    )

    account = models.OneToOneField(
        Account,
        on_delete=models.PROTECT,
        related_name='wallet',
        help_text=(
            "Canonical ledger-backed account for this wallet. "
            "Every wallet must be backed by an Account."
        ),
    )

    wallet_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique wallet reference number.",
    )

    status = models.CharField(
        max_length=20,
        choices=WALLET_STATUS_CHOICES,
        default='ACTIVE',
        db_index=True,
    )

    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the wallet has been verified.",
    )

    daily_transaction_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('500000.00'),
        help_text="Maximum amount that can be transacted per day.",
    )

    single_transaction_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('100000.00'),
        help_text="Maximum amount per single transaction.",
    )

    daily_transaction_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of transactions today.",
    )

    daily_transaction_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total transaction amount today.",
    )

    last_reset_date = models.DateField(
        default=timezone.localdate,
        help_text="Date when daily counters were last reset.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['wallet_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(daily_transaction_limit__gte=0),
                name='wallet_daily_limit_nonnegative',
            ),
            models.CheckConstraint(
                condition=models.Q(single_transaction_limit__gte=0),
                name='wallet_single_limit_nonnegative',
            ),
        ]

    def __str__(self):
        return f"Wallet {self.wallet_reference} - {self.user.email}"

    def clean(self):
        super().clean()

        errors = {}

        if self.daily_transaction_limit < Decimal('0.00'):
            errors['daily_transaction_limit'] = (
                "Daily transaction limit cannot be negative."
            )

        if self.single_transaction_limit < Decimal('0.00'):
            errors['single_transaction_limit'] = (
                "Single transaction limit cannot be negative."
            )

        if self.single_transaction_limit > self.daily_transaction_limit:
            errors['single_transaction_limit'] = (
                "Single transaction limit cannot exceed daily limit."
            )

        if self.account_id is not None:
            if (
                self.account.user_id is not None
                and self.account.user_id != self.user_id
            ):
                errors['account'] = (
                    "Wallet account must belong to the same user as the wallet."
                )
            if self.account.is_system_account:
                errors['account'] = (
                    "Wallet account cannot be a system account."
                )

        if errors:
            raise ValidationError(errors)

    def _reset_daily_limits_if_needed(self):
        today = timezone.localdate()
        if self.last_reset_date < today:
            self.daily_transaction_count = 0
            self.daily_transaction_amount = Decimal('0.00')
            self.last_reset_date = today
            self.save(update_fields=[
                'daily_transaction_count',
                'daily_transaction_amount',
                'last_reset_date',
                'updated_at',
            ])

    def can_transact(self, amount: Decimal) -> bool:
        """
        Check whether a debit of `amount` is permitted by wallet limits.

        This does NOT check available funds. Fund availability is
        checked by AccountingManager.create_double_entry() against the
        ledger-backed Account.
        """
        self._reset_daily_limits_if_needed()

        if self.status != 'ACTIVE':
            raise ValidationError("Wallet is not active.")

        if amount <= Decimal('0.00'):
            raise ValidationError(
                "Transaction amount must be greater than zero."
            )

        if amount > self.single_transaction_limit:
            raise ValidationError(
                f"Transaction amount exceeds single transaction limit of "
                f"₦{self.single_transaction_limit:,.2f}"
            )

        if (
            self.daily_transaction_amount + amount
            > self.daily_transaction_limit
        ):
            raise ValidationError(
                f"Transaction would exceed daily limit of "
                f"₦{self.daily_transaction_limit:,.2f}"
            )

        return True

    def record_transaction(self, amount: Decimal) -> None:
        """
        Record that a transaction has occurred against this wallet.

        Updates counters only. Does NOT mutate any balance.
        """
        self._reset_daily_limits_if_needed()

        if self.status != 'ACTIVE':
            raise ValidationError(
                "Cannot record transaction on inactive wallet."
            )

        self.daily_transaction_count += 1
        self.daily_transaction_amount += amount

        self.save(update_fields=[
            'daily_transaction_count',
            'daily_transaction_amount',
            'updated_at',
        ])

    def activate(self) -> None:
        self.status = 'ACTIVE'
        self.save(update_fields=['status', 'updated_at'])

    def suspend(self, reason: str = "") -> None:
        self.status = 'SUSPENDED'
        self.save(update_fields=['status', 'updated_at'])

    def close(self) -> None:
        if self.balance != Decimal('0.00'):
            raise ValidationError(
                "Cannot close wallet with non-zero ledger balance."
            )
        self.status = 'CLOSED'
        self.save(update_fields=['status', 'updated_at'])

    @property
    def balance(self) -> Decimal:
        from banking.models.accounting import AccountingManager
        return AccountingManager.get_account_balance(self.account)

    @property
    def is_active(self) -> bool:
        return self.status == 'ACTIVE'

    @property
    def has_balance(self) -> bool:
        return self.balance > Decimal('0.00')

    @property
    def remaining_daily_limit(self) -> Decimal:
        self._reset_daily_limits_if_needed()
        return self.daily_transaction_limit - self.daily_transaction_amount

    @property
    def remaining_daily_transactions(self) -> int:
        MAX_DAILY_TRANSACTIONS = 100
        self._reset_daily_limits_if_needed()
        return MAX_DAILY_TRANSACTIONS - self.daily_transaction_count


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'Transaction',
    'PaymentStat',
    'MoneyTransfer',
    'Wallet',
]