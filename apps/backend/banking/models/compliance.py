# apps/backend/banking/models/compliance.py

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .core import Account


class Webhook(models.Model):
    """For external system notifications"""

    EVENT_TYPES = [
        ('transfer.completed', 'Transfer Completed'),
        ('transfer.failed', 'Transfer Failed'),
        ('payment.received', 'Payment Received'),
        ('fraud.detected', 'Fraud Detected'),
        ('account.updated', 'Account Updated'),
    ]

    url = models.URLField()
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    secret = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['event_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} -> {self.url}"


class WebhookDelivery(models.Model):
    """Track webhook delivery attempts"""

    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE)
    payload = models.JSONField()
    response_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['webhook', 'delivered']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Webhook {self.webhook.id} - {self.delivered}"


class CurrencyExchangeRate(models.Model):
    base_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_updated"]
        constraints = [
            models.UniqueConstraint(
                fields=['base_currency', 'target_currency'],
                name='banking_currency_pair_unique',
            ),
        ]
        indexes = [
            models.Index(
                fields=['base_currency', 'target_currency'],
                name='currency_pair_idx',
            ),
            models.Index(
                fields=['last_updated'],
                name='currency_last_updated_idx',
            ),
        ]

    def __str__(self):
        return (
            f"{self.base_currency} to {self.target_currency}: {self.rate}"
        )


class Contact(models.Model):
    """Contact model with central User reference."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacts',
        db_index=True,
    )
    account_number = models.CharField(
        max_length=30, blank=True, db_index=True
    )
    bank_name = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(
        upload_to='contacts/', null=True, blank=True
    )
    is_beneficiary = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['user', 'is_beneficiary'],
                name='contact_user_beneficiary_idx',
            ),
        ]

    def __str__(self):
        name = self.user.first_name if self.user else "Unknown"
        phone = self.user.phone_number if self.user else "Unknown"
        return f"{name} ({phone})"


class ATMCard(models.Model):
    """ATM Card model with central User reference."""

    VISA = 'visa'
    MASTERCARD = 'mastercard'
    VERVE = 'verve'
    CARD_TYPES = [
        (VISA, 'Visa'),
        (MASTERCARD, 'Mastercard'),
        (VERVE, 'Verve'),
    ]

    ACTIVE = 'active'
    INACTIVE = 'inactive'
    BLOCKED = 'blocked'
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
        (BLOCKED, 'Blocked'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cards',
        db_index=True,
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='cards',
        db_index=True,
    )
    card_number = models.CharField(max_length=16, unique=True, db_index=True)
    card_type = models.CharField(
        max_length=20,
        choices=CARD_TYPES,
        default=VISA,
        db_index=True,
    )
    cvv_hash = models.CharField(max_length=128)
    pin_hash = models.CharField(max_length=128)
    expiry_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        db_index=True,
    )
    daily_withdrawal_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=500.00
    )
    daily_pos_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=1000.00
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_cards_created',
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_cards_activated',
    )
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_cards_blocked',
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=['card_type', 'status'],
                name='card_type_status_idx',
            ),
            models.Index(
                fields=['expiry_date', 'status'],
                name='card_expiry_status_idx',
            ),
            models.Index(
                fields=['user', 'status'],
                name='card_user_status_idx',
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_card_type_display()} "
            f"****{self.card_number[-4:]}"
        )

    def set_pin(self, raw_pin):
        if len(raw_pin) != 4 or not raw_pin.isdigit():
            raise ValidationError("PIN must be 4 digits")
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin):
        return check_password(raw_pin, self.pin_hash)

    def set_cvv(self, raw_cvv):
        if len(raw_cvv) != 3 or not raw_cvv.isdigit():
            raise ValidationError("CVV must be 3 digits")
        self.cvv_hash = make_password(raw_cvv)

    def check_cvv(self, raw_cvv):
        return check_password(raw_cvv, self.cvv_hash)

    def get_user_email(self):
        return self.user.email if self.user else None

    def get_user_full_name(self):
        if self.user:
            return (
                f"{self.user.first_name} {self.user.last_name}".strip()
            )
        return None

    def get_user_phone(self):
        return self.user.phone_number if self.user else None


class ATMTransaction(models.Model):
    """ATM Transaction model."""

    WITHDRAWAL = 'withdrawal'
    DEPOSIT = 'deposit'
    BALANCE_INQUIRY = 'balance_inquiry'
    PIN_CHANGE = 'pin_change'
    TRANSACTION_TYPES = [
        (WITHDRAWAL, 'Withdrawal'),
        (DEPOSIT, 'Deposit'),
        (BALANCE_INQUIRY, 'Balance Inquiry'),
        (PIN_CHANGE, 'PIN Change'),
    ]

    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    card = models.ForeignKey(
        ATMCard,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions',
        db_index=True,
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='atm_transactions',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_transactions',
        db_index=True,
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
    )
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )
    terminal_id = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Ledger journal that posted the ATM movement.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='atm_transactions',
        help_text="Ledger journal that posted the ATM movement.",
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_transactions_processed',
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atm_transactions_verified',
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=['transaction_type', 'status'],
                name='atm_tx_type_status_idx',
            ),
            models.Index(
                fields=['amount', 'status'],
                name='atm_tx_amount_status_idx',
            ),
            models.Index(
                fields=['created_at', 'status'],
                name='atm_tx_date_status_idx',
            ),
            models.Index(
                fields=['user', 'status'],
                name='atm_tx_user_status_idx',
            ),
            models.Index(
                fields=['journal'],
                name='banking_atm_journal_idx',
            ),
        ]

    def __str__(self):
        amount = self.amount if self.amount else ''
        return (
            f"{self.get_transaction_type_display()} - "
            f"{amount} ({self.status})"
        )

    def get_user_email(self):
        return self.user.email if self.user else None

    def get_user_full_name(self):
        if self.user:
            return (
                f"{self.user.first_name} {self.user.last_name}".strip()
            )
        return None


class CardIssuance(models.Model):
    """Track card issuance workflow"""

    card = models.ForeignKey(
        ATMCard,
        on_delete=models.CASCADE,
        related_name='issuances',
    )

    REQUEST_TYPES = [
        ('NEW', 'New Card'),
        ('REPLACEMENT', 'Replacement'),
        ('RENEWAL', 'Renewal'),
    ]

    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    delivery_address = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('REQUESTED', 'Requested'),
            ('PROCESSING', 'Processing'),
            ('PRODUCED', 'Card Produced'),
            ('SHIPPED', 'Shipped'),
            ('DELIVERED', 'Delivered'),
            ('ACTIVATED', 'Activated'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='REQUESTED',
    )

    tracking_number = models.CharField(max_length=50, blank=True)
    estimated_delivery = models.DateField()
    actual_delivery = models.DateField(null=True, blank=True)

    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    fee_paid = models.BooleanField(default=False)

    # Ledger journal that posted the issuance fee.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='card_issuances',
        help_text="Ledger journal that posted the card issuance fee.",
    )

    activation_code = models.CharField(max_length=10, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_issuances_requested',
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_issuances_processed',
    )
    shipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_issuances_shipped',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(
                fields=['journal'],
                name='banking_card_journal_idx',
            ),
        ]

    def __str__(self):
        return (
            f"Card Issuance: {self.card.card_number} - {self.status}"
        )