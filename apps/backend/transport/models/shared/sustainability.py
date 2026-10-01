from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings


class SustainabilityProfile(models.Model):
    """Sustainability tracking and goals"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sustainability_profile'
    )
    
    co2_reduction_goal_kg = models.FloatField(
        default=100,
        validators=[MinValueValidator(0)]
    )
    monthly_ride_goal = models.PositiveIntegerField(default=20)
    car_avoidance_goal = models.PositiveIntegerField(
        default=10,
        help_text="Number of car trips to avoid per month"
    )
    
    prefer_electric_vehicles = models.BooleanField(default=True)
    prefer_shared_rides = models.BooleanField(default=True)
    offset_carbon_footprint = models.BooleanField(default=False)
    
    total_co2_saved_kg = models.FloatField(default=0)
    total_car_trips_avoided = models.PositiveIntegerField(default=0)
    current_streak_days = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CarbonCredit(models.Model):
    """Carbon credit tracking and transactions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carbon_credits'
    )
    
    credits_amount = models.FloatField(validators=[MinValueValidator(0)])
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('earned', 'Earned'),
            ('purchased', 'Purchased'),
            ('redeemed', 'Redeemed'),
            ('offset', 'Offset'),
        ]
    )
    
    ride = models.ForeignKey(
        'Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    verification_code = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    
    transaction_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-transaction_date']