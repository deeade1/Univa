# graphql/ecommerce/types/product.py

"""
GraphQL Nodes for Product, ProductType, ProductVariant, and related models.
"""

from django.db.models import Avg, Sum
from django.utils import timezone
from graphene import (
    Boolean,
    DateTime,
    Decimal,
    Field,
    Float,
    Int,
    JSONString,
    List,
    Node,
    String,
    UUID,
)
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.enums import ProductMediaTypes, ProductTypeKind
from ecommerce.models.product import (
    DigitalContent,
    DigitalContentUrl,
    Product,
    ProductChannelListing,
    ProductMedia,
    ProductReview,
    ProductTranslation,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
    ProductVariantTranslation,
    VariantChannelListingPromotionRule,
    VariantMedia,
)


class ProductTypeNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Type."""

    kind_display = String(description="Human-readable kind display")
    product_count = Int(description="Number of products of this type")
    variant_count = Int(description="Number of variants of this type")
    weight_display = String(description="Formatted weight")
    has_attributes = Boolean(description="Whether product type has attributes")

    class Meta:
        model = ProductType
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains", "istartswith"],
            "slug": ["exact", "icontains", "istartswith"],
            "kind": ["exact"],
            "has_variants": ["exact"],
            "is_shipping_required": ["exact"],
            "is_digital": ["exact"],
        }

    def resolve_kind_display(self, info):
        return dict(ProductTypeKind.CHOICES).get(self.kind, self.kind)

    def resolve_product_count(self, info):
        return self.products.count()

    def resolve_variant_count(self, info):
        return ProductVariant.objects.filter(
            product__product_type=self
        ).count()

    def resolve_weight_display(self, info):
        if self.weight:
            return f"{self.weight.value} {self.weight.unit}"
        return None

    def resolve_has_attributes(self, info):
        # Scope links replaced the old product_attributes / variant_attributes M2M.
        return self.attribute_scope_links.exists()

    def resolve_tax_class_details(self, info):
        return self.tax_class


class ProductChannelListingNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Channel Listing."""

    price_display = String(description="Formatted price")
    discounted_price_display = String(description="Formatted discounted price")
    is_available_for_purchase = Boolean(
        description="Whether product is available for purchase"
    )
    is_published = Boolean(
        description="Whether product is published in this channel"
    )
    has_discount = Boolean(description="Whether product has a discount in this channel")
    discount_percentage = Float(description="Discount percentage")

    class Meta:
        model = ProductChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product": ["exact"],
            "channel": ["exact"],
            "currency": ["exact"],
            "price_amount": ["exact", "gte", "lte", "isnull"],
            "discounted_price_amount": ["exact", "gte", "lte", "isnull"],
            "visible_in_listings": ["exact"],
            "published_at": ["exact", "gte", "lte", "isnull"],
            "available_for_purchase_at": ["exact", "gte", "lte", "isnull"],
        }

    def resolve_price_display(self, info):
        if self.price_amount:
            return f"{self.price_amount:.2f} {self.currency}"
        return None

    def resolve_discounted_price_display(self, info):
        if self.discounted_price_amount:
            return f"{self.discounted_price_amount:.2f} {self.currency}"
        return None

    def resolve_is_available_for_purchase(self, info):
        return self.is_available_for_purchase()

    def resolve_is_published(self, info):
        return self.is_published

    def resolve_has_discount(self, info):
        return (
            self.discounted_price_amount is not None
            and self.price_amount is not None
            and self.discounted_price_amount < self.price_amount
        )

    def resolve_discount_percentage(self, info):
        if self.has_discount and self.price_amount > 0:
            return (
                (self.price_amount - self.discounted_price_amount)
                / self.price_amount
            ) * 100
        return 0


class ProductReviewNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Review."""

    rating_display = String(description="Star rating display")

    class Meta:
        model = ProductReview
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product": ["exact"],
            "user": ["exact"],
            "rating": ["exact", "gte", "lte"],
            "comment": ["exact", "icontains"],
            "created_at": ["exact", "gte", "lte"],
        }

    def resolve_rating_display(self, info):
        return f"{'⭐' * self.rating} ({self.rating}/5)"


class ProductTranslationNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Translation."""

    has_name = Boolean(description="Whether translation has a name")
    has_description = Boolean(description="Whether translation has a description")
    description_plaintext = String(description="Plain text version of description")

    class Meta:
        model = ProductTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product": ["exact"],
            "language_code": ["exact"],
            "name": ["exact", "icontains"],
            "slug": ["exact", "icontains"],
            "seo_title": ["exact", "icontains"],
            "seo_description": ["exact", "icontains"],
        }

    def resolve_has_name(self, info):
        return bool(self.name)

    def resolve_has_description(self, info):
        return bool(self.description)

    def resolve_description_plaintext(self, info):
        if self.description and isinstance(self.description, dict):
            blocks = self.description.get("blocks", [])
            texts = []
            for block in blocks:
                if block.get("type") == "paragraph":
                    data = block.get("data", {})
                    if data.get("text"):
                        texts.append(data["text"])
            return " ".join(texts)
        return None


class ProductNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product."""

    has_variants = Boolean(description="Whether product has variants")
    is_in_stock = Boolean(description="Whether product is in stock")
    is_available = Boolean(description="Whether product is available for purchase")
    has_media = Boolean(description="Whether product has media")
    has_reviews = Boolean(description="Whether product has reviews")
    average_rating = Float(description="Average rating")
    review_count = Int(description="Number of reviews")
    main_image_url = String(description="URL of the main product image")

    description_plaintext = String(description="Plain text version of description")
    weight_display = String(description="Formatted weight")

    class Meta:
        model = Product
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product_type": ["exact"],
            "category": ["exact"],
            "tax_class": ["exact"],
            "name": ["exact", "icontains", "istartswith"],
            "slug": ["exact", "icontains", "istartswith"],
            "is_active": ["exact"],
            "seo_title": ["exact", "icontains"],
            "seo_description": ["exact", "icontains"],
            "created_at": ["exact", "gte", "lte"],
            "updated_at": ["exact", "gte", "lte"],
        }

    def resolve_has_variants(self, info):
        return self.variants.exists()

    def resolve_is_in_stock(self, info):
        from ecommerce.models.inventory import Stock

        return Stock.objects.filter(
            product_variant__product=self,
            quantity__gt=0,
        ).exists()

    def resolve_is_available(self, info):
        return self.channel_listings.filter(
            available_for_purchase_at__lte=timezone.now(),
        ).exists()

    def resolve_has_media(self, info):
        return self.media.exists()

    def resolve_has_reviews(self, info):
        return self.reviews.exists()

    def resolve_average_rating(self, info):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    def resolve_review_count(self, info):
        return self.reviews.count()

    def resolve_main_image_url(self, info):
        first_image = self.get_first_image()
        if first_image and first_image.image:
            return first_image.image.url
        return None

    def resolve_description_plaintext(self, info):
        if self.description and isinstance(self.description, dict):
            blocks = self.description.get("blocks", [])
            texts = []
            for block in blocks:
                if block.get("type") == "paragraph":
                    data = block.get("data", {})
                    if data.get("text"):
                        texts.append(data["text"])
            return " ".join(texts)
        return None

    def resolve_weight_display(self, info):
        if self.weight:
            return f"{self.weight.value} {self.weight.unit}"
        return None


class ProductVariantTranslationNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Variant Translation."""

    class Meta:
        model = ProductVariantTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product_variant": ["exact"],
            "language_code": ["exact"],
            "name": ["exact", "icontains"],
        }


class ProductVariantChannelListingNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Variant Channel Listing."""

    price_display = String(description="Formatted price")
    cost_price_display = String(description="Formatted cost price")
    discounted_price_display = String(description="Formatted discounted price")
    has_discount = Boolean(description="Whether variant has a discount in this channel")
    discount_percentage = Float(description="Discount percentage")
    margin = Float(description="Profit margin percentage")

    class Meta:
        model = ProductVariantChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "variant": ["exact"],
            "channel": ["exact"],
            "currency": ["exact"],
            "price_amount": ["exact", "gte", "lte", "isnull"],
            "cost_price_amount": ["exact", "gte", "lte", "isnull"],
            "discounted_price_amount": ["exact", "gte", "lte", "isnull"],
            "is_featured": ["exact"],
            "preorder_quantity_threshold": ["exact", "gte", "lte", "isnull"],
        }

    def resolve_price_display(self, info):
        if self.price_amount:
            return f"{self.price_amount:.2f} {self.currency}"
        return None

    def resolve_cost_price_display(self, info):
        if self.cost_price_amount:
            return f"{self.cost_price_amount:.2f} {self.currency}"
        return None

    def resolve_discounted_price_display(self, info):
        if self.discounted_price_amount:
            return f"{self.discounted_price_amount:.2f} {self.currency}"
        return None

    def resolve_has_discount(self, info):
        return (
            self.discounted_price_amount is not None
            and self.price_amount is not None
            and self.discounted_price_amount < self.price_amount
        )

    def resolve_discount_percentage(self, info):
        if self.has_discount and self.price_amount > 0:
            return (
                (self.price_amount - self.discounted_price_amount)
                / self.price_amount
            ) * 100
        return 0

    def resolve_margin(self, info):
        if (
            self.price_amount
            and self.cost_price_amount
            and self.cost_price_amount > 0
        ):
            return (
                (self.price_amount - self.cost_price_amount)
                / self.price_amount
            ) * 100
        return 0


class VariantChannelListingPromotionRuleNode(OptimizedDjangoObjectType):
    """GraphQL Node for Variant Channel Listing Promotion Rule."""

    discount_display = String(description="Formatted discount")

    class Meta:
        model = VariantChannelListingPromotionRule
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "variant_channel_listing": ["exact"],
            "promotion_rule": ["exact"],
            "currency": ["exact"],
            "discount_amount": ["exact", "gte", "lte"],
        }

    def resolve_discount_display(self, info):
        if self.discount_amount:
            return f"{self.discount_amount:.2f} {self.currency}"
        return None


class ProductVariantNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Variant."""

    is_shipping_required = Boolean(description="Whether variant requires shipping")
    is_gift_card = Boolean(description="Whether variant is a gift card")
    is_digital = Boolean(description="Whether variant is digital")
    is_market_item = Boolean(description="Whether variant is a market item")
    is_preorder_active = Boolean(description="Whether preorder is active")
    has_stock = Boolean(description="Whether variant has stock")
    total_stock = Int(description="Total stock across all warehouses")

    display_product = String(description="Display name with product")
    weight_display = String(description="Formatted weight")
    display_name = String(description="Display name")
    quantity_unit_display = String(description="Human-readable quantity unit")

    class Meta:
        model = ProductVariant
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product": ["exact"],
            "sku": ["exact", "icontains"],
            "name": ["exact", "icontains"],
            "quantity_unit": ["exact"],
            "track_inventory": ["exact"],
            "is_preorder": ["exact"],
            "preorder_global_threshold": ["exact", "gte", "lte", "isnull"],
            "quantity_limit_per_customer": ["exact", "gte", "lte", "isnull"],
            "created_at": ["exact", "gte", "lte"],
            "updated_at": ["exact", "gte", "lte"],
            "preorder_end_date": ["exact", "gte", "lte", "isnull"],
        }

    def resolve_is_shipping_required(self, info):
        return self.is_shipping_required()

    def resolve_is_gift_card(self, info):
        return self.is_gift_card()

    def resolve_is_digital(self, info):
        return self.is_digital()

    def resolve_is_market_item(self, info):
        return self.is_market_item()

    def resolve_is_preorder_active(self, info):
        return self.is_preorder_active()

    def resolve_has_stock(self, info):
        from ecommerce.models.inventory import Stock

        return Stock.objects.filter(
            product_variant=self,
            quantity__gt=0,
        ).exists()

    def resolve_total_stock(self, info):
        from ecommerce.models.inventory import Stock

        return (
            Stock.objects.filter(product_variant=self).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )

    def resolve_display_product(self, info):
        return self.display_product()

    def resolve_weight_display(self, info):
        weight = self.get_weight()
        if weight:
            return f"{weight.value} {weight.unit}"
        return None

    def resolve_display_name(self, info):
        return str(self)

    def resolve_quantity_unit_display(self, info):
        from core.pricing.quantity_unit import label
        from core.pricing.quantity_unit import QuantityUnit

        try:
            return label(QuantityUnit(self.quantity_unit))
        except ValueError:
            return self.quantity_unit


