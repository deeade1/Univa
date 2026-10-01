# graphql/transport/types/vehicle.py

"""
GraphQL Node for Vehicle with full vehicle management capabilities.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, Date
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter

from transport.models.maintenance.vehicle import Vehicle
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.delivery.logistics import Route, RouteStop



class VehicleNode(OptimizedDjangoObjectType):
    class Meta:
        model = Vehicle
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'owner': ['exact'],
            'owner__email': ['exact', 'icontains'],
            'owner__first_name': ['exact', 'icontains'],
            'owner__last_name': ['exact', 'icontains'],
            'provider': ['exact'],
            'provider__user__email': ['exact', 'icontains'],
            'current_provider': ['exact'],
            
            # String fields
            'vehicle_type': ['exact'],
            'category': ['exact'],
            'make': ['exact', 'icontains'],
            'model': ['exact', 'icontains'],
            'license_plate': ['exact', 'icontains'],
            'color': ['exact', 'icontains'],
            'fuel_type': ['exact'],
            'ownership_type': ['exact'],
            'status': ['exact'],
            'registration_number': ['exact', 'icontains'],
            'insurance_provider': ['exact', 'icontains'],
            'insurance_policy_number': ['exact', 'icontains'],
            
            # Numeric fields
            'year': ['exact', 'gte', 'lte'],
            'passenger_capacity': ['exact', 'gte', 'lte'],
            'cargo_capacity_kg': ['exact', 'gte', 'lte'],
            'cargo_volume_m3': ['exact', 'gte', 'lte'],
            'luggage_capacity_kg': ['exact', 'gte', 'lte'],
            'fuel_efficiency': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            'is_verified': ['exact'],
            'is_moving': ['exact'],
            
            # Date fields (from LocationModel)
            'location_timestamp': ['gte', 'lte'],
            'last_location_update': ['gte', 'lte', 'isnull'],
            'insurance_expiry': ['gte', 'lte', 'isnull'],
            'registration_expiry': ['gte', 'lte', 'isnull'],
            'last_inspection_date': ['gte', 'lte', 'isnull'],
            'next_inspection_date': ['gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
            
            # Location source (from LocationModel)
            'location_source': ['exact'],
        }
        
    