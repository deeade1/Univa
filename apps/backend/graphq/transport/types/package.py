# graphql/transport/types/package.py

"""
GraphQL Node for Package with all properties, calculations, and relationships.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.delivery.package import Package
from transport.models.delivery.tracking import Tracking



class PackageNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Package with all properties and calculations.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    volume = Float(description="Volume of the package in cubic units")
    volume_unit = String(description="Unit for volume measurement")
    weight_in_kg = Float(description="Weight converted to kilograms")
    is_oversized = Boolean(description="Whether package is oversized based on dimensions")
    
    
    # ============================================================
    # Status Helpers
    # ============================================================
    
    is_delivered = Boolean(description="Whether package has been delivered")
    is_pending = Boolean(description="Whether package is pending")
    is_in_transit = Boolean(description="Whether package is in transit")
    is_cancelled = Boolean(description="Whether package is cancelled")
    has_exception = Boolean(description="Whether package has an exception")
    
    class Meta:
        model = Package
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'tracking_number': ['exact', 'icontains', 'istartswith'],
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'package_type': ['exact'],
            'status': ['exact'],
            'weight_unit': ['exact'],
            'dimension_unit': ['exact'],
            'currency': ['exact'],
            'receiver_name': ['exact', 'icontains', 'istartswith'],
            'receiver_phone': ['exact', 'icontains'],
            'receiver_email': ['exact', 'icontains'],
            'handling_instructions': ['exact', 'icontains'],
            'notes': ['exact', 'icontains'],
            
            # Foreign keys
            'delivery': ['exact'],
            'delivery__customer': ['exact'],
            'delivery__provider': ['exact'],
            'sender': ['exact'],
            
            # Numeric fields
            'weight': ['gte', 'lte', 'exact'],
            'length': ['gte', 'lte'],
            'width': ['gte', 'lte'],
            'height': ['gte', 'lte'],
            'declared_value': ['gte', 'lte'],
            'insurance_value': ['gte', 'lte'],
            'temperature_min': ['gte', 'lte'],
            'temperature_max': ['gte', 'lte'],
            
            # Boolean fields
            'is_insured': ['exact'],
            'requires_signature': ['exact'],
            'is_fragile': ['exact'],
            'is_perishable': ['exact'],
            'is_dangerous': ['exact'],
            'requires_refrigeration': ['exact'],
            
            # Date fields
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_volume(self, info):
        """Resolve volume of the package."""
        return self.volume
    
    def resolve_volume_unit(self, info):
        """Resolve volume unit."""
        return self.volume_unit
    
    def resolve_weight_in_kg(self, info):
        """Resolve weight converted to kilograms."""
        return float(self.weight_in_kg) if self.weight_in_kg else None
    
    def resolve_is_oversized(self, info):
        """Resolve whether package is oversized."""
        return self.is_oversized
    
    # ============================================================
    # Resolvers - Related Fields
    # ============================================================
    
    def resolve_delivery_details(self, info):
        """Resolve delivery this package belongs to."""
        return self.delivery
    
    def resolve_tracking_info(self, info):
        """Resolve tracking information for this package."""
        return self.get_tracking_info()
    
    def resolve_tracking_events(self, info):
        """Resolve all tracking events for this package."""
        return self.get_tracking_events()
    
    # ============================================================
    # Resolvers - Status Helpers
    # ============================================================
    
    def resolve_is_delivered(self, info):
        """Resolve whether package has been delivered."""
        return self.status == Package.PackageStatus.DELIVERED
    
    def resolve_is_pending(self, info):
        """Resolve whether package is pending."""
        return self.status == Package.PackageStatus.PENDING
    
    def resolve_is_in_transit(self, info):
        """Resolve whether package is in transit."""
        return self.status in [
            Package.PackageStatus.IN_TRANSIT,
            Package.PackageStatus.OUT_FOR_DELIVERY,
        ]
    
    def resolve_is_cancelled(self, info):
        """Resolve whether package is cancelled."""
        return self.status == Package.PackageStatus.CANCELLED
    
    def resolve_has_exception(self, info):
        """Resolve whether package has an exception."""
        return self.status == Package.PackageStatus.EXCEPTION

