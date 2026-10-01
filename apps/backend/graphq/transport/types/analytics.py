# graphql/transport/types/analytics.py

"""
GraphQL Nodes for Analytics including AnalyticsProfile, RideMetrics, and KPI.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.shared.analytics import AnalyticsProfile, RideMetrics, KPI
from transport.models.rides.trip import Trip


class AnalyticsProfileNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AnalyticsProfile with user analytics preferences.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    report_frequency_display = String(description="Human-readable report frequency display")
    is_tracking_enabled = Boolean(description="Whether any tracking is enabled")
    tracking_summary = String(description="Summary of tracking preferences")
    
   
    class Meta:
        model = AnalyticsProfile
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            
            # Boolean fields
            'track_ride_metrics': ['exact'],
            'track_environmental_impact': ['exact'],
            'track_cost_savings': ['exact'],
            'track_accessibility_usage': ['exact'],
            'share_aggregate_data': ['exact'],
            'share_for_research': ['exact'],
            
            # String fields
            'report_frequency': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
       
    
    def resolve_report_frequency_display(self, info):
        """Resolve human-readable report frequency display."""
        return dict(self._meta.model._meta.get_field('report_frequency').choices).get(
            self.report_frequency, self.report_frequency
        )
    
    def resolve_is_tracking_enabled(self, info):
        """Resolve whether any tracking is enabled."""
        return any([
            self.track_ride_metrics,
            self.track_environmental_impact,
            self.track_cost_savings,
            self.track_accessibility_usage,
        ])
    
    def resolve_tracking_summary(self, info):
        """Resolve summary of tracking preferences."""
        enabled = []
        if self.track_ride_metrics:
            enabled.append("Ride Metrics")
        if self.track_environmental_impact:
            enabled.append("Environmental Impact")
        if self.track_cost_savings:
            enabled.append("Cost Savings")
        if self.track_accessibility_usage:
            enabled.append("Accessibility Usage")
        
        return f"Tracking: {', '.join(enabled) if enabled else 'None'}"
    
    def resolve_user_details(self, info):
        """Resolve user who owns this analytics profile."""
        return self.user
    
    def resolve_ride_metrics(self, info):
        """Resolve ride metrics for this user."""
        return RideMetrics.objects.filter(ride__customer=self.user).order_by('-created_at')
    
    @classmethod
    def get_queryset(cls, queryset, info):
        """Only allow users to see their own analytics profiles."""
        user = info.context.user
        if user.is_authenticated:
            if user.is_staff:
                return queryset
            return queryset.filter(user=user)
        return queryset.none()
    
    @classmethod
    def get_node(cls, info, id):
        """Get single node with permission check."""
        try:
            analytics_profile = cls._meta.model.objects.get(pk=id)
            user = info.context.user
            
            if not user.is_authenticated:
                return None
            
            if user.is_staff or analytics_profile.user == user:
                return analytics_profile
            
            return None
        except cls._meta.model.DoesNotExist:
            return None


class RideMetricsNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for RideMetrics with detailed ride analytics.
    """
    
    # ============================================================
    # Custom Calculated Fields
    # ============================================================
    
    cost_per_km = Float(description="Cost per kilometer")
    co2_savings_kg = Float(description="CO2 savings compared to personal car")
    environmental_impact_score = Float(description="Environmental impact score (0-100)")
    efficiency_score = Float(description="Overall efficiency score (0-100)")
    cost_efficiency = Float(description="Cost efficiency ratio")
    
    class Meta:
        model = RideMetrics
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'ride': ['exact'],
            'ride__id': ['exact'],
            'ride__customer__email': ['exact', 'icontains'],
            
            # Numeric fields
            'distance_km': ['exact', 'gte', 'lte'],
            'duration_minutes': ['exact', 'gte', 'lte'],
            'average_speed_kmh': ['exact', 'gte', 'lte'],
            'fuel_consumption_liters': ['exact', 'gte', 'lte', 'isnull'],
            'energy_consumption_kwh': ['exact', 'gte', 'lte', 'isnull'],
            'co2_emissions_kg': ['exact', 'gte', 'lte'],
            'particulate_matter_emissions': ['exact', 'gte', 'lte'],
            'operational_cost': ['exact', 'gte', 'lte'],
            'maintenance_cost_share': ['exact', 'gte', 'lte'],
            'passenger_comfort_score': ['exact', 'gte', 'lte', 'isnull'],
            'accessibility_score': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            '-created_at',
            '-distance_km',
        ]
    
    def resolve_cost_per_km(self, info):
        """Calculate cost per kilometer."""
        if self.distance_km and self.distance_km > 0:
            return float(self.operational_cost / self.distance_km)
        return 0
    
    def resolve_co2_savings_kg(self, info):
        """Calculate CO2 savings compared to personal car."""
        # Assuming personal car emits 0.2 kg CO2 per km
        personal_car_emissions = self.distance_km * 0.2
        return max(0, personal_car_emissions - self.co2_emissions_kg)
    
    def resolve_environmental_impact_score(self, info):
        """Calculate environmental impact score (0-100)."""
        score = 0
        factors = 0
        
        if self.co2_emissions_kg and self.distance_km > 0:
            # Lower CO2 is better (scale: 0.05 kg/km = 100, 0.3 kg/km = 0)
            co2_per_km = self.co2_emissions_kg / self.distance_km
            co2_score = max(0, min(100, (0.3 - co2_per_km) / 0.25 * 100))
            score += co2_score * 0.4
            factors += 0.4
        
        if self.particulate_matter_emissions:
            pm_score = max(0, min(100, 100 - (self.particulate_matter_emissions * 100)))
            score += pm_score * 0.3
            factors += 0.3
        
        if self.accessibility_score is not None:
            score += self.accessibility_score * 0.3
            factors += 0.3
        
        if factors > 0:
            return round(score / factors, 2)
        return 0
    
    def resolve_efficiency_score(self, info):
        """Calculate overall efficiency score (0-100)."""
        scores = []
        
        # Speed efficiency (optimal speed ~50-60 km/h)
        if self.average_speed_kmh:
            speed_score = 100 - abs(self.average_speed_kmh - 55) * 1.5
            scores.append(max(0, min(100, speed_score)))
        
        # Environmental impact
        env_score = self.resolve_environmental_impact_score(info)
        if env_score > 0:
            scores.append(env_score)
        
        # Cost efficiency
        cost_per_km = self.resolve_cost_per_km(info)
        if cost_per_km > 0:
            # Assume optimal cost is $0.50/km
            cost_score = max(0, min(100, (1.0 - cost_per_km) * 100))
            scores.append(cost_score)
        
        if scores:
            return round(sum(scores) / len(scores), 2)
        return 0
    
    def resolve_cost_efficiency(self, info):
        """Calculate cost efficiency ratio."""
        if self.distance_km and self.distance_km > 0:
            return float(self.operational_cost / (self.distance_km * 0.5))
        return 0
    
    def resolve_ride_details(self, info):
        """Resolve ride details."""
        return self.ride
    
    @classmethod
    def get_queryset(cls, queryset, info):
        """Apply permission-based filtering."""
        user = info.context.user
        if user.is_authenticated:
            if user.is_staff:
                return queryset
            
            # Users can see metrics for their own rides
            return queryset.filter(ride__customer=user).distinct()
        
        return queryset.none()
    
    @classmethod
    def get_node(cls, info, id):
        """Get single node with permission check."""
        try:
            ride_metrics = cls._meta.model.objects.get(pk=id)
            user = info.context.user
            
            if not user.is_authenticated:
                return None
            
            if user.is_staff or ride_metrics.ride.customer == user:
                return ride_metrics
            
            return None
        except cls._meta.model.DoesNotExist:
            return None


