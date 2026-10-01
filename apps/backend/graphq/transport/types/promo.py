# graphql/transport/types/promo.py

"""
GraphQL Nodes for Promo Codes and Promo Usage.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.financial.promo import PromoCode, PromoUsage
from transport.models.core.service_request import ServiceRequest


class PromoCodeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promo Code with full promo details and calculations.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_valid = Boolean(description="Whether promo is currently valid")
    remaining_uses = Int(description="Remaining uses available")
    discount_type_display = String(description="Human-readable discount type display")
    applicable_to_display = String(description="Human-readable applicable to display")
    discount_display = String(description="Formatted discount")
    usage_percentage = Float(description="Usage percentage")
    is_expired = Boolean(description="Whether promo has expired")
    is_fully_used = Boolean(description="Whether promo has been fully used")
    days_remaining = Int(description="Days remaining until expiry")

    class Meta:
        model = PromoCode
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'code': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'discount_type': ['exact'],
            'applicable_to': ['exact'],
            
            # Numeric fields
            'discount_value': ['exact', 'gte', 'lte'],
            'min_order_value': ['exact', 'gte', 'lte', 'isnull'],
            'max_discount_amount': ['exact', 'gte', 'lte', 'isnull'],
            'max_uses_total': ['exact', 'gte', 'lte', 'isnull'],
            'max_uses_per_user': ['exact', 'gte', 'lte'],
            'usage_count': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            'is_deleted': ['exact'],
            
            # Foreign keys
            'created_by': ['exact'],
            'created_by__email': ['exact', 'icontains'],
            
            # Date fields
            'start_date': ['exact', 'gte', 'lte'],
            'end_date': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_valid(self, info):
        """Resolve whether promo is currently valid."""
        return self.is_valid
    
    def resolve_remaining_uses(self, info):
        """Resolve remaining uses available."""
        return self.remaining_uses
    
    def resolve_discount_type_display(self, info):
        """Resolve human-readable discount type display."""
        return self.get_discount_type_display()
    
    def resolve_applicable_to_display(self, info):
        """Resolve human-readable applicable to display."""
        return self.get_applicable_to_display()
    
    def resolve_discount_display(self, info):
        """Resolve formatted discount."""
        if self.discount_type == 'percentage':
            return f"{self.discount_value}%"
        elif self.discount_type == 'fixed':
            return f"${self.discount_value:,.2f}"
        elif self.discount_type == 'free_delivery':
            return "Free Delivery"
        return f"${self.discount_value:,.2f}"
    
    def resolve_usage_percentage(self, info):
        """Resolve usage percentage."""
        if self.max_uses_total:
            return (self.usage_count / self.max_uses_total) * 100
        return 0
    
    def resolve_is_expired(self, info):
        """Resolve whether promo has expired."""
        return timezone.now() > self.end_date
    
    def resolve_is_fully_used(self, info):
        """Resolve whether promo has been fully used."""
        if self.max_uses_total:
            return self.usage_count >= self.max_uses_total
        return False
    
    def resolve_days_remaining(self, info):
        """Resolve days remaining until expiry."""
        if self.end_date:
            now = timezone.now()
            if now > self.end_date:
                return 0
            return (self.end_date - now).days
        return None
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this promo."""
        return self.created_by
    
    def resolve_usages(self, info):
        """Resolve all usages of this promo."""
        return self.usages.all().order_by('-used_at')
    
    def resolve_successful_usages(self, info):
        """Resolve successful usages."""
        return self.usages.filter(is_successful=True).order_by('-used_at')


class PromoUsageNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Promo Usage with full usage details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    discount_percentage = Float(description="Discount as percentage of original amount")
    is_successful_display = String(description="Human-readable success status")
    savings_display = String(description="Formatted savings amount")
 
    class Meta:
        model = PromoUsage
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'promo': ['exact'],
            'promo__code': ['exact', 'icontains'],
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            
            # Numeric fields
            'discount_amount': ['exact', 'gte', 'lte'],
            'original_amount': ['exact', 'gte', 'lte'],
            'final_amount': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_successful': ['exact'],
            
            # String fields
            'failure_reason': ['exact', 'icontains'],
            
            # Date fields
            'used_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            '-used_at',
            '-id',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_discount_percentage(self, info):
        """Resolve discount as percentage of original amount."""
        if self.original_amount and self.original_amount > 0:
            return (self.discount_amount / self.original_amount) * 100
        return 0
    
    def resolve_is_successful_display(self, info):
        """Resolve human-readable success status."""
        return "Success" if self.is_successful else f"Failed: {self.failure_reason or 'Unknown reason'}"
    
    def resolve_savings_display(self, info):
        """Resolve formatted savings amount."""
        return f"${self.discount_amount:,.2f}"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_promo_details(self, info):
        """Resolve promo code details."""
        return self.promo
    
    def resolve_user_details(self, info):
        """Resolve user who used the promo."""
        return self.user
    
    def resolve_service_request_details(self, info):
        """Resolve service request."""
        return self.service_request

