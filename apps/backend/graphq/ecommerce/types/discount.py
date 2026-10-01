# graphql/ecommerce/types/voucher.py
"""
GraphQL Nodes for Voucher, VoucherCode, VoucherChannelListing, VoucherCustomer, and VoucherTranslation.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.discount import (
    Voucher,
    VoucherCode,
    VoucherChannelListing,
    VoucherCustomer,
    VoucherTranslation,
    PromotionRule_Variants,
    PromotionTranslation,
    CheckoutDiscount, 
    CheckoutLineDiscount, 
    OrderDiscount,
    Promotion, 
    PromotionEvent, 
    PromotionRule,
    PromotionRuleTranslation,
    OrderLineDiscount
)


class VoucherCodeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Voucher Code.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_used = Boolean(description="Whether this code has been used")
    has_remaining_uses = Boolean(description="Whether this code has remaining uses")
    remaining_uses = Int(description="Number of remaining uses")
    code_display = String(description="Formatted code for display")
    
    class Meta:
        model = VoucherCode
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'voucher': ['exact'],
            
            # String fields
            'code': ['exact', 'icontains', 'istartswith'],
            
            # Numeric fields
            'used': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_is_used(self, info):
        """Resolve whether this code has been used."""
        return self.used > 0
    
    def resolve_has_remaining_uses(self, info):
        """Resolve whether this code has remaining uses."""
        if self.voucher and self.voucher.usage_limit:
            return self.used < self.voucher.usage_limit
        return True
    
    def resolve_remaining_uses(self, info):
        """Resolve number of remaining uses."""
        if self.voucher and self.voucher.usage_limit:
            return max(0, self.voucher.usage_limit - self.used)
        return None
    
    def resolve_code_display(self, info):
        """Resolve formatted code for display."""
        return self.code.upper() if self.code else None
    
    


class VoucherChannelListingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Voucher Channel Listing.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    discount_display = String(description="Formatted discount value")
    min_spent_display = String(description="Formatted minimum spend value")
    is_valid_for_channel = Boolean(description="Whether voucher is valid for this channel")
    
    
    class Meta:
        model = VoucherChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'voucher': ['exact'],
            'channel': ['exact'],
            
            # Numeric fields
            'discount_value': ['exact', 'gte', 'lte'],
            'currency': ['exact'],
            'min_spent_amount': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_active': ['exact'],
        }
    
    
    def resolve_discount_display(self, info):
        """Resolve formatted discount value."""
        if self.discount_value:
            return f"{self.discount_value:.2f} {self.currency}"
        return None
    
    def resolve_min_spent_display(self, info):
        """Resolve formatted minimum spend value."""
        if self.min_spent_amount:
            return f"{self.min_spent_amount:.2f} {self.currency}"
        return None
    
    def resolve_is_valid_for_channel(self, info):
        """Resolve whether voucher is valid for this channel."""
        return self.is_active and self.voucher.is_active if hasattr(self.voucher, 'is_active') else self.is_active
    
   


class VoucherCustomerNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Voucher Customer.
    """
    class Meta:
        model = VoucherCustomer
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'voucher_code': ['exact'],
            
            # String fields
            'customer_email': ['exact', 'icontains'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        


class VoucherTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Voucher Translation.
    """
    class Meta:
        model = VoucherTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'voucher': ['exact'],
            
            # String fields
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
        }
        
    
    


class VoucherNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Voucher with full voucher management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_valid = Boolean(description="Whether voucher is currently valid")
    is_expired = Boolean(description="Whether voucher has expired")
    is_upcoming = Boolean(description="Whether voucher is upcoming (not started yet)")
    has_usage_limit = Boolean(description="Whether voucher has a usage limit")
    has_codes = Boolean(description="Whether voucher has codes")
    code_count = Int(description="Number of codes")
    total_uses = Int(description="Total number of uses across all codes")
    remaining_uses = Int(description="Total remaining uses across all codes")
    
    # Display fields
    type_display = String(description="Human-readable type display")
    discount_value_type_display = String(description="Human-readable discount value type display")
    code_display = String(description="Latest code for display")
    promo_codes = List(String, description="All promo codes")
    status = String(description="Current status (active, expired, upcoming)")
    discount_summary = String(description="Summary of discount")
    
   
    
    class Meta:
        model = Voucher
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'type': ['exact'],
            'discount_value_type': ['exact'],
            
            # Numeric fields
            'usage_limit': ['exact', 'gte', 'lte', 'isnull'],
            'min_checkout_items_quantity': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_active': ['exact'],
            'apply_once_per_order': ['exact'],
            'apply_once_per_customer': ['exact'],
            'single_use': ['exact'],
            'only_for_staff': ['exact'],
            
            # Date fields
            'start_date': ['exact', 'gte', 'lte'],
            'end_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Foreign keys
            'created_by': ['exact'],
            'created_by__email': ['exact', 'icontains'],
        }
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_valid(self, info):
        """Resolve whether voucher is currently valid."""
        now = timezone.now()
        return all([
            self.is_active,
            self.start_date <= now,
            self.end_date is None or self.end_date >= now,
            not self.is_expired,
        ])
    
    def resolve_is_expired(self, info):
        """Resolve whether voucher has expired."""
        if self.end_date:
            return timezone.now() > self.end_date
        return False
    
    def resolve_is_upcoming(self, info):
        """Resolve whether voucher is upcoming (not started yet)."""
        return self.start_date > timezone.now() if self.start_date else False
    
    def resolve_has_usage_limit(self, info):
        """Resolve whether voucher has a usage limit."""
        return self.usage_limit is not None
    
    def resolve_has_codes(self, info):
        """Resolve whether voucher has codes."""
        return self.codes.exists()
    
    def resolve_code_count(self, info):
        """Resolve number of codes."""
        return self.codes.count()
    
    def resolve_total_uses(self, info):
        """Resolve total number of uses across all codes."""
        return self.codes.aggregate(total=models.Sum('used'))['total'] or 0
    
    def resolve_remaining_uses(self, info):
        """Resolve total remaining uses across all codes."""
        if self.usage_limit:
            return max(0, self.usage_limit - self.resolve_total_uses(info))
        return None
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(VoucherType.CHOICES).get(self.type, self.type)
    
    def resolve_discount_value_type_display(self, info):
        """Resolve human-readable discount value type display."""
        return dict(DiscountValueType.CHOICES).get(self.discount_value_type, self.discount_value_type)
    
    def resolve_code_display(self, info):
        """Resolve latest code for display."""
        return self.code
    
    def resolve_promo_codes(self, info):
        """Resolve all promo codes."""
        return self.promo_codes
    
    def resolve_status(self, info):
        """Resolve current status (active, expired, upcoming)."""
        if self.is_expired:
            return "expired"
        if self.is_upcoming:
            return "upcoming"
        if self.is_valid:
            return "active"
        return "inactive"
    
    def resolve_discount_summary(self, info):
        """Resolve summary of discount."""
        if self.discount_value_type == DiscountValueType.FIXED:
            channel_listing = self.channel_listings.first()
            if channel_listing:
                return f"{channel_listing.discount_value:.2f} {channel_listing.currency} off"
            return f"Fixed discount"
        elif self.discount_value_type == DiscountValueType.PERCENTAGE:
            channel_listing = self.channel_listings.first()
            if channel_listing:
                return f"{channel_listing.discount_value:.0f}% off"
            return f"Percentage discount"
        return "Unknown discount type"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this voucher."""
        return self.created_by
    
    def resolve_codes(self, info):
        """Resolve voucher codes."""
        return self.codes.all().order_by('-created_at')
    
    def resolve_channel_listings(self, info):
        """Resolve channel listings."""
        return self.channel_listings.all()
    
    def resolve_translations(self, info):
        """Resolve voucher translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve voucher translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()
   

class PromotionRuleVariantsNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for PromotionRule_Variants (through model).
    """
    

    class Meta:
        model = PromotionRule_Variants
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'promotionrule': ['exact'],
            'productvariant': ['exact'],
        }

    
   


class PromotionTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promotion Translation.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    has_name = Boolean(description="Whether translation has a name")
    has_description = Boolean(description="Whether translation has a description")
    description_plaintext = String(description="Plain text version of description")
    
    
    class Meta:
        model = PromotionTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'promotion': ['exact'],
            
            # String fields
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
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
    
    def resolve_promotion_details(self, info):
        """Resolve parent promotion."""
        return self.promotion


class PromotionRuleTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promotion Rule Translation.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    has_name = Boolean(description="Whether translation has a name")
    has_description = Boolean(description="Whether translation has a description")
    

    class Meta:
        model = PromotionRuleTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'promotion_rule': ['exact'],
            
            # String fields
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
            'description': ['exact', 'icontains'],
        }
    
    def resolve_has_name(self, info):
        """Resolve whether translation has a name."""
        return bool(self.name)
    
    def resolve_has_description(self, info):
        """Resolve whether translation has a description."""
        return bool(self.description)
    


class PromotionRuleNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promotion Rule with full rule configuration.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_valid = Boolean(description="Whether rule is currently valid")
    has_catalogue_predicate = Boolean(description="Whether rule has catalogue predicate")
    has_order_predicate = Boolean(description="Whether rule has order predicate")
    has_reward = Boolean(description="Whether rule has a reward configured")
    is_gift_reward = Boolean(description="Whether rule rewards with gifts")
    is_fixed_discount = Boolean(description="Whether rule gives fixed discount")
    is_percentage_discount = Boolean(description="Whether rule gives percentage discount")
    
    # Display fields
    reward_value_type_display = String(description="Human-readable reward value type display")
    reward_type_display = String(description="Human-readable reward type display")
    reward_summary = String(description="Summary of the reward")
    status = String(description="Current status (active, inactive)")
    channel_count = Int(description="Number of channels this rule applies to")
     
    
    class Meta:
        model = PromotionRule
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
           
            # Foreign keys
            'promotion': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'reward_value_type': ['exact'],
            'reward_type': ['exact'],
            
            # Numeric fields
            'reward_value': ['exact', 'gte', 'lte', 'isnull'],
            'priority': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            'variants_dirty': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_valid(self, info):
        """Resolve whether rule is currently valid."""
        return self.is_active and self.promotion.is_currently_active() if hasattr(self.promotion, 'is_currently_active') else self.is_active
    
    def resolve_has_catalogue_predicate(self, info):
        """Resolve whether rule has catalogue predicate."""
        return bool(self.catalogue_predicate)
    
    def resolve_has_order_predicate(self, info):
        """Resolve whether rule has order predicate."""
        return bool(self.order_predicate)
    
    def resolve_has_reward(self, info):
        """Resolve whether rule has a reward configured."""
        return any([
            self.reward_value is not None,
            self.reward_value_type is not None,
            self.reward_type is not None,
            self.gifts.exists(),
        ])
    
    def resolve_is_gift_reward(self, info):
        """Resolve whether rule rewards with gifts."""
        return self.reward_type == RewardType.GIFT if hasattr(self, 'reward_type') else False
    
    def resolve_is_fixed_discount(self, info):
        """Resolve whether rule gives fixed discount."""
        return self.reward_value_type == RewardValueType.FIXED if hasattr(self, 'reward_value_type') else False
    
    def resolve_is_percentage_discount(self, info):
        """Resolve whether rule gives percentage discount."""
        return self.reward_value_type == RewardValueType.PERCENTAGE if hasattr(self, 'reward_value_type') else False
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_reward_value_type_display(self, info):
        """Resolve human-readable reward value type display."""
        if self.reward_value_type:
            return dict(RewardValueType.CHOICES).get(self.reward_value_type, self.reward_value_type)
        return None
    
    def resolve_reward_type_display(self, info):
        """Resolve human-readable reward type display."""
        if self.reward_type:
            return dict(RewardType.CHOICES).get(self.reward_type, self.reward_type)
        return None
    
    def resolve_reward_summary(self, info):
        """Resolve summary of the reward."""
        if self.is_gift_reward:
            gift_count = self.gifts.count()
            return f"{gift_count} gift item(s)"
        elif self.reward_value_type == RewardValueType.FIXED:
            return f"{self.reward_value:.2f} off"
        elif self.reward_value_type == RewardValueType.PERCENTAGE:
            return f"{self.reward_value:.0f}% off"
        return "No reward configured"
    
    def resolve_status(self, info):
        """Resolve current status (active, inactive)."""
        return "active" if self.is_active else "inactive"
    
    def resolve_channel_count(self, info):
        """Resolve number of channels this rule applies to."""
        return self.channels.count()
    
    

class PromotionNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promotion with full promotion management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_currently_active = Boolean(description="Whether promotion is currently active")
    is_expired = Boolean(description="Whether promotion has expired")
    is_upcoming = Boolean(description="Whether promotion is upcoming (not started yet)")
    has_rules = Boolean(description="Whether promotion has rules")
    rule_count = Int(description="Number of rules")
    active_rule_count = Int(description="Number of active rules")
    
    # Display fields
    type_display = String(description="Human-readable type display")
    status = String(description="Current status (active, expired, upcoming)")
    description_plaintext = String(description="Plain text version of description")
    channel_coverage = List(String, description="List of channel slugs this promotion covers")
    
    
    class Meta:
        model = Promotion
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'type': ['exact'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Numeric fields
            'old_sale_id': ['exact', 'isnull'],
            
            # Date fields
            'start_date': ['exact', 'gte', 'lte'],
            'end_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'last_notification_scheduled_at': ['exact', 'gte', 'lte', 'isnull'],
            
            # Foreign keys
            'created_by': ['exact'],
            'created_by__email': ['exact', 'icontains'],
        }
       
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_currently_active(self, info):
        """Resolve whether promotion is currently active."""
        if hasattr(self, 'is_currently_active'):
            return self.is_currently_active()
        now = timezone.now()
        return all([
            self.is_active,
            self.start_date <= now,
            self.end_date is None or self.end_date >= now,
        ])
    
    def resolve_is_expired(self, info):
        """Resolve whether promotion has expired."""
        if self.end_date:
            return timezone.now() > self.end_date
        return False
    
    def resolve_is_upcoming(self, info):
        """Resolve whether promotion is upcoming (not started yet)."""
        return self.start_date > timezone.now() if self.start_date else False
    
    def resolve_has_rules(self, info):
        """Resolve whether promotion has rules."""
        return self.rules.exists()
    
    def resolve_rule_count(self, info):
        """Resolve number of rules."""
        return self.rules.count()
    
    def resolve_active_rule_count(self, info):
        """Resolve number of active rules."""
        return self.rules.filter(is_active=True).count()
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(PromotionType.CHOICES).get(self.type, self.type)
    
    def resolve_status(self, info):
        """Resolve current status (active, expired, upcoming)."""
        if self.is_expired:
            return "expired"
        if self.is_upcoming:
            return "upcoming"
        if self.is_currently_active:
            return "active"
        return "inactive"
    
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
    
    def resolve_channel_coverage(self, info):
        """Resolve list of channel slugs this promotion covers."""
        channels = set()
        for rule in self.rules.all():
            for channel in rule.channels.all():
                channels.add(channel.slug)
        return list(channels)
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this promotion."""
        return self.created_by
    
    def resolve_rules(self, info):
        """Resolve promotion rules."""
        return self.rules.all().order_by('-priority', 'name')
    
    def resolve_active_rules(self, info):
        """Resolve active promotion rules."""
        return self.rules.filter(is_active=True).order_by('-priority', 'name')
    
    def resolve_translations(self, info):
        """Resolve promotion translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve promotion translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()


