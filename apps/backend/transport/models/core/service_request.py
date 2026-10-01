"""
Optimized base model for service requests - Using canonical LocationModel
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.location import LocationModel
from core.services.routing import haversine_distance, estimate_eta, get_route

logger = logging.getLogger(__name__)


class ServiceRequest(models.Model):
    """
    Optimized base model for service requests.
    Uses LocationModel composition for pickup and dropoff locations.
    """
    
    class ServiceType(models.TextChoices):
        TAXI = 'taxi', _('Taxi Ride')
        DELIVERY = 'delivery', _('Package Delivery')
        SHARED = 'shared', _('Shared Ride')
        FOOD = 'food', _('Food Delivery')
        CARGO = 'cargo', _('Cargo Transport')
        INTERSTATE = 'interstate', _('Interstate Travel')

    class Status(models.TextChoices):
        REQUESTED = 'requested', _('Requested')
        ACCEPTED = 'accepted', _('Accepted')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        SCHEDULED = "scheduled", _('Scheduled')
        DEPARTED = "departed", _('Departed')
        IN_TRANSIT = "in_transit", _('In Transit')
        ARRIVED = "arrived", _('Arrived')
    
    # Basic fields
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        db_index=True,
        help_text=_("Type of service requested")
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
        help_text=_("Current status of the request")
    )
    
    # Relationships
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transport_requests',
        db_index=True,
        help_text=_("Customer who made the request")
    )
    
    provider = models.ForeignKey(
        'transport.ServiceProviderProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_services',
        db_index=True,
        help_text=_("Provider assigned to this request")
    )
    
    vehicle = models.ForeignKey(
        'transport.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_assignments',
        db_index=True,
        help_text=_("Vehicle assigned to this request")
    )
    
    # ============================================================
    # Location Fields - Using LocationModel composition
    # ============================================================
    
    # Pickup location (required)
    pickup_location = models.ForeignKey(
        'transport.StopPoint',
        on_delete=models.PROTECT,
        related_name='pickup_requests',
        help_text=_("Pickup location")
    )
    
    # Dropoff location (optional - some services don't have dropoff)
    dropoff_location = models.ForeignKey(
        'transport.StopPoint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dropoff_requests',
        help_text=_("Dropoff location")
    )
    
    
    # ============================================================
    # Interstate Extensions (for long-distance travel)
    # ============================================================
    
    departure_state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Departure state for interstate travel")
    )
    
    departure_city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Departure city for interstate travel")
    )
    
    departure_terminal = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Departure terminal/station")
    )
    
    destination_state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Destination state for interstate travel")
    )
    
    destination_city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Destination city for interstate travel")
    )
    
    destination_terminal = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Destination terminal/station")
    )
    
    # ============================================================
    # Routing and Timing
    # ============================================================
    
    route = gis_models.LineStringField(
        geography=True,
        null=True,
        blank=True,
        help_text=_("Geographic route path")
    )
    
    estimated_distance = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Estimated distance in kilometers")
    )
    
    estimated_duration = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Estimated duration in minutes")
    )
    
    actual_distance = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Actual distance traveled in kilometers")
    )
    
    actual_duration = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Actual duration in minutes")
    )
    
    estimated_arrival_time = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Estimated arrival time")
    )
    
    # ============================================================
    # Trip Details
    # ============================================================
    
    stopovers = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of stopover dictionaries")
    )
    
    seat_map = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Optional seat map for long trips")
    )
    
    is_recurring_daily = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether this is a recurring daily trip")
    )
    
    # ============================================================
    # Luggage & Pricing
    # ============================================================
    
    luggage_capacity_kg = models.PositiveIntegerField(
        default=0,
        help_text=_("Luggage capacity in kilograms")
    )
    
    luggage_price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Price per kilogram of luggage")
    )
    
    base_fare = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Base fare for the service")
    )
    
    distance_fare = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Distance-based fare component")
    )
    
    time_fare = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Time-based fare component")
    )
    
    total_fare = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Total fare for the service")
    )
    
    # ============================================================
    # Ratings
    # ============================================================
    
    customer_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating given by customer (1-5)")
    )
    
    provider_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating given by provider (1-5)")
    )
    
    # ============================================================
    # Safety and Insurance
    # ============================================================
    
    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Emergency contact name")
    )
    
    emergency_contact_phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text=_("Emergency contact phone number")
    )
    
    insurance_required = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether insurance is required")
    )
    
    insurance_details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Insurance metadata")
    )
    
    # ============================================================
    # Timestamps
    # ============================================================
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When the request was created")
    )
    
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Scheduled time for the service")
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When the service started")
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When the service was completed")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When the request was last updated")
    )
    
    # ============================================================
    # Generic JSON Fields
    # ============================================================
    
    trip_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Trip-specific data")
    )
    
    delivery_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Delivery-specific data")
    )
    
    shared_trip_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Shared trip data")
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional metadata")
    )
    
    # ============================================================
    # Meta
    # ============================================================
    
    class Meta:
        indexes = [
            GistIndex(fields=['route'], name='service_route_gist_idx'),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['service_type', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['departure_state', 'destination_state']),
            models.Index(fields=['estimated_arrival_time']),
            models.Index(fields=['is_recurring_daily']),
            models.Index(fields=['scheduled_at']),
        ]
        ordering = ['-created_at']
        verbose_name = _("Service Request")
        verbose_name_plural = _("Service Requests")
    
    def __str__(self):
        return f"{self.get_service_type_display()} #{self.id} - {self.get_status_display()}"
    
    # ============================================================
    # Validation
    # ============================================================
    
    def clean(self):
        """Validate the model."""
        # Ensure timestamps for status transitions
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        
        if self.status == self.Status.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        
        # Validate that pickup location exists
        if not self.pickup_location_id:
            raise ValidationError({"pickup_location": _("Pickup location is required.")})
        
        # Validate that pickup location has coordinates
        if self.pickup_location and not self.pickup_location.coordinates:
            raise ValidationError({"pickup_location": _("Pickup location must have coordinates.")})
    
    # ============================================================
    # Save
    # ============================================================
    
    def save(self, *args, **kwargs):
        """Save with validation and post-create operations."""
        is_new = self.pk is None
        
        # Validate
        self.full_clean()
        
        # Call parent save
        super().save(*args, **kwargs)
        
        # Trigger post-create operations only for new requests
        if is_new:
            self._post_create()
    
    def _post_create(self):
        """Operations to run after creation (dispatch logic)."""
        try:
            from transport.services.dispatch import get_dispatcher_with_fallback
            dispatcher = get_dispatcher_with_fallback()
            
            if hasattr(dispatcher, 'dispatch_request'):
                result = dispatcher.dispatch_request(self)
                
                if result:
                    logger.info(f"Request {self.id} dispatched successfully")
                    return result
                else:
                    logger.warning(f"Dispatcher returned no provider for request {self.id}")
                    
                    # Ultimate fallback
                    from transport.services.dispatch.dispatch import DispatchService
                    fallback_result = DispatchService().dispatch_request(self)
                    
                    if fallback_result:
                        logger.info(f"Fallback dispatcher succeeded for request {self.id}")
                        return fallback_result
                    else:
                        logger.error(f"All dispatch attempts failed for request {self.id}")
                        return None
            else:
                logger.error(f"Dispatcher has no dispatch_request method")
                return None
                
        except Exception as e:
            logger.error(f"Post-create operations failed for request {self.id}: {e}")
            
            # Emergency fallback
            try:
                from transport.services.dispatch.dispatch import DispatchService
                return DispatchService().dispatch_request(self)
            except Exception as fallback_error:
                logger.error(f"Emergency fallback also failed: {fallback_error}")
                return None
    
    # ============================================================
    # Location Helper Methods
    # ============================================================
    
    def get_pickup_coordinates(self) -> tuple:
        """Get pickup coordinates as (lat, lng)."""
        if self.pickup_location and self.pickup_location.coordinates:
            return self.pickup_location.coordinates
        return None
    
    def get_dropoff_coordinates(self) -> tuple:
        """Get dropoff coordinates as (lat, lng)."""
        if self.dropoff_location and self.dropoff_location.coordinates:
            return self.dropoff_location.coordinates
        return None
    
    def calculate_distance(self) -> float:
        """
        Calculate distance between pickup and dropoff.
        
        Returns:
            float: Distance in kilometers
        """
        pickup_coords = self.get_pickup_coordinates()
        dropoff_coords = self.get_dropoff_coordinates()
        
        if not pickup_coords or not dropoff_coords:
            return None
        
        return haversine_distance(
            pickup_coords[0], pickup_coords[1],
            dropoff_coords[0], dropoff_coords[1]
        )
    
    def calculate_eta(self, avg_speed_kmh: float = 40) -> int:
        """
        Calculate estimated time of arrival.
        
        Returns:
            int: Estimated minutes
        """
        distance = self.calculate_distance()
        if distance:
            return estimate_eta(distance, avg_speed_kmh)
        return None
    
    # ============================================================
    # Business Logic Methods
    # ============================================================
    
    def calculate_fare(self):
        """Calculate fare using service."""
        from transport.services.base import ServiceFactory
        pricing_service = ServiceFactory.get_service('pricing')
        return pricing_service.calculate_fare(self)
    
    def optimize_route(self):
        """Optimize route using service."""
        from transport.services.base import ServiceFactory
        routing_service = ServiceFactory.get_service('routing')
        return routing_service.optimize_route(self)
    
    def create_route(self) -> 'Route':
        """
        Create a route from the stops in this request.
        
        Returns:
            Route: Created route instance
        """
        from transport.models.delivery.logistics import Route, RouteStop
        from django.contrib.gis.geos import LineString
        
        # Get all stops in order
        stops = []
        
        if self.pickup_location:
            stops.append(self.pickup_location)
        
        # Add additional stops
        additional = self.route_stops.select_related('stop').order_by('order')
        for route_stop in additional:
            if route_stop.stop.id != getattr(self.pickup_location, 'id', None):
                stops.append(route_stop.stop)
        
        if self.dropoff_location:
            if self.dropoff_location not in stops:
                stops.append(self.dropoff_location)
        
        if len(stops) < 2:
            raise ValueError("Need at least 2 stops to create a route")
        
        # Create route
        route = Route.objects.create(
            trip=self,
            is_optimized=False,
        )
        
        # Create RouteStop entries
        for idx, stop in enumerate(stops):
            RouteStop.objects.create(
                route=route,
                stop=stop,
                order=idx
            )
        
        # Create path
        if all(s.coordinates for s in stops):
            points = []
            for stop in stops:
                lon, lat = stop.coordinates[1], stop.coordinates[0]
                points.append((lon, lat))
            if len(points) >= 2:
                route.path = LineString(points, srid=4326)
        
        # Calculate distances and times
        route.distance_km = route.get_total_distance()
        route.duration_minutes = route.get_total_duration()
        route.save()
        
        return route
    
    def get_service_specific_data(self):
        """Get service-specific data based on type."""
        if self.service_type in ['taxi', 'trip']:
            return self.trip_data
        elif self.service_type in ['delivery', 'food', 'cargo']:
            return self.delivery_data
        elif self.service_type in ['shared', 'interstate']:
            return self.shared_trip_data
        return {}
    
    def set_service_specific_data(self, data):
        """Set service-specific data."""
        if self.service_type in ['taxi', 'trip']:
            self.trip_data = data
        elif self.service_type in ['delivery', 'food', 'cargo']:
            self.delivery_data = data
        elif self.service_type in ['shared', 'interstate']:
            self.shared_trip_data = data
    
    # ============================================================
    # Properties
    # ============================================================
    
    @property
    def is_trip(self):
        """Check if this is a trip service."""
        return self.service_type in ['taxi', 'shared', 'interstate']
    
    @property
    def is_delivery(self):
        """Check if this is a delivery service."""
        return self.service_type in ['delivery', 'food', 'cargo']
    
    @property
    def has_dropoff(self):
        """Check if there is a dropoff location."""
        return bool(self.dropoff_location)
    
    @property
    def duration_minutes(self):
        """Get duration in minutes."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 60
        return None
    
    @property
    def is_completed(self):
        """Check if request is completed."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_cancelled(self):
        """Check if request is cancelled."""
        return self.status == self.Status.CANCELLED
    
    @property
    def is_in_progress(self):
        """Check if request is in progress."""
        return self.status == self.Status.IN_PROGRESS
    
    @property
    def is_scheduled(self):
        """Check if request is scheduled."""
        return self.status == self.Status.SCHEDULED
    # In ServiceRequest:
# Remove this field entirely:
# additional_stops = models.ManyToManyField(...)

# Instead, use properties:
@property
def all_stops(self):
    """Get all stops from the latest route."""
    latest_route = self.routes.order_by('-created_at').first()
    if latest_route:
        return latest_route.route_stops.all().order_by('order')
    return RouteStop.objects.none()

@property
def additional_stops(self):
    """Get additional stops (excluding pickup/dropoff)."""
    stops = self.all_stops
    pickup_id = self.pickup_location_id
    dropoff_id = self.dropoff_location_id
    return stops.exclude(
        stop_id__in=[pickup_id, dropoff_id]
    ).select_related('stop')