# graphql/transport/types/maintenance.py

"""
GraphQL Nodes for Maintenance Schedule and Maintenance Log.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, Date
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.maintenance.maintenance_schedule import MaintenanceSchedule, MaintenanceLog
from transport.models.maintenance.vehicle import Vehicle




class MaintenanceScheduleNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Maintenance Schedule with full scheduling details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status_display = String(description="Human-readable status display")
    maintenance_type_display = String(description="Human-readable maintenance type display")
    is_overdue_status = Boolean(description="Whether schedule is overdue")
    is_completed = Boolean(description="Whether maintenance is completed")
    is_in_progress = Boolean(description="Whether maintenance is in progress")
    is_scheduled = Boolean(description="Whether maintenance is scheduled")
    is_cancelled = Boolean(description="Whether maintenance is cancelled")
    days_until_scheduled = Int(description="Days until scheduled date")
    days_overdue = Int(description="Days overdue if applicable")
    cost_display = String(description="Formatted cost")
    estimated_duration_display = String(description="Formatted estimated duration")
    completion_rate = Float(description="Completion rate percentage")
    
    class Meta:
        model = MaintenanceSchedule
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'vehicle__license_plate': ['exact', 'icontains'],
            'verified_by': ['exact'],
            'verified_by__email': ['exact', 'icontains'],
            
            # String fields
            'maintenance_type': ['exact'],
            'status': ['exact'],
            'service_center': ['exact', 'icontains', 'istartswith'],
            'technician_notes': ['exact', 'icontains'],
            'description': ['exact', 'icontains'],
            
            # Numeric fields
            'cost': ['exact', 'gte', 'lte'],
            'mileage_at_service': ['exact', 'gte', 'lte'],
            'last_service_odometer': ['exact', 'gte', 'lte'],
            'next_service_odometer': ['exact', 'gte', 'lte'],
            'time_interval_days': ['exact', 'gte', 'lte'],
            'distance_interval_km': ['exact', 'gte', 'lte'],
            'recurrence_interval': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_overdue': ['exact'],
            'is_urgent': ['exact'],
            'is_recurring': ['exact'],
            'is_verified': ['exact'],
            
            # Date fields
            'scheduled_date': ['exact', 'gte', 'lte'],
            'completed_date': ['exact', 'gte', 'lte', 'isnull'],
            'last_service_date': ['exact', 'gte', 'lte', 'isnull'],
            'next_service_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return self.get_status_display()
    
    def resolve_maintenance_type_display(self, info):
        """Resolve human-readable maintenance type display."""
        return self.get_maintenance_type_display()
    
    def resolve_is_overdue_status(self, info):
        """Resolve whether schedule is overdue."""
        return self.is_overdue
    
    def resolve_is_completed(self, info):
        """Resolve whether maintenance is completed."""
        return self.status == self.Status.COMPLETED
    
    def resolve_is_in_progress(self, info):
        """Resolve whether maintenance is in progress."""
        return self.status == self.Status.IN_PROGRESS
    
    def resolve_is_scheduled(self, info):
        """Resolve whether maintenance is scheduled."""
        return self.status == self.Status.SCHEDULED
    
    def resolve_is_cancelled(self, info):
        """Resolve whether maintenance is cancelled."""
        return self.status == self.Status.CANCELLED
    
    def resolve_days_until_scheduled(self, info):
        """Resolve days until scheduled date."""
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return None
        now = timezone.now()
        if self.scheduled_date > now:
            return (self.scheduled_date - now).days
        return 0
    
    def resolve_days_overdue(self, info):
        """Resolve days overdue if applicable."""
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return 0
        if self.is_overdue and self.scheduled_date:
            now = timezone.now()
            if now > self.scheduled_date:
                return (now - self.scheduled_date).days
        return 0
    
    def resolve_cost_display(self, info):
        """Resolve formatted cost."""
        if self.cost is not None:
            return f"${self.cost:,.2f}"
        return None
    
    def resolve_estimated_duration_display(self, info):
        """Resolve formatted estimated duration."""
        if self.estimated_duration:
            hours = self.estimated_duration.total_seconds() / 3600
            if hours >= 1:
                return f"{hours:.1f} hours"
            return f"{self.estimated_duration.total_seconds() / 60:.0f} minutes"
        return None
    
    def resolve_completion_rate(self, info):
        """Resolve completion rate percentage."""
        total = MaintenanceSchedule.objects.filter(vehicle=self.vehicle).count()
        if total == 0:
            return 0
        completed = MaintenanceSchedule.objects.filter(
            vehicle=self.vehicle,
            status=self.Status.COMPLETED
        ).count()
        return (completed / total) * 100
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_vehicle_details(self, info):
        """Resolve vehicle details."""
        return self.vehicle
    
    def resolve_verified_by_details(self, info):
        """Resolve user who verified this maintenance."""
        return self.verified_by
    
    def resolve_logs(self, info):
        """Resolve associated logs."""
        return self.logs.all().order_by('-log_date')
    
    def resolve_latest_log(self, info):
        """Resolve latest log entry."""
        return self.logs.order_by('-log_date').first()


class MaintenanceLogNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Maintenance Log with full log details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    log_type_display = String(description="Human-readable log type display")
    cost_display = String(description="Formatted cost")
    is_verified_status = Boolean(description="Whether log is verified")
    days_ago = Int(description="Days since log entry")
    parts_count = Int(description="Number of parts changed")
    
    class Meta:
        model = MaintenanceLog
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'vehicle': ['exact'],
            'vehicle__make': ['exact', 'icontains'],
            'vehicle__license_plate': ['exact', 'icontains'],
            'maintenance_schedule': ['exact'],
            'verified_by': ['exact'],
            'verified_by__email': ['exact', 'icontains'],
            
            # String fields
            'log_type': ['exact'],
            'title': ['exact', 'icontains'],
            'description': ['exact', 'icontains'],
            'technician': ['exact', 'icontains'],
            'service_provider': ['exact', 'icontains'],
            
            # Numeric fields
            'mileage': ['exact', 'gte', 'lte'],
            'odometer_reading': ['exact', 'gte', 'lte'],
            'cost': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_verified': ['exact'],
            
            # Date fields
            'log_date': ['exact', 'gte', 'lte'],
            'service_date': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
        }
        ordering = [
            '-log_date',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_log_type_display(self, info):
        """Resolve human-readable log type display."""
        return self.get_log_type_display()
    
    def resolve_cost_display(self, info):
        """Resolve formatted cost."""
        if self.cost is not None:
            return f"${self.cost:,.2f}"
        return None
    
    def resolve_is_verified_status(self, info):
        """Resolve whether log is verified."""
        return self.is_verified
    
    def resolve_days_ago(self, info):
        """Resolve days since log entry."""
        now = timezone.now()
        return (now - self.log_date).days
    
    def resolve_parts_count(self, info):
        """Resolve number of parts changed."""
        if self.parts_changed:
            return len(self.parts_changed)
        return 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_vehicle_details(self, info):
        """Resolve vehicle details."""
        return self.vehicle
    
    def resolve_maintenance_schedule_details(self, info):
        """Resolve associated maintenance schedule."""
        return self.maintenance_schedule
    
    def resolve_verified_by_details(self, info):
        """Resolve user who verified this log."""
        return self.verified_by

