# transport/models/core/service_provider.py
"""
Service Provider model with improved structure.
"""

import logging
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.location import LocationModel
from transport.constants import ProviderType

logger = logging.getLogger(__name__)


class ServiceProviderProfile(LocationModel):
    """
    Service provider profile for drivers, couriers, and riders.
    """
    
    class LicenseType(models.TextChoices):
        STANDARD = 'standard', _('Standard')
        PROFESSIONAL = 'professional', _('Professional')
        COMMERCIAL = 'commercial', _('Commercial')
    
    # User relationship
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_provider'
    )
    
    # Provider type
    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.CHOICES,
        db_index=True,
        help_text=_("Type of service provider")
    )
    
    # License information
    license_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Professional license number")
    )
    
    license_type = models.CharField(
        max_length=20,
        choices=LicenseType.choices,
        blank=True,
        help_text=_("Type of license")
    )
    
    license_image = models.ImageField(
        upload_to='provider_licenses/',
        blank=True,
        null=True,
        help_text=_("License document image")
    )
    
    # Union/association
    union_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Union or association ID")
    )
    
    verified_union_member = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether union membership is verified")
    )
    
    # Insurance
    insurance_policy_number = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Insurance policy number")
    )
    
    insurance_provider = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Insurance provider name")
    )
    
    insurance_expiry = models.DateField(
        null=True,
        blank=True,
        help_text=_("Insurance expiry date")
    )
    
    # Vehicle information
    allowed_vehicle_types = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Vehicle types the provider can operate")
    )
    
    # Availability
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether provider is available for new services")
    )
    
    is_online = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether provider is currently online")
    )
    
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether provider is verified")
    )
    
    # Current service
    current_service = models.ForeignKey(
        'transport.ServiceRequest',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_index=True,
        related_name='current_providers',
        help_text=_("Current active service")
    )
    
    # Ratings
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text=_("Average rating")
    )
    
    total_ratings = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of ratings")
    )
    
    # Statistics
    total_services = models.PositiveIntegerField(
        default=0,
        help_text=_("Total services completed")
    )
    
    total_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text=_("Total earnings")
    )
    
    # Timestamps
    last_active = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text=_("Last activity timestamp")
    )
    
    # Emergency contact
    emergency_contact_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Emergency contact name")
    )
    
    emergency_contact_phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text=_("Emergency contact phone")
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional provider metadata")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            GistIndex(fields=['location_point'], name='provider_location_gist_idx'),
            models.Index(fields=['is_available', 'is_online']),
            models.Index(fields=['provider_type', 'is_available']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['rating']),
        ]
        verbose_name = _("Service Provider")
        verbose_name_plural = _("Service Providers")
        ordering = ['-last_active']
    
    def __str__(self):
        if self.user:
            full_name = self.user.get_full_name()
            return f"{full_name or self.user.email} ({self.get_provider_type_display()})"
        return f"Provider #{self.id}"
    
    @property
    def display_name(self):
        """Get provider display name."""
        if self.user:
            return self.user.get_full_name() or self.user.email
        return f"Provider #{self.id}"
    
    @property
    def company_name(self):
        """Get company name from user or return default."""
        if hasattr(self.user, 'company_name') and self.user.company_name:
            return self.user.company_name
        return f"{self.get_provider_type_display()} Service"
    
    def update_availability(self, is_available=True):
        """Update provider availability."""
        self.is_available = is_available
        self.last_active = timezone.now()
        self.save(update_fields=['is_available', 'last_active'])
    
    def update_rating(self):
        """Recalculate rating from all reviews."""
        from transport.models import ProviderRating
        
        stats = ProviderRating.objects.filter(
            provider=self
        ).aggregate(
            avg_rating=models.Avg('rating'),
            total=models.Count('id')
        )
        
        if stats['total'] > 0:
            self.rating = round(stats['avg_rating'], 2)
            self.total_ratings = stats['total']
            self.save(update_fields=['rating', 'total_ratings'])