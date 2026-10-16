# payment/canonical/services/event_evidence.py

"""
PaymentExecutionEvent -> ReconciliationEvidence adapter.

This module is an evidence-boundary adapter.

Responsibilities:
    - validate a PaymentExecutionEvent
    - map supported event types to canonical payment statuses
    - construct ReconciliationEvidence

This adapter must NOT:
    - mutate the event
    - mutate the execution
    - mutate the payment
    - transition lifecycle state
    - perform reconciliation
    - create another event

Event classification
--------------------

PaymentExecutionEvent types fall into two categories:

    1. Outcome events
       Represent a financial outcome or a provider-reported
       in-flight outcome that can be evaluated by reconciliation.

           PROCESSING
           PROVIDER_PENDING
           PROVIDER_COMPLETED
           PROVIDER_FAILED
           PROVIDER_CANCELLED

    2. Timeline / acknowledgement markers
       Represent internal orchestration progress or a provider
       acknowledgement that does not by itself establish a
       financial outcome. These are useful for audit and debugging
       but are NOT reconciliation evidence.

           CREATED
           PROVIDER_ACCEPTED
           RECONCILIATION_REQUIRED
           RECONCILED

Marker events are excluded by omission from EVENT_TYPE_TO_STATUS.
to_evidence() raises ValidationError for them; the evidence
collector silently skips such events.
"""

from django.core.exceptions import ValidationError

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)


class PaymentExecutionEventEvidenceAdapter:
    """
    Convert a PaymentExecutionEvent into ReconciliationEvidence.
    """

    # Only events that establish a financial outcome or an
    # in-flight processing state are treated as reconciliation
    # evidence.
    #
    # CREATED, PROVIDER_ACCEPTED, and reconciliation meta-events
    # are timeline/acknowledgement markers, not evidence. They
    # are excluded by omission.
    EVENT_TYPE_TO_STATUS = {
        PaymentExecutionEvent.EventType.PROCESSING:
            PaymentExecution.Status.PROCESSING,

        PaymentExecutionEvent.EventType.PROVIDER_PENDING:
            PaymentExecution.Status.PENDING,

        PaymentExecutionEvent.EventType.PROVIDER_COMPLETED:
            PaymentExecution.Status.COMPLETED,

        PaymentExecutionEvent.EventType.PROVIDER_FAILED:
            PaymentExecution.Status.FAILED,

        PaymentExecutionEvent.EventType.PROVIDER_CANCELLED:
            PaymentExecution.Status.CANCELLED,
    }

    @classmethod
    def to_evidence(
        cls,
        event: PaymentExecutionEvent,
    ) -> ReconciliationEvidence:
        """
        Convert a persisted PaymentExecutionEvent into canonical
        ReconciliationEvidence.
        """

        cls._validate_event(event)

        execution = event.execution
        payment = execution.payment

        status = cls.EVENT_TYPE_TO_STATUS.get(event.event_type)

        if status is None:
            raise ValidationError(
                f"Event type '{event.event_type}' does not represent "
                "a reconciliation-relevant outcome."
            )

        return ReconciliationEvidence(
            source=event.source,
            status=status,
            amount=payment.amount,
            currency=payment.currency,
            reference=event.provider_reference or "",
            external_event_id=event.provider_event_id or "",
            metadata=event.payload or {},
        )

    @classmethod
    def _validate_event(
        cls,
        event: PaymentExecutionEvent,
    ) -> None:
        if not isinstance(event, PaymentExecutionEvent):
            raise ValidationError(
                "event must be a PaymentExecutionEvent."
            )

        if not event.execution_id:
            raise ValidationError(
                "PaymentExecutionEvent must have an execution."
            )

        if not event.execution.payment_id:
            raise ValidationError(
                "PaymentExecutionEvent execution must have a payment."
            )