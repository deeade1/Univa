# transport/models/delivery/logistics.py

"""
Transport/Delivery/Logistics Models
Using canonical LocationModel and routing services from core.
"""


from typing import Any, Dict, Optional

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.location import LocationModel
from core.services.routing import (
    haversine_distance,
    estimate_eta,
    RouteOptimizer,
)
# =============================================================================
# Stop Point Model
# =============================================================================

class StopPoint(LocationModel):
    """
    A physical stop point (delivery address, pickup location, etc.)
    Inherits location fields from LocationModel.
    """
    
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the stop point")
    )
    
    stop_type = models.CharField(
        max_length=20,
        choices=[
            ('delivery', _('Delivery')),
            ('pickup', _('Pickup')),
            ('transit', _('Transit')),
            ('warehouse', _('Warehouse')),
            ('fuel', _('Fuel Station')),
            ('rest', _('Rest Stop')),
        ],
        default='delivery',
        help_text=_("Type of stop")
    )
    
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Contact phone number")
    )
    
    contact_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Contact person name")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about this stop")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this stop point is active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Stop Point")
        verbose_name_plural = _("Stop Points")
        indexes = [
            models.Index(fields=['stop_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.stop_type})"
    
    def get_distance_to(self, other_stop: 'StopPoint') -> float:
        """Get distance in kilometers to another stop."""
        if not self.coordinates or not other_stop.coordinates:
            return None
        return haversine_distance(
            self.coordinates[0], self.coordinates[1],
            other_stop.coordinates[0], other_stop.coordinates[1]
        )


# =============================================================================
# Route Model
# =============================================================================

class Route(models.Model):
    """
    Optimized route model for deliveries and trips.
    Uses core.services.routing for calculations.
    """
    
    trip = models.ForeignKey(
        'transport.ServiceRequest',
        on_delete=models.CASCADE,
        related_name='routes',
        db_index=True,
        help_text=_("The trip this route belongs to")
    )
    
    # Route geometry
    path = gis_models.LineStringField(
        geography=True,
        null=True,
        blank=True,
        help_text=_("Path of the route")
    )
    
    # Route details (populated from routing service)
    distance_km = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Total distance in kilometers")
    )
    
    duration_minutes = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Estimated duration in minutes")
    )
    
    # Waypoints (stored as JSON for quick access)
    waypoints = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of waypoints along the route")
    )
    
    # Traffic and conditions
    traffic_delay_minutes = models.FloatField(
        default=0,
        help_text=_("Traffic delay in minutes")
    )
    
    road_conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Road conditions along the route")
    )
    
    # Optimization data
    is_optimized = models.BooleanField(
        default=False,
        help_text=_("Whether route has been optimized")
    )
    
    optimization_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Route optimization score (0-100)")
    )
    
    optimization_provider = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('haversine', _('Haversine')),
            ('google', _('Google Maps')),
            ('osrm', _('OSRM')),
            ('manual', _('Manual')),
        ],
        help_text=_("Provider used for optimization")
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional route metadata")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trip']),
            models.Index(fields=['is_optimized']),
            models.Index(fields=['optimization_provider']),
            GistIndex(fields=['path'], name='route_path_gist_idx'),
        ]
        verbose_name = _("Route")
        verbose_name_plural = _("Routes")
    
    def __str__(self):
        return f"Route for {self.trip}"
    
    def optimize(self, use_google: bool = True) -> Dict[str, Any]:
        """
        Optimize this route using RouteOptimizer.
        
        Args:
            use_google: Whether to use Google Maps API
        
        Returns:
            dict: Optimization results
        """
        from core.services.routing import RouteOptimizer
        from django.conf import settings
        
        stops = self.route_stops.select_related('stop').order_by('order')
        
        if not stops:
            return {'error': 'No stops found'}
        
        # Prepare coordinates
        stop_coords = []
        for stop in stops:
            if stop.stop.coordinates:
                stop_coords.append(stop.stop.coordinates)
            else:
                return {'error': f'Stop {stop.stop} has no coordinates'}
        
        # Optimize using RouteOptimizer
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        optimizer = RouteOptimizer(api_key if use_google else None)
        
        result = optimizer.optimize_route(stop_coords, use_google=use_google)
        
        # Update route with optimized data
        if result.get('route'):
            self.distance_km = result.get('distance_km', 0)
            self.duration_minutes = result.get('duration_minutes', 0)
            self.is_optimized = True
            self.optimization_provider = result.get('provider', 'unknown')
            self.save()
            
            # Update stops order
            for idx, stop_index in enumerate(result['route']):
                route_stop = stops[stop_index]
                route_stop.order = idx
                route_stop.save()
        
        return result
    
    def get_total_distance(self) -> float:
        """Get total distance in kilometers."""
        if self.distance_km:
            return self.distance_km
        
        # Calculate from stops
        stops = self.route_stops.select_related('stop').order_by('order')
        if len(stops) < 2:
            return 0
        
        total = 0
        for i in range(len(stops) - 1):
            coord1 = stops[i].stop.coordinates
            coord2 = stops[i+1].stop.coordinates
            if coord1 and coord2:
                total += haversine_distance(
                    coord1[0], coord1[1],
                    coord2[0], coord2[1]
                )
        
        return round(total, 2)
    
    def get_total_duration(self, avg_speed_kmh: float = 40) -> Optional[int]:
        """Get total duration in minutes."""
        if self.duration_minutes:
            return self.duration_minutes
        
        distance = self.get_total_distance()
        if distance:
            return estimate_eta(distance, avg_speed_kmh)
        return None


