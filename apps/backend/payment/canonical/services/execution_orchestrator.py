from django.core.exceptions import ValidationError
from django.db import transaction

from payment.canonical.models import (
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.execution_event import (
    PaymentExecutionEventService,
)
from payment.canonical.services.execution_lifecycle import (
    PaymentExecutionLifecycle,
)
from payment.canonical.services.execution_router import ExecutionRouter
from payment.canonical.services.synchronization import (
    PaymentExecutionSynchronization,
)
from payment.canonical.services.reconciliation_enqueue import (
    ReconciliationEnqueueAdapter,
)


class ExecutionOrchestrator:
    """
    Coordinates one PaymentExecution attempt.

    Responsibilities:
        - resolve the provider adapter
        - move the execution into PROCESSING
        - synchronize the Payment into PROCESSING
        - initiate the provider execution
        - record normalized provider events
        - mirror provider identity onto the execution
        - apply the corresponding execution lifecycle transition
        - synchronize the resulting execution state to the Payment
        - enqueue reconciliation when required

    This service does not:
        - implement provider-specific logic
        - mutate Payment directly
        - create retries
        - perform reconciliation
        - call get_status()
        - bypass PaymentExecutionLifecycle
        - bypass PaymentExecutionEventService
        - bypass PaymentExecutionSynchronization
        - call the reconciliation task directly
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
    def _event_type_for_status(cls, status):
        mapping = {
            PaymentExecution.Status.PROCESSING: (
                PaymentExecutionEvent.EventType.PROCESSING
            ),
            PaymentExecution.Status.PENDING: (
                PaymentExecutionEvent.EventType.PROVIDER_PENDING
            ),
            PaymentExecution.Status.COMPLETED: (
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            PaymentExecution.Status.FAILED: (
                PaymentExecutionEvent.EventType.PROVIDER_FAILED
            ),
            PaymentExecution.Status.CANCELLED: (
                PaymentExecutionEvent.EventType.PROVIDER_CANCELLED
            ),
        }

        try:
            return mapping[status]
        except KeyError:
            raise ValidationError(
                {
                    "status": (
                        "Provider returned unsupported execution "
                        f"status: {status}."
                    )
                }
            )

    @classmethod
    def _record_event(
        cls,
        *,
        execution,
        event_type,
        provider_reference="",
        payload=None,
    ):
        return PaymentExecutionEventService.record_event(
            execution=execution,
            event_type=event_type,
            source=PaymentExecutionEvent.Source.SYSTEM,
            provider_reference=provider_reference or "",
            payload=dict(payload or {}),
        )

    @classmethod
    def _apply_provider_identity(cls, execution, result):
        """
        Persist provider-supplied identity onto the execution.

        The event log remains the immutable history.

        This mirrors the current-state field on the execution so
        downstream systems (reconciliation, support tooling, webhook
        matching) do not have to traverse events to find it.

        Must be called after _record_event() and before
        _apply_lifecycle(), so that lifecycle's full_clean()/save()
        validates and persists provider_reference in a single write.
        """
        if not result.provider_reference:
            return

        if execution.provider_reference == result.provider_reference:
            return

        execution.provider_reference = result.provider_reference
        execution.save(update_fields=["provider_reference"])

    @classmethod
    def _apply_lifecycle(cls, execution, result):
        status = result.status

        if status == PaymentExecution.Status.PROCESSING:
            # The orchestrator already moved CREATED → PROCESSING
            # before calling the provider.
            return execution

        if status == PaymentExecution.Status.PENDING:
            return PaymentExecutionLifecycle.mark_pending(
                execution,
                reconciliation_required=result.reconciliation_required,
            )

        if status == PaymentExecution.Status.COMPLETED:
            return PaymentExecutionLifecycle.mark_completed(
                execution
            )

        if status == PaymentExecution.Status.FAILED:
            return PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_code=result.failure_code,
                failure_reason=result.failure_reason,
            )

        if status == PaymentExecution.Status.CANCELLED:
            return PaymentExecutionLifecycle.cancel(
                execution
            )

        raise ValidationError(
            {
                "status": (
                    "Provider returned unsupported execution "
                    f"status: {status}."
                )
            }
        )

    @classmethod
    @transaction.atomic
    def execute(cls, execution):
        """
        Execute one PaymentExecution attempt.

        Execution flow:

            CREATED
                ↓
            PROCESSING
                ↓
            Synchronize Payment
                ↓
            Record PROCESSING event
                ↓
            ProviderAdapter.initiate()
                ↓
            ProviderResult
                ↓
            Record provider event
                ↓
            Mirror provider identity onto execution
                ↓
            Execution lifecycle transition
                ↓
            Synchronize resulting execution state to Payment
                ↓
            Enqueue reconciliation when required
        """
        cls._validate_execution(execution)

        adapter = ExecutionRouter.resolve(execution)

        # The execution attempt has now begun.
        execution = PaymentExecutionLifecycle.mark_processing(
            execution
        )

        # Synchronize the overall Payment now that execution
        # has entered PROCESSING.
        #
        # This normally drives:
        #
        #     Payment.PENDING → Payment.PROCESSING
        #
        # It must happen before the provider result is applied so
        # that a provider COMPLETED result can subsequently drive:
        #
        #     Payment.PROCESSING → Payment.COMPLETED
        PaymentExecutionSynchronization.synchronize(
            execution
        )

        cls._record_event(
            execution=execution,
            event_type=PaymentExecutionEvent.EventType.PROCESSING,
        )

        result = adapter.initiate(execution)

        if result is None:
            raise ValidationError(
                {"provider": "Provider adapter returned no result."}
            )

        event_type = cls._event_type_for_status(
            result.status
        )

        cls._record_event(
            execution=execution,
            event_type=event_type,
            provider_reference=result.provider_reference,
            payload=result.metadata,
        )

        # Mirror provider identity onto the execution before the
        # lifecycle transition fires, so full_clean()/save() inside
        # mark_completed/mark_failed/mark_pending validates and
        # persists provider_reference together with the transition.
        cls._apply_provider_identity(
            execution,
            result,
        )

        # Apply the normalized provider result to the individual
        # PaymentExecution.
        execution = cls._apply_lifecycle(
            execution,
            result,
        )

        # Synchronize the resulting execution state back to the
        # overall Payment lifecycle before any reconciliation work
        # is enqueued.
        PaymentExecutionSynchronization.synchronize(
            execution
        )

        # Reconciliation is only eligible after the resulting
        # execution state has been synchronized.
        ReconciliationEnqueueAdapter.enqueue(
            execution=execution,
        )

        return execution