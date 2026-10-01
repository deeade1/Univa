# graphql/transport/types/tracking.py

"""
GraphQL Nodes for Tracking and TrackingEvent with LocationModel integration.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, DateTime, Decimal
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter

from transport.models.delivery.tracking import Tracking, TrackingEvent



class TrackingEventNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for TrackingEvent with location capabilities.
    """
   
    
    class Meta:
        model = TrackingEvent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
           # Foreign keys
            'tracking': ['exact'],
            'tracking__tracking_number': ['exact', 'icontains'],
            
            # String fields
            'status': ['exact'],
            'location': ['exact', 'icontains'],
            'description': ['exact', 'icontains'],
            'event_code': ['exact', 'icontains'],
            'notes': ['exact', 'icontains'],
            
            # Numeric fields
            'latitude': ['gte', 'lte', 'exact'],
            'longitude': ['gte', 'lte', 'exact'],
            
            # Date fields
            'timestamp': ['exact', 'gte', 'lte'],
            'created_at': ['gte', 'lte'],
        }
        
    
   

class TrackingNode(OptimizedDjangoObjectType):
    class Meta:
        model = Tracking
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward relations ------------------------------------
            "package": ["exact"],
            "package__tracking_number": ["exact", "icontains"],
            "package__name": ["exact", "icontains"],
            "delivery": ["exact"],
            "service_request": ["exact"],

            # ---- Tracking identifiers ---------------------------------
            "tracking_number": ["exact", "icontains", "istartswith"],
            "carrier_tracking_number": ["exact", "icontains"],
            "carrier_name": ["exact", "icontains"],

            # ---- Status / priority ------------------------------------
            "current_status": ["exact", "in"],
            "priority": ["exact", "in"],

            # ---- Location fields (from LocationModel) -----------------
            "location": ["exact", "icontains"],        # replaces current_address
            "latitude": ["exact", "gte", "lte"],       # replaces current_location exact
            "longitude": ["exact", "gte", "lte"],

            # ---- Boolean flags ----------------------------------------
            "signature_required": ["exact"],

            # ---- Numeric ----------------------------------------------
            "delivery_attempts": ["exact", "gte", "lte"],

            # ---- Dates ------------------------------------------------
            "estimated_delivery": ["exact", "gte", "lte", "lt", "gt"],
            "actual_delivery": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "last_updated": ["exact", "gte", "lte", "lt", "gt"],
            "last_attempt_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }