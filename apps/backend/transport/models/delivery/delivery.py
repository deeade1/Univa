
# transport/models/delivery/delivery.py

"""
Delivery model for package delivery services.
Combines package management with delivery-specific functionality.
"""
from decimal import Decimal
import json
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from transport.models.core.service_request import ServiceRequest
from transport.utils.json_encoder import TransportJSONEncoder

class DeliveryManager(models.Manager):
    """
    Manager for Delivery-specific queries with optimized package handling.
    """
    
    def create_delivery(self, **kwargs):
        """
        Create a delivery with proper data structure.
        Supports both legacy and new package-based delivery creation.
        """
        # Extract delivery-specific data
        delivery_data = {
            'surge_multiplier': float(kwargs.pop('surge_multiplier', 1.0)),
            'cancelled': kwargs.pop('cancelled', False),
            'cancellation_reason': kwargs.pop('cancellation_reason', ''),
        }
        
        # Check for legacy package data (from old version)
        legacy_package_fields = ['package_type', 'weight_kg', 'width_cm', 'height_cm', 'length_cm', 
                                 'fragile', 'insurance_enabled', 'insurance_value']
        
        has_legacy_data = any(field in kwargs for field in legacy_package_fields)
        
        if has_legacy_data:
            # Extract legacy package data for backwards compatibility
            package_data = {
                'package_type': kwargs.pop('package_type', 'parcel'),
                'name': kwargs.pop('name', 'Package'),
                'weight': float(kwargs.pop('weight_kg', 0.0)),
                'weight_unit': 'kg',
                'length': float(kwargs.pop('length_cm', 0.0)),
                'width': float(kwargs.pop('width_cm', 0.0)),
                'height': float(kwargs.pop('height_cm', 0.0)),
                'dimension_unit': 'cm',
                'is_fragile': kwargs.pop('fragile', False),
                'is_insured': kwargs.pop('insurance_enabled', False),
                'insurance_value': float(kwargs.pop('insurance_value', 0.0)),
                'declared_value': float(kwargs.pop('declared_value', 0.0)),
                'requires_signature': kwargs.pop('requires_signature', False),
                'sender_name': kwargs.pop('sender_name', ''),
                'sender_phone': kwargs.pop('sender_phone', ''),
                'receiver_name': kwargs.pop('receiver_name', ''),
                'receiver_phone': kwargs.pop('receiver_phone', ''),
            }
            kwargs['_legacy_package_data'] = package_data
        
        # Create service request
        service_request = ServiceRequest.objects.create(
            service_type='delivery',
            **kwargs
        )
        
        # Set delivery data using JSON encoder
        service_request.delivery_data = json.loads(
            json.dumps(delivery_data, cls=TransportJSONEncoder)
        )
        service_request.save()
        
        # Get the delivery instance
        delivery = Delivery.objects.get(id=service_request.id)
        
        # Create package from legacy data if provided
        if has_legacy_data:
            from .package import Package
            package_data = kwargs.pop('_legacy_package_data', {})
            if package_data:
                # Auto-generate tracking number
                if not package_data.get('tracking_number'):
                    package_data['tracking_number'] = f"PKG-{uuid.uuid4().hex[:12].upper()}"
                package_data['delivery'] = delivery
                Package.objects.create(**package_data)
        
        return delivery
    
    def get_active_deliveries(self, **filters):
        """Get active deliveries with optional filters."""
        queryset = self.get_queryset().filter(
            status__in=['requested', 'accepted', 'in_progress', 'scheduled', 'departed', 'in_transit']
        )
        if filters:
            queryset = queryset.filter(**filters)
        return queryset
    
    def get_completed_deliveries(self, **filters):
        """Get completed deliveries with optional filters."""
        queryset = self.get_queryset().filter(status='completed')
        if filters:
            queryset = queryset.filter(**filters)
        return queryset


