# apps/backend/realestate/models/commission.py

"""
Commission models for real estate.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CommissionPlan(models.Model):
    PLAN_TYPES = [('percentage', 'Percentage'), ('fixed', 'Fixed Amount'), ('tiered', 'Tiered')]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    base_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-id']
        indexes = [models.Index(fields=['plan_type', 'is_active'], name='comm_plan_type_active')]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"

