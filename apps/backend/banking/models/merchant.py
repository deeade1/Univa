import uuid 
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.conf import settings
from .core import Bank, Account


class Merchant(models.Model):
    """OPay-style merchant/vendor accounts"""
    MERCHANT_TYPES = [
        ('INDIVIDUAL', 'Individual Seller'),
        ('SMALL_BUSINESS', 'Small Business'),
        ('MEDIUM_BUSINESS', 'Medium Business'),
        ('ENTERPRISE', 'Enterprise'),
        ('ONLINE_STORE', 'Online Store'),
    ]
    
    VERIFICATION_STATUS = [
        ('UNVERIFIED', 'Unverified'),
        ('PENDING', 'Verification Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    # Merchant Identification
    merchant_id = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merchant_profile'
    )
    
    # Business Details
    business_name = models.CharField(max_length=255, db_index=True)
    business_type = models.CharField(max_length=50, choices=MERCHANT_TYPES)
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    
    # Contact Details
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=20)
    business_address = models.TextField()
    business_state = models.CharField(max_length=100)
    business_city = models.CharField(max_length=100)
    
    # Business Accounts
    settlement_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='merchant_settlements'
    )
    settlement_bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name='merchant_banks'
    )
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='UNVERIFIED'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_merchants'
    )
    
    # Documents (in production, use FileField with secure storage)
    id_document_front = models.ImageField(upload_to='merchant/docs/', blank=True)
    id_document_back = models.ImageField(upload_to='merchant/docs/', blank=True)
    business_registration_cert = models.ImageField(upload_to='merchant/docs/', blank=True)
    utility_bill = models.ImageField(upload_to='merchant/docs/', blank=True)
    
    # Fees & Limits
    transaction_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.5  # 1.5% fee
    )
    daily_transaction_limit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=1000000.00  # ₦1M
    )
    monthly_transaction_limit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=5000000.00  # ₦5M
    )
    
    # Settlement
    settlement_schedule = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('INSTANT', 'Instant (with fee)'),
        ],
        default='DAILY'
    )
    last_settlement_at = models.DateTimeField(null=True, blank=True)
    next_settlement_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_flagged = models.BooleanField(default=False, db_index=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business_name', 'verification_status']),
            models.Index(fields=['verification_status', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.business_name} ({self.merchant_id})"
    
    def save(self, *args, **kwargs):
        if not self.merchant_id:
            self.merchant_id = f"MER{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def calculate_fee(self, amount):
        """Calculate merchant fee for transaction"""
        fee = amount * (self.transaction_fee_percentage / 100)
        # Minimum fee of ₦10
        return max(fee, Decimal('10.00'))
    
    @property
    def total_transactions(self) -> int:
        return self.transactions.count()

    @property
    def successful_transactions(self) -> int:
        return self.transactions.filter(status="COMPLETED").count()

    @property
    def total_volume(self) -> Decimal:
        return (
            self.transactions.filter(status="COMPLETED")
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
  
    def can_accept_payment(self, amount):
        """Check whether the merchant can accept a payment today."""
        today = timezone.now().date()

        from .payments import Transaction

        today_total = (
            Transaction.objects.filter(
                account=self.settlement_account,
                status=Transaction.SUCCESS,
                created_at__date=today,
            ).aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        return (today_total + amount) <= self.daily_transaction_limit


class MerchantTransaction(models.Model):
    """Transactions involving merchants"""
    TRANSACTION_TYPES = [
        ('SALE', 'Sale/Purchase'),
        ('REFUND', 'Refund'),
        ('SETTLEMENT', 'Settlement'),
        ('CHARGEBACK', 'Chargeback'),
    ]
    
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merchant_purchases'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="merchant_transactions",
        help_text="Ledger journal that posted the sale principal.",
    )

    settled_journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="merchant_settlements",
        help_text="Ledger journal that posted the settlement.",
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Items (for sales)
    items = models.JSONField(default=list)  # List of items purchased
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Settlement
    is_settled = models.BooleanField(default=False, db_index=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    settlement_reference = models.CharField(max_length=100, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['is_settled', 'created_at']),
            models.Index(
                fields=["journal"],
                name="banking_mtx_journal_idx",
            ),
            models.Index(
                fields=["settled_journal"],
                name="banking_mtx_settled_jour_idx",
            ),
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - ₦{self.amount} - {self.merchant.business_name}"