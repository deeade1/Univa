"""
Immutable event history for PaymentExecution.

PaymentExecution stores current state.

PaymentExecutionEvent stores execution history.

Events are append-only and are never used as the authoritative
current-state representation.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .execution import PaymentExecution


class PaymentExecutionEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        PROCESSING = "processing", _("Processing")
        PROVIDER_ACCEPTED = (
            "provider_accepted",
            _("Provider Accepted"),
        )
        PROVIDER_PENDING = (
            "provider_pending",
            _("Provider Pending"),
        )
        PROVIDER_COMPLETED = (
            "provider_completed",
            _("Provider Completed"),
        )
        PROVIDER_FAILED = (
            "provider_failed",
            _("Provider Failed"),
        )
        PROVIDER_CANCELLED = (
            "provider_cancelled",
            _("Provider Cancelled"),
        )
        RECONCILIATION_REQUIRED = (
            "reconciliation_required",
            _("Reconciliation Required"),
        )
        RECONCILED = (
            "reconciled",
            _("Reconciled"),
        )

    class Source(models.TextChoices):
        SYSTEM = "system", _("System")
        PROVIDER = "provider", _("Provider")
        WEBHOOK = "webhook", _("Webhook")
        RECONCILIATION = "reconciliation", _("Reconciliation")
        BANKING = "banking", _("Banking")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    execution = models.ForeignKey(
        PaymentExecution,
        on_delete=models.PROTECT,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
    )

    source = models.CharField(
        max_length=30,
        choices=Source.choices,
    )

    provider_event_id = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    provider_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
    )

    occurred_at = models.DateTimeField()

    received_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        app_label = "payment_canonical"
        db_table = "payment_canonical_execution_event"
        ordering = (
            "occurred_at",
            "created_at",
        )
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "execution",
                    "provider_event_id",
                ],
                name="payment_exec_provider_event_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "execution",
                    "event_type",
                    "occurred_at",
                ],
                name="pay_exec_event_type_idx",
            ),
            models.Index(
                fields=[
                    "source",
                    "occurred_at",
                ],
                name="pay_exec_event_source_idx",
            ),
            models.Index(
                fields=["provider_reference"],
                name="pay_exec_prov_ref_idx",
            ),
        ]

    def __str__(self):
        return f"{self.execution.reference}: {self.event_type}"

    def clean(self):
        errors = {}

        if self.source in {
            self.Source.PROVIDER,
            self.Source.WEBHOOK,
        }:
            if not self.provider_event_id:
                errors["provider_event_id"] = _(
                    "Provider events must include a provider event ID."
                )

        if errors:
            raise ValidationError(errors)