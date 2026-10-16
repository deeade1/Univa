# apps/backend/ecommerce/models/product.py

"""
Product catalog models.

This module owns:
    - ProductType            — category of products (physical, digital, market)
    - Product                — the sellable concept (iPhone 15)
    - ProductVariant         — the sellable unit (iPhone 15 128GB Blue)
    - ProductChannelListing  — product visibility/pricing per channel
    - ProductVariantChannelListing — variant pricing per channel
    - ProductMedia           — images, videos, 3D models
    - VariantMedia           — variant ↔ media association
    - DigitalContent         — files for digital products
    - DigitalContentUrl      — download tokens
    - ProductReview          — user reviews
    - Translations           — localized content

Design notes:

  * Money is never `Float`. All prices use `MoneyField` (from
    core.pricing) which pairs a Decimal with a currency column.

  * Prices are channel-scoped via `Product*ChannelListing`. A product
    can be priced in NGN in the Nigeria channel and USD in a future
    diaspora channel.

  * `Product.quantity_unit` is not here — units belong on
    `ProductVariant` because the same product (e.g. beef) can be sold
    by different units on different variants (500g pack vs 1kg pack).

  * Attributes (Size, Color, Material) live in `attribute.py` and
    attach via `AssignedAttribute`. Not here.

  * Reviews live here (`ProductReview`), but `Product.rating` is NOT
    a stored field — it is derived from approved reviews at query
    time (see the ProductManager for the annotation helper).

  * No `graphene` import. Global IDs belong in the GraphQL layer.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models, transaction
from django.db.models import F, JSONField, Q, TextField
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_measurement.models import MeasurementField
from measurement.measures import Weight

from core.models.metadata import (
    ModelWithExternalReference,
    ModelWithMetadata,
)
from core.models.publishable import PublishableModel
from core.models.sortable import SortableModel
from core.pricing.money import Money
from core.pricing.money_field import MoneyField
from core.units import WeightUnits
from core.utils import build_absolute_uri
from core.utils.editorjs import default_clean_editor_js
from core.utils.translations import Translation, get_translation
from core.weight import zero_weight
from ecommerce.manager.managers import (
    ProductManager,
    ProductVariantChannelListingManager,
    ProductVariantManager,
)
from ecommerce.models.category import Category
from ecommerce.models.channel import Channel
from ecommerce.models.discount import PromotionRule
from ecommerce.models.enums import (
    ProductMediaTypes,
    ProductTypeKind,
    QuantityUnit,
)
from seo.models import SeoModel, SeoModelTranslationWithSlug
from tax.models import TaxClass
def _generate_digital_content_token() -> str:
    """
    Default factory for DigitalContentUrl.token.

    Module-level rather than a lambda so Django's migration writer
    can serialize it into AlterField operations. Uses uuid4().hex so
    the value is a 32-character hex string with no dashes.
    """
    return uuid4().hex

# =====================================================================
# PRODUCT TYPE
# =====================================================================


class ProductType(ModelWithMetadata):
    """
    Category of products (physical, digital, gift card, market item).

    A ProductType defines:
      - the kind of product (see ProductTypeKind)
      - whether the product requires shipping
      - whether it is digital
      - whether it has variants
      - default weight and tax class

    Example:
        ProductType("Physical Book", kind=NORMAL, has_variants=False)
        ProductType("T-Shirt",       kind=NORMAL, has_variants=True)
        ProductType("Gift Card",     kind=GIFT_CARD, has_variants=False)
        ProductType("Market Item",   kind=MARKET_ITEM, has_variants=False)
    """

    name = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )
    kind = models.CharField(
        max_length=32,
        choices=ProductTypeKind.CHOICES,
        default=ProductTypeKind.NORMAL,
        db_index=True,
    )
    has_variants = models.BooleanField(default=True)
    is_shipping_required = models.BooleanField(default=True)
    is_digital = models.BooleanField(default=False)
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
        blank=True,
    )
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="product_types",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        permissions = (
            (
                "manage_product_types_and_attributes",
                "Manage product types and attributes.",
            ),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                fields=["name", "slug"],
                name="product_type_search_gin",
                opclasses=["gin_trgm_ops"] * 2,
            ),
        ]
        constraints = [
            # A digital product cannot require shipping.
            models.CheckConstraint(
                condition=Q(is_digital=False) | Q(is_shipping_required=False),
                name="product_type_digital_not_shipped",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# =====================================================================
# PRODUCT
# =====================================================================


class Product(SeoModel, ModelWithMetadata, ModelWithExternalReference):
    """
    A product in the catalog.

    A Product is the *concept* — "iPhone 15", "Beef", "Nike Air Max".
    The *sellable unit* is a `ProductVariant`.

    Examples:
        Product("iPhone 15")      → variants: 128GB Blue, 256GB Black
        Product("Beef")           → variants: 500g pack, 1kg pack
        Product("Nike Air Max")   → variants: size 42, size 43
    """

    product_type = models.ForeignKey(
        ProductType,
        related_name="products",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )
    description = JSONField(
        blank=True,
        default=default_clean_editor_js,
    )
    description_plaintext = TextField(blank=True)

    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=(
            "Deleting a category is prevented while products reference it. "
            "Reassign or deactivate the category instead."
        ),
    )
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
        help_text=(
            "Product-level default weight. If empty, the ProductType "
            "weight is used."
        ),
    )
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=(
            "The preferred variant to display when the product itself "
            "is referenced. Must belong to this product."
        ),
    )
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="products",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Soft-delete flag. Inactive products are hidden from the "
            "storefront but remain referenced by historical orders."
        ),
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search_document = TextField(blank=True, default="")
    search_vector = SearchVectorField(blank=True, null=True)
    search_index_dirty = models.BooleanField(default=False, db_index=True)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = ProductManager()

    class Meta:
        ordering = ("slug",)
        permissions = (("manage_products", "Manage products."),)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            # Full-text search over the precomputed document.
            GinIndex(
                fields=["search_vector"],
                name="product_tsearch",
            ),
            # Trigram search over name + slug for autocomplete.
            GinIndex(
                fields=["name", "slug"],
                name="product_name_slug_gin",
                opclasses=["gin_trgm_ops"] * 2,
            ),
            # Storefront listing queries: filter by category, order by slug.
            models.Index(fields=["category", "slug"], name="product_cat_slug_idx"),
            # Active listing filter.
            models.Index(
                fields=["is_active", "product_type"],
                name="product_active_type_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        """
        Validate cross-field invariants.

        The `default_variant` must belong to this product. The
        OneToOneField enforces uniqueness of the FK value, but not
        that the referenced variant's `product_id` matches this
        product's `pk`. Setting `default_variant` to a variant of a
        different product would silently make `product.default_variant`
        point at the wrong catalog entry.

        `clean()` is called by `full_clean()` and by Django admin
        forms. It is NOT called by `objects.create()` or `save()`, so
        the same invariant must also be enforced at the service layer
        when `default_variant` is assigned programmatically.
        """
        super().clean()

        if self.default_variant_id and self.pk:
            if self.default_variant.product_id != self.pk:
                raise ValidationError(
                    {
                        "default_variant": _(
                            "Default variant must belong to this product."
                        )
                    }
                )

    def get_first_image(self):
        """
        Return the first image ProductMedia for this product, or None.

        Uses a single filtered query rather than loading all media.
        """
        return (
            self.media.filter(type=ProductMediaTypes.IMAGE)
            .order_by("sort_order", "pk")
            .first()
        )


# =====================================================================
# PRODUCT REVIEW
# =====================================================================


class ProductReview(models.Model):
    """
    A user review of a product.

    Rules:
      - one review per (user, product)
      - rating is 1..5
      - reviews are unpublished by default (moderation)
      - `is_verified_purchase` is set by a service when the user has
        an OrderLine referencing this product
    """

    product = models.ForeignKey(
        Product,
        related_name="reviews",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="product_reviews",
        on_delete=models.CASCADE,
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    title = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False, db_index=True)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_review",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="review_rating_1_to_5",
            ),
        ]
        indexes = [
            models.Index(
                fields=["product", "-created_at"],
                name="review_product_created_idx",
            ),
            models.Index(
                fields=["product", "is_published"],
                name="review_product_published_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} - {self.rating}"

    def mark_helpful(self) -> None:
        """
        Atomically increment `helpful_count`.

        Uses a database-level F() expression rather than in-Python
        increment-then-save, so concurrent calls do not lose updates.
        The instance's local `helpful_count` is refreshed afterward
        so callers see the committed value.
        """
        type(self).objects.filter(pk=self.pk).update(
            helpful_count=F("helpful_count") + 1,
        )
        self.refresh_from_db(fields=["helpful_count"])

    @classmethod
    def record_helpful_vote(cls, review_id) -> int:
        """
        Atomically increment `helpful_count` for a review by id and
        return the new count.

        Preferred over instance `mark_helpful()` when the caller only
        has a review id and does not need a `ProductReview` object
        loaded.
        """
        updated = cls.objects.filter(pk=review_id).update(
            helpful_count=F("helpful_count") + 1,
        )

        if not updated:
            raise cls.DoesNotExist(
                f"ProductReview {review_id} does not exist."
            )

        return (
            cls.objects
            .filter(pk=review_id)
            .values_list("helpful_count", flat=True)
            .get()
        )


# =====================================================================
# PRODUCT TRANSLATION
# =====================================================================


class ProductTranslation(SeoModelTranslationWithSlug):
    product = models.ForeignKey(
        Product,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=250, blank=True)
    description = JSONField(
        blank=True,
        default=default_clean_editor_js,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="uniq_lang_slug_producttransl",
            ),
            models.UniqueConstraint(
                fields=["language_code", "product"],
                name="uniq_lang_product_producttransl",
            ),
        ]

    def __str__(self) -> str:
        return self.name or str(self.pk)

    def get_translated_object_id(self):
        return "Product", self.product_id

    def get_translated_keys(self):
        return {
            **super().get_translated_keys(),
            "name": self.name,
            "description": self.description,
        }


# =====================================================================
# PRODUCT CHANNEL LISTING
# =====================================================================


class ProductChannelListing(PublishableModel):
    """
    Product visibility and pricing on a specific channel.

    The `currency` column is denormalized from the Channel so that
    MoneyField can pair it with `price_amount`. Keeping it here means
    a listing carries its own currency and doesn't need a join to
    Channel to resolve Money.
    """

    product = models.ForeignKey(
        Product,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        related_name="product_listings",
        on_delete=models.CASCADE,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    price = MoneyField(
        amount_field="price_amount",
        currency_field="currency",
    )
    discounted_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    discounted_price = MoneyField(
        amount_field="discounted_price_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Availability and merchandising
    # ------------------------------------------------------------------

    visible_in_listings = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Whether the product appears in storefront listings on "
            "this channel. Set to False to stage a launch."
        ),
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Merchandising flag scoped to the channel. A product can "
            "be featured on the Univa app but not on other channels."
        ),
    )
    available_for_purchase_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Products become purchasable at this time.",
    )

    # ------------------------------------------------------------------
    # Discount cache
    # ------------------------------------------------------------------

    discounted_price_dirty = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Set True when the discounted price needs recomputation. "
            "A background task clears it after recalculating."
        ),
    )

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["product", "channel"],
                name="unique_product_channel_listing",
            ),
            # A discounted price cannot exceed the base price, when
            # both are set. NULL on either side is allowed: the
            # discounted price is optional, and the base price is
            # always required but might not be comparable in a
            # different currency (which is why currency is
            # denormalized here).
            models.CheckConstraint(
                condition=(
                    Q(discounted_price_amount__isnull=True)
                    | Q(
                        discounted_price_amount__lte=F("price_amount")
                    )
                ),
                name="prod_listing_discounted_lte_price",
            ),
        ]
        indexes = [
            models.Index(fields=["published_at"]),
            BTreeIndex(
                fields=["discounted_price_amount"],
                name="prod_listing_disc_price_idx",
            ),
            models.Index(
                fields=["channel", "visible_in_listings", "is_featured"],
                name="prod_listing_storefront_idx",
            ),
        ]

    def is_available_for_purchase(self) -> bool:
        return (
            self.available_for_purchase_at is not None
            and timezone.now() >= self.available_for_purchase_at
        )


# =====================================================================
# PRODUCT VARIANT
# =====================================================================


class ProductVariant(
    SortableModel,
    ModelWithMetadata,
    ModelWithExternalReference,
):
    """
    A sellable unit of a Product.

    Every purchasable item is a ProductVariant. Even if the Product
    has no variants (single-SKU products), a default variant exists.

    Quantity is expressed in `quantity_unit`:
      - UNIT / PIECE / BUNCH / BAG — discrete; integer quantities
      - KG / G / L / ML / M / CM — continuous; decimal quantities

    This lets catalog items ("iPhone 15 128GB") and market items
    ("2.5kg of beef") share the same order line model.
    """

    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE,
    )
    sku = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Stock keeping unit. Unique when set. NULL is allowed "
            "for draft variants; multiple NULLs do not collide in "
            "PostgreSQL."
        ),
    )
    name = models.CharField(max_length=255, blank=True)
    quantity_unit = models.CharField(
        max_length=16,
        choices=[(u.value, u.name) for u in QuantityUnit],
        default=QuantityUnit.UNIT.value,
        db_index=True,
        help_text=(
            "How this variant is sold. Discrete units require whole "
            "quantities; continuous units allow decimals."
        ),
    )
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )
    track_inventory = models.BooleanField(default=True)
    is_preorder = models.BooleanField(default=False)
    preorder_end_date = models.DateTimeField(null=True, blank=True)
    preorder_global_threshold = models.PositiveIntegerField(
        blank=True,
        null=True,
    )
    quantity_limit_per_customer = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
    )
    media = models.ManyToManyField(
        "ProductMedia",
        through="VariantMedia",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = ProductVariantManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("sort_order", "sku")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(fields=["product"], name="variant_product_idx"),
            models.Index(
                fields=["product", "sort_order"],
                name="variant_product_sort_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name or self.sku or f"ID:{self.pk}"

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    def get_base_price(
        self,
        channel_listing: "ProductVariantChannelListing",
        price_override: Decimal | None = None,
    ) -> Money:
        if price_override is None:
            return channel_listing.price
        return Money(price_override, channel_listing.currency)

    def get_price(
        self,
        channel_listing: "ProductVariantChannelListing",
        price_override: Decimal | None = None,
        promotion_rules=None,
    ) -> Money:
        from ecommerce.services.promotion import (
            calculate_discounted_price_for_rules,
        )

        if price_override is None:
            return (
                channel_listing.discounted_price
                or channel_listing.price
            )
        price = self.get_base_price(channel_listing, price_override)
        rules = promotion_rules or []
        return calculate_discounted_price_for_rules(
            price=price,
            rules=rules,
            currency=channel_listing.currency,
        )

    # ------------------------------------------------------------------
    # Physical characteristics
    # ------------------------------------------------------------------

    def get_weight(self) -> Weight:
        return (
            self.weight
            or self.product.weight
            or self.product.product_type.weight
        )

    def is_shipping_required(self) -> bool:
        return self.product.product_type.is_shipping_required

    def is_gift_card(self) -> bool:
        return (
            self.product.product_type.kind == ProductTypeKind.GIFT_CARD
        )

    def is_digital(self) -> bool:
        return (
            not self.is_shipping_required()
            and self.product.product_type.is_digital
        )

    def is_market_item(self) -> bool:
        return (
            self.product.product_type.kind == ProductTypeKind.MARKET_ITEM
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_product(self, translated: bool = False) -> str:
        if translated:
            product_name = get_translation(self.product).name
            variant_name = get_translation(self).name
        else:
            product_name = self.product.name
            variant_name = str(self)

        if variant_name:
            return f"{product_name} ({variant_name})"
        return product_name

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def get_ordering_queryset(self):
        return self.product.variants.all()

    # ------------------------------------------------------------------
    # Preorder
    # ------------------------------------------------------------------

    def is_preorder_active(self) -> bool:
        return self.is_preorder and (
            self.preorder_end_date is None
            or timezone.now() <= self.preorder_end_date
        )


# =====================================================================
# PRODUCT VARIANT TRANSLATION
# =====================================================================


class ProductVariantTranslation(Translation):
    product_variant = models.ForeignKey(
        ProductVariant,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["product_variant_id", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "product_variant"],
                name="unique_lang_productvariant_translation",
            ),
        ]

    def __str__(self) -> str:
        return self.name or str(self.product_variant)

    def get_translated_object_id(self):
        return "ProductVariant", self.product_variant_id

    def get_translated_keys(self):
        return {"name": self.name}


# =====================================================================
# PRODUCT VARIANT CHANNEL LISTING
# =====================================================================


class ProductVariantChannelListing(models.Model):
    """
    Variant pricing and availability on a specific channel.
    """

    variant = models.ForeignKey(
        ProductVariant,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        related_name="variant_listings",
        on_delete=models.CASCADE,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    price = MoneyField(
        amount_field="price_amount",
        currency_field="currency",
    )
    cost_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
        help_text=(
            "Internal cost of goods sold. Never exposed to storefront."
        ),
    )
    cost_price = MoneyField(
        amount_field="cost_price_amount",
        currency_field="currency",
    )
    discounted_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    discounted_price = MoneyField(
        amount_field="discounted_price_amount",
        currency_field="currency",
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Merchandising flag scoped to the channel.",
    )
    preorder_quantity_threshold = models.IntegerField(
        blank=True,
        null=True,
    )
    discounted_price_dirty = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Set True when the discounted price needs recomputation."
        ),
    )
    promotion_rules = models.ManyToManyField(
        PromotionRule,
        through="VariantChannelListingPromotionRule",
        blank=True,
    )

    objects = ProductVariantChannelListingManager()

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "channel"],
                name="unique_variant_channel_listing",
            ),
            # A discounted price cannot exceed the base price, when
            # both are set. NULL on either side is allowed.
            models.CheckConstraint(
                condition=(
                    Q(discounted_price_amount__isnull=True)
                    | Q(
                        discounted_price_amount__lte=F("price_amount")
                    )
                ),
                name="variant_listing_discounted_lte_price",
            ),
        ]
        indexes = [
            BTreeIndex(
                fields=["price_amount", "channel"],
                name="variant_price_btree_idx",
            ),
            models.Index(
                fields=["channel", "is_featured"],
                name="variant_listing_feat_idx",
            ),
            models.Index(
                fields=["discounted_price_dirty"],
                name="variant_listing_dirty_idx",
            ),
        ]


# =====================================================================
# VARIANT CHANNEL LISTING PROMOTION RULE
# =====================================================================


class VariantChannelListingPromotionRule(models.Model):
    """
    Denormalized discount amount for a variant on a channel, computed
    from a specific PromotionRule.
    """

    variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        related_name="variantlistingpromotionrule",
        on_delete=models.CASCADE,
    )
    promotion_rule = models.ForeignKey(
        PromotionRule,
        related_name="variantlistingpromotionrule",
        on_delete=models.CASCADE,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    discount = MoneyField(
        amount_field="discount_amount",
        currency_field="currency",
    )

    class Meta:
        ordering = ["variant_channel_listing_id", "promotion_rule_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["variant_channel_listing", "promotion_rule"],
                name="unique_variant_listing_promotion_rule",
            ),
        ]


# =====================================================================
# DIGITAL CONTENT
# =====================================================================


class DigitalContent(ModelWithMetadata):
    """
    File attached to a digital ProductVariant.
    """

    FILE = "file"
    TYPE_CHOICES = ((FILE, "digital_product"),)

    product_variant = models.OneToOneField(
        ProductVariant,
        related_name="digital_content",
        on_delete=models.CASCADE,
    )
    use_default_settings = models.BooleanField(default=True)
    automatic_fulfillment = models.BooleanField(default=False)
    content_type = models.CharField(
        max_length=128,
        default=FILE,
        choices=TYPE_CHOICES,
    )
    content_file = models.FileField(
        upload_to="digital_contents",
        blank=True,
    )
    max_downloads = models.PositiveIntegerField(
        blank=True,
        null=True,
    )
    url_valid_days = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["product_variant_id"]

    def __str__(self) -> str:
        return f"Digital content for {self.product_variant}"

    def create_new_url(self) -> "DigitalContentUrl":
        return self.urls.create()


class DigitalContentUrl(models.Model):
    """
    A time-limited download URL for a DigitalContent.

    `token` is a 32-char hex string (UUID4 without dashes), generated
    on insert. `default=...` is used rather than a `save()` override
    so that `bulk_create()` and any other path that bypasses `save()`
    still produces a valid token.
    """

    content = models.ForeignKey(
        DigitalContent,
        related_name="urls",
        on_delete=models.CASCADE,
    )
    line = models.ForeignKey(
        "ecommerce.OrderLine",
        related_name="digital_content_urls",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text=(
            "The order line this download was issued for. ForeignKey "
            "rather than OneToOne so a re-issued download URL can be "
            "created for the same line."
        ),
    )
    token = models.CharField(
         max_length=32,
         unique=True,
         editable=False,
         default=_generate_digital_content_token,
     )
    is_revoked = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Set True when the download should no longer be served "
            "(e.g. after a refund or chargeback)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    download_num = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Download {self.token[:8]}… for {self.content}"

    def get_absolute_url(self) -> str:
        url = reverse(
            "digital-product",
            kwargs={"token": self.token},
        )
        return build_absolute_uri(url)

    @property
    def is_downloadable(self) -> bool:
        if self.is_revoked:
            return False
        content = self.content
        if content.max_downloads and self.download_num >= content.max_downloads:
            return False
        return True


# =====================================================================
# PRODUCT MEDIA
# =====================================================================


class ProductMedia(SortableModel, ModelWithMetadata):
    """
    An image, video, or other media asset attached to a product.

    Product is nullable so media can be pre-uploaded and associated
    later (e.g. bulk-import workflows).
    """

    product = models.ForeignKey(
        Product,
        related_name="media",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to="products",
        blank=True,
        null=True,
    )
    alt = models.CharField(max_length=250, blank=True)
    type = models.CharField(
        max_length=32,
        choices=ProductMediaTypes.CHOICES,
        default=ProductMediaTypes.IMAGE,
    )
    external_url = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="External URL for videos and other non-image media.",
    )
    oembed_data = JSONField(blank=True, default=dict)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("sort_order", "pk")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["product", "sort_order"],
                name="media_product_sort_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.alt or f"Media #{self.pk}"

    def get_ordering_queryset(self):
        if self.product:
            return self.product.media.all()
        return ProductMedia.objects.none()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Let SortableModel renumber siblings.
        super().delete(*args, **kwargs)


class VariantMedia(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        related_name="variant_media",
        on_delete=models.CASCADE,
    )
    media = models.ForeignKey(
        ProductMedia,
        related_name="variant_media",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["variant_id", "media_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "media"],
                name="unique_variant_media",
            ),
        ]
        indexes = [
            models.Index(
                fields=["variant", "media"],
                name="variant_media_idx",
            ),
        ]