class KPINode(OptimizedDjangoObjectType):
    """
    GraphQL Node for KPI with performance tracking.
    """
    
    # ============================================================
    # Custom Fields
    # ============================================================
    
    performance_percentage = Float(description="Performance against target as percentage")
    status = String(description="KPI status based on target")
    trend = String(description="Trend based on historical data")
    category_display = String(description="Human-readable category display")
    is_met = Boolean(description="Whether KPI target is met")
    
    class Meta:
        model = KPI
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'category': ['exact'],
            'unit': ['exact', 'icontains'],
            
            # Numeric fields
            'value': ['exact', 'gte', 'lte'],
            'target': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'period_start': ['exact', 'gte', 'lte'],
            'period_end': ['exact', 'gte', 'lte'],
            'calculated_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            '-calculated_at',
            'category',
            'name',
        ]
    
    def resolve_performance_percentage(self, info):
        """Calculate performance against target."""
        if self.target and self.target > 0:
            return round((self.value / self.target) * 100, 2)
        return None
    
    def resolve_status(self, info):
        """Determine KPI status based on target."""
        if not self.target:
            return 'no_target'
        
        percentage = self.resolve_performance_percentage(info)
        if percentage is None:
            return 'no_target'
        
        if percentage >= 100:
            return 'exceeded'
        elif percentage >= 90:
            return 'on_track'
        elif percentage >= 75:
            return 'needs_attention'
        else:
            return 'critical'
    
    def resolve_trend(self, info):
        """Calculate trend based on historical data."""
        # Get previous period's KPI for comparison
        previous_kpi = KPI.objects.filter(
            name=self.name,
            category=self.category,
            period_end__lt=self.period_start
        ).order_by('-period_end').first()
        
        if previous_kpi and previous_kpi.value > 0:
            change = ((self.value - previous_kpi.value) / previous_kpi.value) * 100
            
            if change > 5:
                return 'improving'
            elif change < -5:
                return 'declining'
            else:
                return 'stable'
        
        return 'no_data'
    
    def resolve_category_display(self, info):
        """Resolve human-readable category display."""
        return dict(self._meta.model._meta.get_field('category').choices).get(
            self.category, self.category
        )
    
    def resolve_is_met(self, info):
        """Resolve whether KPI target is met."""
        if not self.target:
            return None
        return self.value >= self.target
    
    @classmethod
    def get_queryset(cls, queryset, info):
        """Apply permission-based filtering."""
        user = info.context.user
        if user.is_authenticated:
            if user.is_staff:
                return queryset
            
            # Regular users can see aggregate KPIs (no personal data)
            return queryset.filter(
                category__in=['environmental', 'operational', 'customer']
            ).exclude(
                name__icontains='personal'
            )
        
        # Anonymous users can see public KPIs
        return queryset.filter(
            category__in=['environmental', 'operational']
        )
    
    @classmethod
    def get_node(cls, info, id):
        """Get single node with permission check."""
        try:
            kpi = cls._meta.model.objects.get(pk=id)
            user = info.context.user
            
            if not user.is_authenticated:
                if kpi.category in ['environmental', 'operational']:
                    return kpi
                return None
            
            if user.is_staff:
                return kpi
            
            # Regular users can access non-personal KPIs
            if 'personal' in kpi.name.lower() or 'individual' in kpi.name.lower():
                return None
            
            return kpi
        except cls._meta.model.DoesNotExist:
            return None
