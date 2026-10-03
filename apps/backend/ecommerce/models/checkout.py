# apps/backend/ecommerce/models/checkout.py

"""
Checkout models.

Core entities:

    Checkout            — an in-progress purchase
    CheckoutLine        — a line item in a checkout
    CheckoutMetadata    — attached metadata, kept in a separate table
                          to avoid row-lock contention on Checkout
                          during completion

Design notes:

  * `CheckoutLine.quantity` is Decimal — supports market items
    (2.5 kg of beef) as well as discrete catalog items.

  * `CheckoutLine.quantity_unit` is denormalized from the variant at
    checkout time and carried forward into the Order.

  * `Checkout.user` is SET_NULL — deleting a user does not wipe their
    in-progress carts.

  * Money is stored as paired DecimalField + currency and exposed
    through `MoneyField` / `TaxedMoneyField` descriptors.

  * The `country` field is a cached snapshot. `get_country()` resolves
    the effective country from the shipping address > billing address
    > cached country, without modifying the DB.
"""

from __future__ import annotations

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

from core.models.metadata import ModelWithMetadata
from core.pricing import Money, MoneyField
from core.pricing.quantity_unit import QuantityUnit
from core.pricing.taxed_money_field import TaxedMoneyField
from core.taxes import zero_money
from ecommerce.models.channel import Channel
from ecommerce.models.discount import Voucher
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.shipping import ShippingMethod

if TYPE_CHECKING:
    from ecommerce.models.product import ProductVariant


def get_default_country():
    return settings.DEFAULT_COUNTRY


class Checkout(models.Model):
    """A shopping checkout (in-progress cart)."""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    token = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.SET_NULL,
        help_text=(
            "Owner of the cart. SET_NULL preserves abandoned carts "
            "when a user is deleted."
        ),
    )
    email = models.EmailField(blank=True, null=True)
    language_code = models.CharField(
        max_length=35,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )

    # ------------------------------------------------------------------
    # Channel
    # ------------------------------------------------------------------

    channel = models.ForeignKey(
        Channel,
        related_name="checkouts",
        on_delete=models.PROTECT,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    # ------------------------------------------------------------------
    # Addresses / shipping
    # ------------------------------------------------------------------

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
    country = CountryField(default=get_default_country)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    last_change = models.DateTimeField(auto_now=True, db_index=True)
    completing_started_at = models.DateTimeField(blank=True, null=True)
    price_expiration = models.DateTimeField(default=timezone.now)

    # ------------------------------------------------------------------
    # Payment state (mirrors Order for consistency)
    # ------------------------------------------------------------------

    AUTHORIZE_STATUS_CHOICES = [
        ("none", "Not authorized"),
        ("partial", "Partially authorized"),
        ("full", "Fully authorized"),
    ]
    CHARGE_STATUS_CHOICES = [
        ("none", "Not charged"),
        ("partial", "Partially charged"),
        ("full", "Fully charged"),
        ("overcharged", "Overcharged"),
    ]

    authorize_status = models.CharField(
        max_length=20,
        choices=AUTHORIZE_STATUS_CHOICES,
        default="none",
    )
    charge_status = models.CharField(
        max_length=20,
        choices=CHARGE_STATUS_CHOICES,
        default="none",
    )
    last_transaction_modified_at = models.DateTimeField(
        null=True, blank=True
    )
    automatically_refundable = models.BooleanField(default=False)

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        currency_field="currency",
    )

    base_total_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    base_total = MoneyField(
        amount_field="base_total_amount",
        currency_field="currency",
    )

    subtotal_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    subtotal_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    subtotal = TaxedMoneyField(
        net_amount_field="subtotal_net_amount",
        gross_amount_field="subtotal_gross_amount",
        currency_field="currency",
    )

    base_subtotal_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    base_subtotal = MoneyField(
        amount_field="base_subtotal_amount",
        currency_field="currency",
    )

    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    shipping_price = TaxedMoneyField(
        net_amount_field="shipping_price_net_amount",
        gross_amount_field="shipping_price_gross_amount",
        currency_field="currency",
    )
    shipping_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0"),
    )

    # ------------------------------------------------------------------
    # Discounts
    # ------------------------------------------------------------------

    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    discount = MoneyField(
        amount_field="discount_amount",
        currency_field="currency",
    )
    discount_name = models.CharField(
        max_length=255, blank=True, null=True
    )
    translated_discount_name = models.CharField(
        max_length=255, blank=True, null=True
    )

    # ------------------------------------------------------------------
    # Vouchers / gift cards
    # ------------------------------------------------------------------

    voucher_code = models.CharField(
        max_length=255, blank=True, null=True
    )
    is_voucher_usage_increased = models.BooleanField(default=False)
    gift_cards = models.ManyToManyField(
        GiftCard,
        blank=True,
        related_name="checkouts",
    )

    # ------------------------------------------------------------------
    # Customer-facing metadata
    # ------------------------------------------------------------------

    note = models.TextField(blank=True, default="")
    redirect_url = models.URLField(blank=True, null=True)
    tracking_code = models.CharField(
        max_length=255, blank=True, null=True
    )

    # ------------------------------------------------------------------
    # Tax
    # ------------------------------------------------------------------

    tax_exemption = models.BooleanField(default=False)
    tax_error = models.CharField(
        max_length=255, blank=True, null=True
    )

    class Meta:
        ordering = ("-last_change", "pk")
        permissions = (
            ("manage_checkouts", "Manage checkouts"),
            ("handle_checkouts", "Handle checkouts"),
        )
        indexes = [
            models.Index(
                fields=["user", "-last_change"],
                name="checkout_user_last_change_idx",
            ),
            models.Index(
                fields=["channel", "-last_change"],
                name="checkout_channel_change_idx",
            ),
            models.Index(
                fields=["email"],
                name="checkout_email_idx",
            ),
        ]

    # ------------------------------------------------------------------
    # Iteration / lookup
    # ------------------------------------------------------------------

    def __iter__(self):
        return iter(self.lines.all())

    def get_line(
        self,
        variant: "ProductVariant",
    ) -> Optional["CheckoutLine"]:
        """Return the line for the given variant, if any."""
        return self.lines.filter(variant=variant).first()

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def get_customer_email(self) -> Optional[str]:
        return self.user.email if self.user else self.email

    # ------------------------------------------------------------------
    # Shipping / fulfillment
    # ------------------------------------------------------------------

    def is_shipping_required(self) -> bool:
        """Return True if any line requires shipping."""
        return any(line.is_shipping_required() for line in self)

    def is_checkout_locked(self) -> bool:
        """Return True if the checkout completion lock is held."""
        return bool(
            self.completing_started_at
            and (
                (timezone.now() - self.completing_started_at).seconds
                < settings.CHECKOUT_COMPLETION_LOCK_TIME
            )
        )

    # ------------------------------------------------------------------
    # Gift cards
    # ------------------------------------------------------------------

    def get_total_gift_cards_balance(self) -> Money:
        """Total balance of the checkout's active gift cards."""
        balance = self.gift_cards.active(date=date.today()).aggregate(
            total=models.Sum("current_balance_amount"),
        )["total"]

        if balance is None:
            return zero_money(currency=self.currency)
        return Money(balance, self.currency)

    # ------------------------------------------------------------------
    # Payment
    # ------------------------------------------------------------------

    def get_last_active_payment(self):
        """Most recent active payment, or None."""
        payments = [
            p for p in self.payments.all() if p.is_active
        ]
        return max(payments, default=None, key=attrgetter("pk"))

    # ------------------------------------------------------------------
    # Country
    # ------------------------------------------------------------------

    def set_country(
        self,
        country_code: str,
        commit: bool = False,
        replace: bool = True,
    ):
        """Set the cached country field."""
        if not replace and self.country is not None:
            return
        self.country = Country(country_code)
        if commit:
            self.save(update_fields=["country"])

    def get_country(self) -> str:
        """
        Return the effective country code for this checkout.

        Resolution order:
            1. shipping_address.country
            2. billing_address.country
            3. self.country (cached snapshot)

        Does NOT modify the database. Use `set_country(..., commit=True)`
        explicitly if you want to sync.
        """
        address = self.shipping_address or self.billing_address
        if address and address.country:
            return address.country.code
        return self.country.code