# =============================================================================
# Route Stop Model
# =============================================================================

class RouteStop(models.Model):
    """
    Junction table linking Route to StopPoint with additional data.
    """
    
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='route_stops',
        db_index=True,
        help_text=_("The route this stop belongs to")
    )
    
    stop = models.ForeignKey(
        StopPoint,
        on_delete=models.CASCADE,
        related_name='route_stops',
        db_index=True,
        help_text=_("The stop point")
    )
    
    order = models.PositiveIntegerField(
        help_text=_("Order of this stop in the route")
    )
    
    distance_from_start_km = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Distance from route start in kilometers")
    )
    
    estimated_time_from_start = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Estimated time from route start in minutes")
    )
    
    actual_arrival_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Actual arrival time at this stop")
    )
    
    actual_departure_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Actual departure time from this stop")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Notes for this stop")
    )
    
    class Meta:
        ordering = ['order']
        unique_together = [['route', 'stop']]
        indexes = [
            models.Index(fields=['route', 'order']),
            models.Index(fields=['distance_from_start_km']),
        ]
    
    def __str__(self):
        return f"Stop {self.order} on route {self.route}"
    
    def calculate_distance_from_start(self) -> Optional[float]:
        """
        Calculate distance from route start to this stop.
        
        Returns:
            float: Distance in kilometers, or None if cannot calculate
        """
        if self.distance_from_start_km:
            return self.distance_from_start_km
        
        # Get all previous stops
        previous_stops = RouteStop.objects.filter(
            route=self.route,
            order__lt=self.order
        ).select_related('stop').order_by('order')
        
        if not previous_stops:
            return 0
        
        total = 0
        all_stops = list(previous_stops) + [self]
        
        for i in range(len(all_stops) - 1):
            coord1 = all_stops[i].stop.coordinates
            coord2 = all_stops[i+1].stop.coordinates
            if coord1 and coord2:
                total += haversine_distance(
                    coord1[0], coord1[1],
                    coord2[0], coord2[1]
                )
        
        return round(total, 2)
    
    def calculate_time_from_start(self, avg_speed_kmh: float = 40) -> Optional[int]:
        """
        Calculate estimated time from route start to this stop.
        
        Returns:
            int: Minutes, or None if cannot calculate
        """
        if self.estimated_time_from_start:
            return self.estimated_time_from_start
        
        distance = self.calculate_distance_from_start()
        if distance is not None:
            return estimate_eta(distance, avg_speed_kmh)
        return None