class BaseDiscountNodeMixin:
    """Mixin with common discount fields and resolvers."""
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    type_display = String(description="Human-readable type display")
    value_type_display = String(description="Human-readable value type display")
    amount_display = String(description="Formatted amount")
    discount_summary = String(description="Summary of the discount")
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        if self.type:
            return dict(DiscountType.CHOICES).get(self.type, self.type)
        return None
    
    def resolve_value_type_display(self, info):
        """Resolve human-readable value type display."""
        if self.value_type:
            return dict(DiscountValueType.CHOICES).get(self.value_type, self.value_type)
        return None
    
    def resolve_amount_display(self, info):
        """Resolve formatted amount."""
        if self.amount_value:
            return f"{self.amount_value:.2f} {self.currency}"
        return None
    
    def resolve_discount_summary(self, info):
        """Resolve summary of the discount."""
        if self.value_type == DiscountValueType.FIXED:
            return f"{self.value:.2f} {self.currency} off"
        elif self.value_type == DiscountValueType.PERCENTAGE:
            return f"{self.value:.0f}% off"
        return "Unknown discount"


class OrderDiscountNode(OptimizedDjangoObjectType, BaseDiscountNodeMixin):
    """
    GraphQL Node for Order Discount.
    """
    class Meta:
        model = OrderDiscount
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            'promotion_rule': ['exact'],
            'voucher': ['exact'],
            
            # String fields
            'type': ['exact'],
            'value_type': ['exact'],
            'name': ['exact', 'icontains'],
            'translated_name': ['exact', 'icontains'],
            'voucher_code': ['exact', 'icontains'],
            'currency': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Numeric fields
            'value': ['exact', 'gte', 'lte'],
            'amount_value': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_promotion_rule_details(self, info):
        """Resolve promotion rule details."""
        return self.promotion_rule
    
    def resolve_voucher_details(self, info):
        """Resolve voucher details."""
        return self.voucher


