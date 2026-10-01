# graphql/transport/types/earning.py

"""
GraphQL Nodes for Driver Earnings and Incentive Programs.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, UUID
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.financial.earnings import DriverEarning, IncentiveProgram
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.core.service_request import ServiceRequest




class DriverEarningNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Driver Earnings with full earning details and calculations.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_paid = Boolean(description="Whether earnings have been paid")
    is_pending = Boolean(description="Whether earnings are pending")
    period_display = String(description="Human-readable period display")
    total_earnings_display = String(description="Formatted total earnings")
    net_earnings_display = String(description="Formatted net earnings")
    payout_amount_display = String(description="Formatted payout amount")
    commission_rate_display = String(description="Formatted commission rate")
    completion_rate = Float(description="Completion rate percentage")
    class Meta:
        model = DriverEarning
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'driver': ['exact'],
            'driver__user__email': ['exact', 'icontains'],
            'driver__user__first_name': ['exact', 'icontains'],
            'driver__user__last_name': ['exact', 'icontains'],
            
            # String fields
            'period': ['exact'],
            'payout_status': ['exact'],
            'payout_method': ['exact'],
            'payout_reference': ['exact', 'icontains'],
            
            # Numeric fields
            'total_earnings': ['gte', 'lte', 'exact'],
            'ride_earnings': ['gte', 'lte'],
            'delivery_earnings': ['gte', 'lte'],
            'cancellation_fees': ['gte', 'lte'],
            'tips': ['gte', 'lte'],
            'bonuses': ['gte', 'lte'],
            'commission': ['gte', 'lte'],
            'commission_rate': ['gte', 'lte'],
            'fees': ['gte', 'lte'],
            'adjustments': ['gte', 'lte'],
            'net_earnings': ['gte', 'lte'],
            'payout_amount': ['gte', 'lte'],
            'total_rides': ['gte', 'lte'],
            'completed_rides': ['gte', 'lte'],
            'total_deliveries': ['gte', 'lte'],
            'completed_deliveries': ['gte', 'lte'],
            'total_distance': ['gte', 'lte'],
            'online_hours': ['gte', 'lte'],
            
            # Date fields
            'period_start': ['exact', 'gte', 'lte'],
            'period_end': ['exact', 'gte', 'lte'],
            'paid_at': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_paid(self, info):
        """Resolve whether earnings have been paid."""
        return self.is_paid
    
    def resolve_is_pending(self, info):
        """Resolve whether earnings are pending."""
        return self.is_pending
    
    def resolve_period_display(self, info):
        """Resolve human-readable period display."""
        return self.period_display
    
    def resolve_total_earnings_display(self, info):
        """Resolve formatted total earnings."""
        return f"${self.total_earnings:,.2f}"
    
    def resolve_net_earnings_display(self, info):
        """Resolve formatted net earnings."""
        return f"${self.net_earnings:,.2f}"
    
    def resolve_payout_amount_display(self, info):
        """Resolve formatted payout amount."""
        return f"${self.payout_amount:,.2f}"
    
    def resolve_commission_rate_display(self, info):
        """Resolve formatted commission rate."""
        return f"{self.commission_rate}%"
    
    def resolve_completion_rate(self, info):
        """Resolve completion rate percentage."""
        total = self.total_rides + self.total_deliveries
        completed = self.completed_rides + self.completed_deliveries
        if total > 0:
            return (completed / total) * 100
        return 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_driver_details(self, info):
        """Resolve driver details."""
        return self.driver
    
    def resolve_user_details(self, info):
        """Resolve user details."""
        return self.driver.user if self.driver else None
    
    def resolve_related_services(self, info):
        """Resolve services in this period."""
        return ServiceRequest.objects.filter(
            provider=self.driver,
            created_at__gte=self.period_start,
            created_at__lte=self.period_end
        ).order_by('-created_at')


class IncentiveProgramNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Incentive Programs with full program details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_active_now = Boolean(description="Whether program is currently active")
    incentive_type_display = String(description="Human-readable incentive type display")
    reward_display = String(description="Formatted reward")
    reward_type_display = String(description="Human-readable reward type display")
    days_remaining = Int(description="Days remaining until program ends")
    total_eligible = Int(description="Number of eligible drivers")
    total_rewards_paid = Decimal(description="Total rewards paid out")
    
    class Meta:
        model = IncentiveProgram
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'incentive_type': ['exact'],
            'reward_type': ['exact'],
            
            # Numeric fields
            'min_rating': ['exact', 'gte', 'lte'],
            'min_completion_rate': ['exact', 'gte', 'lte'],
            'min_rides': ['exact', 'gte', 'lte'],
            'reward_amount': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'start_date': ['exact', 'gte', 'lte'],
            'end_date': ['exact', 'gte', 'lte'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
        ordering = [
            '-start_date',
            'incentive_type',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_active_now(self, info):
        """Resolve whether program is currently active."""
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date
        )
    
    def resolve_incentive_type_display(self, info):
        """Resolve human-readable incentive type display."""
        return self.get_incentive_type_display()
    
    def resolve_reward_display(self, info):
        """Resolve formatted reward."""
        if self.reward_type == 'fixed':
            return f"${self.reward_amount:,.2f}"
        elif self.reward_type == 'percentage':
            return f"{self.reward_amount}%"
        elif self.reward_type == 'multiplier':
            return f"{self.reward_amount}x"
        return f"${self.reward_amount:,.2f}"
    
    def resolve_reward_type_display(self, info):
        """Resolve human-readable reward type display."""
        return dict(self._meta.model._meta.get_field('reward_type').choices).get(
            self.reward_type, self.reward_type
        )
    
    def resolve_days_remaining(self, info):
        """Resolve days remaining until program ends."""
        if self.end_date:
            now = timezone.now()
            if now > self.end_date:
                return 0
            return (self.end_date - now).days
        return None
    
    def resolve_total_eligible(self, info):
        """Resolve number of eligible drivers."""
        from transport.models.core.service_provider import ServiceProviderProfile
        
        queryset = ServiceProviderProfile.objects.filter(
            is_verified=True,
            is_available=True
        )
        
        if self.min_rating:
            queryset = queryset.filter(rating__gte=self.min_rating)
        
        return queryset.count()
    
    def resolve_total_rewards_paid(self, info):
        """Resolve total rewards paid out."""
        result = DriverEarning.objects.filter(
            bonuses__gt=0,
            period_start__gte=self.start_date,
            period_end__lte=self.end_date
        ).aggregate(total=models.Sum('bonuses'))
        return result['total'] or Decimal('0.00')
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_eligible_drivers(self, info):
        """Resolve eligible drivers."""
        from transport.models.core.service_provider import ServiceProviderProfile
        
        queryset = ServiceProviderProfile.objects.filter(
            is_verified=True,
            is_available=True
        )
        
        if self.min_rating:
            queryset = queryset.filter(rating__gte=self.min_rating)
        
        if self.min_completion_rate:
            # Filter by completion rate (calculated)
            pass
        
        return queryset[:20]
    
    def resolve_rewarded_earnings(self, info):
        """Resolve earnings with this incentive."""
        return DriverEarning.objects.filter(
            bonuses__gt=0,
            period_start__gte=self.start_date,
            period_end__lte=self.end_date
        ).order_by('-period_start')

