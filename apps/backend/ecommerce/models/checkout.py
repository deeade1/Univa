# apps/backend/ecommerce/models/checkout.py
from datetime import date
from decimal import Decimal
from operator import attrgetter
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.encoding import smart_str
from django_countries.fields import Country, CountryField
from core.pricing import (
    Money,
    
)

from core.models.metadata import ModelWithMetadata
from core.taxes import zero_money
from core.pricing.taxed_money_field import TaxedMoneyField
from core.pricing import MoneyField
from ecommerce.models.channel import Channel
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.shipping import ShippingMethod
from ecommerce.models.discount import Voucher
#from payment.models import Payment
from ecommerce.models.product import ProductVariant


def get_default_country():
    return settings.DEFAULT_COUNTRY


class Checkout(models.Model):
    """A shopping checkout."""

    created_at = models.DateTimeField(auto_now_add=True)
    last_change = models.DateTimeField(auto_now=True, db_index=True)
    completing_started_at = models.DateTimeField(blank=True, null=True)
    last_transaction_modified_at = models.DateTimeField(null=True, blank=True)
    automatically_refundable = models.BooleanField(default=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.CASCADE,
    )
    email = models.EmailField(blank=True, null=True)
    token = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # Only create ForeignKey if Channel is available
    channel = models.ForeignKey(
        Channel,
        related_name="checkouts",
        on_delete=models.PROTECT,
    ) 
    
    billing_address = models.ForeignKey(
        "accounts.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    shipping_address = models.ForeignKey(
        "accounts.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    
    # Only create ForeignKey if ShippingMethod is available
    shipping_method = models.ForeignKey(
        ShippingMethod,
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.SET_NULL,
    ) 
    
    collection_point = models.ForeignKey(
        "ecommerce.Warehouse",
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.SET_NULL,
    )
    note = models.TextField(blank=True, default="")

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    country = CountryField(default=get_default_country)

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    
    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        currency_field="currency",
    )
    # base price contains only catalogue discounts (does not contains voucher discount)
    base_total_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    base_total = MoneyField(amount_field="base_total_amount", currency_field="currency")

    subtotal_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal = TaxedMoneyField(
        net_amount_field="subtotal_net_amount",
        gross_amount_field="subtotal_gross_amount",
        currency_field="currency",
    )
    # base price contains only catalogue discounts (does not contains voucher discount)
    base_subtotal_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    base_subtotal = MoneyField(
        amount_field="base_subtotal_amount", currency_field="currency"
    )

    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    shipping_price = TaxedMoneyField(
        net_amount_field="shipping_price_net_amount",
        gross_amount_field="shipping_price_gross_amount",
        currency_field="currency",
    )
    shipping_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.0")
    )

    AUTHORIZE_STATUS_CHOICES = [
        ('none', 'Not authorized'),
        ('partial', 'Partially authorized'),
        ('full', 'Fully authorized'),
    ]
    
    CHARGE_STATUS_CHOICES = [
        ('none', 'Not charged'),
        ('partial', 'Partially charged'),
        ('full', 'Fully charged'),
        ('overcharged', 'Overcharged'),
    ]
    
    authorize_status = models.CharField(
        max_length=20,
        choices=AUTHORIZE_STATUS_CHOICES,
        default='none'
    )
    
    charge_status = models.CharField(
        max_length=20,
        choices=CHARGE_STATUS_CHOICES,
        default='none'
    )

    price_expiration = models.DateTimeField(default=timezone.now)

    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    discount = MoneyField(amount_field="discount_amount", currency_field="currency")
    discount_name = models.CharField(max_length=255, blank=True, null=True)

    translated_discount_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Only create ManyToMany if GiftCard is available
    gift_cards = models.ManyToManyField(
        GiftCard, 
        blank=True, 
        related_name="checkouts"
    ) 
    
    voucher_code = models.CharField(max_length=255, blank=True, null=True)

    is_voucher_usage_increased = models.BooleanField(default=False)

    redirect_url = models.URLField(blank=True, null=True)
    tracking_code = models.CharField(max_length=255, blank=True, null=True)

    language_code = models.CharField(
        max_length=35, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )

    tax_exemption = models.BooleanField(default=False)
    tax_error = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ("-last_change", "pk")
        permissions = (
            ("manage_checkouts", "Manage checkouts"),
            ("handle_checkouts", "Handle checkouts"),
            ("handle_taxes", "Handle taxes"),
            ("manage_taxes", "Manage taxes"),
        )

    def __iter__(self):
        return iter(self.lines.all())

    def get_customer_email(self) -> Optional[str]:
        return self.user.email if self.user else self.email

    def is_shipping_required(self) -> bool:
        """Return `True` if any of the lines requires shipping."""
        return any(line.is_shipping_required() for line in self)

    def is_checkout_locked(self) -> bool:
        return bool(
            self.completing_started_at
            and (
                (timezone.now() - self.completing_started_at).seconds
                < settings.CHECKOUT_COMPLETION_LOCK_TIME
            )
        )

    def get_total_gift_cards_balance(self):
        """Return the total balance of the gift cards assigned to the checkout."""
        if not GIFTCARD_AVAILABLE or not self.gift_cards:
            return zero_money(currency=self.currency)
        
        balance = self.gift_cards.active(date=date.today()).aggregate(
            models.Sum("current_balance_amount")
        )["current_balance_amount__sum"]
        if balance is None:
            return zero_money(currency=self.currency)
        return Money(balance, self.currency)

    def get_line(self, variant: "ProductVariant") -> Optional["CheckoutLine"]:
        """Return a line matching the given variant and data if any."""
        matching_lines = (line for line in self if line.variant.pk == variant.pk)
        return next(matching_lines, None)

    def get_last_active_payment(self) -> Optional["Payment"]:
        payments = [payment for payment in self.payments.all() if payment.is_active]
        return max(payments, default=None, key=attrgetter("pk"))

    def set_country(
        self, country_code: str, commit: bool = False, replace: bool = True
    ):
        """Set country for checkout."""
        if not replace and self.country is not None:
            return
        self.country = Country(country_code)
        if commit:
            self.save(update_fields=["country"])

    def get_country(self):
        address = self.shipping_address or self.billing_address
        saved_country = self.country
        if address is None or not address.country:
            return saved_country.code

        country_code = address.country.code
        if not country_code == saved_country.code:
            self.set_country(country_code, commit=True)
        return country_code


