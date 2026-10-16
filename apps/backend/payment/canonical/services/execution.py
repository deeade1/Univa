from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from payment.canonical.models import Payment, PaymentExecution


class PaymentExecutionService:
    """
    Canonical service boundary for creating PaymentExecution records.

    This service creates and orchestrates execution attempts.

    It does not:
        - execute a provider
        - select a provider dynamically
        - change Payment lifecycle state
        - process webhooks
        - perform reconciliation
        - move Banking money
    """

    @classmethod
    def _validate_payment(cls, payment):
        if payment is None:
            raise ValidationError({"payment": "Payment is required."})

        if not isinstance(payment, Payment):
            raise ValidationError(
                {"payment": "A valid Payment instance is required."}
            )

        # Only PENDING and FAILED payments can accept a new execution.
        #
        # - PENDING: first attempt, or retry from a non-terminal state
        # - FAILED:  retry after a terminal failure
        #
        # COMPLETED, CANCELLED, REVERSED are terminal — no further attempts
        # PROCESSING: an attempt is already in flight
        allowed = {
            Payment.Status.PENDING,
            Payment.Status.FAILED,
        }

        if payment.status not in allowed:
            raise ValidationError({
                "payment": (
                    f"Cannot create an execution for a "
                    f"{payment.status} payment."
                )
            })    
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
    def _validate_attempt_number(cls, attempt_number):
        if attempt_number is None:
            raise ValidationError(
                {"attempt_number": "Attempt number is required."}
            )

        if attempt_number < 1:
            raise ValidationError(
                {
                    "attempt_number": (
                        "Attempt number must be greater than zero."
                    )
                }
            )

    @classmethod
    def _validate_instrument(cls, payment, instrument):
        if instrument is None:
            return

        if instrument.owner_id not in {
            payment.payer_id,
            payment.beneficiary_id,
        }:
            raise ValidationError(
                {
                    "instrument": (
                        "Payment instrument does not belong to "
                        "a party involved in this payment."
                    )
                }
            )

        if not instrument.can_be_used:
            raise ValidationError(
                {
                    "instrument": (
                        "Payment instrument is not available for use."
                    )
                }
            )

        if (
            payment.direction == Payment.Direction.RECEIVE
            and not instrument.can_fund
        ):
            raise ValidationError(
                {
                    "instrument": (
                        "Payment instrument cannot fund a "
                        "receive payment."
                    )
                }
            )

        if (
            payment.direction == Payment.Direction.DISBURSE
            and not instrument.can_receive
        ):
            raise ValidationError(
                {
                    "instrument": (
                        "Payment instrument cannot receive a "
                        "disbursement."
                    )
                }
            )

    @classmethod
    def _validate_idempotent_match(
        cls,
        execution,
        *,
        payment,
        route_type,
        provider,
        instrument,
    ):
        if (
            execution.payment_id == payment.id
            and execution.route_type == route_type
            and execution.provider == provider
            and execution.instrument_id
            == getattr(instrument, "id", None)
        ):
            return execution

        raise ValidationError(
            {
                "idempotency_key": (
                    "An execution already exists with this "
                    "idempotency key but different execution "
                    "parameters."
                )
            }
        )

    @classmethod
    def _generate_reference(cls):
        import uuid

        return f"PEXEC-{uuid.uuid4().hex[:12].upper()}"

    @classmethod
    def _next_attempt_number(cls, payment):
        last_execution = (
            PaymentExecution.objects
            .filter(payment=payment)
            .order_by("-attempt_number")
            .first()
        )

        if last_execution is None:
            return 1

        return last_execution.attempt_number + 1

    @classmethod
    @transaction.atomic
    def create_execution(
        cls,
        *,
        payment,
        route_type,
        provider,
        idempotency_key,
        attempt_number=None,
        instrument=None,
        metadata=None,
    ):
        cls._validate_payment(payment)

        cls._validate_required(
            route_type=route_type,
            provider=provider,
            idempotency_key=idempotency_key,
        )

        if attempt_number is None:
            attempt_number = cls._next_attempt_number(payment)

        cls._validate_attempt_number(attempt_number)

        cls._validate_instrument(
            payment,
            instrument,
        )

        if metadata is None:
            metadata = {}

        existing = (
            PaymentExecution.objects
            .filter(
                idempotency_key=idempotency_key,
            )
            .first()
        )

        if existing is not None:
            return cls._validate_idempotent_match(
                existing,
                payment=payment,
                route_type=route_type,
                provider=provider,
                instrument=instrument,
            )

        execution = PaymentExecution(
            reference=cls._generate_reference(),
            payment=payment,
            attempt_number=attempt_number,
            idempotency_key=idempotency_key,
            route_type=route_type,
            provider=provider,
            instrument=instrument,
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
            metadata=metadata,
        )

        execution.full_clean()

        try:
            execution.save()
        except IntegrityError:
            existing = PaymentExecution.objects.get(
                idempotency_key=idempotency_key,
            )

            return cls._validate_idempotent_match(
                existing,
                payment=payment,
                route_type=route_type,
                provider=provider,
                instrument=instrument,
            )

        return execution