class OrderLineDiscountNode(OptimizedDjangoObjectType, BaseDiscountNodeMixin):
    """
    GraphQL Node for Order Line Discount.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    unique_type_display = String(description="Human-readable unique type display")
    
    
    class Meta:
        model = OrderLineDiscount
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'line': ['exact'],
            'promotion_rule': ['exact'],
            'voucher': ['exact'],
            
            # String fields
            'type': ['exact'],
            'value_type': ['exact'],
            'unique_type': ['exact'],
            'name': ['exact', 'icontains'],
            'translated_name': ['exact', 'icontains'],
            'voucher_code': ['exact', 'icontains'],
            'currency': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Numeric fields
            'value': ['exact', 'gte', 'lte'],
            'amount_value': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_unique_type_display(self, info):
        """Resolve human-readable unique type display."""
        if self.unique_type:
            return dict(DiscountType.CHOICES).get(self.unique_type, self.unique_type)
        return None
    
    def resolve_line_details(self, info):
        """Resolve order line details."""
        return self.line
    
    def resolve_promotion_rule_details(self, info):
        """Resolve promotion rule details."""
        return self.promotion_rule
    
    def resolve_voucher_details(self, info):
        """Resolve voucher details."""
        return self.voucher


class CheckoutDiscountNode(OptimizedDjangoObjectType, BaseDiscountNodeMixin):
    """
    GraphQL Node for Checkout Discount.
    """
    
    class Meta:
        model = CheckoutDiscount
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'checkout': ['exact'],
            'promotion_rule': ['exact'],
            'voucher': ['exact'],
            
            # String fields
            'type': ['exact'],
            'value_type': ['exact'],
            'name': ['exact', 'icontains'],
            'translated_name': ['exact', 'icontains'],
            'voucher_code': ['exact', 'icontains'],
            'currency': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Numeric fields
            'value': ['exact', 'gte', 'lte'],
            'amount_value': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_checkout_details(self, info):
        """Resolve checkout details."""
        return self.checkout
    
    def resolve_promotion_rule_details(self, info):
        """Resolve promotion rule details."""
        return self.promotion_rule
    
    def resolve_voucher_details(self, info):
        """Resolve voucher details."""
        return self.voucher


class CheckoutLineDiscountNode(OptimizedDjangoObjectType, BaseDiscountNodeMixin):
    """
    GraphQL Node for Checkout Line Discount.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    unique_type_display = String(description="Human-readable unique type display")
    
    class Meta:
        model = CheckoutLineDiscount
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'line': ['exact'],
            'promotion_rule': ['exact'],
            'voucher': ['exact'],
            
            # String fields
            'type': ['exact'],
            'value_type': ['exact'],
            'unique_type': ['exact'],
            'name': ['exact', 'icontains'],
            'translated_name': ['exact', 'icontains'],
            'voucher_code': ['exact', 'icontains'],
            'currency': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Numeric fields
            'value': ['exact', 'gte', 'lte'],
            'amount_value': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_unique_type_display(self, info):
        """Resolve human-readable unique type display."""
        if self.unique_type:
            return dict(DiscountType.CHOICES).get(self.unique_type, self.unique_type)
        return None
    
    def resolve_line_details(self, info):
        """Resolve checkout line details."""
        return self.line
    
    def resolve_promotion_rule_details(self, info):
        """Resolve promotion rule details."""
        return self.promotion_rule
    
    def resolve_voucher_details(self, info):
        """Resolve voucher details."""
        return self.voucher


class PromotionEventNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promotion Event.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    type_display = String(description="Human-readable type display")
    event_summary = String(description="Summary of the event")
    

    class Meta:
        model = PromotionEvent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'promotion': ['exact'],
            'user': ['exact'],
            
            # String fields
            'type': ['exact'],
            'ip_address': ['exact', 'icontains'],
            'user_agent': ['exact', 'icontains'],
            
            # Date fields
            'date': ['exact', 'gte', 'lte'],
        }
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(PromotionEvents.CHOICES).get(self.type, self.type)
    
    def resolve_event_summary(self, info):
        """Resolve summary of the event."""
        return f"{self.get_type_display()} - {self.promotion.name}"
    
    def resolve_promotion_details(self, info):
        """Resolve promotion details."""
        return self.promotion
    
    def resolve_user_details(self, info):
        """Resolve user who triggered the event."""
        return self.user

