# graphql/transport/types/booking.py

"""
GraphQL Node for Booking with full booking management capabilities.
"""

from graphene import Node, Boolean, String, Field, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rides.booking import Booking
from transport.models.core.service_request import ServiceRequest




class BookingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Booking with full booking lifecycle management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status_display = String(description="Human-readable status display")
    is_pending = Boolean(description="Whether booking is pending")
    is_confirmed = Boolean(description="Whether booking is confirmed")
    is_cancelled = Boolean(description="Whether booking is cancelled")
    is_completed = Boolean(description="Whether booking is completed")
    is_active = Boolean(description="Whether booking is active (pending or confirmed)")
    can_be_cancelled = Boolean(description="Whether booking can be cancelled")
    can_be_confirmed = Boolean(description="Whether booking can be confirmed")
    
   
    class Meta:
        model = Booking
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            'service_request__status': ['exact'],
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            
            # String fields
            'status': ['exact'],
            
            # Date fields
            'booked_at': ['exact', 'gte', 'lte'],
            'confirmed_at': ['exact', 'gte', 'lte', 'isnull'],
            'cancelled_at': ['exact', 'gte', 'lte', 'isnull'],
            'completed_at': ['exact', 'gte', 'lte', 'isnull'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return self.get_status_display()
    
    def resolve_is_pending(self, info):
        """Resolve whether booking is pending."""
        return self.status == self.Status.PENDING
    
    def resolve_is_confirmed(self, info):
        """Resolve whether booking is confirmed."""
        return self.status == self.Status.CONFIRMED
    
    def resolve_is_cancelled(self, info):
        """Resolve whether booking is cancelled."""
        return self.status == self.Status.CANCELLED
    
    def resolve_is_completed(self, info):
        """Resolve whether booking is completed."""
        return self.status == self.Status.COMPLETED
    
    def resolve_is_active(self, info):
        """Resolve whether booking is active (pending or confirmed)."""
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]
    
    def resolve_can_be_cancelled(self, info):
        """Resolve whether booking can be cancelled."""
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]
    
    def resolve_can_be_confirmed(self, info):
        """Resolve whether booking can be confirmed."""
        return self.status == self.Status.PENDING
    
    

