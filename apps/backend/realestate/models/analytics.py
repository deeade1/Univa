# apps/backend/realestate/models/analytics.py

"""
Analytics models for real estate calculations and reports.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone

from .listing import Listing


class MortgageCalculation(models.Model):
    """
    Stored mortgage calculation results.
    """
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="mortgage_calculations"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mortgage_calculations"
    )
    
    principal = models.DecimalField(max_digits=15, decimal_places=2)
    annual_rate = models.DecimalField(max_digits=5, decimal_places=2)
    years = models.PositiveIntegerField()
    
    # Results
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2)
    total_payment = models.DecimalField(max_digits=15, decimal_places=2)
    total_interest = models.DecimalField(max_digits=15, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "-created_at"], name="mortgage_listing_created_idx"),
            models.Index(fields=["user", "-created_at"], name="mortgage_user_created_idx"),
        ]
    
    def __str__(self):
        return f"Mortgage for {self.listing.title} - {self.monthly_payment}"


class ROICalculation(models.Model):
    """
    Stored ROI calculation results for investment properties.
    """
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="roi_calculations"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roi_calculations"
    )
    
    # Input parameters
    down_payment = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_term = models.PositiveIntegerField()
    monthly_rent = models.DecimalField(max_digits=15, decimal_places=2)
    annual_appreciation = models.DecimalField(max_digits=5, decimal_places=2)
    expenses_percent = models.DecimalField(max_digits=5, decimal_places=2)
    years = models.PositiveIntegerField(default=5)
    
    # Results
    cash_on_cash_return = models.DecimalField(max_digits=8, decimal_places=2)
    cap_rate = models.DecimalField(max_digits=8, decimal_places=2)
    total_return = models.DecimalField(max_digits=15, decimal_places=2)
    annualized_return = models.DecimalField(max_digits=8, decimal_places=2)
    monthly_cash_flow = models.DecimalField(max_digits=15, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "-created_at"], name="roi_listing_created_idx"),
            models.Index(fields=["user", "-created_at"], name="roi_user_created_idx"),
        ]
    
    def __str__(self):
        return f"ROI for {self.listing.title} - {self.cash_on_cash_return}%"


class CMAReport(models.Model):
    """
    Comparative Market Analysis Report.
    """
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="cma_reports"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cma_reports"
    )
    
    # Report data (stored as JSON for flexibility)
    comparables = models.JSONField(default=list)
    adjustments = models.JSONField(default=dict)
    valuation_range_low = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valuation_range_high = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valuation_avg = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('sent', 'Sent'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "-created_at"], name="cma_listing_created_idx"),
            models.Index(fields=["user", "-created_at"], name="cma_user_created_idx"),
            models.Index(fields=["status"], name="cma_status_idx"),
        ]
    
    def __str__(self):
        return f"CMA Report for {self.listing.title}"


class InstantValuation(models.Model):
    """
    Instant property valuation estimate.
    """
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="instant_valuations"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instant_valuations"
    )
    
    # Valuation results
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Source data
    comparable_count = models.PositiveIntegerField(default=0)
    valuation_method = models.CharField(max_length=50, default='algorithm')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "-created_at"], name="valuation_listing_created_idx"),
            models.Index(fields=["user", "-created_at"], name="valuation_user_created_idx"),
        ]
    
    def __str__(self):
        return f"Valuation for {self.listing.title} - {self.estimated_value}"