# apps/backend/banking/models/bill_payments.py

"""
Bill payment models for the banking domain.

This module contains:
    - BillCategory: Bill categories/types
    - Biller: Biller/provider information
    - BillPayment: Record of bill payment transactions
    - BillProvider: Utility bill providers
    - BillAccount: Customer's bill accounts
    - Bill: Individual bill instance
    - AirtimePurchase: Airtime top-up transactions
    - DataBundlePurchase: Data bundle purchases
"""

import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from banking.models.core import Account
from banking.models.payments import Transaction


# ============================================================================
# BILL CATEGORY
# ============================================================================

class BillCategory(models.Model):
    """Categories of bills that can be paid."""
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Bill Category"
        verbose_name_plural = "Bill Categories"

    def __str__(self):
        return self.name


# ============================================================================
# BILLER
# ============================================================================

class Biller(models.Model):
    """Biller/provider information."""
    
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    category = models.ForeignKey(
        BillCategory,
        on_delete=models.PROTECT,
        related_name='billers'
    )
    code = models.CharField(max_length=50, unique=True, db_index=True)
    logo = models.ImageField(upload_to='billers/', blank=True, null=True)
    description = models.TextField(blank=True)
    
    # API configuration
    api_endpoint = models.URLField(blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    
    # Fee configuration
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fee percentage (0-100)"
    )
    fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fixed fee amount"
    )
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Biller"
        verbose_name_plural = "Billers"
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate fee for a given amount."""
        fee = Decimal('0.00')
        if self.fee_percentage > 0:
            fee += amount * (self.fee_percentage / 100)
        if self.fee_fixed > 0:
            fee += self.fee_fixed
        return fee.quantize(Decimal('0.01'))

    def validate_amount(self, amount: Decimal) -> None:
        """Validate that amount is within allowed range."""
        if amount < self.min_amount:
            raise ValidationError(f"Amount must be at least ₦{self.min_amount:,.2f}")
        if self.max_amount and amount > self.max_amount:
            raise ValidationError(f"Amount cannot exceed ₦{self.max_amount:,.2f}")


# ============================================================================
# BILL PROVIDER (from scheduled.py)
# ============================================================================

class BillProvider(models.Model):
    """Utility bill providers."""
    
    PROVIDER_TYPES = [
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('INTERNET', 'Internet'),
        ('CABLE_TV', 'Cable TV'),
        ('WASTE', 'Waste Management'),
        ('RENT', 'Rent'),
        ('INSURANCE', 'Insurance'),
    ]
    
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    provider_code = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='bill_providers/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # API Configuration
    api_endpoint = models.URLField(blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    validation_required = models.BooleanField(default=True)
    
    # Supported payment methods
    supports_auto_debit = models.BooleanField(default=False)
    supports_one_time_payment = models.BooleanField(default=True)
    
    # Service areas
    service_states = models.JSONField(default=list)
    service_cities = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Bill Provider"
        verbose_name_plural = "Bill Providers"

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


# ============================================================================
# BILL ACCOUNT (from scheduled.py)
# ============================================================================

class BillAccount(models.Model):
    """Customer's bill accounts (meter numbers, customer IDs)."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.ForeignKey(BillProvider, on_delete=models.CASCADE)
    
    # Account identification
    account_number = models.CharField(max_length=100, db_index=True)
    account_name = models.CharField(max_length=200)
    customer_name = models.CharField(max_length=200, blank=True)
    
    # Service address
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    
    # Validation status
    is_validated = models.BooleanField(default=False)
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_reference = models.CharField(max_length=100, blank=True)
    
    # Auto-pay settings
    auto_pay_enabled = models.BooleanField(default=False)
    auto_pay_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    auto_pay_source_account = models.ForeignKey(
        'banking.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'provider', 'account_number']
        ordering = ['-created_at']
        verbose_name = "Bill Account"
        verbose_name_plural = "Bill Accounts"

    def __str__(self):
        return f"{self.account_number} - {self.provider.name}"


# ============================================================================
# BILL (from scheduled.py)
# ============================================================================

class Bill(models.Model):
    """Individual bill instance."""
    
    BILL_STATUS = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
        ('DISPUTED', 'Disputed'),
    ]
    
    bill_account = models.ForeignKey(BillAccount, on_delete=models.CASCADE)
    
    # Bill identification
    bill_reference = models.CharField(max_length=100, unique=True, db_index=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    
    # Billing period
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    due_date = models.DateField()
    issue_date = models.DateTimeField(auto_now_add=True)
    
    # Amounts
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Breakdown
    breakdown = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, choices=BILL_STATUS, default='PENDING')
    is_auto_paid = models.BooleanField(default=False)
    
    # Payment info
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Notifications
    reminder_sent = models.BooleanField(default=False)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['bill_account', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.bill_reference:
            self.bill_reference = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        self.outstanding_amount = self.total_amount - self.amount_paid
        
        # Auto-update status
        if self.outstanding_amount <= 0 and self.total_amount > 0:
            self.status = 'PAID'
        elif self.due_date < timezone.now().date() and self.status == 'PENDING':
            self.status = 'OVERDUE'
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Bill {self.bill_reference} - ₦{self.total_amount}"


# ============================================================================
# BILL PAYMENT (MERGED - Comprehensive Version)
# ============================================================================

class BillPayment(models.Model):
    """
    Record of bill payment transactions.
    
    This model tracks bill payments made by users through the banking platform.
    It supports multiple bill types and integrates with the transaction system.
    """
    
    # ==================================================================
    # BILL TYPES
    # ==================================================================
    
    ELECTRICITY = 'electricity'
    WATER = 'water'
    INTERNET = 'internet'
    CABLE_TV = 'cable_tv'
    AIRTIME = 'airtime'
    DATA = 'data'
    GOVERNMENT = 'government'
    EDUCATION = 'education'
    INSURANCE = 'insurance'
    LOAN = 'loan'
    OTHER = 'other'
    
    BILL_TYPES = [
        (ELECTRICITY, 'Electricity Bill'),
        (WATER, 'Water Bill'),
        (INTERNET, 'Internet Bill'),
        (CABLE_TV, 'Cable TV Bill'),
        (AIRTIME, 'Airtime Purchase'),
        (DATA, 'Data Purchase'),
        (GOVERNMENT, 'Government Payment'),
        (EDUCATION, 'Education Payment'),
        (INSURANCE, 'Insurance Payment'),
        (LOAN, 'Loan Payment'),
        (OTHER, 'Other Bill'),
    ]
    
    # ==================================================================
    # STATUS CHOICES
    # ==================================================================
    
    PENDING = 'PENDING'
    VALIDATING = 'VALIDATING'
    PROCESSING = 'PROCESSING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    REVERSED = 'REVERSED'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (VALIDATING, 'Validating'),
        (PROCESSING, 'Processing'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
        (REVERSED, 'Reversed'),
    ]
    
    # ==================================================================
    # FIELDS
    # ==================================================================
    
    # User and Account
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bill_payments',
        db_index=True
    )
    
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    
    # Transaction linking
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name='bill_payment',
        null=True,
        blank=True
    )
    
    
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bill_payments',
        help_text="Ledger journal that posted the principal.",
    )

    fee_journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bill_payment_fees',
        help_text="Ledger journal that posted the fee, if any.",
    )
    
    # Biller Information
    biller = models.ForeignKey(
        Biller,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )
    
    # Bill Type
    bill_type = models.CharField(
        max_length=20,
        choices=BILL_TYPES,
        db_index=True
    )
    
    provider = models.CharField(
        max_length=100,
        db_index=True
    )
    
    # Customer Details
    customer_id = models.CharField(max_length=100, db_index=True)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_reference = models.CharField(max_length=100, blank=True)
    
    # Amount Details
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        db_index=True
    )
    
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Amount + Fee"
    )
    
    # Reference Numbers
    reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Internal payment reference"
    )
    
    biller_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference from biller"
    )
    
    provider_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference from provider"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True
    )
    
    status_reason = models.TextField(blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Retry Information
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    
    metadata = models.JSONField(
        default=dict,
        blank=True,  # ADD THIS
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ==================================================================
    # META
    # ==================================================================

    class Meta:
        ordering = ['-initiated_at']
        verbose_name = "Bill Payment"
        verbose_name_plural = "Bill Payments"
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['biller', 'customer_id']),
            models.Index(fields=['bill_type', 'status']),
            models.Index(fields=['amount', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['biller_reference']),
            models.Index(fields=['provider_reference']),
            models.Index(fields=['reference']),
            models.Index(
                fields=['journal'],
                name='billing_bp_journal_idx',
            ),
            models.Index(
                fields=['fee_journal'],
                name='billing_bp_fee_journal_idx',
            ),
        ]

    # ==================================================================
    # STRING REPRESENTATION
    # ==================================================================

    def __str__(self):
        if self.biller:
            return f"{self.biller.name} - {self.customer_id} - ₦{self.amount}"
        return f"{self.get_bill_type_display()} - {self.provider} - ₦{self.amount}"

    # ==================================================================
    # METHODS
    # ==================================================================

    def clean(self):
        """Validate model state."""
        super().clean()
        
        if self.fee < 0:
            raise ValidationError({'fee': "Fee cannot be negative."})
        
        if self.total_amount != self.amount + self.fee:
            raise ValidationError({
                'total_amount': "Total amount must equal amount + fee."
            })

    def save(self, *args, **kwargs):
        """Calculate total_amount before saving."""
        if not self.total_amount:
            self.total_amount = self.amount + self.fee
        super().save(*args, **kwargs)

    def calculate_fee(self) -> Decimal:
        """Calculate fee based on biller configuration."""
        if self.biller:
            return self.biller.calculate_fee(self.amount)
        return Decimal('0.00')

    def mark_validating(self):
        """Mark payment as validating."""
        self.status = self.VALIDATING
        self.validated_at = timezone.now()
        self.save(update_fields=['status', 'validated_at', 'updated_at'])

    def mark_processing(self):
        """Mark payment as processing."""
        self.status = self.PROCESSING
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])

    def mark_success(self):
        """Mark payment as successful."""
        self.status = self.SUCCESS
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_failed(self, reason: str = ""):
        """Mark payment as failed."""
        self.status = self.FAILED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    def mark_cancelled(self, reason: str = ""):
        """Mark payment as cancelled."""
        self.status = self.CANCELLED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    def mark_reversed(self, reason: str = ""):
        """Mark payment as reversed."""
        self.status = self.REVERSED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    @property
    def is_pending(self) -> bool:
        """Check if payment is pending."""
        return self.status == self.PENDING

    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == self.SUCCESS

    @property
    def can_retry(self) -> bool:
        """Check if payment can be retried."""
        return self.status in [self.FAILED, self.CANCELLED] and self.retry_count < 3

    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['retry_count', 'last_retry_at', 'updated_at'])


