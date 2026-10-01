from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from payment.canonical.models import (
    PaymentExecution,
    PaymentExecutionEvent,
)


class PaymentExecutionEventService:
    """
    Canonical service boundary for recording
    PaymentExecutionEvent records.

    Events are historical facts about an execution.

    This service does not:
        - change PaymentExecution status
        - change Payment status
        - execute providers
        - perform reconciliation
        - interpret provider outcomes
    """

    @classmethod
    def _validate_execution(cls, execution):
        if execution is None:
            raise ValidationError(
                {"execution": "Payment execution is required."}
            )

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                {
                    "execution": (
                        "A valid PaymentExecution instance is required."
                    )
                }
            )

    @classmethod
    def _validate_required(cls, **values):
        errors = {}

        for field, value in values.items():
            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                errors[field] = f"{field} is required."

        if errors:
            raise ValidationError(errors)

    @classmethod
    def _validate_provider_event_id(
        cls,
        *,
        source,
        provider_event_id,
    ):
        provider_sources = {
            PaymentExecutionEvent.Source.PROVIDER,
            PaymentExecutionEvent.Source.WEBHOOK,
        }

        if (
            source in provider_sources
            and not provider_event_id
        ):
            raise ValidationError(
                {
                    "provider_event_id": (
                        "Provider event ID is required for "
                        "provider and webhook events."
                    )
                }
            )

    @classmethod
    def _validate_idempotent_match(
        cls,
        event,
        *,
        execution,
        event_type,
        source,
        provider_event_id,
        provider_reference,
    ):
        if (
            event.execution_id == execution.id
            and event.event_type == event_type
            and event.source == source
            and event.provider_event_id
            == provider_event_id
            and event.provider_reference
            == (provider_reference or "")
        ):
            return event

        raise ValidationError(
            {
                "provider_event_id": (
                    "An event already exists with this "
                    "provider event ID but with different "
                    "event parameters."
                )
            }
        )

    @classmethod
    @transaction.atomic
    def record_event(
        cls,
        *,
        execution,
        event_type,
        source,
        provider_event_id=None,
        provider_reference="",
        payload=None,
        occurred_at=None,
        received_at=None,
    ):
        cls._validate_execution(execution)

        cls._validate_required(
            event_type=event_type,
            source=source,
        )

        cls._validate_provider_event_id(
            source=source,
            provider_event_id=provider_event_id,
        )

        if payload is None:
            payload = {}

        if occurred_at is None:
            occurred_at = timezone.now()

        if received_at is None:
            received_at = timezone.now()

        existing = None

        if provider_event_id:
            existing = (
                PaymentExecutionEvent.objects
                .filter(
                    execution=execution,
                    provider_event_id=provider_event_id,
                )
                .first()
            )

        if existing is not None:
            return cls._validate_idempotent_match(
                existing,
                execution=execution,
                event_type=event_type,
                source=source,
                provider_event_id=provider_event_id,
                provider_reference=provider_reference,
            )

        event = PaymentExecutionEvent(
            execution=execution,
            event_type=event_type,
            source=source,
            provider_event_id=provider_event_id,
            provider_reference=provider_reference or "",
            payload=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )

        event.full_clean()

        try:
            event.save()
        except IntegrityError:
            if not provider_event_id:
                raise

            existing = PaymentExecutionEvent.objects.get(
                execution=execution,
                provider_event_id=provider_event_id,
            )

            return cls._validate_idempotent_match(
                existing,
                execution=execution,
                event_type=event_type,
                source=source,
                provider_event_id=provider_event_id,
                provider_reference=provider_reference,
            )

        return event