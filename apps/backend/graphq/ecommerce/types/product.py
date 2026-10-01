# graphql/ecommerce/types/product.py

"""
GraphQL Nodes for Product, ProductType, ProductVariant, and related models.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.product import (
    ProductType,
    Product,
    ProductReview,
    ProductTranslation,
    ProductChannelListing,
    ProductVariant,
    ProductVariantTranslation,
    ProductVariantChannelListing,
    VariantChannelListingPromotionRule,
    DigitalContent,
    DigitalContentUrl,
    ProductMedia,
    VariantMedia,
)
 


class ProductTypeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Type.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
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
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            'kind': ['exact'],
            
            # Boolean fields
            'has_variants': ['exact'],
            'is_shipping_required': ['exact'],
            'is_digital': ['exact'],
        }
        
    
    def resolve_kind_display(self, info):
        """Resolve human-readable kind display."""
        return dict(ProductTypeKind.CHOICES).get(self.kind, self.kind)
    
    def resolve_product_count(self, info):
        """Resolve number of products of this type."""
        return self.products.count()
    
    def resolve_variant_count(self, info):
        """Resolve number of variants of this type."""
        return ProductVariant.objects.filter(product__product_type=self).count()
    
    def resolve_weight_display(self, info):
        """Resolve formatted weight."""
        if self.weight:
            return f"{self.weight.value} {self.weight.unit}"
        return None
    
    def resolve_has_attributes(self, info):
        """Resolve whether product type has attributes."""
        return self.product_attributes.exists() or self.variant_attributes.exists()
    
    def resolve_tax_class_details(self, info):
        """Resolve tax class details."""
        return self.tax_class
    
    def resolve_product_attributes(self, info):
        """Resolve product attributes."""
        return self.product_attributes.all()
    
    def resolve_variant_attributes(self, info):
        """Resolve variant attributes."""
        return self.variant_attributes.all()
    
    def resolve_products(self, info):
        """Resolve products of this type."""
        return self.products.all()


class ProductChannelListingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Channel Listing.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    price_display = String(description="Formatted price")
    discounted_price_display = String(description="Formatted discounted price")
    is_available_for_purchase = Boolean(description="Whether product is available for purchase")
    is_published = Boolean(description="Whether product is published in this channel")
    has_discount = Boolean(description="Whether product has a discount in this channel")
    discount_percentage = Float(description="Discount percentage")
    
    class Meta:
        model = ProductChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'product': ['exact'],
            'channel': ['exact'],
            'currency': ['exact'],
            'price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'discounted_price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'visible_in_listings': ['exact'],
            'is_published': ['exact'],
            'published_at': ['exact', 'gte', 'lte', 'isnull'],
            'available_for_purchase_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_price_display(self, info):
        """Resolve formatted price."""
        if self.price_amount:
            return f"{self.price_amount:.2f} {self.currency}"
        return None
    
    def resolve_discounted_price_display(self, info):
        """Resolve formatted discounted price."""
        if self.discounted_price_amount:
            return f"{self.discounted_price_amount:.2f} {self.currency}"
        return None
    
    def resolve_is_available_for_purchase(self, info):
        """Resolve whether product is available for purchase."""
        return self.is_available_for_purchase()
    
    def resolve_is_published(self, info):
        """Resolve whether product is published in this channel."""
        return self.is_published
    
    def resolve_has_discount(self, info):
        """Resolve whether product has a discount in this channel."""
        return (
            self.discounted_price_amount is not None and
            self.price_amount is not None and
            self.discounted_price_amount < self.price_amount
        )
    
    def resolve_discount_percentage(self, info):
        """Resolve discount percentage."""
        if self.has_discount and self.price_amount > 0:
            return ((self.price_amount - self.discounted_price_amount) / self.price_amount) * 100
        return 0
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product
    
    def resolve_channel_details(self, info):
        """Resolve channel details."""
        return self.channel


class ProductReviewNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Review.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    rating_display = String(description="Star rating display")
    

    class Meta:
        model = ProductReview
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'product': ['exact'],
            'user': ['exact'],
            'rating': ['exact', 'gte', 'lte'],
            'comment': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_rating_display(self, info):
        """Resolve star rating display."""
        return f"{'⭐' * self.rating} ({self.rating}/5)"
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product
    
    def resolve_user_details(self, info):
        """Resolve user who wrote the review."""
        return self.user


class ProductTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Translation.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    has_name = Boolean(description="Whether translation has a name")
    has_description = Boolean(description="Whether translation has a description")
    description_plaintext = String(description="Plain text version of description")
    
    class Meta:
        model = ProductTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'product': ['exact'],
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
            'slug': ['exact', 'icontains'],
            'seo_title': ['exact', 'icontains'],
            'seo_description': ['exact', 'icontains'],
        }
        
    
    def resolve_has_name(self, info):
        """Resolve whether translation has a name."""
        return bool(self.name)
    
    def resolve_has_description(self, info):
        """Resolve whether translation has a description."""
        return bool(self.description)
    
    def resolve_description_plaintext(self, info):
        """Resolve plain text version of description."""
        if self.description:
            try:
                import json
                if isinstance(self.description, dict):
                    blocks = self.description.get('blocks', [])
                    texts = []
                    for block in blocks:
                        if block.get('type') == 'paragraph':
                            data = block.get('data', {})
                            if data.get('text'):
                                texts.append(data['text'])
                    return ' '.join(texts)
            except:
                pass
        return None
    
    def resolve_product_details(self, info):
        """Resolve parent product."""
        return self.product


class ProductNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product with full product management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    has_variants = Boolean(description="Whether product has variants")
    is_in_stock = Boolean(description="Whether product is in stock")
    is_available = Boolean(description="Whether product is available for purchase")
    has_media = Boolean(description="Whether product has media")
    has_reviews = Boolean(description="Whether product has reviews")
    average_rating = Float(description="Average rating")
    review_count = Int(description="Number of reviews")
    main_image_url = String(description="URL of the main product image")
    
    # Display fields
    description_plaintext = String(description="Plain text version of description")
    weight_display = String(description="Formatted weight")
    
    class Meta:
        model = Product
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = { 
            # Foreign keys
            'product_type': ['exact'],
            'category': ['exact'],
            'tax_class': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            
            # Numeric fields
            'rating': ['exact', 'gte', 'lte', 'isnull'],
            'flash_sale_price': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_featured': ['exact'],
            'is_flash_sale': ['exact'],
            
            # SEO fields
            'seo_title': ['exact', 'icontains'],
            'seo_description': ['exact', 'icontains'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_has_variants(self, info):
        """Resolve whether product has variants."""
        return self.variants.exists()
    
    def resolve_is_in_stock(self, info):
        """Resolve whether product is in stock."""
        from ecommerce.models.warehouse import Stock
        if self.variants.exists():
            return any(variant.stocks.aggregate(total=models.Sum('quantity'))['total'] or 0 > 0 for variant in self.variants.all())
        return False
    
    def resolve_is_available(self, info):
        """Resolve whether product is available for purchase."""
        return self.channel_listings.filter(
            is_published=True,
            available_for_purchase_at__lte=timezone.now()
        ).exists()
    
    def resolve_has_media(self, info):
        """Resolve whether product has media."""
        return self.media.exists()
    
    def resolve_has_reviews(self, info):
        """Resolve whether product has reviews."""
        return self.reviews.exists()
    
    def resolve_average_rating(self, info):
        """Resolve average rating."""
        return self.reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
    
    def resolve_review_count(self, info):
        """Resolve number of reviews."""
        return self.reviews.count()
    
    def resolve_main_image_url(self, info):
        """Resolve URL of the main product image."""
        first_image = self.get_first_image()
        if first_image and first_image.image:
            return first_image.image.url
        return None
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_description_plaintext(self, info):
        """Resolve plain text version of description."""
        if self.description:
            try:
                import json
                if isinstance(self.description, dict):
                    blocks = self.description.get('blocks', [])
                    texts = []
                    for block in blocks:
                        if block.get('type') == 'paragraph':
                            data = block.get('data', {})
                            if data.get('text'):
                                texts.append(data['text'])
                    return ' '.join(texts)
            except:
                pass
        return None
    
    def resolve_weight_display(self, info):
        """Resolve formatted weight."""
        if self.weight:
            return f"{self.weight.value} {self.weight.unit}"
        return None
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_product_type_details(self, info):
        """Resolve product type details."""
        return self.product_type
    
    def resolve_category_details(self, info):
        """Resolve category details."""
        return self.category
    
    def resolve_default_variant_details(self, info):
        """Resolve default variant."""
        return self.default_variant
    
    def resolve_tax_class_details(self, info):
        """Resolve tax class details."""
        return self.tax_class
    
    def resolve_variants(self, info):
        """Resolve product variants."""
        return self.variants.all()
    
    def resolve_channel_listings(self, info):
        """Resolve channel listings."""
        return self.channel_listings.all()
    
    def resolve_reviews(self, info):
        """Resolve product reviews."""
        return self.reviews.all()
    
    def resolve_translations(self, info):
        """Resolve product translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve product translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()
    
    def resolve_media(self, info):
        """Resolve product media."""
        return self.media.all()


class ProductVariantTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Variant Translation.
    """
    
    class Meta:
        model = ProductVariantTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'product_variant': ['exact'],
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
        }
        
    


class ProductVariantChannelListingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Variant Channel Listing.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
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
            'variant': ['exact'],
            'channel': ['exact'],
            'currency': ['exact'],
            'price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'cost_price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'discounted_price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'preorder_quantity_threshold': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_price_display(self, info):
        """Resolve formatted price."""
        if self.price_amount:
            return f"{self.price_amount:.2f} {self.currency}"
        return None
    
    def resolve_cost_price_display(self, info):
        """Resolve formatted cost price."""
        if self.cost_price_amount:
            return f"{self.cost_price_amount:.2f} {self.currency}"
        return None
    
    def resolve_discounted_price_display(self, info):
        """Resolve formatted discounted price."""
        if self.discounted_price_amount:
            return f"{self.discounted_price_amount:.2f} {self.currency}"
        return None
    
    def resolve_has_discount(self, info):
        """Resolve whether variant has a discount in this channel."""
        return (
            self.discounted_price_amount is not None and
            self.price_amount is not None and
            self.discounted_price_amount < self.price_amount
        )
    
    def resolve_discount_percentage(self, info):
        """Resolve discount percentage."""
        if self.has_discount and self.price_amount > 0:
            return ((self.price_amount - self.discounted_price_amount) / self.price_amount) * 100
        return 0
    
    def resolve_margin(self, info):
        """Resolve profit margin percentage."""
        if self.price_amount and self.cost_price_amount and self.cost_price_amount > 0:
            return ((self.price_amount - self.cost_price_amount) / self.price_amount) * 100
        return 0
    
    def resolve_variant_details(self, info):
        """Resolve variant details."""
        return self.variant
    
    def resolve_channel_details(self, info):
        """Resolve channel details."""
        return self.channel
    
    def resolve_promotion_rules(self, info):
        """Resolve promotion rules."""
        return self.promotion_rules.all()


class VariantChannelListingPromotionRuleNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Variant Channel Listing Promotion Rule.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    discount_display = String(description="Formatted discount")
    
    class Meta:
        model = VariantChannelListingPromotionRule
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'variant_channel_listing': ['exact'],
            'promotion_rule': ['exact'],
            'currency': ['exact'],
            'discount_amount': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_discount_display(self, info):
        """Resolve formatted discount."""
        if self.discount_amount:
            return f"{self.discount_amount:.2f} {self.currency}"
        return None
    
    def resolve_variant_channel_listing_details(self, info):
        """Resolve variant channel listing details."""
        return self.variant_channel_listing
    
    def resolve_promotion_rule_details(self, info):
        """Resolve promotion rule details."""
        return self.promotion_rule


class ProductVariantNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Variant with full variant management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_shipping_required = Boolean(description="Whether variant requires shipping")
    is_gift_card = Boolean(description="Whether variant is a gift card")
    is_digital = Boolean(description="Whether variant is digital")
    is_preorder_active = Boolean(description="Whether preorder is active")
    has_stock = Boolean(description="Whether variant has stock")
    total_stock = Int(description="Total stock across all warehouses")
    
    # Display fields
    display_product = String(description="Display name with product")
    weight_display = String(description="Formatted weight")
    display_name = String(description="Display name")
    
    
    class Meta:
        model = ProductVariant
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'product': ['exact'],
            
            # String fields
            'sku': ['exact', 'icontains'],
            'name': ['exact', 'icontains'],
            
            # Boolean fields
            'track_inventory': ['exact'],
            'is_preorder': ['exact'],
            
            # Numeric fields
            'preorder_global_threshold': ['exact', 'gte', 'lte', 'isnull'],
            'quantity_limit_per_customer': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'preorder_end_date': ['exact', 'gte', 'lte', 'isnull'],
        }
    
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_shipping_required(self, info):
        """Resolve whether variant requires shipping."""
        return self.is_shipping_required()
    
    def resolve_is_gift_card(self, info):
        """Resolve whether variant is a gift card."""
        return self.is_gift_card()
    
    def resolve_is_digital(self, info):
        """Resolve whether variant is digital."""
        return self.is_digital()
    
    def resolve_is_preorder_active(self, info):
        """Resolve whether preorder is active."""
        return self.is_preorder_active()
    
    def resolve_has_stock(self, info):
        """Resolve whether variant has stock."""
        from ecommerce.models.warehouse import Stock
        return Stock.objects.filter(product_variant=self, quantity__gt=0).exists()
    
    def resolve_total_stock(self, info):
        """Resolve total stock across all warehouses."""
        from ecommerce.models.warehouse import Stock
        return Stock.objects.filter(product_variant=self).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_display_product(self, info):
        """Resolve display name with product."""
        return self.display_product()
    
    def resolve_weight_display(self, info):
        """Resolve formatted weight."""
        weight = self.get_weight()
        if weight:
            return f"{weight.value} {weight.unit}"
        return None
    
    def resolve_display_name(self, info):
        """Resolve display name."""
        return str(self)
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product
    
    def resolve_channel_listings(self, info):
        """Resolve channel listings."""
        return self.channel_listings.all()
    
    def resolve_translations(self, info):
        """Resolve variant translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve variant translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()
    
    def resolve_digital_content_details(self, info):
        """Resolve digital content details."""
        return getattr(self, 'digital_content', None)
    
    def resolve_media(self, info):
        """Resolve variant media."""
        return self.media.all()
    
    def resolve_stocks(self, info):
        """Resolve stock information."""
        from ecommerce.models.warehouse import Stock
        return Stock.objects.filter(product_variant=self)


class DigitalContentNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Digital Content.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    content_type_display = String(description="Human-readable content type display")
    has_file = Boolean(description="Whether content has a file")
     
    class Meta:
        model = DigitalContent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'product_variant': ['exact'],
            'use_default_settings': ['exact'],
            'automatic_fulfillment': ['exact'],
            'content_type': ['exact'],
            'max_downloads': ['exact', 'gte', 'lte', 'isnull'],
            'url_valid_days': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_content_type_display(self, info):
        """Resolve human-readable content type display."""
        return dict(DigitalContent.TYPE_CHOICES).get(self.content_type, self.content_type)
    
    def resolve_has_file(self, info):
        """Resolve whether content has a file."""
        return bool(self.content_file)
    
    def resolve_product_variant_details(self, info):
        """Resolve product variant details."""
        return self.product_variant
    
    def resolve_urls(self, info):
        """Resolve digital content URLs."""
        return self.urls.all()


class DigitalContentUrlNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Digital Content URL.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_expired = Boolean(description="Whether URL is expired")
    absolute_url = String(description="Absolute URL to download")
    can_download = Boolean(description="Whether download is allowed")
    
    class Meta:
        model = DigitalContentUrl
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'content': ['exact'],
            'line': ['exact'],
            'token': ['exact'],
            'download_num': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_is_expired(self, info):
        """Resolve whether URL is expired."""
        if self.content and self.content.url_valid_days:
            expiry = self.created_at + timezone.timedelta(days=self.content.url_valid_days)
            return timezone.now() > expiry
        return False
    
    def resolve_absolute_url(self, info):
        """Resolve absolute URL to download."""
        try:
            return self.get_absolute_url()
        except:
            return None
    
    def resolve_can_download(self, info):
        """Resolve whether download is allowed."""
        if self.is_expired:
            return False
        if self.content and self.content.max_downloads:
            return self.download_num < self.content.max_downloads
        return True
    
    def resolve_content_details(self, info):
        """Resolve digital content details."""
        return self.content
    
    def resolve_line_details(self, info):
        """Resolve order line details."""
        return self.line


class ProductMediaNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Product Media.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
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
            'product': ['exact'],
            'alt': ['exact', 'icontains'],
            'type': ['exact'],
        }
        
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(ProductMediaTypes.CHOICES).get(self.type, self.type)
    
    def resolve_image_url(self, info):
        """Resolve URL of the image."""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return None
    
    def resolve_is_image(self, info):
        """Resolve whether media is an image."""
        return self.type == ProductMediaTypes.IMAGE
    
    def resolve_is_video(self, info):
        """Resolve whether media is a video."""
        return self.type == ProductMediaTypes.VIDEO
    
    def resolve_is_external(self, info):
        """Resolve whether media is external."""
        return bool(self.external_url)
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product
    
    def resolve_variant_media(self, info):
        """Resolve variant media associations."""
        return self.variant_media.all()


class VariantMediaNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Variant Media.
    """
    class Meta:
        model = VariantMedia
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'variant': ['exact'],
            'media': ['exact'],
        }
       


