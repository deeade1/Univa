import logging
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class DriverEarning(models.Model):
    """Driver earnings tracking and payouts"""
    
    class PeriodType(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        CUSTOM = 'custom', _('Custom')
    
    class PayoutStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        PAID = 'paid', _('Paid')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(
        'ServiceProviderProfile',
        on_delete=models.CASCADE,
        related_name='earnings',
        db_index=True
    )
    period = models.CharField(
        max_length=10,
        choices=PeriodType.choices,
        db_index=True
    )
    
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)
    
    total_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    ride_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    delivery_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    cancellation_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    tips = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    bonuses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    
    commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    adjustments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    
    net_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    payout_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    
    payout_status = models.CharField(
        max_length=20,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
        db_index=True
    )
    '''payout_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.PaymentType.choices,  
        blank=True
    )'''
    payout_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    
    total_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    total_deliveries = models.PositiveIntegerField(default=0)
    completed_deliveries = models.PositiveIntegerField(default=0)
    total_distance = models.FloatField(default=0.0)
    online_hours = models.FloatField(default=0.0)
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Driver Earning")
        verbose_name_plural = _("Driver Earnings")
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['driver', 'period_start']),
            models.Index(fields=['period', 'payout_status']),
            models.Index(fields=['payout_status', 'period_end']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['driver', 'payout_status']),
            models.Index(fields=['paid_at']),
        ]
        constraints = [
        
            models.UniqueConstraint(
                fields=['driver', 'period_start', 'period_end'],
                name='unique_driver_period_earning'
            ),
            
            models.CheckConstraint(
                condition=models.Q(period_end__gt=models.F('period_start')),
                name='earning_period_valid'
            ),
            
            models.CheckConstraint(
                condition=models.Q(net_earnings__gte=0),
                name='net_earnings_non_negative'
            ),
            
            models.CheckConstraint(
                condition=models.Q(payout_amount__gte=0),
                name='payout_amount_non_negative'
            ),
        ]
        
    
    def __str__(self):
        return f"Earnings {self.driver.user.email} - {self.period} {self.period_start.date()}"
    
    def clean(self):
        """Validate earning data."""
        from django.core.exceptions import ValidationError
        
        if self.period_end <= self.period_start:
            raise ValidationError({
                "period_end": _("Period end must be after period start")
            })
        
        if self.net_earnings < 0:
            raise ValidationError({
                "net_earnings": _("Net earnings cannot be negative")
            })
        
        if self.payout_amount < 0:
            raise ValidationError({
                "payout_amount": _("Payout amount cannot be negative")
            })
        
        # Validate commission rate
        if not (0 <= self.commission_rate <= 100):
            raise ValidationError({
                "commission_rate": _("Commission rate must be between 0 and 100")
            })
        
        # Validate payout status transitions
        if self.pk:
            old = DriverEarning.objects.get(pk=self.pk)
            if old.payout_status == self.PayoutStatus.PAID and self.payout_status != self.PayoutStatus.PAID:
                raise ValidationError({
                    "payout_status": _("Cannot change status after payout is completed")
                })
    
    def save(self, *args, **kwargs):
        self.calculate_earnings()
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calculate_earnings(self):
        """Calculate all earnings and deductions"""
        self.total_earnings = (
            self.ride_earnings +
            self.delivery_earnings +
            self.cancellation_fees +
            self.tips +
            self.bonuses
        )
        
        if not self.commission and self.commission_rate > 0:
            self.commission = (self.total_earnings * self.commission_rate) / 100
        
        self.net_earnings = (
            self.total_earnings -
            self.commission -
            self.fees +
            self.adjustments
        )
        
        self.payout_amount = max(0, self.net_earnings)
    
    def mark_as_paid(self, reference=None):
        """Mark earnings as paid."""
        if self.payout_status == self.PayoutStatus.PAID:
            raise ValidationError(_("Earnings already marked as paid"))
        
        self.payout_status = self.PayoutStatus.PAID
        self.paid_at = timezone.now()
        if reference:
            self.payout_reference = reference
        self.save()
    
    def mark_as_failed(self, reason=None):
        """Mark earnings payout as failed."""
        if self.payout_status == self.PayoutStatus.PAID:
            raise ValidationError(_("Cannot mark paid earnings as failed"))
        
        self.payout_status = self.PayoutStatus.FAILED
        if reason:
            self.metadata['failure_reason'] = reason
        self.save()
    
    def cancel_payout(self):
        """Cancel the payout."""
        if self.payout_status == self.PayoutStatus.PAID:
            raise ValidationError(_("Cannot cancel paid earnings"))
        
        self.payout_status = self.PayoutStatus.CANCELLED
        self.save()
    
    @classmethod
    def get_pending_payouts(cls):
        """Get all pending payouts."""
        return cls.objects.filter(
            payout_status=cls.PayoutStatus.PENDING
        ).order_by('period_end')
    
    @classmethod
    def get_earnings_for_driver(cls, driver_id, period_start=None, period_end=None):
        """Get earnings for a specific driver with optional date range."""
        qs = cls.objects.filter(driver_id=driver_id)
        if period_start:
            qs = qs.filter(period_start__gte=period_start)
        if period_end:
            qs = qs.filter(period_end__lte=period_end)
        return qs.order_by('-period_start')
    
    @classmethod
    def get_total_earnings_for_driver(cls, driver_id, period_start=None, period_end=None):
        """Get total earnings for a driver."""
        qs = cls.get_earnings_for_driver(driver_id, period_start, period_end)
        return qs.aggregate(
            total_earnings=models.Sum('net_earnings')
        )['total_earnings'] or 0
    
    @property
    def is_paid(self):
        """Check if earnings have been paid."""
        return self.payout_status == self.PayoutStatus.PAID
    
    @property
    def is_pending(self):
        """Check if earnings are pending."""
        return self.payout_status == self.PayoutStatus.PENDING
    
    @property
    def period_display(self):
        """Get human-readable period display."""
        return f"{self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}"

class IncentiveProgram(models.Model):
    """Driver incentive and bonus programs"""
    class IncentiveType(models.TextChoices):
        SIGNUP_BONUS = 'signup_bonus', _('Signup Bonus')
        RIDE_CHALLENGE = 'ride_challenge', _('Ride Challenge')
        RATING_BONUS = 'rating_bonus', _('Rating Bonus')
        REFERRAL_BONUS = 'referral_bonus', _('Referral Bonus')
        LOYALTY_BONUS = 'loyalty_bonus', _('Loyalty Bonus')
        SURGE_BONUS = 'surge_bonus', _('Surge Bonus')
    
    name = models.CharField(max_length=200)
    incentive_type = models.CharField(
        max_length=20,
        choices=IncentiveType.choices,
        db_index=True
    )
    description = models.TextField()
    
    min_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    min_completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    min_rides = models.PositiveIntegerField(null=True, blank=True)
    service_types = models.JSONField(default=list, blank=True)
    
    reward_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    reward_type = models.CharField(
        max_length=20,
        choices=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage'),
            ('multiplier', 'Earnings Multiplier'),
        ],
        default='fixed'
    )
    
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['incentive_type', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        verbose_name = _("Incentive Program")
        verbose_name_plural = _("Incentive Programs")
    
    def __str__(self):
        return f"{self.name} - {self.get_incentive_type_display()}"