# graphql/transport/types/telemetry.py

"""
GraphQL Nodes for Vehicle Telemetry and Predictive Alerts.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, Date
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.maintenance.telemetry import VehicleTelemetry, PredictiveAlert
from transport.models.maintenance.vehicle import Vehicle



class VehicleTelemetryNode(OptimizedDjangoObjectType):
    
    class Meta:
        model = VehicleTelemetry
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'vehicle__license_plate': ['exact', 'icontains'],
            
            # Float fields - Engine
            'engine_temperature': ['exact', 'gte', 'lte'],
            'oil_pressure': ['exact', 'gte', 'lte'],
            'oil_level': ['exact', 'gte', 'lte'],
            'battery_voltage': ['exact', 'gte', 'lte'],
            
            # Float fields - Tires
            'tire_pressure_front_left': ['exact', 'gte', 'lte'],
            'tire_pressure_front_right': ['exact', 'gte', 'lte'],
            'tire_pressure_rear_left': ['exact', 'gte', 'lte'],
            'tire_pressure_rear_right': ['exact', 'gte', 'lte'],
            'tire_tread_depth': ['exact', 'gte', 'lte'],
            
            # Float fields - Fuel & Odometer
            'fuel_level': ['exact', 'gte', 'lte'],
            'odometer_reading': ['exact', 'gte', 'lte'],
            'average_fuel_consumption': ['exact', 'gte', 'lte'],
            
            # Date fields
            'recorded_at': ['exact', 'gte', 'lte'],
        }
       
    
    
class PredictiveAlertNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Predictive Alert with full alert details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    alert_type_display = String(description="Human-readable alert type display")
    severity_display = String(description="Human-readable severity display")
    severity_color = String(description="Color code for severity")
    is_high_priority = Boolean(description="Whether alert is high priority")
    is_critical = Boolean(description="Whether alert is critical")
    is_resolved_status = Boolean(description="Whether alert is resolved")
    days_until_recommended_action = Int(description="Days until recommended action")
    days_until_predicted_failure = Int(description="Days until predicted failure")
    confidence_score_display = String(description="Formatted confidence score")
    age_in_days = Int(description="Age of alert in days")
   
    class Meta:
        model = PredictiveAlert
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'vehicle__license_plate': ['exact', 'icontains'],
            
            # String fields
            'alert_type': ['exact'],
            'severity': ['exact'],
            'title': ['exact', 'icontains'],
            'description': ['exact', 'icontains'],
            'predicted_issue': ['exact', 'icontains'],
            'resolution_notes': ['exact', 'icontains'],
            
            # Numeric fields
            'confidence_score': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_resolved': ['exact'],
            
            # Date fields
            'predicted_failure_date': ['exact', 'gte', 'lte', 'isnull'],
            'recommended_action_date': ['exact', 'gte', 'lte'],
            'resolved_at': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_alert_type_display(self, info):
        """Resolve human-readable alert type display."""
        return dict(self._meta.model._meta.get_field('alert_type').choices).get(
            self.alert_type, self.alert_type
        )
    
    def resolve_severity_display(self, info):
        """Resolve human-readable severity display."""
        return dict(self._meta.model._meta.get_field('severity').choices).get(
            self.severity, self.severity
        )
    
    def resolve_severity_color(self, info):
        """Resolve color code for severity."""
        colors = {
            'low': '#4CAF50',      # Green
            'medium': '#FF9800',   # Orange
            'high': '#F44336',     # Red
            'critical': '#9C27B0', # Purple
        }
        return colors.get(self.severity, '#9E9E9E')
    
    def resolve_is_high_priority(self, info):
        """Resolve whether alert is high priority."""
        return self.severity in ['high', 'critical']
    
    def resolve_is_critical(self, info):
        """Resolve whether alert is critical."""
        return self.severity == 'critical'
    
    def resolve_is_resolved_status(self, info):
        """Resolve whether alert is resolved."""
        return self.is_resolved
    
    def resolve_days_until_recommended_action(self, info):
        """Resolve days until recommended action."""
        if self.is_resolved:
            return None
        now = timezone.now().date()
        if self.recommended_action_date > now:
            return (self.recommended_action_date - now).days
        return 0
    
    def resolve_days_until_predicted_failure(self, info):
        """Resolve days until predicted failure."""
        if not self.predicted_failure_date:
            return None
        if self.is_resolved:
            return None
        now = timezone.now().date()
        if self.predicted_failure_date > now:
            return (self.predicted_failure_date - now).days
        return 0
    
    def resolve_confidence_score_display(self, info):
        """Resolve formatted confidence score."""
        return f"{self.confidence_score}%"
    
    def resolve_age_in_days(self, info):
        """Resolve age of alert in days."""
        now = timezone.now()
        return (now - self.created_at).days
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_vehicle_details(self, info):
        """Resolve vehicle details."""
        return self.vehicle
    
    def resolve_related_telemetry(self, info):
        """Resolve related telemetry data."""
        return VehicleTelemetry.objects.filter(
            vehicle=self.vehicle
        ).order_by('-recorded_at').first()
