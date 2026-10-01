from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class VehicleTelemetry(models.Model):
    """Vehicle telemetry data for predictive maintenance"""
    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='telemetry_data'
    )
    
    engine_temperature = models.FloatField(null=True, blank=True)
    oil_pressure = models.FloatField(null=True, blank=True)
    oil_level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    battery_voltage = models.FloatField(null=True, blank=True)
    
    tire_pressure_front_left = models.FloatField(null=True, blank=True)
    tire_pressure_front_right = models.FloatField(null=True, blank=True)
    tire_pressure_rear_left = models.FloatField(null=True, blank=True)
    tire_pressure_rear_right = models.FloatField(null=True, blank=True)
    tire_tread_depth = models.FloatField(null=True, blank=True)
    
    fuel_level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    odometer_reading = models.PositiveIntegerField()
    average_fuel_consumption = models.FloatField(null=True, blank=True)
    
    diagnostic_trouble_codes = models.JSONField(default=list)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vehicle Telemetry"
        verbose_name_plural = "Vehicle Telemetry Data"
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['vehicle', 'recorded_at']),
        ]

class PredictiveAlert(models.Model):
    """Predictive maintenance alerts"""
    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='predictive_alerts'
    )
    
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('maintenance_due', 'Maintenance Due'),
            ('component_failure', 'Component Failure Risk'),
            ('performance_degradation', 'Performance Degradation'),
            ('safety_concern', 'Safety Concern'),
        ]
    )
    
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ]
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    predicted_issue = models.CharField(max_length=100)
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    predicted_failure_date = models.DateField(null=True, blank=True)
    recommended_action_date = models.DateField()
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Predictive Alert"
        verbose_name_plural = "Predictive Alerts"
        ordering = ['-created_at']