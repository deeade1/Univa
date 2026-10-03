# apps/backend/ecommerce/models/discount.py

"""
Discount models.

Three categories:

    Vouchers
        - Voucher, VoucherCode, VoucherChannelListing,
          VoucherCustomer, VoucherTranslation

    Promotions
        - Promotion, PromotionRule, PromotionRule_Variants,
          PromotionRuleTranslation, PromotionTranslation

    Applied discounts (records of a discount in effect)
        - OrderDiscount, OrderLineDiscount,
          CheckoutDiscount, CheckoutLineDiscount

Design notes:

  * `min_checkout_items_quantity` is Decimal — matches the Decimal
    quantity on CheckoutLine / OrderLine so that weighted market
    items can be validated against minimum-quantity rules.

  * Legacy Saleor migration artifacts (`old_sale_id`,
    `old_channel_listing_id`, `old_id`, and their raw-SQL helpers)
    have been removed. They were never used by any active code path.

  * `Voucher.__str__` no longer queries the database unless the
    voucher has no name.

  * Foreign keys that are queried in hot paths (VoucherCode.voucher,
    VoucherCustomer.voucher_code) are now indexed.
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Exists, JSONField, OuterRef, Q, Subquery, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from core.models.metadata import ModelWithMetadata
from core.models.utils.translations import Translation
from core.pricing import Money, format_money
from core.pricing.discount import fixed_discount, percentage_discount
from core.pricing.money_field import MoneyField
from core.utils.editorjs import default_clean_editor_js
from core.utils.json_serializer import CustomJsonEncoder
from ecommerce.models.channel import Channel

from .constants import (
    DiscountType,
    DiscountValueType,
    PromotionEvents,
    PromotionType,
    RewardType,
    RewardValueType,
    VoucherType,
)

if TYPE_CHECKING:
    from accounts.models.user import User

logger = logging.getLogger(__name__)


# =====================================================================
# SHARED
# =====================================================================


class NotApplicable(ValueError):
    """Raised when a discount is not applicable to a given context."""

    def __init__(
        self,
        msg,
        min_spent=None,
        min_checkout_items_quantity=None,
    ):
        super().__init__(msg)
        self.min_spent = min_spent
        self.min_checkout_items_quantity = min_checkout_items_quantity


# =====================================================================
# VOUCHERS
# =====================================================================


class VoucherQueryset(models.QuerySet["Voucher"]):
    def active(self, date):
        subquery = (
            VoucherCode.objects.filter(voucher_id=OuterRef("pk"))
            .order_by()
            .values("voucher_id")
            .annotate(total_used=Sum("used"))
            .values("total_used")
        )
        return self.filter(
            Q(usage_limit__isnull=True)
            | Q(usage_limit__gt=Subquery(subquery)),
            Q(end_date__isnull=True) | Q(end_date__gte=date),
            start_date__lte=date,
        )

    def active_in_channel(self, date, channel_slug: str):
        channels = Channel.objects.filter(
            slug=str(channel_slug),
            is_active=True,
        ).values("id")
        channel_listings = VoucherChannelListing.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id"))),
        ).values("id")

        return self.active(date).filter(
            Exists(channel_listings.filter(voucher_id=OuterRef("pk")))
        )

    def expired(self, date):
        subquery = (
            VoucherCode.objects.filter(voucher_id=OuterRef("pk"))
            .order_by()
            .values("voucher_id")
            .annotate(total_used=Sum("used"))
            .values("total_used")
        )
        return self.filter(
            Q(usage_limit__lte=Subquery(subquery)) | Q(end_date__lt=date),
            start_date__lt=date,
        )


VoucherManager = models.Manager.from_queryset(VoucherQueryset)


class Voucher(ModelWithMetadata):
    type = models.CharField(
        max_length=20,
        choices=VoucherType.CHOICES,
        default=VoucherType.ENTIRE_ORDER,
        db_index=True,
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    apply_once_per_order = models.BooleanField(default=False)
    apply_once_per_customer = models.BooleanField(default=False)
    single_use = models.BooleanField(default=False)
    only_for_staff = models.BooleanField(default=False)

    discount_value_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )

    # ------------------------------------------------------------------
    # Optional filters
    # ------------------------------------------------------------------

    countries = CountryField(multiple=True, blank=True)
    min_checkout_items_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=(
            "Minimum total quantity across checkout lines required "
            "for this voucher to apply. Decimal to support weighted "
            "market items (2.5 kg of beef, etc.)."
        ),
    )
    products = models.ManyToManyField("ecommerce.Product", blank=True)
    variants = models.ManyToManyField("ecommerce.ProductVariant", blank=True)
    collections = models.ManyToManyField("ecommerce.Collection", blank=True)
    categories = models.ManyToManyField("ecommerce.Category", blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vouchers",
    )

    objects = VoucherManager()

    class Meta:
        ordering = ("name", "pk")
        indexes = [
            BTreeIndex(fields=["type"], name="voucher_type_idx"),
            BTreeIndex(
                fields=["start_date", "end_date"],
                name="voucher_dates_idx",
            ),
            BTreeIndex(fields=["is_active"], name="voucher_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(min_checkout_items_quantity__isnull=True)
                    | Q(min_checkout_items_quantity__gt=0)
                ),
                name="voucher_min_qty_positive",
            ),
        ]

    def __str__(self):
        # Avoid the DB query that `self.code` would trigger unless
        # we actually need it.
        if self.name:
            return self.name
        return self.code or "Voucher"

    # ------------------------------------------------------------------
    # Codes
    # ------------------------------------------------------------------

    @property
    def code(self):
        """Primary code for this voucher (queries the DB)."""
        code_instance = self.codes.last()
        return code_instance.code if code_instance else None

    @property
    def promo_codes(self):
        return list(self.codes.values_list("code", flat=True))

    # ------------------------------------------------------------------
    # Discount calculation
    # ------------------------------------------------------------------

    def get_discount(self, channel: Channel):
        voucher_channel_listing = None
        for channel_listing in self.channel_listings.all():
            if channel.id == channel_listing.channel_id:
                voucher_channel_listing = channel_listing
                break

        if not voucher_channel_listing:
            raise NotApplicable(
                "This voucher is not assigned to this channel"
            )

        if self.discount_value_type == DiscountValueType.FIXED:
            discount_amount = Money(
                voucher_channel_listing.discount_value,
                voucher_channel_listing.currency,
            )
            return partial(fixed_discount, discount=discount_amount)

        if self.discount_value_type == DiscountValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=voucher_channel_listing.discount_value,
                rounding=ROUND_HALF_UP,
            )

        raise NotImplementedError("Unknown discount type")

    def get_discount_amount_for(
        self,
        price: Money,
        channel: Channel,
    ) -> Money:
        discount = self.get_discount(channel)
        after_discount = discount(price)
        if after_discount.amount < 0:
            return price
        return price - after_discount

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_min_spent(self, value: Money, channel: Channel):
        voucher_channel_listing = self.channel_listings.filter(
            channel=channel
        ).first()
        if not voucher_channel_listing:
            raise NotApplicable(
                "This voucher is not assigned to this channel"
            )
        min_spent = voucher_channel_listing.min_spent
        if min_spent and value < min_spent:
            msg = (
                "This offer is only valid for orders over "
                f"{format_money(min_spent)}."
            )
            raise NotApplicable(msg, min_spent=min_spent)

    def validate_min_checkout_items_quantity(self, quantity):
        quantity = Decimal(str(quantity))
        min_checkout_items_quantity = self.min_checkout_items_quantity
        if (
            min_checkout_items_quantity
            and min_checkout_items_quantity > quantity
        ):
            msg = (
                "This offer is only valid for orders with a minimum of "
                f"{min_checkout_items_quantity} quantity."
            )
            raise NotApplicable(
                msg,
                min_checkout_items_quantity=min_checkout_items_quantity,
            )

    def validate_once_per_customer(self, customer_email):
        voucher_codes = self.codes.all()
        voucher_customer = VoucherCustomer.objects.filter(
            Exists(voucher_codes.filter(id=OuterRef("voucher_code_id"))),
            customer_email=customer_email,
        )
        if voucher_customer:
            msg = "This offer is valid only once per customer."
            raise NotApplicable(msg)

    def validate_only_for_staff(self, customer: Optional["User"]):
        if not self.only_for_staff:
            return
        if not customer or not customer.is_staff:
            msg = "This offer is valid only for staff customers."
            raise NotApplicable(msg)


class VoucherCode(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    code = models.CharField(max_length=255, unique=True, db_index=True)
    used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    voucher = models.ForeignKey(
        Voucher,
        related_name="codes",
        on_delete=models.CASCADE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "code")
        indexes = [
            BTreeIndex(
                fields=["voucher"],
                name="vouchercode_voucher_idx",
            ),
            BTreeIndex(
                fields=["is_active"],
                name="vouchercode_active_idx",
            ),
            BTreeIndex(
                fields=["voucher", "is_active"],
                name="vouchercode_voucher_active_idx",
            ),
        ]


class VoucherChannelListing(models.Model):
    voucher = models.ForeignKey(
        Voucher,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="voucher_listings",
        on_delete=models.CASCADE,
    )

    discount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    discount = MoneyField(
        amount_field="discount_value",
        currency_field="currency",
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    min_spent_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    min_spent = MoneyField(
        amount_field="min_spent_amount",
        currency_field="currency",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(fields=["is_active"], name="vch_active_idx"),
            BTreeIndex(
                fields=["channel", "is_active"],
                name="vch_chan_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["voucher", "channel"],
                name="voucher_channel_unique",
            ),
        ]


class VoucherCustomer(models.Model):
    voucher_code = models.ForeignKey(
        VoucherCode,
        related_name="customers",
        on_delete=models.CASCADE,
        db_index=True,
    )
    customer_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("voucher_code", "customer_email", "pk")
        indexes = [
            BTreeIndex(
                fields=["voucher_code"],
                name="vouchercustomer_voucher_code_idx",
            ),
            BTreeIndex(
                fields=["customer_email"],
                name="vouchercustomer_email_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["voucher_code", "customer_email"],
                name="unique_voucher_customer",
            ),
        ]


class VoucherTranslation(Translation):
    voucher = models.ForeignKey(
        Voucher,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ("language_code", "voucher", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "voucher"],
                name="unique_voucher_translation",
            ),
        ]

    def get_translated_object_id(self):
        return "Voucher", self.voucher_id

    def get_translated_keys(self):
        return {"name": self.name}


# =====================================================================
# PROMOTIONS
# =====================================================================


class PromotionQueryset(models.QuerySet["Promotion"]):
    def active(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date),
            start_date__lte=date,
            is_active=True,
        )

    def expired(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(end_date__lt=date, start_date__lt=date)

    def by_channel(self, channel_slug):
        return self.filter(
            rules__channels__slug=channel_slug
        ).distinct()


PromotionManager = models.Manager.from_queryset(PromotionQueryset)


class Promotion(ModelWithMetadata):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    name = models.CharField(max_length=255, db_index=True)
    type = models.CharField(
        max_length=255,
        choices=PromotionType.CHOICES,
        default=PromotionType.CATALOGUE,
        db_index=True,
    )
    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )
    start_date = models.DateTimeField(default=timezone.now, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    last_notification_scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_promotions",
    )

    objects = PromotionManager()

    class Meta:
        ordering = ("name", "pk")
        permissions = (
            ("manage_discounts", "Manage promotions and vouchers."),
        )
        indexes = [
            BTreeIndex(
                fields=["start_date"],
                name="promotion_start_date_idx",
            ),
            BTreeIndex(
                fields=["end_date"],
                name="promotion_end_date_idx",
            ),
            BTreeIndex(
                fields=["is_active"],
                name="promotion_active_idx",
            ),
            BTreeIndex(
                fields=["type"],
                name="promotion_type_idx",
            ),
        ]

    def __str__(self):
        return self.name

    def is_currently_active(self, date=None) -> bool:
        if date is None:
            date = timezone.now()
        return (
            self.is_active
            and (not self.end_date or self.end_date >= date)
            and self.start_date <= date
        )

    def get_rules_for_channel(self, channel_id):
        return self.rules.filter(
            channels__id=channel_id,
            is_active=True,
        )


class PromotionTranslation(Translation):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )
    promotion = models.ForeignKey(
        Promotion,
        related_name="translations",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "promotion"],
                name="unique_promotion_translation",
            ),
        ]
        indexes = [
            BTreeIndex(
                fields=["language_code"],
                name="promotiontranslation_lang_idx",
            ),
        ]

    def get_translated_object_id(self):
        return "Promotion", self.promotion_id

    def get_translated_keys(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class PromotionRule(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    channels = models.ManyToManyField(
        Channel,
        related_name="promotion_rules",
    )

    catalogue_predicate = models.JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    order_predicate = models.JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    variants = models.ManyToManyField(
        "ecommerce.ProductVariant",
        blank=True,
        through="PromotionRule_Variants",
    )

    reward_value_type = models.CharField(
        max_length=255,
        choices=RewardValueType.CHOICES,
        blank=True,
        null=True,
    )
    reward_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reward_type = models.CharField(
        max_length=255,
        choices=RewardType.CHOICES,
        blank=True,
        null=True,
    )
    gifts = models.ManyToManyField(
        "ecommerce.ProductVariant",
        blank=True,
        related_name="+",
    )
    variants_dirty = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "name", "pk")
        indexes = [
            BTreeIndex(
                fields=["promotion"],
                name="promotionrule_promotion_idx",
            ),
            BTreeIndex(
                fields=["is_active"],
                name="promotionrule_active_idx",
            ),
            BTreeIndex(
                fields=["priority"],
                name="promotionrule_priority_idx",
            ),
        ]

    def __str__(self):
        return self.name or f"Rule {self.id}"

    def get_discount(self, currency):
        if self.reward_value_type == RewardValueType.FIXED:
            discount_amount = Money(self.reward_value, currency)
            return partial(fixed_discount, discount=discount_amount)
        if self.reward_value_type == RewardValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=self.reward_value,
                rounding=ROUND_HALF_UP,
            )
        raise NotImplementedError("Unknown discount type")


class PromotionRule_Variants(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        editable=False,
        unique=True,
    )
    promotionrule = models.ForeignKey(
        PromotionRule,
        on_delete=models.CASCADE,
    )
    productvariant = models.ForeignKey(
        "ecommerce.ProductVariant",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["promotionrule", "productvariant"],
                name="unique_promotionrule_variant",
            ),
        ]
        indexes = [
            BTreeIndex(
                fields=["promotionrule"],
                name="promotionrule_variants_rule_idx",
            ),
            BTreeIndex(
                fields=["productvariant"],
                name="promorule_var_idx",
            ),
        ]


class PromotionRuleTranslation(models.Model):
    promotion_rule = models.ForeignKey(
        "ecommerce.PromotionRule",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(max_length=10, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    editor_data = models.JSONField(
        blank=True,
        null=True,
        default=default_clean_editor_js,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["promotion_rule", "language_code"],
                name="unique_promotionrule_translation",
            ),
        ]
        verbose_name = _("Promotion Rule Translation")
        verbose_name_plural = _("Promotion Rule Translations")
        indexes = [
            BTreeIndex(
                fields=["language_code"],
                name="promotionruletrans_lang_idx",
            ),
        ]

    def __str__(self):
        return f"{self.promotion_rule} ({self.language_code})"


# =====================================================================
# APPLIED DISCOUNTS
# =====================================================================


class BaseDiscount(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    type = models.CharField(
        max_length=64,
        choices=DiscountType.CHOICES,
        default=DiscountType.MANUAL,
        db_index=True,
    )
    value_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )
    value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    amount = MoneyField(
        amount_field="amount_value",
        currency_field="currency",
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    translated_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True, null=True)

    promotion_rule = models.ForeignKey(
        PromotionRule,
        related_name="+",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        db_index=False,
    )
    voucher = models.ForeignKey(
        Voucher,
        related_name="+",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    voucher_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=False,
    )

    class Meta:
        abstract = True


class OrderDiscount(BaseDiscount):
    order = models.ForeignKey(
        "ecommerce.Order",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"],
                name="orderdiscount_promotion_rule_idx",
            ),
            BTreeIndex(
                fields=["voucher_code"],
                name="orderdiscount_voucher_code_idx",
            ),
            BTreeIndex(
                fields=["order"],
                name="orderdiscount_order_idx",
            ),
            GinIndex(
                fields=["name", "translated_name"],
                opclasses=["gin_trgm_ops", "gin_trgm_ops"],
                name="orderdiscount_translated_idx",
            ),
        ]


class OrderLineDiscount(BaseDiscount):
    line = models.ForeignKey(
        "ecommerce.OrderLine",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    unique_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        choices=DiscountType.CHOICES,
    )

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"],
                name="orderlinedisc_promotion_rule_idx",
            ),
            BTreeIndex(
                fields=["voucher_code"],
                name="orderlinedisc_voucher_code_idx",
            ),
            BTreeIndex(
                fields=["line"],
                name="orderlinedisc_line_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["line_id", "unique_type"],
                name="unique_orderline_discount_type",
            ),
        ]


class CheckoutDiscount(BaseDiscount):
    checkout = models.ForeignKey(
        "ecommerce.Checkout",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"],
                name="checkoutdiscount_rule_idx",
            ),
            BTreeIndex(
                fields=["voucher_code"],
                name="checkoutdiscount_voucher_idx",
            ),
            BTreeIndex(
                fields=["checkout"],
                name="checkoutdiscount_checkout_idx",
            ),
            GinIndex(
                fields=["name", "translated_name"],
                opclasses=["gin_trgm_ops", "gin_trgm_ops"],
                name="checkoutdisc_trans_gin_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["checkout_id", "promotion_rule_id"],
                name="unique_checkout_promotion_rule",
            ),
        ]

    def __str__(self):
        return (
            f"Discount ({self.value_type} - {self.value}) "
            f"on Checkout {self.checkout_id}"
        )


class CheckoutLineDiscount(BaseDiscount):
    line = models.ForeignKey(
        "ecommerce.CheckoutLine",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    unique_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        choices=DiscountType.CHOICES,
    )

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"],
                name="checklinedisc_promotion_rule_idx",
            ),
            BTreeIndex(
                fields=["voucher_code"],
                name="checklinedisc_voucher_code_idx",
            ),
            BTreeIndex(
                fields=["line"],
                name="checklinedisc_line_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["line_id", "unique_type"],
                name="unique_checkoutline_dis_type",
            ),
        ]

    def __str__(self):
        return (
            f"Discount ({self.value_type} - {self.value}) "
            f"on Checkout Line {self.line_id}"
        )


# =====================================================================
# PROMOTION EVENTS
# =====================================================================


class PromotionEvent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )
    date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        editable=False,
    )
    type = models.CharField(
        max_length=255,
        choices=PromotionEvents.CHOICES,
        db_index=True,
    )
    parameters = models.JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="promotion_events",
        on_delete=models.SET_NULL,
    )
    promotion = models.ForeignKey(
        Promotion,
        related_name="events",
        on_delete=models.CASCADE,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-date",)
        indexes = [
            BTreeIndex(
                fields=["promotion", "date"],
                name="promotionevent_promo_date_idx",
            ),
            BTreeIndex(
                fields=["type"],
                name="promotionevent_type_idx",
            ),
            BTreeIndex(
                fields=["user"],
                name="promotionevent_user_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_type_display()} - "
            f"{self.promotion.name} - {self.date}"
        )