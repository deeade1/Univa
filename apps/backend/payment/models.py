# apps/backend/payment/models.py

"""
Canonical Payment Models for Univa.
Used by all apps including transport, ecommerce, etc.
"""

from decimal import Decimal
from operator import attrgetter
import uuid
import datetime

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.metadata import ModelWithMetadata
from core.pricing.money import Money
from core.pricing.money_field import MoneyField
from core.taxes import zero_money

from .constants import (
    ChargeStatus,
    CustomPaymentChoices,
    StorePaymentMethod,
    TransactionAction,
    TransactionEventType,
    TransactionKind,
)


class TransactionItem(ModelWithMetadata):
    """Transaction item model for payment transactions."""
    
    token = models.UUIDField(unique=True, default=uuid.uuid4)
    use_old_id = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    idempotency_key = models.CharField(max_length=512, blank=True, null=True)
    name = models.CharField(max_length=512, blank=True, null=True, default="")
    message = models.CharField(max_length=512, blank=True, null=True, default="")
    psp_reference = models.CharField(max_length=512, blank=True, null=True)
    available_actions = ArrayField(
        models.CharField(max_length=128, choices=TransactionAction.CHOICES),
        default=list,
    )

    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)

    amount_charged = MoneyField(amount_field="charged_value", currency_field="currency")
    charged_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_authorized = MoneyField(
        amount_field="authorized_value", currency_field="currency"
    )
    authorized_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_refunded = MoneyField(
        amount_field="refunded_value", currency_field="currency"
    )
    refunded_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_canceled = MoneyField(
        amount_field="canceled_value", currency_field="currency"
    )
    canceled_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_refund_pending = MoneyField(
        amount_field="refund_pending_value", currency_field="currency"
    )
    refund_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    amount_charge_pending = MoneyField(
        amount_field="charge_pending_value", currency_field="currency"
    )
    charge_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    amount_authorize_pending = MoneyField(
        amount_field="authorize_pending_value", currency_field="currency"
    )
    authorize_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    cancel_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_cancel_pending = MoneyField(
        amount_field="cancel_pending_value", currency_field="currency"
    )

    external_url = models.URLField(blank=True, null=True)

    checkout = models.ForeignKey(
        "ecommerce.Checkout",
        null=True,
        blank=True,
        related_name="payment_transactions",
        on_delete=models.SET_NULL,
    )
    
    order = models.ForeignKey(
        "ecommerce.Order",
        related_name="payment_transactions",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="payment_transactions",
    )
    
    # Transport-specific fields
    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_transactions",
        help_text="Transport service request associated with this transaction"
    )

    # If last release funds action failed the flag will be set to False
    last_refund_success = models.BooleanField(default=True)

    class Meta:
        ordering = ("pk",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['service_request']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="unique_transaction_idempotency",
            ),
        ]

    def __str__(self):
        return f"Transaction {self.token} - {self.currency} {self.charged_value}"


