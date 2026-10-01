import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.discount import ( 
    VoucherNode,
    PromotionEventNode,
    VoucherCustomerNode,
    VoucherChannelListingNode,
    VoucherCodeNode,
    PromotionRuleNode,
    PromotionNode,
    PromotionTranslationNode,
    OrderDiscountNode,
    OrderLineDiscountNode,
    CheckoutDiscountNode,
    CheckoutLineDiscountNode,
)


       
# =============================================================================
# Schema Registration
# =============================================================================


class DiscountQuery(graphene.ObjectType):
    # Node queries
    order_discount = Node.Field(OrderDiscountNode)
    all_order_discounts = DjangoFilterConnectionField(OrderDiscountNode)
    order_line_discount = Node.Field(OrderLineDiscountNode)
    all_order_line_discounts = DjangoFilterConnectionField(OrderLineDiscountNode)
    checkout_discount = Node.Field(CheckoutDiscountNode)
    all_checkout_discounts = DjangoFilterConnectionField(CheckoutDiscountNode)
    checkout_line_discount = Node.Field(CheckoutLineDiscountNode)
    all_checkout_line_discounts = DjangoFilterConnectionField(CheckoutLineDiscountNode)
    promotion_event = Node.Field(PromotionEventNode)
    all_promotion_events = DjangoFilterConnectionField(PromotionEventNode)
    promotion = Node.Field(PromotionNode)
    all_promotions = DjangoFilterConnectionField(PromotionNode)
    promotion_rule = Node.Field(PromotionRuleNode)
    all_promotion_rules = DjangoFilterConnectionField(PromotionRuleNode)
    promotion_translation = Node.Field(PromotionTranslationNode)
    all_promotion_translations = DjangoFilterConnectionField(PromotionTranslationNode)
    voucher = Node.Field(VoucherNode)
    all_vouchers = DjangoFilterConnectionField(VoucherNode)
    voucher_code = Node.Field(VoucherCodeNode) 
    all_voucher_codes = DjangoFilterConnectionField(VoucherCodeNode)
    voucher_channel_listing = Node.Field(VoucherChannelListingNode)
    all_voucher_channel_listings = DjangoFilterConnectionField(VoucherChannelListingNode)