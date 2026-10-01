import logging
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class PricingProfile(models.Model):
    """Optimized dynamic pricing configuration"""
    class ServiceType(models.TextChoices):
        TAXI = 'taxi', _('Taxi Ride')
        DELIVERY = 'delivery', _('Package Delivery')
        SHARED = 'shared', _('Shared Ride')
        FOOD = 'food', _('Food Delivery')
        CARGO = 'cargo', _('Cargo Transport')
    
    service_type = models.CharField(
        max_length=20, 
        choices=ServiceType.choices, 
        unique=True,
        db_index=True
    )
    base_fare = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    per_km_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    per_minute_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    min_fare = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    surge_multiplier = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        default=1.0,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateTimeField(auto_now_add=True, db_index=True)
    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['service_type', 'is_active']),
            models.Index(fields=['effective_from']),
            models.Index(fields=['effective_to']),
        ]
        ordering = ['-effective_from']
        verbose_name = _("Pricing Profile")
        verbose_name_plural = _("Pricing Profiles")
    
    def __str__(self):
        return f"{self.get_service_type_display()} Pricing - {self.effective_from}"
    
    def clean(self):
        if self.service_type == self.ServiceType.TAXI and not self.per_minute_rate:
            raise ValidationError(_("Per minute rate is required for taxi services"))
        
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(_("Effective to date must be after effective from date"))
    
    @classmethod
    def get_current_pricing(cls, service_type):
        from django.core.cache import cache
        
        cache_key = f"current_pricing_{service_type}"
        pricing = cache.get(cache_key)
        
        if not pricing:
            pricing = cls.objects.filter(
                service_type=service_type, 
                is_active=True,
                effective_from__lte=timezone.now()
            ).exclude(
                Q(effective_to__isnull=False) & Q(effective_to__lt=timezone.now())
            ).order_by('-effective_from').first()
            cache.set(cache_key, pricing, 60 * 60)  # Cache for 1 hour
        
        return pricing