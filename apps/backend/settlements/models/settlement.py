"""
Canonical Settlement model for Univa.

A Settlement represents the fulfillment obligation of a financial
entitlement.

Settlement is intentionally independent from:

    - Commission
    - Earning
    - Investor Distribution
    - Payment
    - Banking
    - external payment providers

Entitlements determine what is owed.

Settlement determines how that obligation is fulfilled.

Payment and Banking are separate layers.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Settlement(models.Model):
    """
    Canonical fulfillment record for a financial entitlement.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ELIGIBLE = "eligible", _("Eligible")
        PROCESSING = "processing", _("Processing")
        SETTLED = "settled", _("Settled")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        REVERSED = "reversed", _("Reversed")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="settlements",
    )

    source_type = models.CharField(
        max_length=50,
    )

    source_id = models.CharField(
        max_length=100,
    )

    source_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    idempotency_key = models.CharField(
        max_length=150,
        unique=True,
    )

    failure_code = models.CharField(
        max_length=50,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    eligible_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    processing_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    settled_at = models.DateTimeField(
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

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
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
        verbose_name = _("Settlement")
        verbose_name_plural = _("Settlements")
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["beneficiary", "status"],
                name="settlement_ben_status_idx",
            ),
            models.Index(
                fields=["source_type", "source_id"],
                name="settlement_source_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="settlement_status_created_idx",
            ),
            models.Index(
                fields=["beneficiary", "created_at"],
                name="settlement_ben_created_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="settlement_amount_positive",
            ),
        ]

    def __str__(self):
        return self.reference

    def clean(self):
        """
        Validate Settlement invariants.

        Lifecycle transitions themselves belong to the future
        SettlementLifecycle service. This method validates the
        consistency of an individual Settlement record.
        """

        errors = {}

        if self.amount is not None and self.amount <= 0:
            errors["amount"] = _(
                "Settlement amount must be greater than zero."
            )

        if not self.reference:
            errors["reference"] = _(
                "Settlement reference is required."
            )

        if not self.source_type:
            errors["source_type"] = _(
                "Settlement source type is required."
            )

        if not self.source_id:
            errors["source_id"] = _(
                "Settlement source ID is required."
            )

        if not self.idempotency_key:
            errors["idempotency_key"] = _(
                "Settlement idempotency key is required."
            )

        if self.currency:
            self.currency = self.currency.upper()

            if len(self.currency) != 3:
                errors["currency"] = _(
                    "Currency must be a three-letter code."
                )

        timestamp_requirements = {
            self.Status.ELIGIBLE: (
                "eligible_at",
                self.eligible_at,
            ),
            self.Status.PROCESSING: (
                "processing_at",
                self.processing_at,
            ),
            self.Status.SETTLED: (
                "settled_at",
                self.settled_at,
            ),
            self.Status.FAILED: (
                "failed_at",
                self.failed_at,
            ),
            self.Status.CANCELLED: (
                "cancelled_at",
                self.cancelled_at,
            ),
            self.Status.REVERSED: (
                "reversed_at",
                self.reversed_at,
            ),
        }

        requirement = timestamp_requirements.get(self.status)

        if requirement:
            field_name, value = requirement

            if value is None:
                errors[field_name] = _(
                    "%(field)s is required for the %(status)s status."
                ) % {
                    "field": field_name,
                    "status": self.status,
                }

        if self.status == self.Status.FAILED:
            if not self.failure_reason:
                errors["failure_reason"] = _(
                    "Failure reason is required for a failed settlement."
                )

        if self.status != self.Status.FAILED:
            if self.failure_code or self.failure_reason:
                errors["failure_reason"] = _(
                    "Failure information may only be set for "
                    "a failed settlement."
                )

        self._validate_financial_field_immutability(errors)

        if errors:
            raise ValidationError(errors)

    def _validate_financial_field_immutability(self, errors):
        """
        Prevent modification of core financial identity once
        settlement processing has begun.

        QuerySet.update() can bypass model validation; lifecycle
        operations will therefore remain responsible for enforcing
        the broader transition contract.
        """

        if not self.pk:
            return

        if self.status in {
            self.Status.PROCESSING,
            self.Status.SETTLED,
            self.Status.FAILED,
            self.Status.CANCELLED,
            self.Status.REVERSED,
        }:
            previous = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "beneficiary_id",
                    "amount",
                    "currency",
                    "source_type",
                    "source_id",
                    "source_reference",
                )
                .first()
            )

            if previous is None:
                return

            immutable_fields = (
                "beneficiary_id",
                "amount",
                "currency",
                "source_type",
                "source_id",
                "source_reference",
            )

            for field_name in immutable_fields:
                current_value = getattr(self, field_name)

                if current_value != previous[field_name]:
                    errors[field_name] = _(
                        "%(field)s cannot be changed after "
                        "settlement processing has begun."
                    ) % {
                        "field": field_name,
                    }

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_eligible(self):
        return self.status == self.Status.ELIGIBLE

    @property
    def is_processing(self):
        return self.status == self.Status.PROCESSING

    @property
    def is_settled(self):
        return self.status == self.Status.SETTLED

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_reversed(self):
        return self.status == self.Status.REVERSED