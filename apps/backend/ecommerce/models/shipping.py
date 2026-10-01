# shipping/models.py
# Complete rewritten Shipping system - scalable and optimized

from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, BTreeIndex
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import OuterRef, Q, Subquery, Count, Avg
from django_countries.fields import CountryField
from django_measurement.models import MeasurementField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from measurement.measures import Weight
from core.pricing import (
    Money,
    MoneyField, 
    
)

from core.pricing.taxed_money_field import TaxedMoneyField
import logging
from ecommerce.models.channel import Channel
from core.models.metadata import ModelWithMetadata
from core.units import WeightUnits
from core.weight import convert_weight, get_default_weight_unit, zero_weight

from tax.models import TaxClass
from core.utils.editorjs import clean_editor_js
from .constants import (
    PostalCodeRuleInclusionType, ShippingMethodType, ShippingMethodStatus
)


from ecommerce.services.shipping.postal_codes import filter_shipping_methods_by_postal_code_rules

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_weight_from_lines(lines):
    """Calculate total weight from order/checkout lines."""
    total_weight = zero_weight()
    for line in lines:
        if line and hasattr(line, 'variant') and line.variant:
            weight = line.variant.get_weight()
            if weight:
                quantity = getattr(line, 'quantity', 1)
                total_weight += weight * quantity
    return total_weight


# =============================================================================
# QUERYSETS & MANAGERS
# =============================================================================

class ShippingZoneQuerySet(models.QuerySet):
    """Custom queryset for ShippingZone model."""
    
    def active(self):
        return self.filter(is_active=True)
    
    def by_country(self, country_code):
        return self.filter(countries__contains=country_code)
    
    def by_channel(self, channel_slug):
        return self.filter(channels__slug=channel_slug)
    
    def default_zone(self):
        return self.filter(default=True).first()
    
    def with_methods_count(self):
        return self.annotate(methods_count=Count('shipping_methods'))


class ShippingZoneManager(models.Manager):
    """Custom manager for ShippingZone model."""
    
    def get_queryset(self):
        return ShippingZoneQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def by_country(self, country_code):
        return self.get_queryset().by_country(country_code)
    
    def by_channel(self, channel_slug):
        return self.get_queryset().by_channel(channel_slug)


