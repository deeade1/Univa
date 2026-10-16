from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_trigger import (
    ReconciliationTriggerPolicy,
)
from payment.canonical.tasks.reconciliation import (
    reconcile_payment_execution_task,
)


class ReconciliationEnqueueAdapter:
    """
    Async enqueue boundary for PaymentExecution reconciliation.

    This adapter does not perform reconciliation.

    Responsibilities:
        - validate the execution
        - verify reconciliation eligibility
        - enqueue the canonical reconciliation task

    It must not:
        - collect evidence
        - resolve Banking transactions
        - call ReconciliationEntryPoint
        - mutate PaymentExecution
        - mutate Payment
        - invoke providers
        - implement retry behavior
    """

    @classmethod
    def enqueue(cls, *, execution):
        cls._validate_execution(execution)

        if not ReconciliationTriggerPolicy.is_eligible(
            execution=execution,
        ):
            return None

        return reconcile_payment_execution_task.delay(
            execution.pk,
        )

    @staticmethod
    def _validate_execution(execution):
        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "execution must be persisted before reconciliation can be enqueued."
            )