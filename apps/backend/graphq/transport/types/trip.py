# graphql/transport/types/trip.py

"""
GraphQL Node for Trip with full trip management capabilities.
"""

from graphene import Node, Boolean, Int, String, Field, List, Decimal, DateTime, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rides.trip import Trip
from transport.models.rides.booking import  Booking
from transport.models.rating.ratings import Rating


class TripNode(OptimizedDjangoObjectType):
    
    class Meta:
        model = Trip
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys (from ServiceRequest)
            'customer': ['exact'],
            'customer__email': ['exact', 'icontains'],
            'provider': ['exact'],
            'provider__user__email': ['exact', 'icontains'],
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'pickup_location': ['exact'],
            'dropoff_location': ['exact'],
            
            # String fields (from ServiceRequest)
            'service_type': ['exact'],
            'status': ['exact'],
            #'pickup_address': ['exact', 'icontains'],
            #'dropoff_address': ['exact', 'icontains'],
            'departure_state': ['exact', 'icontains'],
            'departure_city': ['exact', 'icontains'],
            'destination_state': ['exact', 'icontains'],
            'destination_city': ['exact', 'icontains'],
            
            # Numeric fields
            'total_fare': ['exact', 'gte', 'lte'],
            'base_fare': ['exact', 'gte', 'lte'],
            'estimated_distance': ['exact', 'gte', 'lte'],
            'estimated_duration': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_recurring_daily': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'scheduled_at': ['exact', 'gte', 'lte', 'isnull'],
            'started_at': ['exact', 'gte', 'lte', 'isnull'],
            'completed_at': ['exact', 'gte', 'lte', 'isnull'],
            'estimated_arrival_time': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    