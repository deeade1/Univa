import uuid
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

def qr_ticket_upload_to(instance, filename):
    return f"tickets/{instance.trip.id}/{instance.id}.png"


class BoardingTicket(models.Model):
    """QR Boarding Ticket model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(
        "Trip", 
        on_delete=models.CASCADE, 
        related_name="tickets",
        db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name="tickets",
        db_index=True
    )
    booking = models.ForeignKey(
        "Booking", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="tickets",
        db_index=True
    )
    
    # Ticket details
    seat_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Assigned seat number"
    )
    ticket_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique ticket number (can be generated)"
    )
    ticket_type = models.CharField(
        max_length=50,
        choices=[
            ('standard', 'Standard'),
            ('premium', 'Premium'),
            ('vip', 'VIP'),
            ('discount', 'Discount'),
            ('promotional', 'Promotional'),
        ],
        default='standard',
        db_index=True
    )
    
    # QR Code
    qr_image = models.ImageField(
        upload_to=qr_ticket_upload_to, 
        null=True, 
        blank=True,
        help_text="QR code image for ticket"
    )
    qr_code_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Raw data encoded in QR code"
    )
    
    # Status
    redeemed = models.BooleanField(
        default=False, 
        db_index=True
    )
    redeemed_at = models.DateTimeField(
        null=True, 
        blank=True
    )
    cancelled = models.BooleanField(
        default=False,
        db_index=True
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Usage
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ticket was used"
    )
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_checked_in",
        help_text="Staff who checked in the ticket"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Boarding Ticket")
        verbose_name_plural = _("Boarding Tickets")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["trip", "user"]),
            models.Index(fields=["ticket_type", "redeemed"]),
            models.Index(fields=["redeemed", "created_at"]),
            models.Index(fields=["ticket_number"]),
            models.Index(fields=["cancelled", "redeemed"]),
        ]
        constraints = [
            
            models.UniqueConstraint(
                fields=["trip", "user", "booking"],
                name="unique_trip_user_booking_ticket"
            ),
            
            models.UniqueConstraint(
                fields=["ticket_number"],
                condition=models.Q(ticket_number__isnull=False),
                name="unique_ticket_number_when_provided"
            ),
        ]
        
    
    def __str__(self):
        return f"Ticket {self.id} for {self.user.email} on trip {self.trip.id}"

    def generate_qr(self, payload: dict | None = None):
        """Generate and store QR image"""
        import json
        from io import BytesIO
        from django.core.files.base import ContentFile
        import qrcode
        
        data = payload or {
            "ticket_id": str(self.id),
            "trip_id": str(self.trip.id),
            "user_id": str(self.user.id),
            "ticket_type": self.ticket_type,
        }
        
        self.qr_code_data = data
        
        payload_str = json.dumps(data)
        img = qrcode.make(payload_str)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        django_file = ContentFile(buffer.read(), name=f"{self.id}.png")
        self.qr_image.save(f"{self.id}.png", django_file, save=True)
        return self.qr_image.url
    
    def generate_ticket_number(self):
        """Generate a unique ticket number."""
        import secrets
        import string
        
        # Generate a unique ticket number
        prefix = "TKT"
        characters = string.ascii_uppercase + string.digits
        random_part = ''.join(secrets.choice(characters) for _ in range(12))
        self.ticket_number = f"{prefix}-{random_part}"
        
        # Ensure uniqueness
        while BoardingTicket.objects.filter(ticket_number=self.ticket_number).exists():
            random_part = ''.join(secrets.choice(characters) for _ in range(12))
            self.ticket_number = f"{prefix}-{random_part}"
        
        return self.ticket_number
    
    def redeem(self, staff_user=None):
        """Redeem the ticket"""
        if self.redeemed:
            raise ValidationError(_("Ticket has already been redeemed"))
        
        if self.cancelled:
            raise ValidationError(_("Cannot redeem a cancelled ticket"))
        
        self.redeemed = True
        self.redeemed_at = timezone.now()
        self.used_at = timezone.now()
        if staff_user:
            self.checked_in_by = staff_user
        self.save()
    
    def cancel(self):
        """Cancel the ticket"""
        if self.redeemed:
            raise ValidationError(_("Cannot cancel a redeemed ticket"))
        
        self.cancelled = True
        self.cancelled_at = timezone.now()
        self.save()
    
    def is_valid(self):
        """Check if the ticket is valid for use"""
        return not self.redeemed and not self.cancelled
    
    @property
    def is_redeemed(self):
        return self.redeemed
    
    @property
    def is_cancelled(self):
        return self.cancelled
    
    @property
    def status(self):
        """Get the status of the ticket"""
        if self.cancelled:
            return 'cancelled'
        if self.redeemed:
            return 'redeemed'
        return 'active'
    
    @classmethod
    def get_active_tickets_for_user(cls, user):
        """Get all active tickets for a user"""
        return cls.objects.filter(
            user=user,
            redeemed=False,
            cancelled=False
        ).order_by('trip__departure_time')
    
    @classmethod
    def get_redeemed_tickets_for_trip(cls, trip):
        """Get all redeemed tickets for a trip"""
        return cls.objects.filter(
            trip=trip,
            redeemed=True
        ).select_related('user')
    
    @classmethod
    def get_ticket_count_for_trip(cls, trip):
        """Get ticket count for a trip"""
        return cls.objects.filter(trip=trip).count()
    
    @classmethod
    def get_redeemed_count_for_trip(cls, trip):
        """Get redeemed ticket count for a trip"""
        return cls.objects.filter(trip=trip, redeemed=True).count()