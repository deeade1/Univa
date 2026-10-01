# apps/backend/banking/models/cards.py

from decimal import Decimal

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .payments import Transaction, Wallet


MONEY_QUANTUM = Decimal("0.01")


class CardBrand(models.Model):
    """Card brands (Visa, Mastercard, Verve, etc.)"""

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(
        upload_to='card_brands/', blank=True, null=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class VirtualCard(models.Model):
    """Virtual card for online transactions."""

    CARD_TYPES = [
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('VERVE', 'Verve'),
    ]
    CARD_STATUS = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('FROZEN', 'Frozen'),
        ('EXPIRED', 'Expired'),
        ('CLOSED', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='virtual_cards',
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='virtual_cards',
        help_text="Wallet metadata pointer. Funding source is the "
                  "linked customer Account.",
    )
    card_brand = models.ForeignKey(
        CardBrand, on_delete=models.PROTECT
    )

    # Card details (encrypted)
    card_number = models.CharField(max_length=255)
    card_holder_name = models.CharField(max_length=100)
    expiry_month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    expiry_year = models.IntegerField(
        validators=[MinValueValidator(2024)]
    )
    cvv = models.CharField(max_length=255)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    last_four = models.CharField(max_length=4)
    bin = models.CharField(max_length=6)

    # Limits
    daily_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=100000
    )
    monthly_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=1000000
    )
    per_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=50000
    )

    # Status
    status = models.CharField(
        max_length=20, choices=CARD_STATUS, default='PENDING'
    )
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    is_stolen = models.BooleanField(default=False)

    # Dates
    issued_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['last_four']),
            models.Index(fields=['card_number']),
        ]
        ordering = ['-issued_at']

    def __str__(self):
        return (
            f"{self.card_type} ****{self.last_four} ({self.user.email})"
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    # ------------------------------------------------------------------
    # Card number / CVV encryption
    #
    # Fernet requires a bytes key. settings.CARD_ENCRYPTION_KEY is a
    # str, so encode before passing to Fernet.
    # ------------------------------------------------------------------

    @staticmethod
    def _cipher() -> Fernet:
        return Fernet(settings.CARD_ENCRYPTION_KEY.encode())

    def get_card_number(self) -> str:
        return self._decrypt_field(self.card_number)

    def get_cvv(self) -> str:
        return self._decrypt_field(self.cvv)

    def _encrypt_field(self, value: str) -> str:
        return self._cipher().encrypt(value.encode()).decode()

    def _decrypt_field(self, value: str) -> str:
        return self._cipher().decrypt(value.encode()).decode()

    # ------------------------------------------------------------------
    # Usage — derived from CardTransaction
    #
    # These are NOT stored. Prior versions kept running counters on
    # the row which could drift from the transaction table on any
    # failed write, manual admin edit, or reversal.
    # ------------------------------------------------------------------

    @property
    def daily_usage(self) -> Decimal:
        from django.db.models import Sum

        today = timezone.now().date()
        total = (
            self.transactions
            .filter(
                status__in=["AUTHORIZED", "SETTLED"],
                created_at__date=today,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return Decimal(total).quantize(MONEY_QUANTUM)

    @property
    def monthly_usage(self) -> Decimal:
        from django.db.models import Sum

        now = timezone.now()
        total = (
            self.transactions
            .filter(
                status__in=["AUTHORIZED", "SETTLED"],
                created_at__year=now.year,
                created_at__month=now.month,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return Decimal(total).quantize(MONEY_QUANTUM)

    @property
    def total_usage(self) -> Decimal:
        from django.db.models import Sum

        total = (
            self.transactions
            .filter(status__in=["AUTHORIZED", "SETTLED"])
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return Decimal(total).quantize(MONEY_QUANTUM)


class CardTransaction(models.Model):
    """Transactions made using virtual cards."""

    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('REFUND', 'Refund'),
        ('AUTHORIZATION', 'Authorization'),
        ('REVERSAL', 'Reversal'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('AUTHORIZED', 'Authorized'),
        ('SETTLED', 'Settled'),
        ('DECLINED', 'Declined'),
        ('REVERSED', 'Reversed'),
        ('CHARGEBACK', 'Chargeback'),
    ]

    card = models.ForeignKey(
        VirtualCard,
        on_delete=models.PROTECT,
        related_name='transactions',
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='card_transaction',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='card_transactions',
    )

    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')

    merchant_name = models.CharField(max_length=200)
    merchant_category_code = models.CharField(max_length=4)
    merchant_country = models.CharField(max_length=2)

    auth_code = models.CharField(
        max_length=50, unique=True, null=True
    )
    auth_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    status_reason = models.TextField(blank=True)

    acquirer_id = models.CharField(max_length=50)
    acquirer_reference = models.CharField(
        max_length=100, unique=True, null=True
    )

    # Ledger journal that posted the hold / settlement / reversal.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='card_transactions',
        help_text="Ledger journal that posted the hold / settlement.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['card', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['acquirer_reference']),
            models.Index(
                fields=['journal'],
                name='banking_cardt_journal_idx',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.transaction_type} - {self.amount} "
            f"{self.currency} - {self.merchant_name}"
        )


class PhysicalCard(models.Model):
    """Physical debit card requests."""

    DELIVERY_STATUS = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='physical_cards',
    )
    virtual_card = models.ForeignKey(
        VirtualCard,
        on_delete=models.PROTECT,
        related_name='physical_card_requests',
    )

    # Delivery
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_state = models.CharField(max_length=100)
    delivery_country = models.CharField(max_length=2, default='NG')
    delivery_phone = models.CharField(max_length=20)

    shipping_method = models.CharField(max_length=50)
    tracking_number = models.CharField(max_length=100, blank=True)
    delivery_status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS, default='PENDING'
    )

    card_fee = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Ledger journal that posted the fee.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='physical_card_requests',
        help_text="Ledger journal that posted the card and shipping fee.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'delivery_status']),
            models.Index(fields=['tracking_number']),
            models.Index(
                fields=['journal'],
                name='banking_physc_journal_idx',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Physical Card for {self.user.email} - "
            f"{self.delivery_status}"
        )

    @property
    def total_fee(self) -> Decimal:
        return (
            (self.card_fee or Decimal("0.00"))
            + (self.shipping_fee or Decimal("0.00"))
        ).quantize(MONEY_QUANTUM)