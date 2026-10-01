# graphql/transport/types/service_provider.py

"""
GraphQL Node for Service Provider Profile with LocationModel integration.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal
from graphene_gis.converter import gis_converter
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.core.service_request import ServiceRequest



class ServiceProviderProfileNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Service Provider Profile with location capabilities.
    Inherits LocationModel fields via the model.
    """
    
    # Location fields (from LocationModel)
    lat = Float(description="Latitude coordinate")
    lng = Float(description="Longitude coordinate")
    coordinates_string = String(description="Human-readable coordinates string")
    has_location = Boolean(description="Whether location is set")
    has_address = Boolean(description="Whether address is set")
    is_valid_location = Boolean(description="Whether location is valid")
    
    # Calculated fields
    display_name = String(description="Provider display name")
    company_name = String(description="Company name")
    is_available_and_online = Boolean(description="Whether provider is available and online")
    can_accept_services = Boolean(description="Whether provider can accept new services")
    service_count_today = Int(description="Number of services completed today")
    earnings_today = Decimal(description="Earnings today")
    rating_percentage = Float(description="Rating as percentage (0-100)")
    # Distance fields
    distance_to = Float(
        description="Distance in kilometers to a location",
        lat=Float(required=True, description="Target latitude"),
        lng=Float(required=True, description="Target longitude")
    )
    is_near = Boolean(
        description="Whether provider is within radius of a location",
        lat=Float(required=True, description="Target latitude"),
        lng=Float(required=True, description="Target longitude"),
        radius_km=Float(required=False, default_value=5, description="Radius in kilometers")
    )
    
    class Meta:
        model = ServiceProviderProfile
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'user': ['exact'],
            'user__first_name': ['exact', 'icontains'],
            'user__last_name': ['exact', 'icontains'],
            'user__email': ['exact', 'icontains'],
            'current_service': ['exact'],
            
            # Choice fields
            'provider_type': ['exact'],
            'license_type': ['exact'],
            
            # String fields
            'union_id': ['exact', 'icontains', 'istartswith'],
            'license_number': ['exact', 'icontains'],
            'insurance_policy_number': ['exact', 'icontains'],
            'insurance_provider': ['exact', 'icontains'],
            'emergency_contact_name': ['exact', 'icontains'],
            'emergency_contact_phone': ['exact', 'icontains'],
            
            # Boolean fields
            'is_available': ['exact'],
            'is_online': ['exact'],
            'is_verified': ['exact'],
            'verified_union_member': ['exact'],
            
            # Numeric fields
            'rating': ['gte', 'lte', 'exact'],
            'total_ratings': ['gte', 'lte'],
            'total_services': ['gte', 'lte'],
            'total_earnings': ['gte', 'lte'],
            
            # Date fields (from LocationModel)
            'location_timestamp': ['gte', 'lte'],
            'last_active': ['gte', 'lte'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
            
            # Location source (from LocationModel)
            'location_source': ['exact'],
        }
       
    
    # ============================================================
    # Resolvers - Location Fields (from LocationModel)
    # ============================================================
    
    def resolve_lat(self, info):
        """Resolve latitude as Float."""
        return float(self.latitude) if self.latitude else None
    
    def resolve_lng(self, info):
        """Resolve longitude as Float."""
        return float(self.longitude) if self.longitude else None
    
    def resolve_coordinates_string(self, info):
        """Resolve human-readable coordinates."""
        if self.coordinates:
            lat, lng = self.coordinates
            return f"{lat:.6f}, {lng:.6f}"
        return None
    
    def resolve_has_location(self, info):
        """Resolve whether location is set."""
        return self.has_location
    
    def resolve_has_address(self, info):
        """Resolve whether address is set."""
        return self.has_address
    
    def resolve_is_valid_location(self, info):
        """Resolve whether location is valid."""
        return self.is_valid_location
    
    # ============================================================
    # Resolvers - Calculated Fields
    # ============================================================
    
    def resolve_display_name(self, info):
        """Resolve provider display name."""
        return self.display_name
    
    def resolve_company_name(self, info):
        """Resolve company name."""
        return self.company_name
    
    def resolve_is_available_and_online(self, info):
        """Resolve whether provider is available and online."""
        return self.is_available and self.is_online
    
    def resolve_can_accept_services(self, info):
        """Resolve whether provider can accept new services."""
        return (
            self.is_available and
            self.is_online and
            self.is_verified and
            self.current_service is None
        )
    
    def resolve_service_count_today(self, info):
        """Resolve number of services completed today."""
        from django.utils import timezone
        from django.db.models import Count
        
        today = timezone.now().date()
        return ServiceRequest.objects.filter(
            provider=self,
            status=ServiceRequest.Status.COMPLETED,
            completed_at__date=today
        ).count()
    
    def resolve_earnings_today(self, info):
        """Resolve earnings today."""
        from django.utils import timezone
        from django.db.models import Sum
        
        today = timezone.now().date()
        result = ServiceRequest.objects.filter(
            provider=self,
            status=ServiceRequest.Status.COMPLETED,
            completed_at__date=today
        ).aggregate(total=Sum('total_fare'))
        
        return result['total'] or 0
    
    def resolve_rating_percentage(self, info):
        """Resolve rating as percentage (0-100)."""
        if self.rating:
            return (self.rating / 5) * 100
        return 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_current_service_details(self, info):
        """Resolve current active service details."""
        if self.current_service:
            return self.current_service
        return None
    
    def resolve_recent_services(self, info):
        """Resolve recent services (last 10)."""
        return ServiceRequest.objects.filter(
            provider=self
        ).order_by('-created_at')[:10]
    
    # ============================================================
    # Resolvers - Distance Fields
    # ============================================================
    
    def resolve_distance_to(self, info, lat, lng):
        """
        Resolve distance in kilometers to a location.
        
        Args:
            lat: Target latitude
            lng: Target longitude
        
        Returns:
            float: Distance in kilometers
        """
        if not self.coordinates:
            return None
        
        from core.services.routing import haversine_distance
        return haversine_distance(
            self.coordinates[0], self.coordinates[1],
            lat, lng
        )
    
    def resolve_is_near(self, info, lat, lng, radius_km=5):
        """
        Resolve whether provider is within radius of a location.
        
        Args:
            lat: Target latitude
            lng: Target longitude
            radius_km: Radius in kilometers (default: 5)
        
        Returns:
            bool: True if within radius
        """
        if not self.coordinates:
            return False
        
        distance = self.resolve_distance_to(info, lat, lng)
        if distance is None:
            return False
        
        return distance <= radius_km

