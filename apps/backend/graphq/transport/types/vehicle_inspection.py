# graphql/transport/types/inspection.py

"""
GraphQL Nodes for Vehicle Inspection.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.maintenance.vehicle_inspection import VehicleInspection
from transport.models.maintenance.vehicle import Vehicle


class VehicleInspectionNode(OptimizedDjangoObjectType):
     
    class Meta:
        model = VehicleInspection
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'vehicle__license_plate': ['exact', 'icontains'],
            'inspected_by': ['exact'],
            'inspected_by__email': ['exact', 'icontains'],
            'inspected_by__first_name': ['exact', 'icontains'],
            'inspected_by__last_name': ['exact', 'icontains'],
            
            # Choices fields
            'inspection_type': ['exact'],
            'result': ['exact'],
            
            # Text fields
            'findings': ['exact', 'icontains'],
            'recommendations': ['exact', 'icontains'],
            'notes': ['exact', 'icontains'],
            
            # Boolean fields
            'follow_up_required': ['exact'],
            
            # Date fields
            'inspection_date': ['exact', 'gte', 'lte'],
            'next_inspection_date': ['exact', 'gte', 'lte', 'isnull'],
            'follow_up_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
       
    
