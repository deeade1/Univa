# apps/backend/banking/models/reconciliation.py

from django.conf import settings
from django.db import models

from .accounting import FloatAccount


class ReconciliationRun(models.Model):
    """Main reconciliation process run"""

    RUN_STATUS = [
        ('STARTED', 'Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partially Completed'),
    ]

    reference = models.CharField(max_length=50, unique=True, db_index=True)
    run_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20, choices=RUN_STATUS, default='STARTED', db_index=True
    )

    # Scope
    float_accounts = models.ManyToManyField(FloatAccount)
    date_from = models.DateField()
    date_to = models.DateField()

    # Results
    total_transactions = models.IntegerField(default=0)
    matched_transactions = models.IntegerField(default=0)
    unmatched_transactions = models.IntegerField(default=0)
    total_discrepancy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00
    )

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Metadata
    config = models.JSONField(default=dict)
    results = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['run_date', 'status']),
            models.Index(fields=['status']),
        ]
        ordering = ['-run_date']

    def __str__(self):
        return f"Reconciliation {self.reference} - {self.run_date}"


class ReconciliationMatch(models.Model):
    """Matched transactions between internal and external records"""

    MATCH_TYPE = [
        ('PERFECT', 'Perfect Match'),
        ('AMOUNT_MISMATCH', 'Amount Mismatch'),
        ('DATE_MISMATCH', 'Date Mismatch'),
        ('MANUAL', 'Manually Matched'),
    ]

    reconciliation_run = models.ForeignKey(
        ReconciliationRun,
        on_delete=models.CASCADE,
        related_name='matches',
    )
    float_account = models.ForeignKey(FloatAccount, on_delete=models.CASCADE)

    internal_transaction = models.ForeignKey(
        'banking.Transaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    internal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    internal_date = models.DateTimeField()

    external_reference = models.CharField(max_length=100, db_index=True)
    external_amount = models.DecimalField(max_digits=12, decimal_places=2)
    external_date = models.DateTimeField()
    external_description = models.TextField(blank=True)

    match_type = models.CharField(max_length=20, choices=MATCH_TYPE)
    match_confidence = models.FloatField(default=0.0)
    amount_difference = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )

    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    matched_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['external_reference']),
            models.Index(fields=['match_type']),
            models.Index(fields=['internal_transaction']),
        ]

    def __str__(self):
        ref = (
            self.internal_transaction.reference
            if self.internal_transaction
            else 'Manual'
        )
        return f"Match {ref}"


class UnreconciledTransaction(models.Model):
    """Transactions that couldn't be matched automatically"""

    reconciliation_run = models.ForeignKey(
        ReconciliationRun,
        on_delete=models.CASCADE,
        related_name='unreconciled_items',
    )
    float_account = models.ForeignKey(FloatAccount, on_delete=models.CASCADE)

    SOURCE_CHOICES = [
        ('INTERNAL', 'Internal System'),
        ('EXTERNAL', 'External/Bank'),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    transaction_reference = models.CharField(max_length=100, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField()
    description = models.TextField(blank=True)

    RESOLUTION_STATUS = [
        ('PENDING', 'Pending Investigation'),
        ('INVESTIGATING', 'Under Investigation'),
        ('RESOLVED', 'Resolved'),
        ('ADJUSTED', 'Ledger Adjusted'),
        ('IGNORED', 'Ignored - Valid Difference'),
    ]

    resolution_status = models.CharField(
        max_length=20,
        choices=RESOLUTION_STATUS,
        default='PENDING',
        db_index=True,
    )

    investigation_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['source', 'resolution_status']),
            models.Index(fields=['transaction_reference']),
        ]

    def __str__(self):
        return f"Unreconciled {self.source} - {self.transaction_reference}"