class Payment(ModelWithMetadata):
    """Canonical Payment model used across all apps."""

    gateway = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    to_confirm = models.BooleanField(default=False)
    partial = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    charge_status = models.CharField(
        max_length=20, choices=ChargeStatus.CHOICES, default=ChargeStatus.NOT_CHARGED
    )
    token = models.CharField(max_length=512, blank=True, default="")
    total = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    captured_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH
    )

    checkout = models.ForeignKey(
        "ecommerce.Checkout", 
        null=True,
        blank=True,
        related_name="payments",
        on_delete=models.SET_NULL
    )
    
    order = models.ForeignKey(
        "ecommerce.Order",
        related_name="payments",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="payments",
        help_text="User who made the payment"
    )
    
    # Transport-specific fields
    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
        help_text="Transport service request associated with this payment"
    )
    
    store_payment_method = models.CharField(
        max_length=11,
        choices=StorePaymentMethod.CHOICES,
        default=StorePaymentMethod.NONE,
    )

    billing_email = models.EmailField(blank=True)
    billing_first_name = models.CharField(max_length=256, blank=True)
    billing_last_name = models.CharField(max_length=256, blank=True)
    billing_company_name = models.CharField(max_length=256, blank=True)
    billing_address_1 = models.CharField(max_length=256, blank=True)
    billing_address_2 = models.CharField(max_length=256, blank=True)
    billing_city = models.CharField(max_length=256, blank=True)
    billing_city_area = models.CharField(max_length=128, blank=True)
    billing_postal_code = models.CharField(max_length=256, blank=True)
    billing_country_code = models.CharField(max_length=2, blank=True)
    billing_country_area = models.CharField(max_length=256, blank=True)

    cc_first_digits = models.CharField(max_length=6, blank=True, default="")
    cc_last_digits = models.CharField(max_length=4, blank=True, default="")
    cc_brand = models.CharField(max_length=40, blank=True, default="")
    cc_exp_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)], null=True, blank=True
    )
    cc_exp_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1000)], null=True, blank=True
    )

    payment_method_type = models.CharField(max_length=256, blank=True)

    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
    extra_data = models.TextField(blank=True, default="")
    return_url = models.URLField(blank=True, null=True)
    psp_reference = models.CharField(
        max_length=512, null=True, blank=True, db_index=True
    )

    class Meta:
        ordering = ("pk",)
        permissions = (
            (
                "handle_payments",
                "Handle payments",
            ),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            BTreeIndex(fields=["order_id"], name="order_id_btree_idx"),
            BTreeIndex(fields=["is_active"], name="is_active_btree_idx"),
            BTreeIndex(fields=["charge_status"], name="charge_status_btree_idx"),
            models.Index(fields=['service_request']),
            models.Index(fields=['user']),
        ]

    def __repr__(self):
        return (
            f"Payment(gateway={self.gateway}, is_active={self.is_active}, "
            f"created={self.created_at}, charge_status={self.charge_status})"
        )

    def get_last_transaction(self):
        return max(self.transactions.all(), default=None, key=attrgetter("pk"))

    def get_total(self):
        return Money(self.total, self.currency)

    def get_authorized_amount(self):
        money = zero_money(self.currency)
        transactions = self.transactions.all()
        if any([txn.kind == TransactionKind.CAPTURE and txn.is_success for txn in transactions]):
            return money
        authorized_txns = [
            txn for txn in transactions
            if txn.kind == TransactionKind.AUTH and txn.is_success and not txn.action_required
        ]
        for txn in authorized_txns:
            money += Money(txn.amount, self.currency)
        return money

    def get_captured_amount(self):
        return Money(self.captured_amount, self.currency)

    def get_charge_amount(self):
        return self.total - self.captured_amount

    @property
    def is_authorized(self):
        return any([
            txn.kind == TransactionKind.AUTH and txn.is_success and not txn.action_required
            for txn in self.transactions.all()
        ])

    @property
    def not_charged(self):
        return self.charge_status == ChargeStatus.NOT_CHARGED

    def can_authorize(self):
        return self.is_active and self.not_charged

    def can_capture(self):
        return self.is_active and self.not_charged

    def can_void(self):
        return self.not_charged and self.is_authorized

    def can_refund(self):
        can_refund_charge_status = (
            ChargeStatus.PARTIALLY_CHARGED,
            ChargeStatus.FULLY_CHARGED,
            ChargeStatus.PARTIALLY_REFUNDED,
        )
        return self.charge_status in can_refund_charge_status

    def can_confirm(self):
        return self.is_active and self.not_charged

    def is_manual(self):
        return self.gateway == CustomPaymentChoices.MANUAL


class Transaction(models.Model):
    """Represents a single payment operation."""

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    payment = models.ForeignKey(
        Payment, related_name="transactions", on_delete=models.PROTECT
    )
    token = models.CharField(max_length=512, blank=True, default="")
    kind = models.CharField(max_length=25, choices=TransactionKind.CHOICES)
    is_success = models.BooleanField(default=False)
    action_required = models.BooleanField(default=False)
    action_required_data = JSONField(
        blank=True, default=dict, encoder=DjangoJSONEncoder
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    error = models.TextField(null=True)
    customer_id = models.CharField(max_length=256, null=True)
    gateway_response = JSONField(encoder=DjangoJSONEncoder)
    already_processed = models.BooleanField(default=False)
    discount_applied = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    is_univa_payment = models.BooleanField(default=False)
    
    class Meta:
        ordering = ("pk",)
        indexes = [
            GinIndex(
                name="token_idx",
                fields=["token"],
                opclasses=["gin_trgm_ops"],
            ),
            models.Index(fields=['payment', 'kind']),
        ]
        
    def __repr__(self):
        return (
            f"Transaction(type={self.kind}, is_success={self.is_success}, "
            f"created={self.created_at})"
        )

    def get_amount(self):
        return Money(self.amount, self.currency)


class TransactionEvent(models.Model):
    """Transaction event model for tracking transaction events."""
    
    created_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.CharField(max_length=512, blank=True, null=True)
    psp_reference = models.CharField(max_length=512, blank=True, null=True)
    message = models.CharField(max_length=512, blank=True, null=True, default="")
    transaction = models.ForeignKey(
        TransactionItem, related_name="events", on_delete=models.CASCADE
    )
    external_url = models.URLField(blank=True, null=True)
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    type = models.CharField(
        max_length=128,
        choices=TransactionEventType.CHOICES,
        default=TransactionEventType.INFO,
    )
    amount = MoneyField(amount_field="amount_value", currency_field="currency")
    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    include_in_calculations = models.BooleanField(default=False)
    
    # Optional - only if order app is available
    related_granted_refund = models.ForeignKey(
        "ecommerce.OrderGrantedRefund",
        related_name="transaction_events",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["transaction_id", "idempotency_key"],
                name="unique_transaction_event_idempotency",
            )
        ]

    def __str__(self):
        return f"Event {self.type} - {self.transaction.token}"