class CheckoutLine(ModelWithMetadata):
    """A single checkout line.

    Multiple lines in the same checkout can refer to the same product variant if
    their `data` field is different.
    """

    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    old_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    checkout = models.ForeignKey(
        Checkout, related_name="lines", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "ecommerce.ProductVariant", related_name="+", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_gift = models.BooleanField(default=False)
    price_override = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_price = TaxedMoneyField(
        net_amount_field="total_price_net_amount",
        gross_amount_field="total_price_gross_amount",
        currency_field="currency",
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.0")
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkout_lines_created',
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkout_lines_modified',
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["old_id"],
                condition=models.Q(old_id__isnull=False),
                name="unique_checkout_line_old_id"
            ),
        ]

    def __str__(self):
        return smart_str(self.variant)

    __hash__ = models.Model.__hash__

    def __eq__(self, other):
        if not isinstance(other, CheckoutLine):
            return NotImplemented

        return self.variant == other.variant and self.quantity == other.quantity

    def __ne__(self, other):
        return not self == other  # pragma: no cover

    def __repr__(self):
        return f"CheckoutLine(variant={self.variant!r}, quantity={self.quantity!r})"

    def __getstate__(self):
        return self.variant, self.quantity

    def __setstate__(self, data):
        self.variant, self.quantity = data

    def is_shipping_required(self) -> bool:
        """Return `True` if the related product variant requires shipping."""
        return self.variant.is_shipping_required()


# Checkout metadata is moved to separate model so it can be used when checkout model is
# locked by select_for_update during complete_checkout.
class CheckoutMetadata(ModelWithMetadata):
    checkout = models.OneToOneField(
        Checkout, related_name="metadata_storage", on_delete=models.CASCADE
    )
    
    class Meta(ModelWithMetadata.Meta):
        ordering = ["id"]



