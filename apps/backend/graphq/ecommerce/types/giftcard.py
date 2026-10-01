# graphql/ecommerce/types/gift_card.py

"""
GraphQL Nodes for GiftCard, GiftCardTag, and GiftCardEvent.
"""

from graphene import Node, String, Boolean,  List, Float, Int, Decimal, UUID, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.giftcard import (
    GiftCard,
    GiftCardTag,
    GiftCardEvent,
)


class GiftCardTagNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Gift Card Tag.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    gift_card_count = Int(description="Number of gift cards with this tag")
    is_active_status = Boolean(description="Whether tag is active")
    
    class Meta:
        model = GiftCardTag
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_gift_card_count(self, info):
        """Resolve number of gift cards with this tag."""
        return self.gift_cards.count()
    
    def resolve_is_active_status(self, info):
        """Resolve whether tag is active."""
        return self.is_active
    
    def resolve_gift_cards(self, info):
        """Resolve gift cards with this tag."""
        return self.gift_cards.all()


class GiftCardEventNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Gift Card Event.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    type_display = String(description="Human-readable type display")
    event_summary = String(description="Summary of the event")
    amount_display = String(description="Formatted amount")
    previous_balance_display = String(description="Formatted previous balance")
    new_balance_display = String(description="Formatted new balance")
    
   
    class Meta:
        model = GiftCardEvent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'gift_card': ['exact'],
            'user': ['exact'],
            'order': ['exact'],
            
            # String fields
            'type': ['exact'],
            'ip_address': ['exact', 'icontains'],
            'user_agent': ['exact', 'icontains'],
            
            # Numeric fields
            'amount': ['exact', 'gte', 'lte', 'isnull'],
            'previous_balance': ['exact', 'gte', 'lte', 'isnull'],
            'new_balance': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'date': ['exact', 'gte', 'lte'],
        }
       
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(GiftCardEvents.CHOICES).get(self.type, self.type)
    
    def resolve_event_summary(self, info):
        """Resolve summary of the event."""
        return f"{self.get_type_display()} - {self.gift_card.display_code}"
    
    def resolve_amount_display(self, info):
        """Resolve formatted amount."""
        if self.amount:
            return f"{self.amount:.2f}"
        return None
    
    def resolve_previous_balance_display(self, info):
        """Resolve formatted previous balance."""
        if self.previous_balance:
            return f"{self.previous_balance:.2f}"
        return None
    
    def resolve_new_balance_display(self, info):
        """Resolve formatted new balance."""
        if self.new_balance:
            return f"{self.new_balance:.2f}"
        return None
    
    def resolve_gift_card_details(self, info):
        """Resolve gift card details."""
        return self.gift_card
    
    def resolve_user_details(self, info):
        """Resolve user who performed the action."""
        return self.user
    
    def resolve_order_details(self, info):
        """Resolve order associated with the event."""
        return self.order


class GiftCardNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Gift Card with full gift card management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_fully_used = Boolean(description="Whether gift card is fully used")
    is_expired = Boolean(description="Whether gift card is expired")
    is_usable = Boolean(description="Whether gift card can be used")
    is_active_status = Boolean(description="Whether gift card is active")
    has_expiry_date = Boolean(description="Whether gift card has expiry date")
    days_until_expiry = Int(description="Days until expiry")
    
    # Display fields
    display_code = String(description="Display only the last 4 characters")
    status_display = String(description="Human-readable status display")
    initial_balance_display = String(description="Formatted initial balance")
    current_balance_display = String(description="Formatted current balance")
    used_amount = Decimal(description="Amount used from the gift card")
    usage_percentage = Float(description="Percentage of balance used")
    
   
    class Meta:
        model = GiftCard
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'code': ['exact', 'icontains', 'istartswith'],
            'currency': ['exact'],
            'status': ['exact'],
            'created_by_email': ['exact', 'icontains'],
            'used_by_email': ['exact', 'icontains'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Numeric fields
            'initial_balance_amount': ['exact', 'gte', 'lte'],
            'current_balance_amount': ['exact', 'gte', 'lte'],
            
            # Date fields
            'expiry_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'last_used_on': ['exact', 'gte', 'lte', 'isnull'],
            'activated_at': ['exact', 'gte', 'lte', 'isnull'],
            
            # Foreign keys
            'created_by': ['exact'],
            'used_by': ['exact'],
            'product': ['exact'],
            'fulfillment_line': ['exact'],
        }
        
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_fully_used(self, info):
        """Resolve whether gift card is fully used."""
        return self.is_fully_used
    
    def resolve_is_expired(self, info):
        """Resolve whether gift card is expired."""
        return self.is_expired
    
    def resolve_is_usable(self, info):
        """Resolve whether gift card can be used."""
        return self.is_usable
    
    def resolve_is_active_status(self, info):
        """Resolve whether gift card is active."""
        return self.is_active
    
    def resolve_has_expiry_date(self, info):
        """Resolve whether gift card has expiry date."""
        return self.expiry_date is not None
    
    def resolve_days_until_expiry(self, info):
        """Resolve days until expiry."""
        if self.expiry_date:
            now = timezone.now().date()
            if self.expiry_date >= now:
                return (self.expiry_date - now).days
            return 0
        return None
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_display_code(self, info):
        """Resolve display only the last 4 characters."""
        return self.display_code
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(GiftCardStatus.CHOICES).get(self.status, self.status)
    
    def resolve_initial_balance_display(self, info):
        """Resolve formatted initial balance."""
        if self.initial_balance_amount:
            return f"{self.initial_balance_amount:.2f} {self.currency}"
        return None
    
    def resolve_current_balance_display(self, info):
        """Resolve formatted current balance."""
        if self.current_balance_amount:
            return f"{self.current_balance_amount:.2f} {self.currency}"
        return None
    
    def resolve_used_amount(self, info):
        """Resolve amount used from the gift card."""
        return self.initial_balance_amount - self.current_balance_amount
    
    def resolve_usage_percentage(self, info):
        """Resolve percentage of balance used."""
        if self.initial_balance_amount > 0:
            used = self.initial_balance_amount - self.current_balance_amount
            return (used / self.initial_balance_amount) * 100
        return 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created the gift card."""
        return self.created_by
    
    def resolve_used_by_details(self, info):
        """Resolve user who used the gift card."""
        return self.used_by
    
    def resolve_product_details(self, info):
        """Resolve product associated with this gift card."""
        return self.product
    
    def resolve_fulfillment_line_details(self, info):
        """Resolve fulfillment line associated."""
        return self.fulfillment_line
    
    def resolve_tags(self, info):
        """Resolve tags for this gift card."""
        return self.tags.all()
    
    def resolve_events(self, info):
        """Resolve events for this gift card."""
        return self.events.all().order_by('-date')

