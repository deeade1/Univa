# transport/models/trip/shared_trip.py

"""
Shared Trip models for ride-sharing services.
SharedTrip should be a proxy model of ServiceRequest.
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from transport.models.core.service_request import ServiceRequest

logger = logging.getLogger(__name__)


class SharedTrip(ServiceRequest):
    """
    Shared Trip model - Proxy model for ServiceRequest.
    Represents a shared ride service with multiple passengers.
    """
    
    class DayTime(models.TextChoices):
        DAY = 'day', _('Day Trip')
        NIGHT = 'night', _('Night Trip')
    
    class SharedStatus(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        FULL = 'full', _('Fully Booked')
        DEPARTED = 'departed', _('Departed')
        COMPLETED = 'completed', _('Completed')
    
    class Meta:
        proxy = True
        verbose_name = _("Shared Trip")
        verbose_name_plural = _("Shared Trips")
        ordering = ['-created_at']
        # ✅ REMOVE indexes on JSON fields - they don't exist in the database
        # indexes = [
        #     models.Index(fields=['status', 'shared_day_time']),  # ❌ shared_day_time doesn't exist
        #     models.Index(fields=['shared_available_seats']),     # ❌ shared_available_seats doesn't exist
        # ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure service_type is set to SHARED
        if not self.pk:
            self.service_type = self.ServiceType.SHARED
        self._shared_data = self.shared_trip_data.copy() if self.shared_trip_data else {}
    
    # ============================================================
    # Shared Trip Properties (stored in shared_trip_data JSON)
    # ============================================================
    
    @property
    def shared_available_seats(self):
        """Get available seats."""
        return self._shared_data.get('available_seats', 3)
    
    @shared_available_seats.setter
    def shared_available_seats(self, value):
        self._shared_data['available_seats'] = value
        self._update_shared_data()
    
    @property
    def shared_day_time(self):
        """Get day/night preference."""
        return self._shared_data.get('day_time', SharedTrip.DayTime.DAY)
    
    @shared_day_time.setter
    def shared_day_time(self, value):
        self._shared_data['day_time'] = value
        self._update_shared_data()
    
    @property
    def shared_status(self):
        """Get shared trip status."""
        return self._shared_data.get('shared_status', SharedTrip.SharedStatus.AVAILABLE)
    
    @shared_status.setter
    def shared_status(self, value):
        self._shared_data['shared_status'] = value
        self._update_shared_data()
    
    @property
    def waitlist_count(self):
        """Get number of users on waitlist."""
        return WaitlistEntry.objects.filter(
            shared_trip=self,
            expired=False
        ).count()
    
    @property
    def is_available(self):
        """Check if trip has available seats."""
        return self.shared_available_seats > 0 and self.shared_status != self.SharedStatus.FULL
    
    @property
    def is_full(self):
        """Check if trip is full."""
        return self.shared_status == self.SharedStatus.FULL
    
    @property
    def day_time_display(self):
        """Get human-readable day/time display."""
        return dict(self.DayTime.choices).get(self.shared_day_time, self.shared_day_time)
    
    @property
    def shared_status_display(self):
        """Get human-readable shared status display."""
        return dict(self.SharedStatus.choices).get(self.shared_status, self.shared_status)
    
    # ============================================================
    # Internal Methods
    # ============================================================
    
    def _update_shared_data(self):
        """Update the shared_trip_data JSON field."""
        self.shared_trip_data = self._shared_data
    
    # ============================================================
    # Save Override
    # ============================================================
    
    def save(self, *args, **kwargs):
        """Save with shared data update."""
        if hasattr(self, '_shared_data'):
            self.shared_trip_data = self._shared_data
        super().save(*args, **kwargs)
    
    # ============================================================
    # Business Logic Methods
    # ============================================================
    
    def book_seat(self, user):
        """
        Book a seat on the shared trip.
        
        Args:
            user: User booking the seat
        
        Returns:
            Booking: Created booking instance
        
        Raises:
            ValueError: If no seats available
        """
        from transport.models.booking.booking import Booking
        
        if self.shared_status == self.SharedStatus.FULL:
            raise ValueError(_("This trip is already fully booked"))
        
        if self.shared_available_seats <= 0:
            self.shared_status = self.SharedStatus.FULL
            self.save()
            raise ValueError(_("No available seats left"))
        
        with transaction.atomic():
            # Create booking
            booking = Booking.objects.create(
                service_request=self,
                user=user,
                status=Booking.Status.CONFIRMED
            )
            
            # Decrease available seats
            self.shared_available_seats -= 1
            if self.shared_available_seats <= 0:
                self.shared_status = self.SharedStatus.FULL
            self.save()
            
            # Notify waitlist if full
            if self.shared_status == self.SharedStatus.FULL:
                self._notify_waitlist_users()
            
            return booking
    
    def add_to_waitlist(self, user):
        """
        Add user to waitlist for this shared trip.
        
        Args:
            user: User to add to waitlist
        
        Returns:
            WaitlistEntry: Created or existing waitlist entry
        """
        waitlist_entry, created = WaitlistEntry.objects.get_or_create(
            shared_trip=self,
            user=user,
            defaults={'expired': False}
        )
        return waitlist_entry
    
    def _notify_waitlist_users(self):
        """Notify users on waitlist that seats are available."""
        from transport.tasks import notify_waitlist_users
        notify_waitlist_users.delay(self.id)
    
    def calculate_shared_price(self):
        """Calculate dynamic pricing for shared trips."""
        from transport.services.pricing import PricingService
        pricing_service = PricingService()
        return pricing_service.calculate_shared_price(self)
    
    def get_waitlist_entries(self):
        """Get all active waitlist entries for this trip."""
        return WaitlistEntry.objects.filter(
            shared_trip=self,
            expired=False
        ).order_by('position')
    
    def get_position_for_user(self, user):
        """Get waitlist position for a specific user."""
        entry = WaitlistEntry.objects.filter(
            shared_trip=self,
            user=user,
            expired=False
        ).first()
        return entry.position if entry else None


class WaitlistEntry(models.Model):
    """
    Waitlist entry for shared trips.
    """
    
    shared_trip = models.ForeignKey(
        SharedTrip,
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
        db_index=True,
        help_text=_("Shared trip for this waitlist entry")
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trip_waitlists',
        db_index=True,
        help_text=_("User on the waitlist")
    )
    
    joined_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When user joined the waitlist")
    )
    
    position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Current position in waitlist (1-based)")
    )
    
    notified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether user has been notified")
    )
    
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When user was notified")
    )
    
    expired = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether entry has expired")
    )
    
    expired_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When entry expired")
    )
    
    # Preferences
    preferred_seats = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of preferred seat numbers")
    )
    
    special_requests = models.TextField(
        blank=True,
        help_text=_("Any special requests or requirements")
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Waitlist Entry")
        verbose_name_plural = _("Waitlist Entries")
        ordering = ['position', 'joined_at']
        indexes = [
            models.Index(fields=['shared_trip', 'notified']),
            models.Index(fields=['shared_trip', 'position']),
            models.Index(fields=['user', 'expired']),
            models.Index(fields=['joined_at']),
            models.Index(fields=['notified', 'expired']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['shared_trip', 'user'],
                name='unique_shared_trip_user_waitlist'
            ),
            models.UniqueConstraint(
                fields=['shared_trip', 'position'],
                condition=models.Q(position__isnull=False),
                name='unique_position_per_trip'
            ),
            models.UniqueConstraint(
                fields=['shared_trip', 'user'],
                condition=models.Q(expired=False),
                name='unique_active_waitlist_per_user_trip'
            ),
        ]
    
    def __str__(self):
        return f"Waitlist entry for {self.user.email} on Trip #{self.shared_trip.id}"
    
    def save(self, *args, **kwargs):
        """Save with automatic position assignment if not set."""
        if self.position is None and not self.expired:
            self.assign_position()
        super().save(*args, **kwargs)
    
    def assign_position(self):
        """Assign the next available position in the waitlist."""
        existing = WaitlistEntry.objects.filter(
            shared_trip=self.shared_trip,
            expired=False
        )
        if self.pk:
            existing = existing.exclude(pk=self.pk)
        
        max_position = existing.aggregate(
            max_pos=models.Max('position')
        )['max_pos']
        
        self.position = (max_position or 0) + 1
    
    def notify_availability(self):
        """Notify user of seat availability."""
        if self.notified or self.expired:
            return False
        
        from transport.tasks import send_seat_available_notification
        send_seat_available_notification.delay(
            user_id=self.user.id,
            trip_id=self.shared_trip.id,
            waitlist_entry_id=self.id
        )
        
        self.notified = True
        self.notified_at = timezone.now()
        self.save(update_fields=['notified', 'notified_at'])
        return True
    
    def expire(self):
        """Expire the waitlist entry."""
        if self.expired:
            return
        
        self.expired = True
        self.expired_at = timezone.now()
        self.save(update_fields=['expired', 'expired_at'])
    
    def activate(self):
        """Reactivate an expired waitlist entry."""
        if not self.expired:
            return
        
        self.expired = False
        self.expired_at = None
        self.position = None  # Will be re-assigned on save
        self.save()
    
    def get_position_display(self):
        """Get human-readable position with total count."""
        if not self.position:
            return "Waiting"
        
        total = WaitlistEntry.objects.filter(
            shared_trip=self.shared_trip,
            expired=False
        ).count()
        
        return f"{self.position} of {total}"
    
    @property
    def wait_time_hours(self):
        """Calculate estimated wait time in hours."""
        if not self.joined_at:
            return None
        
        delta = timezone.now() - self.joined_at
        return round(delta.total_seconds() / 3600, 1)
    
    @property
    def is_active(self):
        """Check if the waitlist entry is still active."""
        return not self.expired
    
    @property
    def priority_score(self):
        """Calculate a priority score based on various factors."""
        score = 0
        
        # Base score from position (lower position = higher priority)
        if self.position:
            score += max(100 - self.position, 0)
        
        # Bonus for long wait time
        if self.wait_time_hours:
            score += min(self.wait_time_hours * 5, 50)
        
        # Bonus for premium user (if applicable)
        if hasattr(self.user, 'is_premium') and self.user.is_premium:
            score += 20
        
        return score
    
    @classmethod
    def get_waitlist_for_trip(cls, shared_trip):
        """Get all active waitlist entries for a trip."""
        return cls.objects.filter(
            shared_trip=shared_trip,
            expired=False
        ).order_by('position')
    
    @classmethod
    def get_next_available(cls, shared_trip):
        """Get the next available user from the waitlist."""
        return cls.objects.filter(
            shared_trip=shared_trip,
            expired=False,
            notified=False
        ).order_by('position').first()


class UserPreference(models.Model):
    """
    User preferences for shared rides.
    """
    
    class MusicPreference(models.TextChoices):
        NONE = 'none', _('No Music')
        QUIET = 'quiet', _('Quiet Background')
        POP = 'pop', _('Pop Music')
        ROCK = 'rock', _('Rock Music')
        JAZZ = 'jazz', _('Jazz')
        CLASSICAL = 'classical', _('Classical')
    
    class ConversationLevel(models.IntegerChoices):
        QUIET = 1, _('Quiet')
        LOW = 2, _('Low')
        MODERATE = 3, _('Moderate')
        HIGH = 4, _('High')
        VERY_HIGH = 5, _('Very High')
    
    class TemperaturePreference(models.IntegerChoices):
        COOL = 1, _('Cool')
        MODERATE = 2, _('Moderate')
        WARM = 3, _('Warm')
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ride_preferences',
        help_text=_("User who owns these preferences")
    )
    
    music_preference = models.CharField(
        max_length=20,
        choices=MusicPreference.choices,
        default=MusicPreference.NONE,
        help_text=_("Preferred music type")
    )
    
    conversation_level = models.IntegerField(
        default=ConversationLevel.MODERATE,
        choices=ConversationLevel.choices,
        help_text=_("Preferred conversation level (1-5)")
    )
    
    temperature_preference = models.IntegerField(
        default=TemperaturePreference.MODERATE,
        choices=TemperaturePreference.choices,
        help_text=_("Preferred temperature setting")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("User Preference")
        verbose_name_plural = _("User Preferences")
    
    def __str__(self):
        return f"Preferences for {self.user.email}"