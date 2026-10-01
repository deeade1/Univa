# apps/backend/banking/models/regulatory.py

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class BVNVerification(models.Model):
    """BVN integration - MANDATORY for Nigerian fintech"""

    # BVN Validation regex (11 digits)
    bvn_validator = RegexValidator(
        regex=r'^\d{11}$',
        message='BVN must be exactly 11 digits'
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bvn_verification'
    )

    bvn_number = models.CharField(
        max_length=11,
        validators=[bvn_validator],
        db_index=True
    )

    # Verification status
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Verification Failed'),
        ('SUSPENDED', 'Suspended'),
    ]

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='PENDING',
        db_index=True
    )

    # BVN data (from NIBSS)
    full_name = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    enrollment_bank = models.CharField(max_length=100, blank=True)
    enrollment_branch = models.CharField(max_length=100, blank=True)

    # Timestamps
    verified_at = models.DateTimeField(null=True, blank=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Audit
    verification_attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    lock_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            BTreeIndex(fields=['verification_status']),
            BTreeIndex(fields=['bvn_number']),
            BTreeIndex(fields=['created_at']),
        ]
        verbose_name = 'BVN Verification'
        verbose_name_plural = 'BVN Verifications'

    def __str__(self):
        return f"BVN {self.bvn_number} - {self.user}"

    def can_attempt_verification(self):
        """Check if verification can be attempted"""
        if self.lock_until and timezone.now() < self.lock_until:
            return False
        return self.verification_attempts < 5

    def record_attempt(self, success=False):
        """Record verification attempt"""
        self.verification_attempts += 1
        self.last_attempt_at = timezone.now()

        if not success and self.verification_attempts >= 5:
            # Lock for 24 hours after 5 failed attempts
            self.lock_until = timezone.now() + timezone.timedelta(hours=24)

        self.save()


class CBNReport(models.Model):
    """Regulatory reporting to Central Bank of Nigeria"""

    REPORT_TYPES = [
        ('TRANSACTION', 'Transaction Report'),
        ('SUSPICIOUS', 'Suspicious Activity Report'),
        ('FRAUD', 'Fraud Report'),
        ('QUARTERLY', 'Quarterly Returns'),
        ('ANNUAL', 'Annual Returns'),
    ]

    REPORT_STATUS = [
        ('DRAFT', 'Draft'),
        ('GENERATED', 'Generated'),
        ('SUBMITTED', 'Submitted'),
        ('ACKNOWLEDGED', 'Acknowledged by CBN'),
        ('FAILED', 'Submission Failed'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, db_index=True)
    reporting_period = models.CharField(max_length=10)  # Format: YYYY-MM or YYYY-QQ
    reference = models.CharField(max_length=50, unique=True, db_index=True)

    # Report content
    report_data = models.JSONField()  # Actual report content
    summary = models.JSONField()  # Report summary statistics

    # Status tracking
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='DRAFT', db_index=True)

    # Submission details
    generated_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    # CBN response
    cbn_reference = models.CharField(max_length=100, blank=True)
    cbn_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            BTreeIndex(fields=['report_type', 'reporting_period']),
            BTreeIndex(fields=['status']),
            BTreeIndex(fields=['submitted_at']),
        ]
        verbose_name = 'CBN Report'
        verbose_name_plural = 'CBN Reports'

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.reporting_period}"