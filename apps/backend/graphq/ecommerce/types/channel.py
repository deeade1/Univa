# graphql/ecommerce/types/channel.py

"""
GraphQL Nodes for Channel.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.channel import Channel

from graphq.accounts.types.user import UserNode


class ChannelNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Channel with full channel configuration.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    allocation_strategy_display = String(description="Human-readable allocation strategy display")
    order_mark_as_paid_strategy_display = String(description="Human-readable mark as paid strategy display")
    transaction_flow_strategy_display = String(description="Human-readable transaction flow strategy display")
    is_default = Boolean(description="Whether this is the default channel")
    is_configured = Boolean(description="Whether channel is fully configured")
    has_valid_currency = Boolean(description="Whether currency is valid")
    has_valid_country = Boolean(description="Whether country is valid")
    order_expiry_minutes = Int(description="Order expiry in minutes")
    delete_expiry_days = Int(description="Days after which expired orders are deleted")
    settings_summary = JSONString(description="Summary of channel settings")
    
    # ============================================================
    # Nested Fields
    # ============================================================
    
    created_by_details = Field(UserNode, description="User who created this channel")
    modified_by_details = Field(UserNode, description="User who last modified this channel")
    
    class Meta:
        model = Channel
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            'currency_code': ['exact'],
            'default_country': ['exact'],
            
            # Boolean fields
            'is_active': ['exact'],
            'automatically_confirm_all_new_orders': ['exact'],
            'allow_unpaid_orders': ['exact'],
            'automatically_fulfill_non_shippable_gift_card': ['exact'],
            'include_draft_order_in_voucher_usage': ['exact'],
            'use_legacy_error_flow_for_checkout': ['exact'],
            
            # Choice fields
            'allocation_strategy': ['exact'],
            'order_mark_as_paid_strategy': ['exact'],
            'default_transaction_flow_strategy': ['exact'],
            
            # Numeric fields
            'expire_orders_after': ['exact', 'gte', 'lte', 'isnull'],
            'delete_expired_orders_after': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Foreign keys
            'created_by': ['exact'],
            'created_by__email': ['exact', 'icontains'],
            'modified_by': ['exact'],
            'modified_by__email': ['exact', 'icontains'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_allocation_strategy_display(self, info):
        """Resolve human-readable allocation strategy display."""
        if hasattr(self, 'get_allocation_strategy_display'):
            return self.get_allocation_strategy_display()
        return dict(AllocationStrategy.CHOICES).get(self.allocation_strategy, self.allocation_strategy)
    
    def resolve_order_mark_as_paid_strategy_display(self, info):
        """Resolve human-readable mark as paid strategy display."""
        if hasattr(self, 'get_order_mark_as_paid_strategy_display'):
            return self.get_order_mark_as_paid_strategy_display()
        return dict(MarkAsPaidStrategy.CHOICES).get(self.order_mark_as_paid_strategy, self.order_mark_as_paid_strategy)
    
    def resolve_transaction_flow_strategy_display(self, info):
        """Resolve human-readable transaction flow strategy display."""
        if hasattr(self, 'get_transaction_flow_strategy_display'):
            return self.get_transaction_flow_strategy_display()
        return dict(TransactionFlowStrategy.CHOICES).get(self.default_transaction_flow_strategy, self.default_transaction_flow_strategy)
    
    def resolve_is_default(self, info):
        """Resolve whether this is the default channel."""
        default = Channel.get_default_channel()
        return default and default.id == self.id
    
    def resolve_is_configured(self, info):
        """Resolve whether channel is fully configured."""
        return all([
            self.is_active,
            bool(self.name),
            bool(self.slug),
            bool(self.currency_code),
            bool(self.default_country),
        ])
    
    def resolve_has_valid_currency(self, info):
        """Resolve whether currency is valid."""
        # Check if currency is in supported currencies
        from django.conf import settings
        supported_currencies = getattr(settings, 'AVAILABLE_CURRENCIES', [])
        if supported_currencies:
            return self.currency_code in supported_currencies
        return bool(self.currency_code)
    
    def resolve_has_valid_country(self, info):
        """Resolve whether country is valid."""
        # Check if country is in supported countries
        from django_countries import countries
        return self.default_country in dict(countries)
    
    def resolve_order_expiry_minutes(self, info):
        """Resolve order expiry in minutes."""
        if self.expire_orders_after:
            return self.expire_orders_after
        return None
    
    def resolve_delete_expiry_days(self, info):
        """Resolve days after which expired orders are deleted."""
        if self.delete_expired_orders_after:
            return self.delete_expired_orders_after.days
        return None
    
    def resolve_settings_summary(self, info):
        """Resolve summary of channel settings."""
        import json
        settings_summary = {
            'currency': self.currency_code,
            'country': str(self.default_country),
            'allocation_strategy': self.allocation_strategy,
            'mark_as_paid_strategy': self.order_mark_as_paid_strategy,
            'transaction_flow': self.default_transaction_flow_strategy,
            'auto_confirm_orders': self.automatically_confirm_all_new_orders,
            'allow_unpaid_orders': self.allow_unpaid_orders,
            'order_expiry_minutes': self.expire_orders_after,
        }
        return json.dumps(settings_summary)
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this channel."""
        return self.created_by
    
    def resolve_modified_by_details(self, info):
        """Resolve user who last modified this channel."""
        return self.modified_by

