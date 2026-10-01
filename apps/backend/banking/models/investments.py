# apps/backend/banking/models/investments.py

"""
Investment models.

Architecture
------------

Investment records are metadata. Money movement is ledger-backed.

The money fields on Investment are derived:

    expected_return      computed from amount, rate, tenure
    actual_return        sum of credits to the wallet's account
                         from journals linked to this investment
    total_return         amount + actual_return
    interest_paid        sum of InvestmentEarnings amounts
    early_withdrawal_fee the fee on the withdrawal journal

InvestmentProduct aggregates are derived from Investment rows:

    total_invested       sum of Investment.amount for active/matured
    total_investors      count of distinct users with active/matured

Investment.journal links to the AccountingJournal that posted the
purchase. InvestmentEarnings.journal links to the journal that paid
an earning.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from banking.models.payments import Wallet


# ============================================================================
# INVESTMENT PRODUCT
# ============================================================================

class InvestmentProduct(models.Model):
    """Investment products offered."""

    PRODUCT_TYPES = [
        ('FIXED_DEPOSIT', 'Fixed Deposit'),
        ('TREASURY_BILLS', 'Treasury Bills'),
        ('MONEY_MARKET', 'Money Market'),
        ('REAL_ESTATE', 'Real Estate'),
        ('AGRICULTURE', 'Agriculture'),
        ('BONDS', 'Bonds'),
        ('STOCKS', 'Stocks'),
        ('CRYPTO', 'Crypto'),
        ('SAVINGS', 'Savings'),
        ('OTHER', 'Other'),
    ]
    RISK_LEVELS = [
        ('VERY_LOW', 'Very Low'),
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('VERY_HIGH', 'Very High'),
    ]
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUALLY', 'Annually'),
        ('AT_MATURITY', 'At Maturity'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    description = models.TextField()
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)

    min_investment = models.DecimalField(max_digits=15, decimal_places=2)
    max_investment = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    min_tenure_days = models.IntegerField()
    max_tenure_days = models.IntegerField()
    default_tenure_days = models.IntegerField()

    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    interest_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='AT_MATURITY',
    )
    compounding = models.BooleanField(default=False)
    compounding_frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, null=True, blank=True,
    )

    management_fee = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )
    early_withdrawal_fee = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )

    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)

    max_capacity = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )

    available_from = models.DateTimeField()
    available_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_product_type_display()})"

    @property
    def total_invested(self):
        """
        Total principal currently invested in this product, summed
        across investments that are still live.
        """
        result = (
            self.investments
            .filter(status__in=['ACTIVE', 'MATURED'])
            .aggregate(total=Sum('amount'))
        )
        return result['total'] or Decimal('0.00')

    @property
    def total_investors(self):
        """
        Number of distinct users with a live investment in this product.
        """
        return (
            self.investments
            .filter(status__in=['ACTIVE', 'MATURED'])
            .values('user_id')
            .distinct()
            .count()
        )

    @property
    def available_slots(self):
        """Remaining capacity, or None if capacity is unlimited."""
        if self.max_capacity:
            return self.max_capacity - self.total_invested
        return None


# ============================================================================
# INVESTMENT
# ============================================================================

class Investment(models.Model):
    """User's investment records."""

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('MATURED', 'Matured'),
        ('WITHDRAWN', 'Withdrawn'),
        ('CANCELLED', 'Cancelled'),
        ('PENDING', 'Pending'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='investments',
    )
    product = models.ForeignKey(
        InvestmentProduct,
        on_delete=models.PROTECT,
        related_name='investments',
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='investments',
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    tenure_days = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    start_date = models.DateTimeField()
    maturity_date = models.DateTimeField()
    interest_payment_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
    )
    status_reason = models.TextField(blank=True)

    withdrawal_date = models.DateTimeField(null=True, blank=True)
    early_withdrawal = models.BooleanField(default=False)

    next_interest_date = models.DateTimeField(null=True, blank=True)

    investment_reference = models.CharField(max_length=100, unique=True)

    # Ledger linkage
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='investments',
        help_text="Ledger journal posted for the initial purchase.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['maturity_date']),
            models.Index(fields=['investment_reference']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} - ₦{self.amount}"

    # ------------------------------------------------------------------
    # Derived money fields
    # ------------------------------------------------------------------

    @property
    def expected_return(self):
        """
        Expected interest over the full tenure.

        Expected return = amount * (rate / 100) * (tenure_days / 365)

        Uses Decimal arithmetic throughout to avoid float precision loss.
        """
        rate = Decimal(str(self.interest_rate)) / Decimal("100")
        days = Decimal(self.tenure_days)
        year = Decimal("365")
        raw = Decimal(str(self.amount)) * rate * (days / year)
        return raw.quantize(Decimal("0.01"))

    @property
    def interest_paid(self):
        """
        Sum of earnings actually paid to the user for this investment.
        """
        result = self.earnings.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')

    @property
    def actual_return(self):
        """
        Interest actually earned, based on paid earnings.

        For ACTIVE investments this is the sum of earnings already
        paid out. For MATURED or WITHDRAWN investments this equals
        interest_paid because no further earnings will accrue.
        """
        return self.interest_paid

    @property
    def total_return(self):
        """
        Principal + actual return. Zero if the investment hasn't
        matured or been withdrawn yet.
        """
        if self.status in ('MATURED', 'WITHDRAWN'):
            return (Decimal(str(self.amount)) + self.actual_return).quantize(
                Decimal("0.01")
            )
        return Decimal("0.00")

    @property
    def early_withdrawal_fee(self):
        """
        Fee charged for early withdrawal, if any.

        This is derived from the product's early_withdrawal_fee
        percentage applied to the principal.
        """
        if not self.early_withdrawal:
            return Decimal("0.00")
        pct = Decimal(str(self.product.early_withdrawal_fee)) / Decimal("100")
        return (Decimal(str(self.amount)) * pct).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def calculate_return(self):
        """
        Current accrued return based on time held.

        For an ACTIVE investment, this is a pro-rata accrual that
        stops at maturity. For a MATURED investment, it equals
        expected_return.
        """
        now = timezone.now()
        end = min(now, self.maturity_date)
        days_held = (end - self.start_date).days
        if days_held < 0:
            days_held = 0

        rate = Decimal(str(self.interest_rate)) / Decimal("100")
        year = Decimal("365")
        raw = Decimal(str(self.amount)) * rate * (Decimal(days_held) / year)
        return raw.quantize(Decimal("0.01"))

    def is_matured(self):
        return timezone.now() >= self.maturity_date


# ============================================================================
# INVESTMENT EARNINGS
# ============================================================================

class InvestmentEarnings(models.Model):
    """Earnings from investments."""

    EARNING_TYPES = [
        ('INTEREST', 'Interest'),
        ('BONUS', 'Bonus'),
        ('REFERRAL', 'Referral'),
        ('OTHER', 'Other'),
    ]

    investment = models.ForeignKey(
        Investment,
        on_delete=models.CASCADE,
        related_name='earnings',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='investment_earnings',
    )
    transaction = models.ForeignKey(
        'banking.Transaction',
        on_delete=models.PROTECT,
        related_name='investment_earnings',
        null=True,
        blank=True,
    )

    earning_type = models.CharField(max_length=20, choices=EARNING_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255)

    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    paid_at = models.DateTimeField(auto_now_add=True)

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='investment_earnings',
        help_text="Ledger journal that paid this earning.",
    )

    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-paid_at']
        indexes = [
            models.Index(fields=['investment', 'earning_type']),
            models.Index(fields=['user', 'paid_at']),
        ]

    def __str__(self):
        return f"{self.get_earning_type_display()} - ₦{self.amount}"