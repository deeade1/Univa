# apps/backend/banking/models/scheduled.py

import uuid
from django.conf import settings
from django.db import models

from .core import Account
from .merchant import Merchant


class ScheduledPayment(models.Model):
    """Standing orders, recurring transfers, bill payments"""

    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    source_account = models.ForeignKey(Account, on_delete=models.CASCADE)
    beneficiary_name = models.CharField(max_length=200)
    beneficiary_account = models.CharField(max_length=20)
    beneficiary_bank_code = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    last_processed = models.DateTimeField(null=True, blank=True)
    next_processing = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Scheduled Payment"
        verbose_name_plural = "Scheduled Payments"
        ordering = ['next_processing']

    def __str__(self):
        return (
            f"ScheduledPayment({self.user.first_name}, "
            f"{self.amount}, {self.frequency})"
        )


class CreditProduct(models.Model):
    """Credit products like Quick Loans, Overdrafts"""

    PRODUCT_TYPES = [
        ('QUICK_LOAN', 'Quick Loan'),
        ('PAYDAY_LOAN', 'Payday Loan'),
        ('OVERDRAFT', 'Overdraft'),
        ('BUSINESS_LOAN', 'Business Loan'),
    ]

    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenor_days = models.IntegerField()  # Loan duration in days
    eligibility_criteria = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Credit Product"
        verbose_name_plural = "Credit Products"
        ordering = ['name']

    def __str__(self):
        return f"CreditProduct({self.name}, {self.product_type})"


class SupportTicket(models.Model):
    """Customer support ticketing system"""

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    ticket_id = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, default='OPEN')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_support_tickets',
    )
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"SupportTicket({self.ticket_id}, {self.subject}, {self.status})"
        )


class APIKey(models.Model):
    """API keys for third-party integrations"""

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    key = models.CharField(max_length=64, unique=True)
    secret = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=list)
    rate_limit = models.IntegerField(default=100)
    webhook_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"APIKey({self.key[:8]}...)"


class RemittanceProvider(models.Model):
    """International money transfer providers"""

    PROVIDER_CHOICES = [
        ('WESTERN_UNION', 'Western Union'),
        ('MONEYGRAM', 'MoneyGram'),
        ('WORLDREMIT', 'WorldRemit'),
        ('REMITLY', 'Remitly'),
        ('WISE', 'Wise (TransferWise)'),
        ('RIA', 'Ria Money Transfer'),
        ('FLUTTERWAVE', 'Flutterwave Send'),
        ('PAYSTACK', 'Paystack Send'),
    ]

    name = models.CharField(max_length=100)
    provider_code = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(
        upload_to='remittance_providers/', null=True, blank=True
    )

    # Service details
    supported_countries = models.JSONField(default=list)
    supported_currencies = models.JSONField(default=list)
    transfer_methods = models.JSONField(default=list)

    # Pricing
    fee_structure = models.JSONField(default=dict)
    exchange_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0
    )

    # Limits
    min_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=10.00
    )
    max_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=10000.00
    )
    daily_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=50000.00
    )

    # API Configuration
    api_endpoint = models.URLField(blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    api_secret = models.CharField(max_length=200, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class InternationalTransfer(models.Model):
    """International money transfer record"""

    TRANSFER_TYPES = [
        ('SEND', 'Send Money Abroad'),
        ('RECEIVE', 'Receive Money from Abroad'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
    ]

    PAYOUT_METHODS = [
        ('BANK_DEPOSIT', 'Bank Deposit'),
        ('CASH_PICKUP', 'Cash Pickup'),
        ('MOBILE_WALLET', 'Mobile Wallet'),
        ('HOME_DELIVERY', 'Home Delivery'),
    ]

    # Transfer identification
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    external_reference = models.CharField(max_length=100, blank=True)

    # User information
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_remittances',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_remittances',
    )

    # Source account (debit side)
    source_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='international_transfers',
        help_text="Customer account debited for this transfer.",
    )

    # Ledger journal that posted this transfer
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='international_transfers',
        help_text="Ledger journal that posted the transfer principal.",
    )

    fee_journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='international_transfer_fees',
        help_text="Ledger journal that posted the platform fee.",
    )

    # Transfer details
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPES)
    provider = models.ForeignKey(RemittanceProvider, on_delete=models.PROTECT)

    # Amounts
    source_amount = models.DecimalField(max_digits=15, decimal_places=2)
    source_currency = models.CharField(max_length=3, default='NGN')
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    target_currency = models.CharField(max_length=3)

    # Exchange rate
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6)
    exchange_rate_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )

    # Fees
    provider_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    platform_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    total_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )

    # Payout method
    payout_method = models.CharField(
        max_length=50,
        choices=PAYOUT_METHODS,
    )

    # Recipient details
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_email = models.EmailField(blank=True)
    recipient_country = models.CharField(max_length=2, blank=True)
    recipient_bank = models.CharField(max_length=100, blank=True)
    recipient_account = models.CharField(max_length=100, blank=True)

    # Status tracking
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Compliance
    purpose_of_remittance = models.CharField(max_length=200, blank=True)
    source_of_funds = models.CharField(max_length=200, blank=True)
    compliance_check_passed = models.BooleanField(default=False)

    # Timeline
    created_at = models.DateTimeField(auto_now_add=True)
    initiated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['created_at']),
            models.Index(
                fields=['journal'],
                name='banking_intl_journal_idx',
            ),
            models.Index(
                fields=['fee_journal'],
                name='banking_intl_fee_journal_idx',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"INTL-{uuid.uuid4().hex[:8].upper()}"
        self.total_fee = self.provider_fee + self.platform_fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"International Transfer {self.reference}"


class ExchangeRate(models.Model):
    """Real-time exchange rates for remittance"""

    base_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)

    buy_rate = models.DecimalField(max_digits=12, decimal_places=6)
    sell_rate = models.DecimalField(max_digits=12, decimal_places=6)
    mid_rate = models.DecimalField(max_digits=12, decimal_places=6)

    provider_buy_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    provider_sell_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )

    provider = models.ForeignKey(
        RemittanceProvider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    next_update = models.DateTimeField()

    class Meta:
        ordering = ['base_currency', 'target_currency']
        constraints = [
            models.UniqueConstraint(
                fields=['base_currency', 'target_currency', 'provider'],
                name='banking_exchangerate_unique_pair_provider',
            ),
        ]

    def __str__(self):
        return (
            f"{self.base_currency}/{self.target_currency}: {self.sell_rate}"
        )