# transport/models/core/vehicle.py

"""
Vehicle management models for transport services.
Supports both taxi and logistics vehicle types with comprehensive management.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GinIndex, GistIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.location import LocationModel

logger = logging.getLogger(__name__)


class Vehicle(LocationModel):
    """
    Unified vehicle model supporting both taxi and logistics operations.
    Inherits location capabilities from core.LocationModel.
    """
    
    # ============================================================
    # Vehicle Categories and Types
    # ============================================================
    
    class VehicleCategory(models.TextChoices):
        TAXI = 'taxi', _('Taxi')
        LOGISTICS = 'logistics', _('Logistics')
        DUAL = 'dual', _('Taxi & Logistics')
    
    class VehicleType(models.TextChoices):
        # Taxi types
        ECONOMY = 'economy', _('Economy Car')
        COMFORT = 'comfort', _('Comfort Car')
        PREMIUM = 'premium', _('Premium Car')
        XL = 'xl', _('XL Vehicle')
        GREEN = 'green', _('Eco Vehicle')
        
        # Logistics types
        BIKE = 'bike', _('Motorcycle')
        CARGO_BIKE = 'cargo_bike', _('Cargo Bike')
        VAN = 'van', _('Delivery Van')
        TRUCK = 'truck', _('Truck')
        BOX_TRUCK = 'box_truck', _('Box Truck')
        REFRIGERATED = 'refrigerated', _('Refrigerated Truck')
        TANKER = 'tanker', _('Tanker')
        TRAILER = 'trailer', _('Trailer')
        
        # General types
        SEDAN = 'sedan', _('Sedan')
        SUV = 'suv', _('SUV')
        BUS = 'bus', _('Bus')
        MINIVAN = 'minivan', _('Minivan')
        PICKUP = 'pickup', _('Pickup Truck')
        MOTORCYCLE = 'motorcycle', _('Motorcycle')
        BICYCLE = 'bicycle', _('Bicycle')
    
    class FuelType(models.TextChoices):
        PETROL = 'petrol', _('Petrol')
        DIESEL = 'diesel', _('Diesel')
        ELECTRIC = 'electric', _('Electric')
        HYBRID = 'hybrid', _('Hybrid')
        CNG = 'cng', _('CNG')
        LPG = 'lpg', _('LPG')
    
    class OwnershipType(models.TextChoices):
        OWNED = 'owned', _('Owned')
        LEASED = 'leased', _('Leased')
        RENTED = 'rented', _('Rented')
        COMPANY = 'company', _('Company Provided')
    
    class VehicleStatus(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        IN_USE = 'in_use', _('In Use')
        MAINTENANCE = 'maintenance', _('Under Maintenance')
        UNAVAILABLE = 'unavailable', _('Unavailable')
        RETIRED = 'retired', _('Retired')
    
    # ============================================================
    # Basic Information
    # ============================================================
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles',
        db_index=True,
        help_text=_("Vehicle owner")
    )
    
    category = models.CharField(
        max_length=20,
        choices=VehicleCategory.choices,
        db_index=True,
        help_text=_("Vehicle category (taxi, logistics, or dual)")
    )
    
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        db_index=True,
        help_text=_("Type of vehicle")
    )
    
    make = models.CharField(
        max_length=50,
        help_text=_("Vehicle make (e.g., Toyota)")
    )
    
    model = models.CharField(
        max_length=50,
        help_text=_("Vehicle model (e.g., Camry)")
    )
    
    year = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(timezone.now().year + 1)
        ],
        help_text=_("Manufacturing year")
    )
    
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                r'^[A-Z0-9\- ]+$',
                _('License plate must contain only uppercase letters, numbers, hyphens and spaces')
            )
        ],
        help_text=_("Vehicle license plate number")
    )
    
    color = models.CharField(
        max_length=30,
        blank=True,
        help_text=_("Vehicle color")
    )
    
    # ============================================================
    # Capacity
    # ============================================================
    
    passenger_capacity = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text=_("Maximum number of passengers")
    )
    
    cargo_capacity_kg = models.PositiveIntegerField(
        default=0,
        help_text=_("Cargo capacity in kilograms")
    )
    
    cargo_volume_m3 = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text=_("Cargo volume in cubic meters")
    )
    
    luggage_capacity_kg = models.PositiveIntegerField(
        default=0,
        help_text=_("Luggage capacity in kilograms")
    )
    
    # ============================================================
    # Fuel and Efficiency
    # ============================================================
    
    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        default=FuelType.PETROL,
        help_text=_("Fuel type")
    )
    
    fuel_efficiency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Fuel efficiency in km/liter or mpg")
    )
    
    # ============================================================
    # Ownership
    # ============================================================
    
    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.OWNED,
        help_text=_("Ownership type")
    )
    
    provider = models.ForeignKey(
        'transport.ServiceProviderProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
        db_index=True,
        help_text=_("Provider currently using this vehicle")
    )
    
    # ============================================================
    # Insurance
    # ============================================================
    
    insurance_provider = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Insurance provider name")
    )
    
    insurance_policy_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Insurance policy number")
    )
    
    insurance_expiry = models.DateField(
        null=True,
        blank=True,
        help_text=_("Insurance expiry date")
    )
    
    insurance_document = models.FileField(
        upload_to='vehicle_insurance/',
        blank=True,
        null=True,
        help_text=_("Insurance document")
    )
    
    # ============================================================
    # Registration
    # ============================================================
    
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Vehicle registration number")
    )
    
    registration_expiry = models.DateField(
        null=True,
        blank=True,
        help_text=_("Registration expiry date")
    )
    
    registration_document = models.FileField(
        upload_to='vehicle_registration/',
        blank=True,
        null=True,
        help_text=_("Vehicle registration document")
    )
    
    # ============================================================
    # Status
    # ============================================================
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether vehicle is active")
    )
    
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether vehicle is verified")
    )
    
    status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        default=VehicleStatus.AVAILABLE,
        db_index=True,
        help_text=_("Current vehicle status")
    )
    
    is_moving = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether vehicle is currently moving")
    )
    
    current_provider = models.ForeignKey(
        'transport.ServiceProviderProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_vehicle',
        db_index=True,
        help_text=_("Provider currently using this vehicle")
    )
    
    # ============================================================
    # Location Tracking (from LocationModel)
    # ============================================================
    
    # Note: location fields (location, latitude, longitude, location_point, etc.)
    # are inherited from LocationModel
    
    last_location_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Last location update time")
    )
    
    # ============================================================
    # Photos
    # ============================================================
    
    front_photo = models.ImageField(
        upload_to='vehicle_photos/',
        blank=True,
        null=True,
        help_text=_("Front view photo")
    )
    
    rear_photo = models.ImageField(
        upload_to='vehicle_photos/',
        blank=True,
        null=True,
        help_text=_("Rear view photo")
    )
    
    side_photo = models.ImageField(
        upload_to='vehicle_photos/',
        blank=True,
        null=True,
        help_text=_("Side view photo")
    )
    
    interior_photo = models.ImageField(
        upload_to='vehicle_photos/',
        blank=True,
        null=True,
        help_text=_("Interior view photo")
    )
    
    # ============================================================
    # Inspection
    # ============================================================
    
    inspection_certificate = models.FileField(
        upload_to='vehicle_inspection/',
        blank=True,
        null=True,
        help_text=_("Vehicle inspection certificate")
    )
    
    last_inspection_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Last inspection date")
    )
    
    next_inspection_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Next inspection due date")
    )
    
    # ============================================================
    # Metadata
    # ============================================================
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional vehicle metadata")
    )
    
    # ============================================================
    # Timestamps
    # ============================================================
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ============================================================
    # Meta
    # ============================================================
    
    class Meta:
        verbose_name = _("Vehicle")
        verbose_name_plural = _("Vehicles")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license_plate']),
            models.Index(fields=['vehicle_type', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['is_moving']),
            models.Index(fields=['last_location_update']),
            # GIS index from LocationModel is already included
            GinIndex(
                name='vehicle_make_model_gin_idx',
                fields=['make', 'model'],
                opclasses=['gin_trgm_ops', 'gin_trgm_ops']
            ),
        ]
    
    # ============================================================
    # String Representation
    # ============================================================
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"
    
    @property
    def display_name(self):
        """Get display name for the vehicle."""
        return f"{self.year} {self.make} {self.model} - {self.license_plate}"
    
    @property
    def is_available(self):
        """Check if vehicle is available for service."""
        return self.is_active and self.is_verified and self.status == self.VehicleStatus.AVAILABLE
    
    @property
    def is_taxi(self):
        """Check if vehicle is a taxi."""
        return self.category in [self.VehicleCategory.TAXI, self.VehicleCategory.DUAL]
    
    @property
    def is_logistics(self):
        """Check if vehicle is for logistics."""
        return self.category in [self.VehicleCategory.LOGISTICS, self.VehicleCategory.DUAL]
    
    @property
    def capacity_display(self):
        """Display capacity based on vehicle type."""
        if self.is_taxi:
            return f"{self.passenger_capacity} passengers"
        else:
            return f"{self.cargo_capacity_kg} kg cargo"
    
    # ============================================================
    # Validation
    # ============================================================
    
    def clean(self):
        """Validate vehicle data."""
        super().clean()
        
        # Validate year
        if self.year > timezone.now().year:
            raise ValidationError({"year": _("Year cannot be in the future.")})
        
        # Validate insurance expiry
        if self.insurance_expiry and self.insurance_expiry < timezone.now().date():
            raise ValidationError({"insurance_expiry": _("Insurance has expired.")})
        
        # Validate registration expiry
        if self.registration_expiry and self.registration_expiry < timezone.now().date():
            raise ValidationError({"registration_expiry": _("Registration has expired.")})
        
        # Validate category-vehicle type compatibility
        taxi_types = [
            self.VehicleType.ECONOMY,
            self.VehicleType.COMFORT,
            self.VehicleType.PREMIUM,
            self.VehicleType.XL,
            self.VehicleType.GREEN,
            self.VehicleType.SEDAN,
            self.VehicleType.SUV,
            self.VehicleType.MINIVAN
        ]
        
        logistics_types = [
            self.VehicleType.BIKE,
            self.VehicleType.CARGO_BIKE,
            self.VehicleType.VAN,
            self.VehicleType.TRUCK,
            self.VehicleType.BOX_TRUCK,
            self.VehicleType.REFRIGERATED,
            self.VehicleType.TANKER,
            self.VehicleType.TRAILER,
            self.VehicleType.PICKUP,
            self.VehicleType.MOTORCYCLE
        ]
        
        if self.category == self.VehicleCategory.TAXI and self.vehicle_type not in taxi_types:
            raise ValidationError({
                "vehicle_type": _("Invalid vehicle type for taxi category")
            })
        
        if self.category == self.VehicleCategory.LOGISTICS and self.vehicle_type not in logistics_types:
            raise ValidationError({
                "vehicle_type": _("Invalid vehicle type for logistics category")
            })
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    # ============================================================
    # Location Methods (Override from LocationModel)
    # ============================================================
    
    def update_location(self, latitude, longitude, accuracy=None, source="gps", save=True):
        """
        Update vehicle location with timestamp.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: GPS accuracy in meters
            source: Source of location data
            save: Whether to save immediately
        """
        super().update_location(latitude, longitude, accuracy, source, save)
        self.last_location_update = timezone.now()
        if save:
            self.save(update_fields=['last_location_update'])
        return self
    
    def get_nearby_vehicles(self, radius_km=10, category=None):
        """
        Get other vehicles nearby.
        
        Args:
            radius_km: Search radius in kilometers
            category: Optional category filter
        
        Returns:
            QuerySet of nearby vehicles
        """
        if not self.location_point:
            return Vehicle.objects.none()
        
        queryset = Vehicle.objects.nearby(
            self.location_point,
            radius_km=radius_km,
        ).exclude(id=self.id)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    # ============================================================
    # Capacity Methods
    # ============================================================
    
    def get_capacity(self):
        """Get vehicle capacity based on type."""
        if self.category in [self.VehicleCategory.TAXI, self.VehicleCategory.DUAL]:
            return self.passenger_capacity
        return self.cargo_capacity_kg
    
    def can_accommodate_passengers(self, count):
        """Check if vehicle can accommodate a number of passengers."""
        return self.is_taxi and self.passenger_capacity >= count
    
    def can_accommodate_cargo(self, weight_kg, volume_m3=None):
        """Check if vehicle can accommodate cargo."""
        if not self.is_logistics:
            return False
        
        if weight_kg > self.cargo_capacity_kg:
            return False
        
        if volume_m3 and self.cargo_volume_m3 and volume_m3 > float(self.cargo_volume_m3):
            return False
        
        return True
    
    # ============================================================
    # Status Methods
    # ============================================================
    
    def set_in_use(self):
        """Mark vehicle as in use."""
        self.status = self.VehicleStatus.IN_USE
        self.is_moving = True
        self.save(update_fields=['status', 'is_moving'])
    
    def set_available(self):
        """Mark vehicle as available."""
        self.status = self.VehicleStatus.AVAILABLE
        self.is_moving = False
        self.save(update_fields=['status', 'is_moving'])
    
    def set_maintenance(self):
        """Mark vehicle as under maintenance."""
        self.status = self.VehicleStatus.MAINTENANCE
        self.is_moving = False
        self.save(update_fields=['status', 'is_moving'])
    
    def set_retired(self):
        """Mark vehicle as retired."""
        self.status = self.VehicleStatus.RETIRED
        self.is_active = False
        self.is_moving = False
        self.save(update_fields=['status', 'is_active', 'is_moving'])