# ============================================================================
# AIRTIME PURCHASE (MERGED)
# ============================================================================

class AirtimePurchase(models.Model):
    """
    Airtime top-up purchases.
    
    This model tracks airtime purchases made by users through the banking platform.
    It supports multiple network operators and integrates with the transaction system.
    """
    
    # Network Operators
    MTN = 'MTN'
    AIRTEL = 'AIRTEL'
    GLO = 'GLO'
    ETISALAT = 'ETISALAT'
    NINE_MOBILE = '9MOBILE'
    
    OPERATORS = [
        (MTN, 'MTN'),
        (AIRTEL, 'Airtel'),
        (GLO, 'Glo'),
        (ETISALAT, 'Etisalat'),
        (NINE_MOBILE, '9mobile'),
    ]
    
    # Status Choices
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    REVERSED = 'REVERSED'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
        (REVERSED, 'Reversed'),
    ]
    
    # Fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='airtime_purchases',
        db_index=True
    )
    
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name='airtime_purchase',
        null=True,
        blank=True
    )
    
    
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='airtime_purchases',
        help_text="Ledger journal that posted the principal.",
    )

    fee_journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='airtime_purchase_fees',
        help_text="Ledger journal that posted the fee, if any.",
    )
    
    phone_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Phone number to top up"
    )
    
    operator = models.CharField(
        max_length=20,
        choices=OPERATORS,
        db_index=True,
        help_text="Network operator"
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        db_index=True,
        help_text="Airtime amount"
    )
    
    bonus_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Bonus airtime from provider"
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount + fee (total charged)"
    )
    
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Service fee"
    )
    
    reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Internal purchase reference"
    )
    
    provider_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference from provider"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True
    )
    
    status_reason = models.TextField(
        blank=True,
        help_text="Reason for current status"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Airtime Purchase"
        verbose_name_plural = "Airtime Purchases"
        indexes = [
            models.Index(fields=['user', 'status'], name='airtime_user_status_idx'),
            models.Index(fields=['operator', 'status'], name='airtime_operator_status_idx'),
            models.Index(fields=['amount', 'status'], name='airtime_amount_status_idx'),
            models.Index(fields=['phone_number'], name='airtime_phone_idx'),
            models.Index(fields=['reference'], name='airtime_reference_idx'),
            models.Index(fields=['provider_reference'], name='airtime_provider_ref_idx'),
            models.Index(
                fields=['journal'],
                name='billing_airtime_journal_idx',
            ),
            models.Index(
                fields=['fee_journal'],
                name='billing_airtime_fee_jour_idx',
            ),
        ]

    def __str__(self):
        return f"{self.operator} - {self.phone_number} - ₦{self.amount}"

    def clean(self):
        """Validate model state."""
        super().clean()
        
        if self.fee < 0:
            raise ValidationError({'fee': "Fee cannot be negative."})
        
        if self.bonus_amount < 0:
            raise ValidationError({'bonus_amount': "Bonus amount cannot be negative."})

    def save(self, *args, **kwargs):
        """Calculate total_amount before saving."""
        if not self.total_amount:
            self.total_amount = self.amount + self.fee
        super().save(*args, **kwargs)


    def calculate_fee(self) -> Decimal:
        """Calculate fee based on operator/amount."""
        if self.amount <= Decimal('50.00'):
            return Decimal('5.00')
        elif self.amount <= Decimal('100.00'):
            return Decimal('7.00')
        elif self.amount <= Decimal('500.00'):
            return Decimal('10.00')
        elif self.amount <= Decimal('1000.00'):
            return Decimal('15.00')
        return Decimal('20.00')
 
 
    def mark_processing(self):
        """Mark purchase as processing."""
        self.status = self.PROCESSING
        self.processing_at = timezone.now()
        self.save(update_fields=['status', 'processing_at', 'updated_at'])

    def mark_success(self, provider_ref: str = None):
        """Mark purchase as successful."""
        self.status = self.SUCCESS
        self.completed_at = timezone.now()
        if provider_ref:
            self.provider_reference = provider_ref
        self.save(update_fields=['status', 'completed_at', 'provider_reference', 'updated_at'])

    def mark_failed(self, reason: str = ""):
        """Mark purchase as failed."""
        self.status = self.FAILED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    def mark_cancelled(self, reason: str = ""):
        """Mark purchase as cancelled."""
        self.status = self.CANCELLED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    def mark_reversed(self, reason: str = ""):
        """Mark purchase as reversed."""
        self.status = self.REVERSED
        self.status_reason = reason
        self.save(update_fields=['status', 'status_reason', 'updated_at'])

    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['retry_count', 'last_retry_at', 'updated_at'])

    @property
    def is_pending(self) -> bool:
        """Check if purchase is pending."""
        return self.status == self.PENDING

    @property
    def is_successful(self) -> bool:
        """Check if purchase was successful."""
        return self.status == self.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if purchase failed."""
        return self.status == self.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if purchase can be retried."""
        return self.status in [self.FAILED, self.CANCELLED] and self.retry_count < 3

    @property
    def total_charged(self) -> Decimal:
        """Get total amount charged (amount + fee)."""
        return self.amount + self.fee


