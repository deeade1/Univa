from decimal import Decimal
import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from transport.models.core.service_request import ServiceRequest
from transport.utils.json_encoder import TransportJSONEncoder

class TripManager(models.Manager):
    """Manager for Trip-specific queries"""
    
    def create_trip(self, **kwargs):
        """Create a trip with proper data structure"""
        # Extract trip-specific data
        trip_data = {
            'shared': kwargs.pop('shared', False),
            'available_seats': kwargs.pop('available_seats', 1),
            'rider_count': kwargs.pop('rider_count', 1),
            'special_requests': kwargs.pop('special_requests', ''),
            'day_time': kwargs.pop('day_time', 'day'),
            'surge_multiplier': float(kwargs.pop('surge_multiplier', 1.0)),  # Convert to float
            'safety_incidents': kwargs.pop('safety_incidents', 0),
            'cancelled': kwargs.pop('cancelled', False),
            'cancellation_reason': kwargs.pop('cancellation_reason', ''),
        }
        
        # Create service request
        service_request = ServiceRequest.objects.create(
            service_type='taxi',
            **kwargs
        )
        
        # Set trip data using JSON encoder
        service_request.trip_data = json.loads(
            json.dumps(trip_data, cls=TransportJSONEncoder)
        )
        service_request.save()
        
        # Return as Trip instance
        return Trip.objects.get(id=service_request.id)

class Trip(ServiceRequest):
    """
    Proxy model for Trip functionality.
    """
    class Meta:
        proxy = True
        verbose_name = _("Trip")
        verbose_name_plural = _("Trips")
    
    objects = TripManager()
    
    def __init__(self, *args, **kwargs):
        # Call parent's __init__ first
        super().__init__(*args, **kwargs)
        # Initialize _trip_data from trip_data JSON field
        if hasattr(self, 'trip_data') and self.trip_data:
            self._trip_data = self.trip_data.copy()
        else:
            self._trip_data = {}
    
    def __getstate__(self):
        """Handle pickling"""
        state = super().__getstate__()
        state['_trip_data'] = self._trip_data
        return state
    
    def __setstate__(self, state):
        """Handle unpickling"""
        super().__setstate__(state)
        self._trip_data = state.get('_trip_data', {})
    
    @property
    def shared(self):
        return self._trip_data.get('shared', False)
    
    @shared.setter
    def shared(self, value):
        self._trip_data['shared'] = value
        self.trip_data = json.loads(
            json.dumps(self._trip_data, cls=TransportJSONEncoder)
        )
    
    # Update other setters to use JSON encoder
    @property
    def surge_multiplier(self):
        return Decimal(str(self._trip_data.get('surge_multiplier', 1.0)))
    
    @surge_multiplier.setter
    def surge_multiplier(self, value):
        self._trip_data['surge_multiplier'] = float(value)
        self.trip_data = json.loads(
            json.dumps(self._trip_data, cls=TransportJSONEncoder)
        )
    
    def save(self, *args, **kwargs):
        # Convert _trip_data to JSON before saving
        if hasattr(self, '_trip_data'):
            self.trip_data = json.loads(
                json.dumps(self._trip_data, cls=TransportJSONEncoder)
            )
        super().save(*args, **kwargs)
    
    # In your Trip model's clean() method
    def clean(self):
        super().clean()
        if self.rider_count < 1:
            raise ValidationError("Rider count must be at least 1")
        if self.rider_count > 10:
            raise ValidationError("Rider count cannot exceed 10")