class DigitalContentNode(OptimizedDjangoObjectType):
    """GraphQL Node for Digital Content."""

    content_type_display = String(description="Human-readable content type display")
    has_file = Boolean(description="Whether content has a file")

    class Meta:
        model = DigitalContent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product_variant": ["exact"],
            "use_default_settings": ["exact"],
            "automatic_fulfillment": ["exact"],
            "content_type": ["exact"],
            "max_downloads": ["exact", "gte", "lte", "isnull"],
            "url_valid_days": ["exact", "gte", "lte", "isnull"],
        }

    def resolve_content_type_display(self, info):
        return dict(DigitalContent.TYPE_CHOICES).get(
            self.content_type, self.content_type
        )

    def resolve_has_file(self, info):
        return bool(self.content_file)


class DigitalContentUrlNode(OptimizedDjangoObjectType):
    """GraphQL Node for Digital Content URL."""

    is_expired = Boolean(description="Whether URL is expired")
    absolute_url = String(description="Absolute URL to download")
    can_download = Boolean(description="Whether download is allowed")

    class Meta:
        model = DigitalContentUrl
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "content": ["exact"],
            "line": ["exact"],
            "token": ["exact"],
            "is_revoked": ["exact"],
            "download_num": ["exact", "gte", "lte"],
            "created_at": ["exact", "gte", "lte"],
        }

    def resolve_is_expired(self, info):
        if self.content and self.content.url_valid_days:
            expiry = self.created_at + timezone.timedelta(
                days=self.content.url_valid_days
            )
            return timezone.now() > expiry
        return False

    def resolve_absolute_url(self, info):
        try:
            return self.get_absolute_url()
        except Exception:
            return None

    def resolve_can_download(self, info):
        if self.is_revoked:
            return False
        if self.is_expired:
            return False
        if self.content and self.content.max_downloads:
            return self.download_num < self.content.max_downloads
        return True


class ProductMediaNode(OptimizedDjangoObjectType):
    """GraphQL Node for Product Media."""

    type_display = String(description="Human-readable type display")
    image_url = String(description="URL of the image")
    is_image = Boolean(description="Whether media is an image")
    is_video = Boolean(description="Whether media is a video")
    is_external = Boolean(description="Whether media is external")

    class Meta:
        model = ProductMedia
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "product": ["exact"],
            "alt": ["exact", "icontains"],
            "type": ["exact"],
        }

    def resolve_type_display(self, info):
        return dict(ProductMediaTypes.CHOICES).get(self.type, self.type)

    def resolve_image_url(self, info):
        if self.image and hasattr(self.image, "url"):
            return self.image.url
        return None

    def resolve_is_image(self, info):
        return self.type == ProductMediaTypes.IMAGE

    def resolve_is_video(self, info):
        return self.type == ProductMediaTypes.VIDEO

    def resolve_is_external(self, info):
        return bool(self.external_url)


class VariantMediaNode(OptimizedDjangoObjectType):
    """GraphQL Node for Variant Media."""

    class Meta:
        model = VariantMedia
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "variant": ["exact"],
            "media": ["exact"],
        }