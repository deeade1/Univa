# transport/models/finance/promo.py
"""
Promotion and discount models.
"""

import logging
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class PromoCode(models.Model):
    """
    Promotional codes and discounts.
    """
    
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', _('Percentage')
        FIXED = 'fixed', _('Fixed Amount')
        FREE_DELIVERY = 'free_delivery', _('Free Delivery')
    
    class ApplicableTo(models.TextChoices):
        ALL = 'all', _('All Services')
        TAXI = 'taxi', _('Taxi Only')
        DELIVERY = 'delivery', _('Delivery Only')
        FOOD = 'food', _('Food Delivery Only')
        CARGO = 'cargo', _('Cargo Only')
        INTERSTATE = 'interstate', _('Interstate Only')
    
    # Code details
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Promo code (e.g., SAVE10)")
    )
    
    description = models.CharField(
        max_length=255,
        help_text=_("Description of the promo")
    )
    
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        help_text=_("Type of discount")
    )
    
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Discount amount or percentage")
    )
    
    # Conditions
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Minimum order value to apply")
    )
    
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum discount amount")
    )
    
    applicable_to = models.CharField(
        max_length=20,
        choices=ApplicableTo.choices,
        default=ApplicableTo.ALL,
        help_text=_("Services this promo applies to")
    )
    
    # Usage limits
    max_uses_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum total uses")
    )
    
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text=_("Maximum uses per user")
    )
    
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Total usage count")
    )
    
    # Time limits
    start_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Start date/time")
    )
    
    end_date = models.DateTimeField(
        db_index=True,
        help_text=_("End date/time")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether promo is active")
    )
    
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether promo is deleted")
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_promos',
        help_text=_("User who created this promo")
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional promo metadata")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Promo Code")
        verbose_name_plural = _("Promo Codes")
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['applicable_to']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else ' USD'}"
    
    @property
    def is_valid(self):
        """Check if promo is currently valid."""
        now = timezone.now()
        return (
            self.is_active and
            not self.is_deleted and
            self.start_date <= now <= self.end_date and
            (self.max_uses_total is None or self.usage_count < self.max_uses_total)
        )
    
    @property
    def remaining_uses(self):
        if self.max_uses_total:
            return self.max_uses_total - self.usage_count
        return None
    
    def can_user_use(self, user):
        """Check if a user can use this promo."""
        if not self.is_valid:
            return False
        
        if self.max_uses_per_user:
            used_count = PromoUsage.objects.filter(
                promo=self,
                user=user,
                is_successful=True
            ).count()
            if used_count >= self.max_uses_per_user:
                return False
        
        return True
    
    def calculate_discount(self, amount, delivery_fee=0):
        """Calculate discount for a given amount."""
        if not self.is_valid:
            return Decimal('0.00')
        
        if self.min_order_value and amount < self.min_order_value:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        
        elif self.discount_type == 'fixed':
            discount = self.discount_value
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        
        elif self.discount_type == 'free_delivery':
            return delivery_fee
        
        return Decimal('0.00')


class PromoUsage(models.Model):
    """
    Record of promo code usage.
    """
    
    promo = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='usages',
        db_index=True,
        help_text=_("Promo code used")
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_usages',
        db_index=True,
        help_text=_("User who used the promo")
    )
    
    service_request = models.ForeignKey(
        'transport.ServiceRequest',
        on_delete=models.CASCADE,
        related_name='promo_usages_request',
        db_index=True,
        help_text=_("Service request")
    )
    
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Discount amount applied")
    )
    
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_("Original amount before discount")
    )
    
    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_("Final amount after discount")
    )
    
    is_successful = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether promo was successfully applied")
    )
    
    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Reason for failure")
    )
    
    used_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("When promo was used")
    )
    
    class Meta:
        verbose_name = _("Promo Usage")
        verbose_name_plural = _("Promo Usages")
        indexes = [
            models.Index(fields=['promo']),
            models.Index(fields=['user']),
            models.Index(fields=['service_request']),
            models.Index(fields=['is_successful']),
        ]
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.user.email} used {self.promo.code} - {self.discount_amount} discount"