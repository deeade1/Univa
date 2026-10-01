# graphql/transport/types/boarding_ticket.py

"""
GraphQL Node for Boarding Ticket with QR code and ticket management capabilities.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, DateTime, UUID
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rides.boarding import BoardingTicket
from transport.models.rides.trip import Trip
from transport.models.rides.booking import Booking


class BoardingTicketNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Boarding Ticket with QR code and full ticket management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status = String(description="Current ticket status (active, redeemed, cancelled)")
    is_valid = Boolean(description="Whether ticket is valid for use")
    is_redeemed = Boolean(description="Whether ticket has been redeemed")
    is_cancelled = Boolean(description="Whether ticket has been cancelled")
    is_active = Boolean(description="Whether ticket is active (not redeemed or cancelled)")
    ticket_type_display = String(description="Human-readable ticket type display")
    qr_code_url = String(description="URL to the QR code image")
    

    class Meta:
        model = BoardingTicket
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'trip': ['exact'],
            'trip__id': ['exact'],
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            'user__first_name': ['exact', 'icontains'],
            'booking': ['exact'],
            'booking__id': ['exact'],
            'checked_in_by': ['exact'],
            'checked_in_by__email': ['exact', 'icontains'],
            
            # String fields
            'seat_number': ['exact', 'icontains'],
            'ticket_number': ['exact', 'icontains', 'istartswith'],
            'ticket_type': ['exact'],
            
            # Boolean fields
            'redeemed': ['exact'],
            'cancelled': ['exact'],
            
            # Date fields
            'redeemed_at': ['exact', 'gte', 'lte', 'isnull'],
            'cancelled_at': ['exact', 'gte', 'lte', 'isnull'],
            'used_at': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_status(self, info):
        """Resolve current ticket status."""
        return self.status
    
    def resolve_is_valid(self, info):
        """Resolve whether ticket is valid for use."""
        return self.is_valid()
    
    def resolve_is_redeemed(self, info):
        """Resolve whether ticket has been redeemed."""
        return self.is_redeemed
    
    def resolve_is_cancelled(self, info):
        """Resolve whether ticket has been cancelled."""
        return self.is_cancelled
    
    def resolve_is_active(self, info):
        """Resolve whether ticket is active."""
        return self.is_valid()
    
    def resolve_ticket_type_display(self, info):
        """Resolve human-readable ticket type display."""
        return dict(self._meta.model._meta.get_field('ticket_type').choices).get(
            self.ticket_type, self.ticket_type
        )
    
    def resolve_qr_code_url(self, info):
        """Resolve URL to the QR code image."""
        if self.qr_image and hasattr(self.qr_image, 'url'):
            return self.qr_image.url
        return None
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_trip_details(self, info):
        """Resolve trip details."""
        return self.trip
    
    def resolve_user_details(self, info):
        """Resolve user who owns the ticket."""
        return self.user
    
    def resolve_booking_details(self, info):
        """Resolve booking details."""
        return self.booking
    
    def resolve_checked_in_by_details(self, info):
        """Resolve staff who checked in the ticket."""
        return self.checked_in_by

