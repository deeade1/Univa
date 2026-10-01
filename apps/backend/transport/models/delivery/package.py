# transport/models/delivery/package.py

"""
Package model for delivery services.
"""
from django.contrib.auth import settings
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import GinIndex


class Package(models.Model):
    """
    Physical package being delivered.
    This is a concrete model that stores all package information.
    """
    
    class PackageType(models.TextChoices):
        ENVELOPE = 'envelope', _('Envelope')
        PARCEL = 'parcel', _('Parcel')
        BOX = 'box', _('Box')
        PALLET = 'pallet', _('Pallet')
        CONTAINER = 'container', _('Container')
        DOCUMENT = 'document', _('Document')
        FRAGILE = 'fragile', _('Fragile Item')
        PERISHABLE = 'perishable', _('Perishable')
        DANGEROUS = 'dangerous', _('Dangerous Goods')
        OVERSIZED = 'oversized', _('Oversized Item')
        OTHER = 'other', _('Other')

    
    class PackageStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PICKED_UP = 'picked_up', _('Picked Up')
        IN_TRANSIT = 'in_transit', _('In Transit')
        OUT_FOR_DELIVERY = 'out_for_delivery', _('Out for Delivery')
        DELIVERED = 'delivered', _('Delivered')
        EXCEPTION = 'exception', _('Exception')
        RETURNED = 'returned', _('Returned')
        CANCELLED = 'cancelled', _('Cancelled')
    
    
    
   
    class WeightUnit(models.TextChoices):
        KG = 'kg', _('Kilogram')
        G = 'g', _('Gram')
        LB = 'lb', _('Pound')
        OZ = 'oz', _('Ounce')
    
    class DimensionUnit(models.TextChoices):
        CM = 'cm', _('Centimeter')
        M = 'm', _('Meter')
        IN = 'in', _('Inch')
        FT = 'ft', _('Foot')
    
    # Basic package info
    tracking_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Unique tracking number for the package")
    )
    
    status = models.CharField(
        max_length=20,
        choices=PackageStatus.choices,
        default=PackageStatus.PENDING,
        db_index=True,
        help_text=_("Current status of the package")
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Package name or description")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of the package")
    )
    
    package_type = models.CharField(
        max_length=20,
        choices=PackageType.choices,
        default=PackageType.PARCEL,
        db_index=True,
        help_text=_("Type of package")
    )
    
    # Weight
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Weight of the package")
    )
    
    weight_unit = models.CharField(
        max_length=2,
        choices=WeightUnit.choices,
        default=WeightUnit.KG,
        help_text=_("Unit of weight measurement")
    )
    
    # Dimensions
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Length of the package")
    )
    
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Width of the package")
    )
    
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Height of the package")
    )
    
    dimension_unit = models.CharField(
        max_length=2,
        choices=DimensionUnit.choices,
        default=DimensionUnit.CM,
        help_text=_("Unit of dimension measurement")
    )
    
    # Value and insurance
    declared_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Declared value of the package")
    )
    
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text=_("Currency code for value")
    )
    
    is_insured = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the package is insured")
    )
    
    insurance_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Insurance coverage amount")
    )
    
    # Special handling
    requires_signature = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether signature is required upon delivery")
    )
    
    is_fragile = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the package contains fragile items")
    )
    
    is_perishable = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the package contains perishable items")
    )
    
    is_dangerous = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the package contains dangerous goods")
    )
    
    handling_instructions = models.TextField(
        blank=True,
        help_text=_("Special handling instructions")
    )
    
    # Storage
    temperature_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Minimum temperature in Celsius")
    )
    
    temperature_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum temperature in Celsius")
    )
    
    requires_refrigeration = models.BooleanField(
        default=False,
        help_text=_("Whether the package requires refrigeration")
    )
    
    # Sender and receiver
    sender = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_packages",   
    )
    
    
    receiver_name = models.CharField(
        max_length=200,
        help_text=_("Name of the receiver")
    )
    
    receiver_phone = models.CharField(
        max_length=30,
        help_text=_("Receiver's phone number")
    )
    
    receiver_email = models.EmailField(
        blank=True,
        help_text=_("Receiver's email address")
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about the package")
    )
    
    # Relationships
    delivery = models.ForeignKey(
        'transport.Delivery',
        on_delete=models.CASCADE,
        related_name='packages',
        db_index=True,
        help_text=_("The delivery this package belongs to")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Package")
        verbose_name_plural = _("Packages")
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['package_type']),
            models.Index(fields=['is_fragile', 'is_perishable']),
            models.Index(fields=['requires_signature']),
            GinIndex(fields=['handling_instructions'], name='package_handling_gin', opclasses=['gin_trgm_ops']),
        ]
    
    def __str__(self):
        return f"{self.tracking_number} - {self.name}"
    
    @property
    def volume(self):
        """Calculate the volume of the package."""
        if self.length and self.width and self.height:
            return self.length * self.width * self.height
        return None
    
    @property
    def volume_unit(self):
        """Get the unit for volume."""
        if self.dimension_unit == 'cm':
            return 'cm³'
        elif self.dimension_unit == 'm':
            return 'm³'
        elif self.dimension_unit == 'in':
            return 'in³'
        elif self.dimension_unit == 'ft':
            return 'ft³'
        return 'units³'
    
    @property
    def weight_in_kg(self):
        """Convert weight to kilograms."""
        if self.weight_unit == 'kg':
            return self.weight
        elif self.weight_unit == 'g':
            return self.weight / 1000
        elif self.weight_unit == 'lb':
            return self.weight * 0.453592
        elif self.weight_unit == 'oz':
            return self.weight * 0.0283495
        return self.weight
    
    @property
    def is_oversized(self):
        """Check if package is oversized based on dimensions."""
        if self.package_type == 'oversized':
            return True
        # Check if any dimension exceeds standard limits
        # Standard limits: 120cm length, 80cm width, 80cm height
        if self.length and self.width and self.height:
            if self.dimension_unit == 'cm':
                return (self.length > 120 or self.width > 80 or self.height > 80)
            elif self.dimension_unit == 'in':
                return (self.length > 48 or self.width > 32 or self.height > 32)
        return False
    
    def clean(self):
        """Validate package data."""
        from django.core.exceptions import ValidationError
        
        # Validate dimensions
        if self.length and self.length <= 0:
            raise ValidationError({"length": _("Length must be greater than 0.")})
        if self.width and self.width <= 0:
            raise ValidationError({"width": _("Width must be greater than 0.")})
        if self.height and self.height <= 0:
            raise ValidationError({"height": _("Height must be greater than 0.")})
        
        # Validate insurance
        if self.is_insured and not self.insurance_value:
            raise ValidationError({
                "insurance_value": _("Insurance value is required when package is insured.")
            })
        
        if self.is_insured and self.insurance_value and self.declared_value:
            if self.insurance_value > self.declared_value:
                raise ValidationError({
                    "insurance_value": _("Insurance value cannot exceed declared value.")
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
     # Add tracking relationship helper
    def get_tracking_info(self):
        """Get tracking information for this package."""
        return getattr(self, 'tracking', None)
    
    def get_tracking_events(self):
        """Get tracking events for this package."""
        tracking = self.get_tracking_info()
        if tracking:
            return tracking.events.all()
        return [] 