class Delivery(ServiceRequest):
    """
    Proxy model for Delivery functionality with package management.
    """
    
    class Meta:
        proxy = True
        verbose_name = _("Delivery")
        verbose_name_plural = _("Deliveries")
    
    objects = DeliveryManager()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'delivery_data') and self.delivery_data:
            self._delivery_data = self.delivery_data.copy()
        else:
            self._delivery_data = {}
    
    def __getstate__(self):
        state = super().__getstate__()
        state['_delivery_data'] = self._delivery_data
        return state
    
    def __setstate__(self, state):
        super().__setstate__(state)
        self._delivery_data = state.get('_delivery_data', {})
    
    # ============================================================
    # Delivery Properties
    # ============================================================
    
    @property
    def surge_multiplier(self):
        """Get the surge pricing multiplier."""
        return Decimal(str(self._delivery_data.get('surge_multiplier', 1.0)))
    
    @surge_multiplier.setter
    def surge_multiplier(self, value):
        self._delivery_data['surge_multiplier'] = float(value)
        self._update_delivery_data()
    
    @property
    def is_cancelled(self):
        """Check if delivery is cancelled."""
        return self._delivery_data.get('cancelled', False)
    
    @property
    def cancellation_reason(self):
        """Get cancellation reason."""
        return self._delivery_data.get('cancellation_reason', '')
    
    @property
    def package_count(self):
        """Get total number of packages."""
        return self.packages.count()
    
    @property
    def total_weight(self):
        """Get total weight of all packages."""
        total = self.packages.aggregate(
            total=models.Sum('weight')
        )['total'] or 0
        return float(total)
    
    @property
    def total_value(self):
        """Get total declared value of all packages."""
        total = self.packages.aggregate(
            total=models.Sum('declared_value')
        )['total'] or 0
        return float(total)
    
    @property
    def has_fragile_items(self):
        """Check if any package is fragile."""
        return self.packages.filter(is_fragile=True).exists()
    
    @property
    def has_perishable_items(self):
        """Check if any package is perishable."""
        return self.packages.filter(is_perishable=True).exists()
    
    @property
    def has_dangerous_goods(self):
        """Check if any package contains dangerous goods."""
        return self.packages.filter(is_dangerous=True).exists()
    
    @property
    def requires_refrigeration(self):
        """Check if any package requires refrigeration."""
        return self.packages.filter(requires_refrigeration=True).exists()
    
    @property
    def has_packages(self):
        """Check if delivery has any packages."""
        return self.packages.exists()
    
    @property
    def is_express(self):
        """Check if delivery is express."""
        return self.packages.filter(priority='express').exists()
    
    @property
    def delivery_status(self):
        """Get delivery status with additional context."""
        if self.is_cancelled:
            return 'cancelled'
        if self.status == 'completed':
            return 'delivered'
        if self.status == 'in_transit':
            return 'in_transit'
        if self.status == 'accepted':
            return 'accepted'
        return 'pending'
    
    # ============================================================
    # Internal Methods
    # ============================================================
    
    def _update_delivery_data(self):
        """Update the delivery_data JSON field."""
        self.delivery_data = json.loads(
            json.dumps(self._delivery_data, cls=TransportJSONEncoder)
        )
    
    # ============================================================
    # Save Override
    # ============================================================
    
    def save(self, *args, **kwargs):
        """Save with delivery data update."""
        if hasattr(self, '_delivery_data'):
            self.delivery_data = json.loads(
                json.dumps(self._delivery_data, cls=TransportJSONEncoder)
            )
        
        # Update status based on packages if all delivered
        if self.packages.exists() and self.status != 'completed':
            all_delivered = self.packages.filter(
                status__in=['delivered', 'completed']
            ).count() == self.packages.count()
            
            if all_delivered and self.status not in ['completed', 'cancelled']:
                self.status = 'completed'
        
        super().save(*args, **kwargs)
    
    # ============================================================
    # Package Management Methods
    # ============================================================
    
    def add_package(self, **package_data):
        """
        Add a package to this delivery.
        
        Args:
            **package_data: Package fields including:
                - name (required)
                - weight (required)
                - sender_name (required)
                - sender_phone (required)
                - receiver_name (required)
                - receiver_phone (required)
                - tracking_number (optional, auto-generated)
                - package_type (default: parcel)
                - weight_unit (default: kg)
                - declared_value (optional)
                - is_insured (default: False)
                - is_fragile (default: False)
                - is_perishable (default: False)
                - is_dangerous (default: False)
                - requires_signature (default: False)
                - requires_refrigeration (default: False)
        
        Returns:
            Package: The created package instance
        """
        from .package import Package
        
        # Auto-generate tracking number if not provided
        if not package_data.get('tracking_number'):
            package_data['tracking_number'] = f"PKG-{uuid.uuid4().hex[:12].upper()}"
        
        # Set delivery
        package_data['delivery'] = self
        
        # Validate required fields
        required_fields = ['name', 'weight', 'sender_name', 'sender_phone', 'receiver_name', 'receiver_phone']
        for field in required_fields:
            if field not in package_data or not package_data[field]:
                raise ValueError(f"{field} is required for package creation")
        
        return Package.objects.create(**package_data)
    
    def add_packages(self, packages_data):
        """
        Add multiple packages to this delivery.
        
        Args:
            packages_data: List of package data dictionaries
        
        Returns:
            List[Package]: List of created package instances
        """
        created_packages = []
        for package_data in packages_data:
            created_packages.append(self.add_package(**package_data))
        return created_packages
    
    def get_packages(self):
        """Get all packages in this delivery."""
        return self.packages.all()
    
    def get_packages_by_type(self, package_type):
        """Get packages by type."""
        return self.packages.filter(package_type=package_type)
    
    def get_packages_by_status(self, status):
        """Get packages by status."""
        return self.packages.filter(status=status)
    
    def get_pending_packages(self):
        """Get packages that are pending delivery."""
        return self.packages.filter(status='pending')
    
    def get_delivered_packages(self):
        """Get packages that have been delivered."""
        return self.packages.filter(status='delivered')
    
    def get_exception_packages(self):
        """Get packages with exceptions."""
        return self.packages.filter(status='exception')
    
    def remove_package(self, package_id):
        """Remove a package from this delivery."""
        try:
            package = self.packages.get(id=package_id)
            package.delete()
            return True
        except Package.DoesNotExist:
            return False
    
    # ============================================================
    # Tracking Methods
    # ============================================================
    
    def create_tracking_for_package(self, package):
        """Create tracking for a specific package."""
        from .tracking import Tracking
        
        if hasattr(package, 'tracking'):
            return package.tracking
        
        tracking = Tracking.objects.create(
            package=package,
            delivery=self,
            tracking_number=package.tracking_number,
            estimated_delivery=self.estimated_arrival_time or timezone.now() + timedelta(days=3),
            current_status=Tracking.Status.LABEL_CREATED,
            priority=Tracking.Priority.STANDARD
        )
        return tracking
    
    def create_tracking_for_all_packages(self):
        """Create tracking for all packages in this delivery."""
        trackings = []
        for package in self.packages.all():
            if not hasattr(package, 'tracking'):
                trackings.append(self.create_tracking_for_package(package))
        return trackings
    
    # ============================================================
    # Status Management
    # ============================================================
    
    def cancel_delivery(self, reason=""):
        """Cancel this delivery."""
        if self.status in ['completed', 'cancelled']:
            raise ValueError(f"Cannot cancel delivery with status: {self.status}")
        
        self.is_cancelled = True
        self.cancellation_reason = reason
        self.status = 'cancelled'
        self._update_delivery_data()
        self.save(update_fields=['status', 'delivery_data'])
        
        # Cancel all packages
        for package in self.packages.all():
            package.status = 'cancelled'
            package.save(update_fields=['status'])
        
        return True
    
    # ============================================================
    # Statistics Methods
    # ============================================================
    
    def get_stats(self):
        """Get delivery statistics."""
        total_packages = self.packages.count()
        delivered = self.packages.filter(status='delivered').count()
        in_transit = self.packages.filter(status='in_transit').count()
        pending = self.packages.filter(status='pending').count()
        exceptions = self.packages.filter(status='exception').count()
        
        return {
            'total_packages': total_packages,
            'delivered': delivered,
            'in_transit': in_transit,
            'pending': pending,
            'exceptions': exceptions,
            'delivery_rate': (delivered / total_packages * 100) if total_packages > 0 else 0,
            'total_weight_kg': self.total_weight,
            'total_value': self.total_value,
            'has_fragile': self.has_fragile_items,
            'has_perishable': self.has_perishable_items,
            'has_dangerous': self.has_dangerous_goods,
            'requires_refrigeration': self.requires_refrigeration,
        }
    
    # ============================================================
    # Serialization
    # ============================================================
    
    def to_dict(self):
        """Convert delivery to dictionary for API responses."""
        return {
            'id': self.id,
            'service_type': self.service_type,
            'status': self.delivery_status,
            'packages': [p.to_dict() for p in self.packages.all()],
            'package_count': self.package_count,
            'total_weight_kg': self.total_weight,
            'total_value': self.total_value,
            'has_fragile_items': self.has_fragile_items,
            'has_perishable_items': self.has_perishable_items,
            'has_dangerous_goods': self.has_dangerous_goods,
            'requires_refrigeration': self.requires_refrigeration,
            'surge_multiplier': float(self.surge_multiplier),
            'estimated_arrival_time': self.estimated_arrival_time,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'customer': {
                'id': self.customer.id,
                'name': self.customer.get_full_name(),
                'email': self.customer.email
            } if self.customer else None,
            'provider': {
                'id': self.provider.id,
                'name': self.provider.display_name
            } if self.provider else None,
        }


