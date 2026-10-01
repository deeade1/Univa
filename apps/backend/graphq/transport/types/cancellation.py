# graphql/transport/types/cancellation.py

"""
GraphQL Nodes for Cancellation Policy and Cancellation Records.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.financial.cancellation import CancellationPolicy, CancellationRecord
from transport.models.core.service_request import ServiceRequest




class CancellationPolicyNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Cancellation Policy with full policy details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_effective = Boolean(description="Whether policy is currently effective")
    service_type_display = String(description="Human-readable service type display")
    cancellation_fee_display = String(description="Formatted cancellation fee")
    refund_percentage_display = String(description="Formatted refund percentage")
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_cancellations = Int(description="Total cancellations using this policy")
    total_refunds = Decimal(description="Total refunds issued")
    total_driver_compensation = Decimal(description="Total driver compensation paid")
    
    class Meta:
        model = CancellationPolicy
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'service_type': ['exact'],
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            
            # Numeric fields
            'free_cancellation_minutes': ['exact', 'gte', 'lte'],
            'no_penalty_cancellation_minutes': ['exact', 'gte', 'lte'],
            'cancellation_fee': ['exact', 'gte', 'lte'],
            'cancellation_fee_percentage': ['exact', 'gte', 'lte'],
            'refund_percentage': ['exact', 'gte', 'lte'],
            'min_refund_amount': ['exact', 'gte', 'lte'],
            'driver_compensation_percentage': ['exact', 'gte', 'lte'],
            'max_cancellations_per_day': ['exact', 'gte', 'lte'],
            'suspension_days': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'effective_from': ['exact', 'gte', 'lte'],
            'effective_to': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_effective(self, info):
        """Resolve whether policy is currently effective."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.effective_from and self.effective_from > now:
            return False
        if self.effective_to and self.effective_to < now:
            return False
        return True
    
    def resolve_service_type_display(self, info):
        """Resolve human-readable service type display."""
        return self.get_service_type_display()
    
    def resolve_cancellation_fee_display(self, info):
        """Resolve formatted cancellation fee."""
        return f"${self.cancellation_fee}"
    
    def resolve_refund_percentage_display(self, info):
        """Resolve formatted refund percentage."""
        return f"{self.refund_percentage}%"
    
    # ============================================================
    # Resolvers - Statistics
    # ============================================================
    
    def resolve_total_cancellations(self, info):
        """Resolve total cancellations using this policy."""
        return CancellationRecord.objects.filter(policy=self).count()
    
    def resolve_total_refunds(self, info):
        """Resolve total refunds issued."""
        result = CancellationRecord.objects.filter(
            policy=self
        ).aggregate(total=models.Sum('refund_amount'))
        return result['total'] or Decimal('0.00')
    
    def resolve_total_driver_compensation(self, info):
        """Resolve total driver compensation paid."""
        result = CancellationRecord.objects.filter(
            policy=self
        ).aggregate(total=models.Sum('driver_compensation'))
        return result['total'] or Decimal('0.00')


class CancellationRecordNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Cancellation Record with full cancellation details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    reason_display = String(description="Human-readable reason display")
    cancellation_party_display = String(description="Human-readable party display")
    was_penalty_applied = Boolean(description="Whether penalty was applied")
    is_within_free_cancellation = Boolean(description="Whether cancellation was within free period")
    minutes_to_cancellation = Float(description="Minutes from acceptance to cancellation")
    refund_rate = Float(description="Refund rate as percentage")
    
    
    
    
    class Meta:
        model = CancellationRecord
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            'service_request__status': ['exact'],
            'cancelled_by': ['exact'],
            'cancelled_by__email': ['exact', 'icontains'],
            'cancelled_by__first_name': ['exact', 'icontains'],
            'cancelled_by__last_name': ['exact', 'icontains'],
            'policy': ['exact'],
            
            # String fields
            'cancellation_party': ['exact'],
            'reason': ['exact', 'icontains'],
            'reason_description': ['exact', 'icontains'],
            
            # Numeric fields
            'minutes_after_acceptance': ['exact', 'gte', 'lte'],
            'ride_fare': ['exact', 'gte', 'lte'],
            'cancellation_fee': ['exact', 'gte', 'lte'],
            'refund_amount': ['exact', 'gte', 'lte'],
            'driver_compensation': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'penalty_applied': ['exact'],
            
            # Date fields
            'accepted_at': ['exact', 'gte', 'lte', 'isnull'],
            'cancelled_at': ['exact', 'gte', 'lte'],
            'created_at': ['gte', 'lte'],
        }
        ordering = [
            '-cancelled_at',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_reason_display(self, info):
        """Resolve human-readable reason display."""
        return self.get_reason_display() if self.reason else None
    
    def resolve_cancellation_party_display(self, info):
        """Resolve human-readable party display."""
        return self.get_cancellation_party_display()
    
    def resolve_was_penalty_applied(self, info):
        """Resolve whether penalty was applied."""
        return self.penalty_applied
    
    def resolve_is_within_free_cancellation(self, info):
        """Resolve whether cancellation was within free period."""
        if not self.policy or not self.accepted_at:
            return False
        
        time_diff = (self.cancelled_at - self.accepted_at).total_seconds() / 60
        return time_diff <= self.policy.free_cancellation_minutes
    
    def resolve_minutes_to_cancellation(self, info):
        """Resolve minutes from acceptance to cancellation."""
        if self.minutes_after_acceptance:
            return self.minutes_after_acceptance
        
        if self.accepted_at and self.cancelled_at:
            return (self.cancelled_at - self.accepted_at).total_seconds() / 60
        return None
    
    def resolve_refund_rate(self, info):
        """Resolve refund rate as percentage."""
        if self.ride_fare and self.ride_fare > 0:
            return (self.refund_amount / self.ride_fare) * 100
        return 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_service_request_details(self, info):
        """Resolve service request details."""
        return self.service_request
    
    def resolve_cancelled_by_details(self, info):
        """Resolve user who cancelled."""
        return self.cancelled_by
    
    def resolve_policy_details(self, info):
        """Resolve policy used."""
        return self.policy
    
    def resolve_related_cancellations(self, info):
        """Resolve related cancellations by same user."""
        return CancellationRecord.objects.filter(
            cancelled_by=self.cancelled_by
        ).exclude(id=self.id).order_by('-cancelled_at')[:10]

