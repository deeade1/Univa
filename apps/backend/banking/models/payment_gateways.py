# apps/backend/banking/models/payment_gateways.py

import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from django.utils import timezone


def _normalize_phone(phone) -> str:
    """
    Return the phone number as a digits-only E.164 string.

    Accepts strings, ints, and phonenumber_field PhoneNumber
    instances (whose __str__ is verbose). Coerces to digits and
    keeps a leading country-code-less national format compatible
    with Nigerian USSD gateways (10-13 digits).
    """
    if phone is None:
        return ""

    # PhoneNumber exposes .national_number and .country_code
    national = getattr(phone, "national_number", None)
    country = getattr(phone, "country_code", None)
    if national:
        if country:
            return f"+{country}{national}".lstrip("+")
        return str(national)

    digits = "".join(c for c in str(phone) if c.isdigit())
    return digits

class PaymentGateway(models.Model):
    """Unified payment gateway configuration."""

    PROVIDER_CHOICES = [
        ('FLUTTERWAVE', 'Flutterwave'),
        ('PAYSTACK', 'Paystack'),
        ('MONNIFY', 'Monnify'),
        ('REMITA', 'Remita'),
        ('INTERSWITCH', 'Interswitch'),
        ('NIBSS', 'NIBSS'),
    ]

    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES
    )

    # Encrypted credentials
    _public_key = models.BinaryField(null=True, blank=True)
    _secret_key = models.BinaryField(null=True, blank=True)
    _encryption_key = models.BinaryField(null=True, blank=True)

    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    weight = models.IntegerField(default=1)

    supports_transfer = models.BooleanField(default=True)
    supports_collection = models.BooleanField(default=True)
    supports_ussd = models.BooleanField(default=False)
    supports_card = models.BooleanField(default=False)
    supports_bank_account = models.BooleanField(default=True)

    success_rate = models.FloatField(default=0.0)
    average_response_time = models.FloatField(default=0.0)
    uptime_percentage = models.FloatField(default=100.0)

    requests_per_minute = models.IntegerField(default=60)
    daily_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=5000000.00
    )

    config = models.JSONField(default=dict)

    class Meta:
        ordering = ['-is_default', 'weight']

    def __str__(self):
        return f"{self.name} ({self.provider})"

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------

    def _get_cipher(self):
        return Fernet(settings.ENCRYPTION_KEY.encode())

    @property
    def public_key(self):
        if self._public_key:
            return self._get_cipher().decrypt(self._public_key).decode()
        return None

    @public_key.setter
    def public_key(self, value):
        if value:
            self._public_key = self._get_cipher().encrypt(value.encode())

    @property
    def secret_key(self):
        if self._secret_key:
            return self._get_cipher().decrypt(self._secret_key).decode()
        return None

    @secret_key.setter
    def secret_key(self, value):
        if value:
            self._secret_key = self._get_cipher().encrypt(value.encode())

    @property
    def encryption_key(self):
        if self._encryption_key:
            return self._get_cipher().decrypt(
                self._encryption_key
            ).decode()
        return None

    @encryption_key.setter
    def encryption_key(self, value):
        if value:
            self._encryption_key = self._get_cipher().encrypt(
                value.encode()
            )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        if not self.is_active:
            return False
        return self.uptime_percentage >= 95.0


class USSDSession(models.Model):
    """USSD session management."""

    session_id = models.CharField(
        max_length=50, unique=True, db_index=True
    )
    phone_number = models.CharField(max_length=32, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    current_menu = models.CharField(max_length=50, default='main')
    previous_menu = models.CharField(max_length=50, blank=True)
    session_data = models.JSONField(default=dict)

    transaction_type = models.CharField(max_length=50, blank=True)
    transaction_data = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.session_id:
            self.session_id = f"USSD-{uuid.uuid4().hex[:8].upper()}"

        if not self.expires_at:
            self.expires_at = (
                timezone.now() + timezone.timedelta(minutes=5)
            )

        # Coerce to E.164 digits. User.phone_number may be a
        # phonenumber_field PhoneNumber whose str() is verbose.
        if self.phone_number:
            self.phone_number = _normalize_phone(self.phone_number)

        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"USSDSession({self.session_id}, {self.phone_number})"


class USSDOperation(models.Model):
    """USSD operation logging."""

    OPERATION_TYPES = [
        ('BALANCE_CHECK', 'Check Balance'),
        ('TRANSFER', 'Transfer Funds'),
        ('AIR_TIME', 'Buy Airtime'),
        ('DATA', 'Buy Data'),
        ('BILL_PAYMENT', 'Pay Bill'),
        ('PIN_CHANGE', 'Change PIN'),
        ('MINI_STATEMENT', 'Mini Statement'),
        ('MAIN_MENU', 'Main Menu'),
        ('OTHER', 'Other'),
    ]

    session = models.ForeignKey(USSDSession, on_delete=models.CASCADE)
    operation_type = models.CharField(
        max_length=50, choices=OPERATION_TYPES
    )
    ussd_code = models.CharField(max_length=50)
    input_text = models.TextField()
    response_text = models.TextField()
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    transaction_ref = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"USSDOperation({self.operation_type}, "
            f"{self.session.phone_number}, {self.created_at})"
        )