# ============================================================================
# DATA BUNDLE PURCHASE
# ============================================================================

class DataBundlePurchase(models.Model):
    """Data bundle purchases."""
    
    DATA_TYPES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name='data_purchase',
        null=True,
        blank=True
    )
    
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name='data_bundle_purchases',
        help_text="Source account that funded this purchase.",
    )

    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='data_bundle_purchases',
        help_text="Ledger journal that posted the purchase.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='data_purchases'
    )
    phone_number = models.CharField(max_length=20)
    operator = models.CharField(max_length=20, choices=AirtimePurchase.OPERATORS)
    
    bundle_name = models.CharField(max_length=100)
    data_amount = models.CharField(max_length=20)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    validity_days = models.IntegerField()
    
    provider_reference = models.CharField(max_length=100, unique=True, null=True)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['phone_number', 'operator']),
            models.Index(
                fields=['account'],
                name='billing_data_account_idx',
            ),
            models.Index(
                fields=['journal'],
                name='billing_data_journal_idx',
            ),
        ]
        
        ordering = ['-created_at']
        verbose_name = "Data Bundle Purchase"
        verbose_name_plural = "Data Bundle Purchases"

    def __str__(self):
        return f"{self.operator} - {self.bundle_name} - ₦{self.price}"


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'BillCategory',
    'Biller',
    'BillProvider',
    'BillAccount',
    'Bill',
    'BillPayment',
    'AirtimePurchase',
    'DataBundlePurchase',
]