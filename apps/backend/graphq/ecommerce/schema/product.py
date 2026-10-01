import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.utils import timezone

from graphq.ecommerce.types.product import (
    ProductTypeNode,
    ProductNode,
    ProductVariantNode,
    ProductChannelListingNode,
    ProductReviewNode,
    ProductTranslationNode,
    ProductVariantTranslationNode,
    ProductVariantChannelListingNode,
    VariantChannelListingPromotionRuleNode,
    DigitalContentNode,
    DigitalContentUrlNode,
    ProductMediaNode,
    VariantMediaNode,
)

# =============================================================================
# Schema Registration
# =============================================================================

# In your schema.py, you would register these nodes:

class ProductQuery(graphene.ObjectType):
    # Node queries
    product_type = Node.Field(ProductTypeNode)
    all_product_types = DjangoFilterConnectionField(ProductTypeNode)
    product = Node.Field(ProductNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    product_variant = Node.Field(ProductVariantNode)
    all_product_variants = DjangoFilterConnectionField(ProductVariantNode)
    product_channel_listing = Node.Field(ProductChannelListingNode)
    product_review = Node.Field(ProductReviewNode)
    product_translation = Node.Field(ProductTranslationNode)
    product_variant_translation = Node.Field(ProductVariantTranslationNode)
    product_variant_channel_listing = Node.Field(ProductVariantChannelListingNode)
    variant_channel_listing_promotion_rule = Node.Field(VariantChannelListingPromotionRuleNode)
    product_variant = Node.Field(ProductVariantNode)
    digital_content = Node.Field(DigitalContentNode)
    digital_content_url = Node.Field(DigitalContentUrlNode)
    product_media= Node.Field(ProductMediaNode)
    variant_media= Node.Field(VariantMediaNode) 
    
    all_product_channel_listing = DjangoFilterConnectionField(ProductChannelListingNode)
    all_product_review = DjangoFilterConnectionField(ProductReviewNode)
    all_product_translation = DjangoFilterConnectionField(ProductTranslationNode)
    all_product_variant_translation = DjangoFilterConnectionField(ProductVariantTranslationNode)
    all_product_variant_channel_listing = DjangoFilterConnectionField(ProductVariantChannelListingNode)
    all_variant_channel_listing_promotion_rule = DjangoFilterConnectionField(VariantChannelListingPromotionRuleNode)
    all_product_variant = DjangoFilterConnectionField(ProductVariantNode)
    all_digital_content = DjangoFilterConnectionField(DigitalContentNode)
    all_digital_content_url = DjangoFilterConnectionField(DigitalContentUrlNode)
    all_product_media= DjangoFilterConnectionField(ProductMediaNode)
    all_variant_media= DjangoFilterConnectionField(VariantMediaNode)