class ShippingMethodQueryset(models.QuerySet):
    """Optimized queryset for ShippingMethod with common queries."""
    
    def active(self):
        return self.filter(status=ShippingMethodStatus.ACTIVE, is_active=True)
    
    def price_based(self):
        return self.filter(type=ShippingMethodType.PRICE_BASED)
    
    def weight_based(self):
        return self.filter(type=ShippingMethodType.WEIGHT_BASED)
    
    def for_channel(self, channel_slug: str):
        return self.filter(
            shipping_zone__channels__slug=channel_slug,
            channel_listings__channel__slug=channel_slug,
            channel_listings__is_active=True,
        ).select_related("shipping_zone", "tax_class").prefetch_related("channel_listings").distinct()
    
    def annotate_channel_pricing(self, channel_id: int):
        return self.annotate(
            price_amount=Subquery(
                ShippingMethodChannelListing.objects.filter(
                    shipping_method=OuterRef("pk"),
                    channel_id=channel_id,
                    is_active=True,
                ).values("price_amount")[:1]
            ),
            minimum_order_price_amount=Subquery(
                ShippingMethodChannelListing.objects.filter(
                    shipping_method=OuterRef("pk"),
                    channel_id=channel_id,
                    is_active=True,
                ).values("minimum_order_price_amount")[:1]
            ),
            maximum_order_price_amount=Subquery(
                ShippingMethodChannelListing.objects.filter(
                    shipping_method=OuterRef("pk"),
                    channel_id=channel_id,
                    is_active=True,
                ).values("maximum_order_price_amount")[:1]
            ),
            currency=Subquery(
                ShippingMethodChannelListing.objects.filter(
                    shipping_method=OuterRef("pk"),
                    channel_id=channel_id,
                    is_active=True,
                ).values("currency")[:1]
            ),
        )
    
    def applicable_for_country(self, country_code: str):
        return self.filter(shipping_zone__countries__contains=country_code)
    
    def exclude_products(self, product_ids: list[int]):
        if not product_ids:
            return self
        return self.exclude(excluded_products__id__in=product_ids)
    
    def applicable_for_weight(self, weight: Weight):
        return self.filter(
            Q(minimum_order_weight__lte=weight) | Q(minimum_order_weight__isnull=True),
            Q(maximum_order_weight__gte=weight) | Q(maximum_order_weight__isnull=True),
            type=ShippingMethodType.WEIGHT_BASED,
        )
    
    def applicable_for_price(self, price: Money, channel_id: int):
        return self.filter(
            type=ShippingMethodType.PRICE_BASED,
            channel_listings__channel_id=channel_id,
            channel_listings__currency=price.currency,
            channel_listings__minimum_order_price_amount__lte=price.amount,
            channel_listings__maximum_order_price_amount__gte=price.amount,
            channel_listings__is_active=True,
        ).distinct()
    
    def applicable_shipping_methods(
        self,
        price: Money,
        channel_id: int,
        weight: Weight,
        country_code: str,
        product_ids: Optional[list[int]] = None,
    ):
        base_qs = (
            self.active()
            .filter(shipping_zone__countries__contains=country_code)
            .filter(shipping_zone__channels__id=channel_id)
            .annotate_channel_pricing(channel_id)
            .exclude_products(product_ids or [])
            .prefetch_related("shipping_zone", "postal_code_rules")
        )

        price_based = self.applicable_for_price(price, channel_id)
        weight_based = self.applicable_for_weight(weight)
        
        return (price_based | weight_based).filter(id__in=base_qs.values("id"))
    
    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query) |
            Q(shipping_zone__name__icontains=query)
        )