# ============================================================
# Utility Functions
# ============================================================

def create_delivery_with_package(customer, pickup_location, dropoff_location, package_data, **kwargs):
    """
    Helper function to create a delivery with a single package.
    
    Args:
        customer: User object
        pickup_location: Point or dict with lat/lng
        dropoff_location: Point or dict with lat/lng
        package_data: Dict with package fields
        **kwargs: Additional delivery fields
    
    Returns:
        Delivery: Created delivery instance
    """
    from django.contrib.gis.geos import Point
    
    # Convert location dicts to Points if needed
    if isinstance(pickup_location, dict):
        pickup_location = Point(
            pickup_location['lng'],
            pickup_location['lat'],
            srid=4326
        )
    
    if isinstance(dropoff_location, dict):
        dropoff_location = Point(
            dropoff_location['lng'],
            dropoff_location['lat'],
            srid=4326
        )
    
    # Create delivery
    delivery = Delivery.objects.create_delivery(
        customer=customer,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        **kwargs
    )
    
    # Add package
    delivery.add_package(**package_data)
    
    return delivery


def create_delivery_with_multiple_packages(customer, pickup_location, dropoff_location, packages_data, **kwargs):
    """
    Helper function to create a delivery with multiple packages.
    
    Args:
        customer: User object
        pickup_location: Point or dict with lat/lng
        dropoff_location: Point or dict with lat/lng
        packages_data: List of dicts with package fields
        **kwargs: Additional delivery fields
    
    Returns:
        Delivery: Created delivery instance
    """
    from django.contrib.gis.geos import Point
    
    # Convert location dicts to Points if needed
    if isinstance(pickup_location, dict):
        pickup_location = Point(
            pickup_location['lng'],
            pickup_location['lat'],
            srid=4326
        )
    
    if isinstance(dropoff_location, dict):
        dropoff_location = Point(
            dropoff_location['lng'],
            dropoff_location['lat'],
            srid=4326
        )
    
    # Create delivery
    delivery = Delivery.objects.create_delivery(
        customer=customer,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        **kwargs
    )
    
    # Add all packages
    delivery.add_packages(packages_data)
    
    return delivery