class CheckoutLine(ModelWithMetadata):
    """
    A single checkout line.

    Lines are distinguished by variant. Two lines in the same checkout
    referring to the same variant are merged.
    """

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    checkout = models.ForeignKey(
        Checkout,
        related_name="lines",
        on_delete=models.CASCADE,
    )
    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        related_name="+",
        on_delete=models.CASCADE,
    )

    # ------------------------------------------------------------------
    # Quantity
    # ------------------------------------------------------------------

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantity_unit = models.CharField(
        max_length=16,
        choices=QuantityUnit.choices(),
        default=QuantityUnit.UNIT.value,
        db_index=True,
        help_text=(
            "Unit of measure for this line. Denormalized from the "
            "variant and carried into the Order on checkout."
        ),
    )

    # ------------------------------------------------------------------
    # Price
    # ------------------------------------------------------------------

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
        default=Decimal("0"),
    )
    total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    total_price = TaxedMoneyField(
        net_amount_field="total_price_net_amount",
        gross_amount_field="total_price_gross_amount",
        currency_field="currency",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0"),
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkout_lines_created",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkout_lines_modified",
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="checkoutline_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=["checkout", "variant"],
                name="checkoutline_unique_variant_per_checkout",
            ),
        ]
        indexes = [
            models.Index(
                fields=["checkout", "created_at"],
                name="checkline_checkout_created_idx",
            ),
            models.Index(
                fields=["variant"],
                name="checkoutline_variant_idx",
            ),
        ]

    def __str__(self):
        return smart_str(self.variant)

    __hash__ = models.Model.__hash__

    def __eq__(self, other):
        if not isinstance(other, CheckoutLine):
            return NotImplemented
        return (
            self.variant == other.variant
            and self.quantity == other.quantity
        )

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return (
            f"CheckoutLine(variant={self.variant!r}, "
            f"quantity={self.quantity!r})"
        )

    def __getstate__(self):
        return self.variant, self.quantity

    def __setstate__(self, data):
        self.variant, self.quantity = data

    def is_shipping_required(self) -> bool:
        return self.variant.is_shipping_required()


class CheckoutMetadata(ModelWithMetadata):
    """
    Metadata stored in a separate table.

    Exists so that metadata can be updated without locking the main
    Checkout row during completion (`select_for_update` on Checkout
    would otherwise block metadata writes).
    """

    checkout = models.OneToOneField(
        Checkout,
        related_name="metadata_storage",
        on_delete=models.CASCADE,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ["id"]

    def __str__(self):
        return f"CheckoutMetadata for {self.checkout_id}"