class ShippingMethodManager(models.Manager):
    """Custom manager for ShippingMethod model."""
    
    def get_queryset(self):
        return ShippingMethodQueryset(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def price_based(self):
        return self.get_queryset().price_based()
    
    def weight_based(self):
        return self.get_queryset().weight_based()
    
    def for_channel(self, channel_slug):
        return self.get_queryset().for_channel(channel_slug)
    
    def search(self, query):
        return self.get_queryset().search(query)


# =============================================================================
# MODELS
# =============================================================================

class ShippingZone(ModelWithMetadata):
    """
    Shipping Zone model.
    
    Defines geographic areas and their shipping methods.
    """
    
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the shipping zone"
    )
    countries = CountryField(
        multiple=True,
        default=[],
        blank=True,
        help_text="Countries in this shipping zone"
    )
    default = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the default shipping zone"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the shipping zone"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this zone is active"
    )
    channels = models.ManyToManyField(
        Channel,
        related_name="shipping_zones",
        db_index=True,
        help_text="Channels this zone applies to"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ShippingZoneManager()

    class Meta(ModelWithMetadata.Meta):
        permissions = (("manage_shipping", "Manage shipping."),)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            BTreeIndex(
                fields=["name"],
                name="shippingzone_name_idx",
            ),
            BTreeIndex(
                fields=["default", "is_active"],
                name="shippingzone_default_active_idx",
            ),
            BTreeIndex(
                fields=["created_at"],
                name="shippingzone_created_idx",
            ),
            BTreeIndex(
                fields=["countries"],
                name="shippingzone_countries_idx",
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        """Validate shipping zone data."""
        if self.default:
            # Check if another default zone exists
            existing_default = ShippingZone.objects.filter(
                default=True, is_active=True
            ).exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError({
                    "default": "Only one default shipping zone can exist."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_shipping_methods_for_channel(self, channel_slug: str):
        """Get shipping methods for a specific channel."""
        return (
            self.shipping_methods
            .active()
            .filter(channel_listings__channel__slug=channel_slug)
            .select_related("shipping_zone", "tax_class")
            .prefetch_related("channel_listings")
            .distinct()
        )


class ShippingMethod(ModelWithMetadata):
    """
    Shipping Method model.
    
    Defines shipping methods and their rules.
    """
    
    # Basic Info
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the shipping method"
    )
    type = models.CharField(
        max_length=30,
        choices=ShippingMethodType.CHOICES,
        default=ShippingMethodType.PRICE_BASED,
        db_index=True,
        help_text="Type of shipping method"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the shipping method"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ShippingMethodStatus.CHOICES,
        default=ShippingMethodStatus.ACTIVE,
        db_index=True,
        help_text="Current status of the shipping method"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this shipping method is active"
    )
    
    # Relationships
    shipping_zone = models.ForeignKey(
        ShippingZone,
        related_name="shipping_methods",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Shipping zone this method belongs to"
    )
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="shipping_methods",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Tax class for this shipping method"
    )
    
    # Weight Rules
    minimum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
        help_text="Minimum order weight for this method"
    )
    maximum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
        help_text="Maximum order weight for this method"
    )
    
    # Product exclusions
    excluded_products = models.ManyToManyField(
        "ecommerce.Product",
        blank=True,
        related_name="excluded_shipping_methods",
        db_index=True,
        help_text="Products excluded from this shipping method"
    )
    
    # Time estimates
    delivery_time_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum delivery days"
    )
    delivery_time_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum delivery days"
    )
    cutoff_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Daily order cutoff time"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shipping_methods",
        help_text="User who created this shipping method"
    )
    
    objects = ShippingMethodManager()

    class Meta:
        indexes = [
            BTreeIndex(fields=["type", "status"], name="shippingmethod_type_status_idx"),
            BTreeIndex(fields=["name"], name="shippingmethod_name_idx"),
            BTreeIndex(fields=["shipping_zone", "type"], name="shippingmethod_zone_type_idx"),
            BTreeIndex(fields=["created_at"], name="shippingmethod_created_idx"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def clean(self):
        """Validate shipping method data."""
        # Validate weight ranges
        if self.minimum_order_weight and self.maximum_order_weight:
            if self.minimum_order_weight > self.maximum_order_weight:
                raise ValidationError({
                    "minimum_order_weight": "Minimum weight cannot be greater than maximum weight."
                })
        
        # Validate delivery time
        if self.delivery_time_min and self.delivery_time_max:
            if self.delivery_time_min > self.delivery_time_max:
                raise ValidationError({
                    "delivery_time_min": "Minimum delivery time cannot be greater than maximum."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_price(self, channel_id: int) -> Optional[Money]:
        """Get price for a specific channel."""
        if not hasattr(self, "_channel_prices"):
            self._channel_prices = {
                listing.channel_id: listing.get_price()
                for listing in self.channel_listings.filter(is_active=True)
            }
        return self._channel_prices.get(channel_id)

    def is_applicable(
        self,
        price: Money,
        weight: Weight,
        channel_id: int,
        country_code: str,
        product_ids: Optional[list[int]] = None,
    ) -> bool:
        """Check if shipping method is applicable for given parameters."""
        if self.status != ShippingMethodStatus.ACTIVE or not self.is_active:
            return False
        
        if self.type == ShippingMethodType.PRICE_BASED:
            listing = self.channel_listings.filter(
                channel_id=channel_id,
                currency=price.currency,
                minimum_order_price_amount__lte=price.amount,
                maximum_order_price_amount__gte=price.amount,
                is_active=True,
            ).first()
            return bool(listing)
        
        elif self.type == ShippingMethodType.WEIGHT_BASED:
            weight_valid = (
                (not self.minimum_order_weight or self.minimum_order_weight <= weight)
                and (not self.maximum_order_weight or self.maximum_order_weight >= weight)
            )
            country_valid = self.shipping_zone.countries.filter(code=country_code).exists()
            product_valid = not (product_ids and self.excluded_products.filter(id__in=product_ids).exists())
            return weight_valid and country_valid and product_valid
        
        return False

# shipping/models.py - Updated with UniqueConstraint

# ============================================================================
# SHIPPING METHOD POSTAL CODE RULE
# ============================================================================

class ShippingMethodPostalCodeRule(models.Model):
    """
    Postal Code Rule model.
    
    Defines postal code inclusion/exclusion rules for shipping methods.
    """
    
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.CASCADE,
        related_name="postal_code_rules",
        db_index=True,
        help_text="Shipping method this rule applies to"
    )
    start = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Start of postal code range"
    )
    end = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        db_index=True,
        help_text="End of postal code range (optional)"
    )
    inclusion_type = models.CharField(
        max_length=32,
        choices=PostalCodeRuleInclusionType.CHOICES,
        default=PostalCodeRuleInclusionType.EXCLUDE,
        db_index=True,
        help_text="Whether to include or exclude"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this rule is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            BTreeIndex(fields=["start", "end"], name="postalrule_start_end_idx"),
            BTreeIndex(fields=["shipping_method", "is_active"], name="postalrule_method_active_idx"),
        ]
        ordering = ["shipping_method", "start"]
        constraints = [
            
            models.UniqueConstraint(
                fields=["shipping_method", "start", "end"],
                name="unique_shipping_method_postal_rule"
            ),
        ]
        

    def __str__(self):
        return f"{self.get_inclusion_type_display()}: {self.start}-{self.end or self.start}"

    def clean(self):
        """Validate postal code rule."""
        if self.end and self.start > self.end:
            raise ValidationError({
                "end": "End postal code cannot be before start postal code."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def matches(self, postal_code: str) -> bool:
        """Check if a postal code matches this rule."""
        if not postal_code:
            return False
        
        if self.end:
            return self.start <= postal_code <= self.end
        return self.start == postal_code


# ============================================================================
# SHIPPING METHOD CHANNEL LISTING
# ============================================================================

class ShippingMethodChannelListing(models.Model):
    """
    Channel Listing model.
    
    Channel-specific pricing and availability for shipping methods.
    """
    
    shipping_method = models.ForeignKey(
        ShippingMethod,
        related_name="channel_listings",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Shipping method this listing belongs to"
    )
    channel = models.ForeignKey(
        Channel,
        related_name="shipping_method_listings",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Channel this listing is for"
    )
    
    # Pricing
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text="Price amount"
    )
    price = MoneyField(
        amount_field="price_amount",
        currency_field="currency",
        help_text="Price with currency"
    )
    
    # Minimum order price
    minimum_order_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text="Minimum order price for this method"
    )
    minimum_order_price = MoneyField(
        amount_field="minimum_order_price_amount",
        currency_field="currency",
        help_text="Minimum order price with currency"
    )
    
    # Maximum order price
    maximum_order_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text="Maximum order price for this method"
    )
    maximum_order_price = MoneyField(
        amount_field="maximum_order_price_amount",
        currency_field="currency",
        help_text="Maximum order price with currency"
    )
    
    # Status
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        help_text="Currency code"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this listing is active"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("channel", "price_amount")
        indexes = [
            BTreeIndex(fields=["channel", "is_active"], name="shipmeth_chan_active_idx"),
            BTreeIndex(fields=["price_amount", "currency"], name="shipmeth_price_curr_idx"),
            BTreeIndex(fields=["minimum_order_price_amount", "currency"], name="shippinglisting_min_price_idx"),
        ]
        constraints = [
            
            models.UniqueConstraint(
                fields=["shipping_method", "channel"],
                name="unique_shipping_method_channel_listing"
            ),
        ]
        

    def __str__(self):
        return f"{self.shipping_method.name} - {self.channel.name}"

    def clean(self):
        """Validate price ranges."""
        if (
            self.minimum_order_price_amount is not None
            and self.maximum_order_price_amount is not None
            and self.minimum_order_price_amount > self.maximum_order_price_amount
        ):
            raise ValidationError({
                "minimum_order_price_amount": "Minimum order price cannot be greater than maximum order price."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_price(self) -> Money:
        """Get the price as a Money object."""
        return Money(self.price_amount, self.currency)

    def get_total(self) -> Money:
        """Get total price with proper currency handling."""
        return self.get_price()

    def is_applicable(self, order_price: Money) -> bool:
        """Check if this listing is applicable for an order price."""
        if not self.is_active:
            return False
        
        if order_price.currency != self.currency:
            return False
        
        price_amount = order_price.amount
        if self.minimum_order_price_amount and price_amount < self.minimum_order_price_amount:
            return False
        
        if self.maximum_order_price_amount and price_amount > self.maximum_order_price_amount:
            return False
        
        return True


# ============================================================================
# SHIPPING METHOD TRANSLATION
# ============================================================================

class ShippingMethodTranslation(models.Model):
    """
    Translation model for shipping methods.
    """
    
    shipping_method = models.ForeignKey(
        ShippingMethod,
        related_name="translations",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Shipping method to translate"
    )
    language_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Language code"
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Translated name"
    )
    description = models.JSONField(
        blank=True,
        null=True,
        help_text="Translated description (JSON format)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            BTreeIndex(fields=["language_code", "shipping_method"], name="shiptrans_lang_method_idx"),
        ]
        constraints = [
            
            models.UniqueConstraint(
                fields=["language_code", "shipping_method"],
                name="unique_shipping_method_translation"
            ),
        ]
        

    def __str__(self):
        return f"{self.shipping_method.name} ({self.language_code})"

    def clean(self):
        """Clean and validate translation data."""
        if self.description:
            self.description = clean_editor_js(self.description, to_string=False)
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_translated_object_id(self):
        return "ShippingMethod", self.shipping_method_id

    def get_translated_keys(self):
        return {
            "name": self.name,
            "description": self.description,
        }

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_checkout_weight(lines) -> Weight:
    """Calculate total weight of checkout lines."""
    return calculate_weight_from_lines(lines)


def filter_shipping_methods_by_postal_code_rules(methods, shipping_address):
    """Filter shipping methods by postal code rules."""
    if not shipping_address or not shipping_address.postal_code:
        return methods
    
    postal_code = shipping_address.postal_code
    filtered_methods = []
    
    for method in methods:
        rules = method.postal_code_rules.filter(is_active=True)
        if not rules.exists():
            filtered_methods.append(method)
            continue
        
        # Check if any rule excludes this postal code
        excluded = rules.filter(
            inclusion_type=PostalCodeRuleInclusionType.EXCLUDE
        ).filter(
            Q(start__lte=postal_code, end__isnull=True) |
            Q(start__lte=postal_code, end__gte=postal_code)
        ).exists()
        
        if excluded:
            continue
        
        # Check if any rule includes this postal code
        included = rules.filter(
            inclusion_type=PostalCodeRuleInclusionType.INCLUDE
        ).filter(
            Q(start__lte=postal_code, end__isnull=True) |
            Q(start__lte=postal_code, end__gte=postal_code)
        ).exists()
        
        if included or not rules.filter(inclusion_type=PostalCodeRuleInclusionType.INCLUDE).exists():
            filtered_methods.append(method)
    
    return filtered_methods


# =============================================================================
# SIGNALS
# =============================================================================

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=ShippingZone)
def shipping_zone_pre_save(sender, instance, **kwargs):
    """Handle shipping zone pre-save actions."""
    if instance.default:
        # Deactivate other default zones
        ShippingZone.objects.filter(default=True, is_active=True).exclude(pk=instance.pk).update(default=False)


@receiver(post_save, sender=ShippingMethod)
def shipping_method_post_save(sender, instance, created, **kwargs):
    """Handle shipping method post-save actions."""
    if created:
        logger.info(f"Shipping method created: {instance.name} (ID: {instance.id})")


@receiver(post_delete, sender=ShippingMethod)
def shipping_method_post_delete(sender, instance, **kwargs):
    """Handle shipping method post-delete actions."""
    logger.info(f"Shipping method deleted: {instance.name} (ID: {instance.id})")

