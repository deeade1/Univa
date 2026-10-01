# apps/backend/transport/models/analytics.py
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
import json
from datetime import datetime, timedelta
import pandas as pd
from django.db.models import Avg, Count, F, Sum
from django.utils import timezone
from django.conf import settings

class AnalyticsProfile(models.Model):
    """Configuration for analytics tracking and reporting"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_profiles'
    )
    
    # Tracking preferences
    track_ride_metrics = models.BooleanField(default=True)
    track_environmental_impact = models.BooleanField(default=True)
    track_cost_savings = models.BooleanField(default=True)
    track_accessibility_usage = models.BooleanField(default=True)
    
    # Reporting preferences
    report_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ],
        default='weekly'
    )
    
    # Data sharing preferences
    share_aggregate_data = models.BooleanField(default=False)
    share_for_research = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class RideMetrics(models.Model):
    """Detailed metrics for each ride"""
    
    ride = models.OneToOneField(
        'Trip',
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Performance metrics
    distance_km = models.FloatField(validators=[MinValueValidator(0)])
    duration_minutes = models.FloatField(validators=[MinValueValidator(0)])
    average_speed_kmh = models.FloatField(validators=[MinValueValidator(0)])
    fuel_consumption_liters = models.FloatField(validators=[MinValueValidator(0)], null=True, blank=True)
    energy_consumption_kwh = models.FloatField(validators=[MinValueValidator(0)], null=True, blank=True)
    
    # Environmental metrics
    co2_emissions_kg = models.FloatField(validators=[MinValueValidator(0)])
    particulate_matter_emissions = models.FloatField(validators=[MinValueValidator(0)])
    
    # Cost metrics
    operational_cost = models.DecimalField(max_digits=10, decimal_places=2)
    maintenance_cost_share = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Quality metrics
    passenger_comfort_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    accessibility_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

class KPI(models.Model):
    """Key Performance Indicators for the transport system"""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    value = models.FloatField()
    target = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50)
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=[
            ('environmental', 'Environmental'),
            ('financial', 'Financial'),
            ('operational', 'Operational'),
            ('customer', 'Customer Satisfaction'),
            ('safety', 'Safety'),
        ]
    )
    
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    calculated_at = models.DateTimeField(auto_now_add=True)



