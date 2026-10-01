# graphql/transport/types/delivery.py

"""
GraphQL Node for Delivery with package management and location capabilities.
Extends ServiceRequestNode with delivery-specific fields.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter

from transport.models.delivery.delivery import Delivery
from transport.models.delivery.package import Package

from .service_request import ServiceRequestNode


class DeliveryNode(ServiceRequestNode):
    """
    GraphQL Node for Delivery with package management capabilities.
    Extends ServiceRequestNode with delivery-specific fields.
    """
    
    # ============================================================
    # Delivery Properties (from Delivery model)
    # ============================================================
    
    surge_multiplier = Decimal(description="Surge pricing multiplier")
    is_cancelled = Boolean(description="Whether delivery is cancelled")
    cancellation_reason = String(description="Reason for cancellation")
    
    # Package statistics
    package_count = Int(description="Total number of packages")
    total_weight = Float(description="Total weight of all packages in kg")
    total_value = Float(description="Total declared value of all packages")
    
    # Package flags
    has_fragile_items = Boolean(description="Whether any package is fragile")
    has_perishable_items = Boolean(description="Whether any package is perishable")
    has_dangerous_goods = Boolean(description="Whether any package contains dangerous goods")
    requires_refrigeration = Boolean(description="Whether any package requires refrigeration")
    has_packages = Boolean(description="Whether delivery has any packages")
    is_express = Boolean(description="Whether delivery is express")
    
    # Status
    delivery_status = String(description="Delivery status with additional context")
    
    class Meta:
        model = Delivery
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys (from ServiceRequest)
            'customer': ['exact'],
            'customer__email': ['exact', 'icontains'],
            'provider': ['exact'],
            'provider__provider_type': ['exact'],
            'vehicle': ['exact'],
            'vehicle__name': ['exact', 'icontains'],
            
            # Location fields (using StopPoint)
            'pickup_location': ['exact'],
            'dropoff_location': ['exact'],
            
            # String fields
            'service_type': ['exact'],
            'status': ['exact'],
            'pickup_address': ['exact', 'icontains'],
            'dropoff_address': ['exact', 'icontains'],
            
            # Numeric fields
            'total_fare': ['gte', 'lte'],
            'estimated_distance': ['gte', 'lte'],
            'estimated_duration': ['gte', 'lte'],
            
            # Boolean fields
            'is_recurring_daily': ['exact'],
            'insurance_required': ['exact'],
            
            # Date fields
            'created_at': ['gte', 'lte'],
            'scheduled_at': ['gte', 'lte', 'isnull'],
            'started_at': ['gte', 'lte', 'isnull'],
            'completed_at': ['gte', 'lte', 'isnull'],
            'estimated_arrival_time': ['gte', 'lte', 'isnull'],
        }
    
    # ============================================================
    # Resolvers - Delivery Properties
    # ============================================================
    
    def resolve_surge_multiplier(self, info):
        """Resolve surge multiplier."""
        return self.surge_multiplier
    
    def resolve_is_cancelled(self, info):
        """Resolve whether delivery is cancelled."""
        return self.is_cancelled
    
    def resolve_cancellation_reason(self, info):
        """Resolve cancellation reason."""
        return self.cancellation_reason
    
    def resolve_package_count(self, info):
        """Resolve total number of packages."""
        return self.package_count
    
    def resolve_total_weight(self, info):
        """Resolve total weight of all packages."""
        return self.total_weight
    
    def resolve_total_value(self, info):
        """Resolve total declared value of all packages."""
        return self.total_value
    
    def resolve_has_fragile_items(self, info):
        """Resolve whether any package is fragile."""
        return self.has_fragile_items
    
    def resolve_has_perishable_items(self, info):
        """Resolve whether any package is perishable."""
        return self.has_perishable_items
    
    def resolve_has_dangerous_goods(self, info):
        """Resolve whether any package contains dangerous goods."""
        return self.has_dangerous_goods
    
    def resolve_requires_refrigeration(self, info):
        """Resolve whether any package requires refrigeration."""
        return self.requires_refrigeration
    
    def resolve_has_packages(self, info):
        """Resolve whether delivery has any packages."""
        return self.has_packages
    
    def resolve_is_express(self, info):
        """Resolve whether delivery is express."""
        return self.is_express
    
    def resolve_delivery_status(self, info):
        """Resolve delivery status with additional context."""
        return self.delivery_status
    
    # ============================================================
    # Resolvers - Nested Fields (Packages)
    # ============================================================
    
    def resolve_packages(self, info):
        """Resolve all packages in this delivery."""
        return self.packages.all()
    
    def resolve_pending_packages(self, info):
        """Resolve packages pending delivery."""
        return self.get_pending_packages()
    
    def resolve_delivered_packages(self, info):
        """Resolve packages that have been delivered."""
        return self.get_delivered_packages()
    
    def resolve_exception_packages(self, info):
        """Resolve packages with exceptions."""
        return self.get_exception_packages()
    
    def resolve_packages_by_type(self, info, package_type):
        """Resolve packages filtered by type."""
        return self.get_packages_by_type(package_type)
    
    # ============================================================
    # Resolvers - Tracking
    # ============================================================
    
    def resolve_tracking_info(self, info):
        """Resolve tracking information for all packages."""
        from transport.models.delivery.tracking import Tracking
        return Tracking.objects.filter(delivery=self)
    

