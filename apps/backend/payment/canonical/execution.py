"""
Canonical PaymentExecution model for Univa.

A PaymentExecution represents one attempt to execute a Payment.

Payment:
    business payment operation

PaymentExecution:
    individual execution attempt

Provider:
    external/internal execution infrastructure
"""

import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .payment import Payment


class PaymentExecution(models.Model):
    class RouteType(models.TextChoices):
        UNIVA_INTERNAL = "univa_internal", _("Univa Internal")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
        CARD = "card", _("Card")
        WALLET = "wallet", _("Wallet")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        CREATED = "created", _("Created")
        PROCESSING = "processing", _("Processing")
        PENDING = "pending", _("Pending")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    class ReconciliationState(models.TextChoices):
        NOT_REQUIRED = "not_required", _("Not Required")
        PENDING = "pending", _("Pending")
        REQUIRED = "required", _("Required")
        RECONCILED = "reconciled", _("Reconciled")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="executions",
    )

    attempt_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    idempotency_key = models.CharField(
        max_length=150,
        unique=True,
    )

    route_type = models.CharField(
        max_length=30,
        choices=RouteType.choices,
    )

    # Normalized provider identifier/reference.
    # This is deliberately not a FK to Banking or a provider model.
    provider = models.CharField(
        max_length=100,
    )

    provider_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    # Canonical PaymentInstrument belongs to the same
    # payment_canonical Django app label.
    instrument = models.ForeignKey(
        "payment_canonical.PaymentInstrument",
        on_delete=models.PROTECT,
        related_name="executions",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    reconciliation_state = models.CharField(
        max_length=20,
        choices=ReconciliationState.choices,
        default=ReconciliationState.NOT_REQUIRED,
    )

    failure_code = models.CharField(
        max_length=50,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    processing_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    pending_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reconciled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "payment_canonical"
        db_table = "payment_canonical_execution"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "attempt_number"],
                name="payment_execution_attempt_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["payment", "status", "created_at"],
                name="pay_exec_payment_status_idx",
            ),
            models.Index(
                fields=["provider", "provider_reference"],
                name="pay_exec_provider_ref_idx",
            ),
            models.Index(
                fields=["reconciliation_state", "created_at"],
                name="pay_exec_reconcile_idx",
            ),
        ]

    def __str__(self):
        return self.reference

    def clean(self):
        errors = {}

        # ---------------------------------------------------------
        # Attempt number
        # ---------------------------------------------------------
        if self.attempt_number < 1:
            errors["attempt_number"] = _(
                "Attempt number must be at least 1."
            )

        # ---------------------------------------------------------
        # Provider
        # ---------------------------------------------------------
        if not self.provider:
            errors["provider"] = _("Provider is required.")

        # ---------------------------------------------------------
        # Failure information
        # ---------------------------------------------------------
        if self.status == self.Status.FAILED:
            if not self.failure_reason:
                errors["failure_reason"] = _(
                    "Failure reason is required for a failed execution."
                )
        else:
            if self.failure_code:
                errors["failure_code"] = _(
                    "Failure code is only allowed for failed executions."
                )

            if self.failure_reason:
                errors["failure_reason"] = _(
                    "Failure reason is only allowed for failed executions."
                )

        # ---------------------------------------------------------
        # Pending executions must have reconciliation state
        # ---------------------------------------------------------
        if (
            self.status == self.Status.PENDING
            and self.reconciliation_state
            == self.ReconciliationState.NOT_REQUIRED
        ):
            errors["reconciliation_state"] = _(
                "A pending execution must have a reconciliation state."
            )

        if errors:
            raise ValidationError(errors)

        # ---------------------------------------------------------
        # Execution identity immutability
        # ---------------------------------------------------------
        if not self._state.adding and self.pk:
            previous = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "payment_id",
                    "attempt_number",
                    "route_type",
                    "provider",
                    "instrument_id",
                    "idempotency_key",
                )
                .first()
            )

            if previous:
                immutable_fields = (
                    "payment_id",
                    "attempt_number",
                    "route_type",
                    "provider",
                    "instrument_id",
                    "idempotency_key",
                )

                for field in immutable_fields:
                    current_value = getattr(self, field)
                    previous_value = previous[field]

                    if current_value != previous_value:
                        errors[field] = _(
                            "Execution identity cannot be changed after "
                            "the execution has been created."
                        )

        if errors:
            raise ValidationError(errors)

    # -------------------------------------------------------------
    # Status helpers
    # -------------------------------------------------------------

    @property
    def is_created(self):
        return self.status == self.Status.CREATED

    @property
    def is_processing(self):
        return self.status == self.Status.PROCESSING

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def requires_reconciliation(self):
        return (
            self.reconciliation_state
            == self.ReconciliationState.REQUIRED
        )