class PaymentMethod(models.Model):
    """Stored payment methods for customers"""
    
    class PaymentType(models.TextChoices):
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
        DEBIT_CARD = 'DEBIT_CARD', _('Debit Card')
        PAYPAL = 'PAYPAL', _('PayPal')
        APPLE_PAY = 'APPLE_PAY', _('Apple Pay')
        GOOGLE_PAY = 'GOOGLE_PAY', _('Google Pay')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CRYPTO = 'CRYPTO', _('Cryptocurrency')
    
    class GatewayProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        PAYPAL = 'paypal', _('PayPal')
        PAYSTACK = 'paystack', _('Paystack')
        FLUTTERWAVE = 'flutterwave', _('Flutterwave')
        RAZORPAY = 'razorpay', _('Razorpay')
        APPLE = 'apple', _('Apple Pay')
        GOOGLE = 'google', _('Google Pay')
    
    class CardBrand(models.TextChoices):
        VISA = 'visa', _('Visa')
        MASTERCARD = 'mastercard', _('Mastercard')
        AMEX = 'amex', _('American Express')
        DISCOVER = 'discover', _('Discover')
        DINERS = 'diners', _('Diners Club')
        JCB = 'jcb', _('JCB')
        UNIONPAY = 'unionpay', _('UnionPay')
        OTHER = 'other', _('Other')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="stored_payment_methods",
        on_delete=models.CASCADE,
        db_index=True
    )
    type = models.CharField(
        max_length=50,
        choices=PaymentType.choices,
        db_index=True
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name for the payment method"
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="SVG icon or emoji representation"
    )
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    
    cc_last_digits = models.CharField(max_length=4, blank=True)
    cc_brand = models.CharField(max_length=50, blank=True, choices=CardBrand.choices)
    cc_exp_month = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)])
    cc_exp_year = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(2024)])
    
    gateway_token = models.CharField(max_length=255, blank=True, db_index=True)
    gateway = models.CharField(max_length=50, choices=GatewayProvider.choices, default=GatewayProvider.STRIPE, db_index=True)
    gateway_customer_id = models.CharField(max_length=255, blank=True)
    
    billing_address = models.ForeignKey(
        "accounts.Address",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_methods"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            BTreeIndex(fields=["user", "is_default"], name="paymethod_user_default_idx"),
            BTreeIndex(fields=["user", "is_active"], name="paymethod_user_active_idx"),
            models.Index(fields=["gateway", "gateway_token"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "gateway_token"],
                name="unique_user_gateway_token"
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_payment_method_per_user"
            ),
        ]
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"
    
    def clean(self):
        if self.type in [self.PaymentType.CREDIT_CARD, self.PaymentType.DEBIT_CARD]:
            if not self.cc_last_digits:
                raise ValidationError({"cc_last_digits": "Last 4 digits are required for card payments."})
            if not self.cc_exp_month or not self.cc_exp_year:
                raise ValidationError({"cc_exp_month": "Expiration date is required for card payments."})
            now = datetime.datetime.now()
            if self.cc_exp_year < now.year or (self.cc_exp_year == now.year and self.cc_exp_month < now.month):
                raise ValidationError({"cc_exp_month": "Card has expired."})
    
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        self.full_clean()
        super().save(*args, **kwargs)
    
    def set_as_default(self):
        PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])
    
    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at', 'updated_at'])
    
    @property
    def is_card(self):
        return self.type in [self.PaymentType.CREDIT_CARD, self.PaymentType.DEBIT_CARD]
    
    @property
    def is_expired(self):
        if not self.cc_exp_month or not self.cc_exp_year:
            return False
        now = datetime.datetime.now()
        return self.cc_exp_year < now.year or (self.cc_exp_year == now.year and self.cc_exp_month < now.month)
    
    @property
    def display_name(self):
        if self.is_card and self.cc_brand and self.cc_last_digits:
            return f"{self.get_cc_brand_display()} •••• {self.cc_last_digits}"
        return self.name
    
    @classmethod
    def get_default_for_user(cls, user):
        return cls.objects.filter(user=user, is_default=True, is_active=True).first()
    
    @classmethod
    def get_active_for_user(cls, user):
        return cls.objects.filter(user=user, is_active=True)