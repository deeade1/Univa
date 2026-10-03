"""
Canonical payment webhook ingestion service.

Architectural boundary
----------------------

Provider webhook
    ↓
WebhookIngestionService
    ↓
PaymentExecutionEventService
    ↓
PaymentExecutionEvent
    ↓
Reconciliation (later)

This service does NOT:

    - mutate PaymentExecution
    - mutate Payment
    - perform reconciliation
    - retry executions
    - call providers
    - perform Banking operations

It converts an incoming provider webhook into canonical payment
execution evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from django.core.exceptions import ValidationError

from payment.canonical.models import (
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.execution_event import (
    PaymentExecutionEventService,
)
from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)


@dataclass(frozen=True)
class WebhookPayload:
    provider: str
    provider_event_id: str
    provider_reference: str
    status: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookIngestionResult:
    class Outcome:
        ACCEPTED = "accepted"
        DUPLICATE = "duplicate"

    outcome: str
    execution: PaymentExecution
    event: PaymentExecutionEvent
    evidence: ReconciliationEvidence

    @property
    def is_accepted(self) -> bool:
        return self.outcome == self.Outcome.ACCEPTED

    @property
    def is_duplicate(self) -> bool:
        return self.outcome == self.Outcome.DUPLICATE


class WebhookIngestionService:
    """
    Canonical service for ingesting provider webhooks.

    The execution is supplied by the caller. Resolving a webhook to
    an execution is intentionally outside this service for now.
    """

    STATUS_TO_EVENT_TYPE = {
        PaymentExecution.Status.PROCESSING:
            PaymentExecutionEvent.EventType.PROCESSING,

        PaymentExecution.Status.PENDING:
            PaymentExecutionEvent.EventType.PROVIDER_PENDING,

        PaymentExecution.Status.COMPLETED:
            PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,

        PaymentExecution.Status.FAILED:
            PaymentExecutionEvent.EventType.PROVIDER_FAILED,

        PaymentExecution.Status.CANCELLED:
            PaymentExecutionEvent.EventType.PROVIDER_CANCELLED,
    }

    VALID_STATUSES = frozenset(STATUS_TO_EVENT_TYPE)

    @classmethod
    def ingest(
        cls,
        *,
        execution: PaymentExecution,
        payload: WebhookPayload,
    ) -> WebhookIngestionResult:
        """
        Validate and ingest one provider webhook.

        Returns:

            ACCEPTED
                A new PaymentExecutionEvent was created.

            DUPLICATE
                The provider event was already ingested.

        Raises ValidationError for invalid or conflicting webhook data.
        """

        cls._validate_execution(execution)
        cls._validate_payload(execution, payload)

        event_type = cls.STATUS_TO_EVENT_TYPE[payload.status]

        existing_event = (
            PaymentExecutionEvent.objects
            .filter(
                execution=execution,
                provider_event_id=payload.provider_event_id,
            )
            .first()
        )

        if existing_event is not None:
            cls._validate_duplicate(
                existing_event=existing_event,
                payload=payload,
                event_type=event_type,
            )

            evidence = cls._build_evidence(payload)

            return WebhookIngestionResult(
                outcome=WebhookIngestionResult.Outcome.DUPLICATE,
                execution=execution,
                event=existing_event,
                evidence=evidence,
            )

        event = PaymentExecutionEventService.record_event(
            execution=execution,
            event_type=event_type,
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id=payload.provider_event_id,
            provider_reference=payload.provider_reference,
            payload=dict(payload.payload),
            occurred_at=payload.occurred_at,
        )

        evidence = cls._build_evidence(payload)

        return WebhookIngestionResult(
            outcome=WebhookIngestionResult.Outcome.ACCEPTED,
            execution=execution,
            event=event,
            evidence=evidence,
        )

    @classmethod
    def _validate_execution(
        cls,
        execution: PaymentExecution,
    ) -> None:
        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if not execution.payment_id:
            raise ValidationError(
                "PaymentExecution must belong to a Payment."
            )

        if not execution.provider:
            raise ValidationError(
                "PaymentExecution provider is required."
            )

    @classmethod
    def _validate_payload(
        cls,
        execution: PaymentExecution,
        payload: WebhookPayload,
    ) -> None:
        if not isinstance(payload, WebhookPayload):
            raise ValidationError(
                "payload must be a WebhookPayload instance."
            )

        provider = str(payload.provider or "").strip()

        if not provider:
            raise ValidationError(
                "Webhook provider is required."
            )

        if provider != execution.provider:
            raise ValidationError(
                "Webhook provider does not match execution provider."
            )

        provider_event_id = str(
            payload.provider_event_id or ""
        ).strip()

        if not provider_event_id:
            raise ValidationError(
                "Webhook provider_event_id is required."
            )

        provider_reference = str(
            payload.provider_reference or ""
        ).strip()

        if not provider_reference:
            raise ValidationError(
                "Webhook provider_reference is required."
            )

        if payload.status not in cls.VALID_STATUSES:
            raise ValidationError(
                f"Unsupported webhook status: {payload.status!r}."
            )

        if not isinstance(payload.amount, Decimal):
            raise ValidationError(
                "Webhook amount must be a Decimal."
            )

        if payload.amount <= Decimal("0"):
            raise ValidationError(
                "Webhook amount must be greater than zero."
            )

        if payload.amount != execution.payment.amount:
            raise ValidationError(
                "Webhook amount does not match payment amount."
            )

        currency = str(payload.currency or "").strip().upper()

        if len(currency) != 3:
            raise ValidationError(
                "Webhook currency must be a 3-character currency code."
            )

        if currency != execution.payment.currency.upper():
            raise ValidationError(
                "Webhook currency does not match payment currency."
            )

        if not isinstance(payload.occurred_at, datetime):
            raise ValidationError(
                "Webhook occurred_at must be a datetime."
            )

    @classmethod
    def _validate_duplicate(
        cls,
        *,
        existing_event: PaymentExecutionEvent,
        payload: WebhookPayload,
        event_type: str,
    ) -> None:
        """
        Ensure a repeated provider event really represents the same
        webhook.

        Same provider event ID with different event data is a conflict,
        not a harmless duplicate.
        """

        if existing_event.event_type != event_type:
            raise ValidationError(
                "Provider event ID already exists with a different "
                "event type."
            )

        if (
            existing_event.provider_reference
            != payload.provider_reference
        ):
            raise ValidationError(
                "Provider event ID already exists with a different "
                "provider reference."
            )

        if existing_event.payload != dict(payload.payload):
            raise ValidationError(
                "Provider event ID already exists with different "
                "payload data."
            )

    @classmethod
    def _build_evidence(
        cls,
        payload: WebhookPayload,
    ) -> ReconciliationEvidence:
        return ReconciliationEvidence(
            source="WEBHOOK",
            status=payload.status,
            amount=payload.amount,
            currency=payload.currency,
            reference=payload.provider_reference,
            external_event_id=payload.provider_event_id,
            metadata=dict(payload.payload),
        )


