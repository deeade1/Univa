# transport/schema/nodes.py

"""
GraphQL Nodes for Transport/Delivery/Logistics models.
Uses canonical LocationModel and routing services from core.
"""

from graphene import Node, Float, List, String, Int, Boolean, Field, DateTime
from graphene_gis.converter import gis_converter
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.delivery.logistics import StopPoint, Route, RouteStop
from transport.models.core.service_request import ServiceRequest
from core.services.routing import haversine_distance, estimate_eta


# =============================================================================
# StopPoint Node
# =============================================================================

class StopPointNode(OptimizedDjangoObjectType):
    """GraphQL Node for StopPoint with location capabilities."""
    
    lat = Float()
    lng = Float()
    distance_to = Float(description="Distance in kilometers to another stop")
    coordinates_string = String(description="Human-readable coordinates string")
    has_location = Boolean(description="Whether location is set")
    has_address = Boolean(description="Whether address is set")
    
    class Meta:
        model = StopPoint
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            # Choices fields
            'stop_type': ['exact'],
            'contact_name': ['exact', 'icontains'],
            'contact_phone': ['exact', 'icontains'],
            # Text fields
            'notes': ['exact', 'icontains'],
            # Boolean fields
            'is_active': ['exact'],
            # Date fields
            "created_at": ["gte", "lte"],
            "updated_at": ["gte", "lte"],
        }
    
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
    
    def resolve_distance_to(self, info, **kwargs):
        """
        Resolve distance to another stop.
        
        Usage:
            stopPoint(distanceTo: "other_stop_id")
        """
        # This would need to be implemented with a custom resolver
        # that takes the target stop ID as an argument
        return None


# =============================================================================
# Route Node
# =============================================================================

class RouteNode(OptimizedDjangoObjectType):
    """GraphQL Node for Route with optimization capabilities."""
    
    # Calculated fields
    total_distance_km = Float(description="Total distance in kilometers")
    total_duration_minutes = Float(description="Total duration in minutes")
    total_stops = Int(description="Number of stops in this route")
    is_complete = Boolean(description="Whether route has all required data")
    # Optimization fields
    can_optimize = Boolean(description="Whether route can be optimized")
    optimization_status = String(description="Current optimization status")
    
    class Meta:
        model = Route
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign key
            'trip': ['exact'],
            # Numeric fields
            'distance_km': ['gte', 'lte', 'exact'],
            'duration_minutes': ['gte', 'lte', 'exact'],
            'traffic_delay_minutes': ['gte', 'lte'],
            'optimization_score': ['gte', 'lte'],
            # Boolean fields
            'is_optimized': ['exact'],
            # Choice fields
            'optimization_provider': ['exact'],
            # Date fields
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
    
    def resolve_total_distance_km(self, info):
        """Resolve total distance in kilometers."""
        return self.get_total_distance() if hasattr(self, 'get_total_distance') else self.distance_km
    
    def resolve_total_duration_minutes(self, info):
        """Resolve total duration in minutes."""
        if self.duration_minutes:
            return self.duration_minutes
        return self.get_total_duration() if hasattr(self, 'get_total_duration') else None
    
    def resolve_total_stops(self, info):
        """Resolve number of stops."""
        return self.route_stops.count() if hasattr(self, 'route_stops') else 0
    
    def resolve_is_complete(self, info):
        """Resolve whether route is complete."""
        return (
            self.distance_km is not None and
            self.duration_minutes is not None and
            self.route_stops.exists()
        )
    
    def resolve_first_stop(self, info):
        """Resolve first stop in route."""
        first = self.route_stops.order_by('order').first()
        return first.stop if first else None
    
    def resolve_last_stop(self, info):
        """Resolve last stop in route."""
        last = self.route_stops.order_by('-order').first()
        return last.stop if last else None
    
    def resolve_stops(self, info):
        """Resolve all stops in order."""
        return [rs.stop for rs in self.route_stops.select_related('stop').order_by('order')]
    
    def resolve_can_optimize(self, info):
        """Resolve whether route can be optimized."""
        return self.route_stops.count() >= 2
    
    def resolve_optimization_status(self, info):
        """Resolve optimization status."""
        if self.is_optimized:
            return f"Optimized ({self.optimization_provider or 'unknown'})"
        elif self.route_stops.count() >= 2:
            return "Ready for optimization"
        else:
            return "Need at least 2 stops"


# =============================================================================
# RouteStop Node
# =============================================================================

class RouteStopNode(OptimizedDjangoObjectType):
    """GraphQL Node for RouteStop with distance and time calculations."""
    
    # Calculated fields
    distance_from_start_km_calculated = Float(description="Calculated distance from start")
    time_from_start_minutes_calculated = Float(description="Calculated time from start")
    is_first_stop = Boolean(description="Whether this is the first stop")
    is_last_stop = Boolean(description="Whether this is the last stop")
    stop_count = Int(description="Total stops in this route")
    
    class Meta:
        model = RouteStop
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'route': ['exact'],
            'stop': ['exact'],
            # Numeric fields
            'order': ['gte', 'lte', 'exact'],
            'distance_from_start_km': ['gte', 'lte'],
            'estimated_time_from_start': ['gte', 'lte'],
            # Date fields
            'actual_arrival_time': ['gte', 'lte'],
            'actual_departure_time': ['gte', 'lte'],
        }
    
    def resolve_distance_from_start_km_calculated(self, info):
        """Resolve calculated distance from start."""
        if hasattr(self, 'calculate_distance_from_start'):
            return self.calculate_distance_from_start()
        return self.distance_from_start_km
    
    def resolve_time_from_start_minutes_calculated(self, info):
        """Resolve calculated time from start."""
        if hasattr(self, 'calculate_time_from_start'):
            return self.calculate_time_from_start()
        return self.estimated_time_from_start
    
    def resolve_is_first_stop(self, info):
        """Resolve whether this is the first stop."""
        return self.order == 0
    
    def resolve_is_last_stop(self, info):
        """Resolve whether this is the last stop."""
        if hasattr(self.route, 'route_stops'):
            return self.order == self.route.route_stops.count() - 1
        return False
    
    def resolve_stop_count(self, info):
        """Resolve total number of stops."""
        if hasattr(self.route, 'route_stops'):
            return self.route.route_stops.count()
        return 0
    
    def resolve_stop_details(self, info):
        """Resolve detailed stop information."""
        return self.stop
    
    def resolve_route_details(self, info):
        """Resolve detailed route information."""
        return self.route
    
    def resolve_previous_stop(self, info):
        """Resolve previous stop."""
        previous = RouteStop.objects.filter(
            route=self.route,
            order__lt=self.order
        ).order_by('-order').first()
        return previous.stop if previous else None
    
    def resolve_next_stop(self, info):
        """Resolve next stop."""
        next_stop = RouteStop.objects.filter(
            route=self.route,
            order__gt=self.order
        ).order_by('order').first()
        return next_stop.stop if next_stop else None

