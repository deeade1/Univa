# graphql/transport/types/tracking.py

"""
GraphQL Nodes for Real-time Tracking, Traffic Conditions, and Emergency Alerts.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, UUID
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_gis.converter import gis_converter

from transport.models.shared.realtime import RealTimeTracking, TrafficConditions, EmergencyAlert




class RealTimeTrackingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Real-time Tracking with location capabilities.
    """
    
    # ============================================================
    # Location Fields (from LocationModel via location FK)
    # ============================================================
    
    lat = Float(description="Current latitude")
    lng = Float(description="Current longitude")
    has_location = Boolean(description="Whether location is set")
   
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    platform_display = String(description="Human-readable platform display")
    is_online = Boolean(description="Whether device is reporting online")
    location_age_seconds = Float(description="Age of location data in seconds")
   
    class Meta:
        model = RealTimeTracking
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__id': ['exact'],
            'vehicle__license_plate': ['exact', 'icontains'],
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            'location': ['exact'],
            
            # String fields
            'platform': ['exact'],
            'device_id': ['exact', 'icontains'],
            'app_version': ['exact', 'icontains'],
            
            # Numeric fields
            'speed': ['exact', 'gte', 'lte'],
            'heading': ['exact', 'gte', 'lte'],
            'accuracy': ['exact', 'gte', 'lte', 'isnull'],
            'altitude': ['exact', 'gte', 'lte', 'isnull'],
            'battery_level': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_moving': ['exact'],
            
            # Date fields
            'timestamp': ['exact', 'gte', 'lte'],
        }
       
    
    def resolve_lat(self, info):
        """Resolve current latitude."""
        return self.current_lat
    
    def resolve_lng(self, info):
        """Resolve current longitude."""
        return self.current_lng
    
    def resolve_has_location(self, info):
        """Resolve whether location is set."""
        return self.has_location
    
    def resolve_location_details(self, info):
        """Resolve detailed location information."""
        return self.location
    
    def resolve_platform_display(self, info):
        """Resolve human-readable platform display."""
        if self.platform:
            return self.get_platform_display()
        return None
    
    def resolve_is_online(self, info):
        """Resolve whether device is reporting online."""
        # Consider online if timestamp is within last 5 minutes
        if self.timestamp:
            age = (timezone.now() - self.timestamp).total_seconds()
            return age < 300  # 5 minutes
        return False
    
    def resolve_location_age_seconds(self, info):
        """Resolve age of location data in seconds."""
        if self.timestamp:
            return (timezone.now() - self.timestamp).total_seconds()
        return None
    
    def resolve_vehicle_details(self, info):
        """Resolve vehicle being tracked."""
        return self.vehicle
    
    def resolve_service_request_details(self, info):
        """Resolve service request details."""
        return self.service_request


class TrafficConditionsNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Traffic Conditions with location capabilities.
    """
    
    # ============================================================
    # Location Fields
    # ============================================================
    
    lat = Float(description="Latitude of traffic condition")
    lng = Float(description="Longitude of traffic condition")
    has_location = Boolean(description="Whether location is set")
   
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    traffic_level_display = String(description="Human-readable traffic level display")
    source_display = String(description="Human-readable source display")
    is_valid = Boolean(description="Whether traffic data is still valid")
    validity_hours = Float(description="Hours remaining until data expires")
    
    class Meta:
        model = TrafficConditions
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'location': ['exact'],
            
            # String fields
            'traffic_level': ['exact'],
            'road_name': ['exact', 'icontains', 'istartswith'],
            'source': ['exact'],
            
            # Numeric fields
            'average_speed': ['exact', 'gte', 'lte'],
            'delay_minutes': ['exact', 'gte', 'lte'],
            'confidence': ['exact', 'gte', 'lte'],
            
            # Date fields
            'recorded_at': ['exact', 'gte', 'lte'],
            'valid_until': ['exact', 'gte', 'lte'],
        }
        ordering = [
            '-recorded_at',
            'traffic_level',
        ]
    
    def resolve_lat(self, info):
        """Resolve latitude of traffic condition."""
        return self.lat
    
    def resolve_lng(self, info):
        """Resolve longitude of traffic condition."""
        return self.lng
    
    def resolve_has_location(self, info):
        """Resolve whether location is set."""
        return self.location is not None or self.location_point is not None
    
    def resolve_location_details(self, info):
        """Resolve detailed location information."""
        return self.location
    
    def resolve_traffic_level_display(self, info):
        """Resolve human-readable traffic level display."""
        return self.traffic_level_display
    
    def resolve_source_display(self, info):
        """Resolve human-readable source display."""
        if self.source:
            return self.get_source_display()
        return None
    
    def resolve_is_valid(self, info):
        """Resolve whether traffic data is still valid."""
        return self.is_valid
    
    def resolve_validity_hours(self, info):
        """Resolve hours remaining until data expires."""
        if self.valid_until:
            now = timezone.now()
            if now < self.valid_until:
                return (self.valid_until - now).total_seconds() / 3600
            return 0
        return None


class EmergencyAlertNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Emergency Alerts with location capabilities.
    """
    
    # ============================================================
    # Location Fields
    # ============================================================
    
    lat = Float(description="Latitude of emergency")
    lng = Float(description="Longitude of emergency")
    has_location = Boolean(description="Whether location is set")
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    alert_type_display = String(description="Human-readable alert type display")
    severity_display = String(description="Human-readable severity display")
    status_display = String(description="Human-readable status display")
    is_active = Boolean(description="Whether alert is active")
    is_acknowledged = Boolean(description="Whether alert is acknowledged")
    is_resolved = Boolean(description="Whether alert is resolved")
    age_hours = Float(description="Age of alert in hours")
    acknowledged_count = Int(description="Number of acknowledgements")
    
    
    class Meta:
        model = EmergencyAlert
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'location': ['exact'],
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            'reported_by': ['exact'],
            'reported_by__email': ['exact', 'icontains'],
            
            # String fields
            'alert_type': ['exact'],
            'severity': ['exact'],
            'status': ['exact'],
            'title': ['exact', 'icontains'],
            'location_description': ['exact', 'icontains'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'acknowledged_at': ['exact', 'gte', 'lte', 'isnull'],
            'resolved_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        ordering = [
            '-created_at',
            '-severity',
        ]
    
    def resolve_lat(self, info):
        """Resolve latitude of emergency."""
        return self.lat
    
    def resolve_lng(self, info):
        """Resolve longitude of emergency."""
        return self.lng
    
    def resolve_has_location(self, info):
        """Resolve whether location is set."""
        return self.has_location
    
    def resolve_location_details(self, info):
        """Resolve detailed location information."""
        return self.location
    
    def resolve_alert_type_display(self, info):
        """Resolve human-readable alert type display."""
        return self.alert_type_display
    
    def resolve_severity_display(self, info):
        """Resolve human-readable severity display."""
        return self.severity_display
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return self.status_display
    
    def resolve_is_active(self, info):
        """Resolve whether alert is active."""
        return self.is_active()
    
    def resolve_is_acknowledged(self, info):
        """Resolve whether alert is acknowledged."""
        return self.is_acknowledged()
    
    def resolve_is_resolved(self, info):
        """Resolve whether alert is resolved."""
        return self.is_resolved()
    
    def resolve_age_hours(self, info):
        """Resolve age of alert in hours."""
        if self.created_at:
            return (timezone.now() - self.created_at).total_seconds() / 3600
        return None
    
    def resolve_acknowledged_count(self, info):
        """Resolve number of acknowledgements."""
        return self.acknowledged_by.count()
    
    def resolve_reported_by_details(self, info):
        """Resolve user who reported the emergency."""
        return self.reported_by
    
    def resolve_service_request_details(self, info):
        """Resolve service request details."""
        return self.service_request
    
    def resolve_acknowledged_by_details(self, info):
        """Resolve providers who acknowledged this alert."""
        return self.acknowledged_by.all()
