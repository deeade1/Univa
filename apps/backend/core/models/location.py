# core/models/location.py

"""
Core location model for Univa.
Shared by all apps (realestate, transport, accounts, etc.)
This is the CANONICAL location model - use this everywhere.
"""

from decimal import Decimal

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import LocationManager


class LocationModel(models.Model):
    """
    Abstract reusable location model for all Univa apps.
    
    Every application can inherit from this model for location capabilities.
    
    Examples:
        - realestate.Property(LocationModel)
        - transport.Vehicle(LocationModel)
        - accounts.Address(LocationModel)
        - delivery.Package(LocationModel)
    """

    # Human readable address
    location = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text=_("Resolved address from reverse geocoding"),
    )

    # Coordinates
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Latitude coordinate (WGS84)"),
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Longitude coordinate (WGS84)"),
    )

    # GIS Point (for spatial queries)
    location_point = gis_models.PointField(
        geography=True,
        srid=4326,
        blank=True,
        null=True,
        spatial_index=True,
        help_text=_("GIS point for spatial queries"),
    )

    # Location metadata
    location_accuracy = models.FloatField(
        blank=True,
        null=True,
        help_text=_("GPS accuracy in meters"),
    )

    location_source = models.CharField(
        max_length=20,
        default="unknown",
        choices=[
            ("gps", _("GPS")),
            ("network", _("Network")),
            ("manual", _("Manual")),
            ("ip", _("IP Address")),
            ("geocoding", _("Geocoding")),
            ("reverse_geocoding", _("Reverse Geocoding")),
            ("unknown", _("Unknown")),
        ],
        help_text=_("Source of location data"),
    )

    location_timestamp = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When the location was recorded"),
    )

    # Custom manager
    objects = LocationManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["location_source"]),
            models.Index(fields=["location_timestamp"]),
        ]

    # ============================================================
    # Validation
    # ============================================================

    @staticmethod
    def validate_coordinates(latitude, longitude):
        """
        Validate latitude and longitude values.
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
        
        Returns:
            tuple: (lat, lng) as floats
        
        Raises:
            ValidationError: If coordinates are invalid
        """
        try:
            lat = float(latitude)
            lng = float(longitude)
        except (TypeError, ValueError):
            raise ValidationError(_("Invalid coordinates."))

        if not (-90 <= lat <= 90):
            raise ValidationError(_("Latitude must be between -90 and 90."))

        if not (-180 <= lng <= 180):
            raise ValidationError(_("Longitude must be between -180 and 180."))

        return lat, lng

    def clean(self):
        """Validate location data."""
        if self.latitude is not None and self.longitude is not None:
            self.validate_coordinates(self.latitude, self.longitude)

    # ============================================================
    # Save
    # ============================================================

    def save(self, *args, **kwargs):
        """
        Save with point synchronization.

        Note: `full_clean()` is deliberately NOT called here.
        Validation is the service layer's responsibility; DB
        constraints catch the invariants that can be expressed as
        constraints. `_sync_location_point()` stays because it
        keeps location_point consistent with latitude/longitude
        on every save.
        """
        self._sync_location_point()
        super().save(*args, **kwargs)

    # ============================================================
    # Location Methods
    # ============================================================

    def update_location(
        self,
        latitude,
        longitude,
        accuracy=None,
        source="gps",
        save=True,
        queue_tasks=True,
    ):
        """
        Update location coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: GPS accuracy in meters (optional)
            source: Source of location data
            save: Whether to save immediately
            queue_tasks: Whether to queue background tasks
        
        Returns:
            self: Updated instance
        """
        lat, lng = self.validate_coordinates(latitude, longitude)

        self.latitude = Decimal(str(lat))
        self.longitude = Decimal(str(lng))
        self.location_point = Point(lng, lat, srid=4326)
        self.location_accuracy = accuracy
        self.location_source = source
        self.location_timestamp = timezone.now()

        if save:
            self.save(update_fields=[
                "latitude",
                "longitude",
                "location_point",
                "location_accuracy",
                "location_source",
                "location_timestamp",
            ])

        # Background processing
        if queue_tasks:
            self._queue_background_tasks()

        return self

    def _sync_location_point(self):
        """Synchronize location_point with latitude/longitude."""
        if self.latitude is not None and self.longitude is not None:
            if self.location_point is None:
                self.location_point = Point(
                    float(self.longitude),
                    float(self.latitude),
                    srid=4326
                )
            else:
                # Update point if coordinates changed
                if (abs(self.location_point.x - float(self.longitude)) > 0.000001 or
                    abs(self.location_point.y - float(self.latitude)) > 0.000001):
                    self.location_point = Point(
                        float(self.longitude),
                        float(self.latitude),
                        srid=4326
                    )
        elif self.location_point is not None:
            # Update lat/lng from point
            self.latitude = Decimal(str(self.location_point.y))
            self.longitude = Decimal(str(self.location_point.x))

    def _queue_background_tasks(self):
        """Queue background tasks for location processing."""
        try:
            from core.tasks.reverse_geocode import reverse_geocode_location
            from core.tasks.fraud_detection import detect_location_fraud

            reverse_geocode_location.delay(
                self._meta.label,
                self.pk,
            )
            detect_location_fraud.delay(
                self._meta.label,
                self.pk,
            )
        except Exception:
            pass

    # ============================================================
    # Properties
    # ============================================================

    @property
    def coordinates(self):
        """
        Get coordinates as a tuple.
        
        Returns:
            tuple: (latitude, longitude) or None
        """
        if self.latitude is None or self.longitude is None:
            return None
        return (float(self.latitude), float(self.longitude))

    @property
    def has_location(self):
        """Check if location is set."""
        return self.location_point is not None

    @property
    def has_address(self):
        """Check if address is set."""
        return bool(self.location)

    @property
    def location_string(self):
        """Get a human-readable location string."""
        if self.location:
            return self.location
        if self.coordinates:
            lat, lng = self.coordinates
            return f"{lat:.6f}, {lng:.6f}"
        return "Location not set"

    @property
    def is_valid_location(self):
        """Check if location is valid."""
        if self.latitude is None or self.longitude is None:
            return False
        try:
            self.validate_coordinates(self.latitude, self.longitude)
            return True
        except ValidationError:
            return False

    # ============================================================
    # Distance Methods (Using canonical routing service)
    # ============================================================

    def distance_to(self, other, unit="km"):
        """
        Calculate distance to another location object.
        
        Args:
            other: Another LocationModel instance or coordinates tuple
            unit: Unit of measurement ('km', 'meters', 'miles')
        
        Returns:
            float: Distance in specified unit, or None
        """
        from core.services.routing import haversine_distance
        
        if self.coordinates is None:
            return None
        
        if hasattr(other, 'coordinates'):
            other_coords = other.coordinates
        elif isinstance(other, (tuple, list)) and len(other) == 2:
            other_coords = other
        else:
            return None
        
        if other_coords is None:
            return None
        
        lat1, lon1 = self.coordinates
        lat2, lon2 = other_coords
        
        distance_km = haversine_distance(lat1, lon1, lat2, lon2)
        
        if unit == "meters":
            return distance_km * 1000
        elif unit == "miles":
            return distance_km * 0.621371
        return distance_km  # kilometers

    def is_near(self, other, radius_km=10):
        """
        Check if this location is within radius of another.
        
        Args:
            other: Another LocationModel instance
            radius_km: Radius in kilometers
        
        Returns:
            bool: True if within radius
        """
        distance = self.distance_to(other)
        if distance is None:
            return False
        return distance <= radius_km

    # ============================================================
    # Serialization
    # ============================================================

    def get_location_info(self):
        """
        Get location information as a dictionary.
        
        Returns:
            dict: Location information
        """
        return {
            "address": self.location,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy": self.location_accuracy,
            "source": self.location_source,
            "timestamp": self.location_timestamp.isoformat() if self.location_timestamp else None,
        }

    def to_geojson(self):
        """
        Convert location to GeoJSON format.
        
        Returns:
            dict: GeoJSON feature
        """
        if not self.location_point:
            return None

        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(self.location_point.x),
                    float(self.location_point.y)
                ]
            },
            "properties": {
                "address": self.location,
                "accuracy": self.location_accuracy,
                "source": self.location_source,
                "timestamp": self.location_timestamp.isoformat() if self.location_timestamp else None,
            }
        }

    def __str__(self):
        """String representation."""
        if self.location:
            return self.location
        if self.coordinates:
            lat, lng = self.coordinates
            return f"{lat:.6f}, {lng:.6f}"
        return "Unknown Location"