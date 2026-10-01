# graphql/transport/types/service_request.py

"""
GraphQL Types for Service Request with routing capabilities.
Uses canonical LocationModel and routing services from core.
"""

from graphene import Node, Int, Float, Field, Boolean, List, String, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.core.service_request import ServiceRequest
from transport.models.delivery.logistics import StopPoint, Route, RouteStop


class ServiceRequestNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Service Request with routing capabilities.
    """
    
    # Calculated fields
    total_stops = Int(description="Total number of stops")
    route_count = Int(description="Number of routes for this request")
    is_completed = Boolean(description="Whether request is completed")
    is_cancelled = Boolean(description="Whether request is cancelled")
    is_in_progress = Boolean(description="Whether request is in progress")
    is_scheduled = Boolean(description="Whether request is scheduled")
    duration_minutes = Float(description="Duration in minutes")
    
    
    # Calculated route info
    estimated_distance_km = Float(description="Estimated distance in kilometers")
    estimated_duration_minutes = Float(description="Estimated duration in minutes")
    
   
    class Meta:
        model = ServiceRequest
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            # Foreign keys
            'customer': ['exact'],
            'customer__email': ['exact', 'icontains'],
            'provider': ['exact'],
            'provider__provider_type': ['exact', 'icontains'],
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'pickup_location': ['exact'],
            'dropoff_location': ['exact'],
            # String fields
            'service_type': ['exact'],
            'status': ['exact'],
            # Numeric fields
            'total_fare': ['gte', 'lte'],
            # Boolean fields
            'is_recurring_daily': ['exact'],
            'insurance_required': ['exact'],
            # Date fields
            'created_at': ['gte', 'lte'],
            'scheduled_at': ['gte', 'lte', 'isnull'],
            'started_at': ['gte', 'lte', 'isnull'],
            'completed_at': ['gte', 'lte', 'isnull'],
            'updated_at': ['gte', 'lte'],
            'estimated_arrival_time': ['gte', 'lte', 'isnull'],
            # Interstate fields
            'departure_state': ['exact', 'icontains'],
            'departure_city': ['exact', 'icontains'],
            'destination_state': ['exact', 'icontains'],
            'destination_city': ['exact', 'icontains'],
        }
    
    # ============================================================
    # Resolvers - Basic Fields
    # ============================================================
    
    def resolve_total_stops(self, info):
        """Resolve total number of stops."""
        count = 1 if self.pickup_location_id else 0
        count += 1 if self.dropoff_location_id else 0
        count += self.additional_stops.count()
        return count
    
    def resolve_current_route(self, info):
        """Resolve current active route."""
        return self.routes.order_by('-created_at').first()
    
    def resolve_route_count(self, info):
        """Resolve number of routes."""
        return self.routes.count()
    
    def resolve_is_completed(self, info):
        """Resolve whether request is completed."""
        return self.status == ServiceRequest.Status.COMPLETED
    
    def resolve_is_cancelled(self, info):
        """Resolve whether request is cancelled."""
        return self.status == ServiceRequest.Status.CANCELLED
    
    def resolve_is_in_progress(self, info):
        """Resolve whether request is in progress."""
        return self.status == ServiceRequest.Status.IN_PROGRESS
    
    def resolve_is_scheduled(self, info):
        """Resolve whether request is scheduled."""
        return self.status == ServiceRequest.Status.SCHEDULED
    
    def resolve_duration_minutes(self, info):
        """Resolve duration in minutes."""
        return self.duration_minutes
    
    # ============================================================
    # Resolvers - Location Fields
    # ============================================================
    
    def resolve_pickup_details(self, info):
        """Resolve detailed pickup location."""
        return self.pickup_location
    
    def resolve_dropoff_details(self, info):
        """Resolve detailed dropoff location."""
        return self.dropoff_location
    
    def resolve_all_stops(self, info):
        """Resolve all stops including pickup, dropoff, and additional."""
        stops = []
        
        if self.pickup_location:
            stops.append(self.pickup_location)
        
        # Add additional stops in order
        additional = self.route_stops.select_related('stop').order_by('order')
        for route_stop in additional:
            if route_stop.stop.id != getattr(self.pickup_location, 'id', None):
                stops.append(route_stop.stop)
        
        if self.dropoff_location:
            if self.dropoff_location not in stops:
                stops.append(self.dropoff_location)
        
        return stops
    
    # ============================================================
    # Resolvers - Route Information
    # ============================================================
    
    def resolve_estimated_distance_km(self, info):
        """Resolve estimated distance in kilometers."""
        if self.estimated_distance:
            return self.estimated_distance
        
        # Calculate from locations
        if self.pickup_location and self.dropoff_location:
            return self.pickup_location.distance_to(self.dropoff_location)
        return None
    
    def resolve_estimated_duration_minutes(self, info):
        """Resolve estimated duration in minutes."""
        if self.estimated_duration:
            return self.estimated_duration
        
        # Calculate from distance
        distance = self.resolve_estimated_distance_km(info)
        if distance:
            from core.services.routing import estimate_eta
            return estimate_eta(distance, 40)  # Default speed 40 km/h
        return None
    
    def resolve_all_routes(self, info):
        """Resolve all routes."""
        return self.routes.all()