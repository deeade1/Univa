# apps/backend/banking/models/integrations.py

import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class BankAPIIntegration(models.Model):
    """Configuration for Nigerian bank/payment processor integrations."""

    PROVIDER_CHOICES = [
        ('NIBSS', 'NIBSS Instant Payment'),
        ('PAYSTACK', 'Paystack'),
        ('FLUTTERWAVE', 'Flutterwave'),
        ('MONNIFY', 'Monnify'),
        ('INTERSWITCH', 'Interswitch'),
        ('BANK', 'Direct Bank API'),
    ]

    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, db_index=True
    )

    # Encrypted credentials
    _api_key = models.BinaryField(null=True, blank=True)
    _secret_key = models.BinaryField(null=True, blank=True)
    base_url = models.URLField()

    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False, db_index=True)
    weight = models.IntegerField(default=1)

    max_amount_per_transaction = models.DecimalField(
        max_digits=12, decimal_places=2, default=500000.00
    )
    daily_amount_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=5000000.00
    )
    supported_banks = models.JSONField(default=list)

    success_rate = models.FloatField(default=0.0)
    average_response_time = models.FloatField(default=0.0)
    total_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider})"

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------

    def _get_cipher(self):
        key = settings.ENCRYPTION_KEY.encode()
        return Fernet(key)

    @property
    def api_key(self):
        if not self._api_key:
            return None
        cipher = self._get_cipher()
        return cipher.decrypt(self._api_key).decode()

    @api_key.setter
    def api_key(self, value):
        if value:
            cipher = self._get_cipher()
            self._api_key = cipher.encrypt(value.encode())

    @property
    def secret_key(self):
        if not self._secret_key:
            return None
        cipher = self._get_cipher()
        return cipher.decrypt(self._secret_key).decode()

    @secret_key.setter
    def secret_key(self, value):
        if value:
            cipher = self._get_cipher()
            self._secret_key = cipher.encrypt(value.encode())

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """
        Return whether this integration is currently healthy.

        Healthy means is_active and either no traffic yet or a
        success_rate >= 50 (percentage).
        """
        if not self.is_active:
            return False
        if self.total_requests == 0:
            return True
        return self.success_rate >= 50.0

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def record_request(self, *, successful: bool, duration_ms: float = 0.0):
        """
        Update rolling success rate and average response time.

        Stores success_rate as a percentage 0-100.
        """
        total = self.total_requests + 1
        completed = self.total_requests

        if successful:
            completed_successes = round(
                (self.success_rate / 100.0) * self.total_requests
            ) + 1
        else:
            completed_successes = round(
                (self.success_rate / 100.0) * self.total_requests
            )
            self.failed_requests += 1

        self.success_rate = (completed_successes / total) * 100.0

        if duration_ms > 0:
            if self.total_requests == 0:
                self.average_response_time = duration_ms
            else:
                self.average_response_time = (
                    self.average_response_time * completed + duration_ms
                ) / total

        self.total_requests = total
        self.save(update_fields=[
            "success_rate",
            "average_response_time",
            "total_requests",
            "failed_requests",
            "updated_at",
        ])


class APITransactionLog(models.Model):
    """Comprehensive log of all external API calls."""

    integration = models.ForeignKey(
        BankAPIIntegration,
        on_delete=models.CASCADE,
        related_name='api_logs',
    )

    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10, default='POST')
    request_headers = models.JSONField(default=dict)
    request_body = models.JSONField()

    response_headers = models.JSONField(default=dict)
    response_body = models.JSONField()
    http_status = models.IntegerField()

    reference = models.CharField(max_length=100, db_index=True)
    external_reference = models.CharField(
        max_length=100, blank=True, null=True, db_index=True
    )

    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.FloatField(default=0.0)

    is_successful = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['is_successful', 'created_at']),
            models.Index(fields=['http_status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"API Log {self.reference} - {self.http_status}"