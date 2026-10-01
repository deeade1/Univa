# graphql/transport/types/trip_schedule_template.py

"""
GraphQL Node for Trip Schedule Template with full template management capabilities.
"""

from graphene import Node, Boolean, String, Field, List, Decimal, Time, UUID, DateTime, Int
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rides.schedule import TripScheduleTemplate
from transport.models.rides.trip import Trip


class TripScheduleTemplateNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Trip Schedule Template with recurring trip management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    days_of_week_display = String(description="Human-readable days of week display")
    route_display = String(description="Full route display (city to city)")
    is_active = Boolean(description="Whether template is active")
    days_count = Int(description="Number of days in the schedule")
    weekday_names = List(String, description="List of weekday names")
    
    class Meta:
        model = TripScheduleTemplate
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'route_name': ['exact', 'icontains', 'istartswith'],
            'departure_state': ['exact', 'icontains'],
            'departure_city': ['exact', 'icontains'],
            'destination_state': ['exact', 'icontains'],
            'destination_city': ['exact', 'icontains'],
            'vehicle_type': ['exact', 'icontains'],
            
            # Numeric fields
            'base_fare': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'active': ['exact'],
            
            # Time fields
            'departure_time': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_days_of_week_display(self, info):
        """Resolve human-readable days of week display."""
        if not self.days_of_week:
            return "No days set"
        
        day_names = {
            0: "Monday",
            1: "Tuesday", 
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"
        }
        
        days = [day_names.get(d, str(d)) for d in self.days_of_week if d in day_names]
        return ", ".join(days)
    
    def resolve_route_display(self, info):
        """Resolve full route display."""
        return f"{self.departure_city} → {self.destination_city}"
    
    def resolve_is_active(self, info):
        """Resolve whether template is active."""
        return self.active
    
    def resolve_days_count(self, info):
        """Resolve number of days in the schedule."""
        return len(self.days_of_week) if self.days_of_week else 0
    
    def resolve_weekday_names(self, info):
        """Resolve list of weekday names."""
        if not self.days_of_week:
            return []
        
        day_names = {
            0: "Monday",
            1: "Tuesday", 
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"
        }
        
        return [day_names.get(d, str(d)) for d in self.days_of_week if d in day_names]
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_upcoming_trips(self, info):
        """Resolve upcoming trips from this template."""
        from transport.models.trip.trip import Trip
        
        now = timezone.now()
        return Trip.objects.filter(
            trip_template_id=self.id,
            departure_time__gte=now,
            status__in=['scheduled', 'departed', 'in_transit']
        ).order_by('departure_time')[:10]
    
    def resolve_recent_trips(self, info):
        """Resolve recent trips from this template."""
        from transport.models.trip.trip import Trip
        
        return Trip.objects.filter(
            trip_template_id=self.id
        ).order_by('-departure_time')[:10]
    
    def resolve_trip_count(self, info):
        """Resolve total trips created from this template."""
        from transport.models.trip.trip import Trip
        return Trip.objects.filter(trip_template_id=self.id).count()

