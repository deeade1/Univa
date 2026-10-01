import logging
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


logger = logging.getLogger(__name__)

class CancellationPolicy(models.Model):
    """Cancellation policy for different service types"""
    class ServiceType(models.TextChoices):
        TAXI = 'taxi', _('Taxi Ride')
        SHARED = 'shared', _('Shared Ride')
        DELIVERY = 'delivery', _('Package Delivery')
        FOOD = 'food', _('Food Delivery')
        CARGO = 'cargo', _('Cargo Transport')
        PREMIUM = 'premium', _('Premium Ride')
    
    class CancellationParty(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        DRIVER = 'driver', _('Driver')
        SYSTEM = 'system', _('System')
    
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        unique=True,
        db_index=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    free_cancellation_minutes = models.PositiveIntegerField(
        default=5,
        help_text=_("Free cancellation within X minutes of booking")
    )
    no_penalty_cancellation_minutes = models.PositiveIntegerField(
        default=2,
        help_text=_("No penalty cancellation within X minutes of driver acceptance")
    )
    
    cancellation_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0)]
    )
    cancellation_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage of fare as cancellation fee")
    )
    
    refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    min_refund_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=2.00,
        validators=[MinValueValidator(0)]
    )
    
    driver_compensation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    max_cancellations_per_day = models.PositiveIntegerField(
        default=3,
        help_text=_("Maximum cancellations allowed per user per day")
    )
    suspension_days = models.PositiveIntegerField(
        default=1,
        help_text=_("Account suspension days for excessive cancellations")
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateTimeField(default=timezone.now, db_index=True)
    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['service_type', 'is_active']),
            models.Index(fields=['effective_from', 'effective_to']),
        ]
        verbose_name = _("Cancellation Policy")
        verbose_name_plural = _("Cancellation Policies")
        ordering = ['service_type']
    
    def __str__(self):
        return f"{self.get_service_type_display()} Cancellation Policy"

class CancellationRecord(models.Model):
    """Record of all cancellations for analytics and enforcement"""
    class CancellationReason(models.TextChoices):
        CUSTOMER_CHANGE_MIND = 'customer_change_mind', _('Changed mind')
        CUSTOMER_DELAY = 'customer_delay', _('Too long wait')
        CUSTOMER_PRICE = 'customer_price', _('Price too high')
        DRIVER_TOO_FAR = 'driver_too_far', _('Driver too far')
        DRIVER_UNAVAILABLE = 'driver_unavailable', _('Driver unavailable')
        VEHICLE_ISSUE = 'vehicle_issue', _('Vehicle issue')
        WEATHER = 'weather', _('Bad weather')
        TRAFFIC = 'traffic', _('Heavy traffic')
        EMERGENCY = 'emergency', _('Emergency')
        OTHER = 'other', _('Other')
    
    service_request = models.OneToOneField(
        'ServiceRequest',
        on_delete=models.CASCADE,
        related_name='cancellation_record',
        db_index=True
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cancellations_made',
        db_index=True
    )
    cancellation_party = models.CharField(
        max_length=20,
        choices=CancellationPolicy.CancellationParty.choices,
        db_index=True
    )
    reason = models.CharField(
        max_length=50,
        choices=CancellationReason.choices,
        db_index=True
    )
    reason_description = models.TextField(blank=True)
    
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(default=timezone.now, db_index=True)
    minutes_after_acceptance = models.FloatField(null=True, blank=True)
    
    ride_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    cancellation_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00
    )
    refund_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00
    )
    driver_compensation = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00
    )
    
    policy = models.ForeignKey(
        CancellationPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancellation_record_policy',
    )
    
    penalty_applied = models.BooleanField(default=False)
    penalty_details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cancelled_by', 'cancelled_at']),
            models.Index(fields=['cancellation_party', 'cancelled_at']),
            models.Index(fields=['reason', 'cancelled_at']),
            models.Index(fields=['penalty_applied']),
        ]
        verbose_name = _("Cancellation Record")
        verbose_name_plural = _("Cancellation Records")
        ordering = ['-cancelled_at']
    
    def __str__(self):
        return f"Cancellation {self.service_request.id} by {self.cancelled_by.email}"