# apps/backend/banking/models/security.py

"""
Banking security models.

This module contains banking-specific security models including:
    - BankingSecurity: PIN management for banking users
    - PhoneChangeRequest: Phone number change with OTP
    - FraudDetectionRule: Fraud detection rules
    - FraudAlert: Fraud alerts
    - AuditLog: Banking audit trail

Banking security models.

This module contains banking-specific security models including:
    - BankingSecurity: PIN management for banking users (SINGLE SOURCE OF TRUTH)
    - PhoneChangeRequest: Phone number change with OTP
    - FraudDetectionRule: Fraud detection rules
    - FraudAlert: Fraud alerts
    - AuditLog: Banking audit trail

IMPORTANT
---------
BankingSecurity is the SINGLE SOURCE OF TRUTH for banking PINs.

The Account model does NOT store PINs anymore.
Use BankingSecurity for all PIN operations:

    security = BankingSecurity.objects.get(user=user)
    security.set_pin("1234")
    security.check_pin("1234")
"""
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ============================================================================
# BANKING SECURITY
# ============================================================================

class BankingSecurity(models.Model):
    """
    Banking-specific security settings for a user.

    This model stores banking PINs and security-related settings.
    It belongs to the banking domain, NOT accounts.

    This is the SINGLE SOURCE OF TRUTH for banking PINs.

    PIN features:
        - Hashed storage (never plaintext)
        - 4-digit validation
        - Lockout after 3 failed attempts
        - 30-minute lockout duration
        - Attempt tracking
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_security",
    )

    # ------------------------------------------------------------------
    # PIN - SINGLE SOURCE OF TRUTH
    # ------------------------------------------------------------------

    pin_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Hashed banking PIN.",
    )

    pin_set_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the PIN was last set.",
    )

    pin_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of consecutive failed PIN attempts.",
    )

    pin_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the PIN will be unlocked.",
    )

    # ------------------------------------------------------------------
    # Security settings
    # ------------------------------------------------------------------

    require_pin_for_transactions = models.BooleanField(
        default=True,
        help_text="Whether PIN is required for transactions.",
    )

    require_pin_for_login = models.BooleanField(
        default=False,
        help_text="Whether PIN is required for login.",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Banking Security")
        verbose_name_plural = _("Banking Security Settings")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "pin_locked_until"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Banking Security for {self.user.email}"

    # ------------------------------------------------------------------
    # PIN Properties
    # ------------------------------------------------------------------

    @property
    def has_pin(self) -> bool:
        """Return True if a PIN is set."""
        return bool(self.pin_hash)

    @property
    def is_pin_locked(self) -> bool:
        """Return True if the PIN is currently locked."""
        if not self.pin_locked_until:
            return False
        return timezone.now() < self.pin_locked_until

    @property
    def remaining_lockout_minutes(self) -> int:
        """Return remaining lockout minutes, or 0 if not locked."""
        if not self.is_pin_locked:
            return 0
        return int((self.pin_locked_until - timezone.now()).total_seconds() // 60)

    # ------------------------------------------------------------------
    # PIN Management
    # ------------------------------------------------------------------

    def set_pin(self, pin: str) -> None:
        """
        Hash and store a new PIN.

        Args:
            pin: 4-digit PIN string.

        Raises:
            ValidationError: If PIN format is invalid.

        This is the SINGLE SOURCE OF TRUTH for setting PINs.
        """
        if not pin or len(pin) != 4 or not pin.isdigit():
            raise ValidationError("PIN must be exactly 4 digits.")

        self.pin_hash = make_password(pin)
        self.pin_set_at = timezone.now()
        self.pin_attempts = 0
        self.pin_locked_until = None
        self.save()

    def check_pin(self, pin: str) -> bool:
        """
        Verify a PIN with lockout protection.

        Args:
            pin: 4-digit PIN to verify.

        Returns:
            True if PIN is correct.

        Raises:
            ValidationError: If PIN is incorrect or account is locked.

        This is the SINGLE SOURCE OF TRUTH for checking PINs.
        """
        if self.is_pin_locked:
            remaining = self.remaining_lockout_minutes
            raise ValidationError(
                f"PIN is temporarily locked. Try again in {remaining} minutes."
            )

        if not self.pin_hash:
            raise ValidationError("No PIN is set for this account.")

        if check_password(pin, self.pin_hash):
            # Success - reset attempts
            self.pin_attempts = 0
            self.pin_locked_until = None
            self.save()
            return True

        # Failure - increment attempts
        self.pin_attempts += 1

        if self.pin_attempts >= 3:
            self.pin_locked_until = timezone.now() + timedelta(minutes=30)

        self.save()
        remaining = 3 - self.pin_attempts

        if self.is_pin_locked:
            raise ValidationError("Too many failed attempts. PIN is locked for 30 minutes.")

        raise ValidationError(f"Incorrect PIN. You have {remaining} attempt(s) left.")

    def reset_pin_attempts(self) -> None:
        """Reset failed PIN attempts and unlock the PIN."""
        self.pin_attempts = 0
        self.pin_locked_until = None
        self.save()

    def clear_pin(self) -> None:
        """Clear the stored PIN (disable PIN authentication)."""
        self.pin_hash = None
        self.pin_set_at = None
        self.pin_attempts = 0
        self.pin_locked_until = None
        self.save()


# ============================================================================
# PHONE CHANGE REQUEST
# ============================================================================

class PhoneChangeRequest(models.Model):
    """
    Request to change a user's phone number.
    
    This model manages the phone number change process with OTP verification.
    It includes rate limiting, lockout protection, and OTP expiration.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="phone_change_request"
    )
    old_phone = models.CharField(max_length=20)
    new_phone = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # OTP attempt tracking
    otp_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Constants
    OTP_EXPIRY_MINUTES = 10
    OTP_RESEND_INTERVAL = 60  # seconds
    MAX_ATTEMPTS = 3
    LOCK_DURATION_MINUTES = 30

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['new_phone', 'verified']),
            models.Index(fields=['otp_sent_at']),
        ]

    def generate_otp(self):
        """
        Generate a new OTP with rate limiting and lockout protection.
        
        Returns:
            str: The generated 6-digit OTP.
            
        Raises:
            ValidationError: If rate limit is exceeded or account is locked.
        """
        now = timezone.now()

        # Check if locked
        if self.locked_until and now < self.locked_until:
            remaining = int((self.locked_until - now).total_seconds() // 60)
            raise ValidationError(
                f"Too many failed attempts. Try again in {remaining} minutes."
            )

        # Enforce resend interval
        if self.otp_sent_at and (now - self.otp_sent_at).total_seconds() < self.OTP_RESEND_INTERVAL:
            remaining = int(self.OTP_RESEND_INTERVAL - (now - self.otp_sent_at).total_seconds())
            raise ValidationError(
                f"Please wait {remaining}s before requesting another OTP."
            )

        # Reset attempts & lock if sending new OTP
        self.otp_attempts = 0
        self.locked_until = None

        # Generate random 6-digit OTP
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_sent_at = now
        self.save(update_fields=["otp_code", "otp_sent_at", "otp_attempts", "locked_until"])
        
        return self.otp_code

    def is_otp_valid(self, code: str) -> bool:
        """
        Validate OTP with lockout and expiration checks.
        
        Args:
            code: The OTP code to validate.
            
        Returns:
            bool: True if OTP is valid.
            
        Raises:
            ValidationError: If OTP is invalid, expired, or account is locked.
        """
        now = timezone.now()

        # Check if locked
        if self.locked_until and now < self.locked_until:
            raise ValidationError("Too many failed attempts. Please try again later.")

        # Check if OTP exists
        if not self.otp_code or not self.otp_sent_at:
            raise ValidationError("No OTP found.")

        # Check expiration
        if now - self.otp_sent_at > timedelta(minutes=self.OTP_EXPIRY_MINUTES):
            raise ValidationError("OTP has expired.")

        # Validate code
        if self.otp_code != code:
            self.otp_attempts += 1
            
            if self.otp_attempts >= self.MAX_ATTEMPTS:
                self.locked_until = now + timedelta(minutes=self.LOCK_DURATION_MINUTES)
                self.save(update_fields=["otp_attempts", "locked_until"])
                raise ValidationError("Too many failed attempts. Please try again later.")
            
            self.save(update_fields=["otp_attempts"])
            remaining = self.MAX_ATTEMPTS - self.otp_attempts
            raise ValidationError(f"Incorrect OTP. You have {remaining} attempt(s) left.")
        
        return True

    def mark_verified(self):
        """Mark the phone change request as verified."""
        self.verified = True
        self.save(update_fields=["verified"])
    
    def __str__(self):
        return f"PhoneChangeRequest({self.user}, {self.new_phone})"

# ============================================================================
# FRAUD DETECTION RULE
# ============================================================================

class FraudDetectionRule(models.Model):
    """Defines rules for detecting fraudulent activities."""
    
    class RuleType(models.TextChoices):
        TRANSACTION_AMOUNT = 'TRANSACTION_AMOUNT', _('Transaction Amount')
        FREQUENCY = 'FREQUENCY', _('Frequency Threshold')
        LOCATION = 'LOCATION', _('Location Anomaly')
        DEVICE = 'DEVICE', _('Device Change')
        BEHAVIORAL = 'BEHAVIORAL', _('Behavioral Pattern')

    name = models.CharField(_('Rule Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    rule_type = models.CharField(
        _('Rule Type'),
        max_length=20,
        choices=RuleType.choices
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    threshold = models.FloatField(_('Threshold Value'))
    conditions = models.JSONField(_('Rule Conditions'), default=dict)
    action = models.CharField(
        _('Action'),
        max_length=50,
        choices=[
            ('FLAG', _('Flag for review')),
            ('BLOCK', _('Block transaction')),
            ('NOTIFY', _('Notify admin')),
            ('REQUIRE_VERIFICATION', _('Require additional verification'))
        ],
        default='FLAG'
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use User directly
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_fraud_rules'
    )

    class Meta:
        verbose_name = _('Fraud Detection Rule')
        verbose_name_plural = _('Fraud Detection Rules')
        ordering = ['-is_active', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


# ============================================================================
# FRAUD ALERT
# ============================================================================

class FraudAlert(models.Model):
    """Records instances where fraud detection rules were triggered."""
    
    class AlertStatus(models.TextChoices):
        OPEN = 'OPEN', _('Open')
        INVESTIGATING = 'INVESTIGATING', _('Under Investigation')
        RESOLVED = 'RESOLVED', _('Resolved')
        FALSE_POSITIVE = 'FALSE_POSITIVE', _('False Positive')

    rule = models.ForeignKey(
        FraudDetectionRule,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use User directly
        on_delete=models.CASCADE,
        related_name='fraud_alerts',
        null=True,
        blank=True
    )
    transaction_reference = models.CharField(
        _('Transaction Reference'),
        max_length=100,
        blank=True,
        null=True
    )
    detected_value = models.FloatField(_('Detected Value'))
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=AlertStatus.choices,
        default='OPEN'
    )
    evidence_data = models.JSONField(_('Evidence Data'), default=dict)
    notes = models.TextField(_('Investigation Notes'), blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use User directly
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Fraud Alert')
        verbose_name_plural = _('Fraud Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user']),
            models.Index(fields=['rule']),
        ]

    def __str__(self):
        return f"Alert #{self.id} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if self.status in ['RESOLVED', 'FALSE_POSITIVE'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


# ============================================================================
# AUDIT LOG
# ============================================================================

class AuditLog(models.Model):
    """Comprehensive audit trail for all banking operations."""
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('TRANSACTION', 'Transaction'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use User directly
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type}"


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "BankingSecurity",
    "PhoneChangeRequest",
    "FraudDetectionRule",
    "FraudAlert",
    "AuditLog",
]