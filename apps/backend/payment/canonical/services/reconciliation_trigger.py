"""
Canonical reconciliation trigger policy.

Architectural responsibility
----------------------------

This module determines whether a PaymentExecution is currently
eligible to enter the reconciliation flow.

It does NOT:

    - perform reconciliation
    - collect evidence
    - resolve Banking transactions
    - create PaymentExecutionEvents
    - mutate PaymentExecution
    - mutate Payment
    - call providers
    - perform retries

The actual reconciliation composition remains owned by:

    ReconciliationEntryPoint
"""

from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution


class ReconciliationTriggerPolicy:
    """
    Determine whether a PaymentExecution may enter reconciliation.
    """

    @classmethod
    def is_eligible(
        cls,
        *,
        execution: PaymentExecution,
    ) -> bool:
        """
        Return whether the execution is eligible for reconciliation.

        Reconciliation is eligible only when the execution has explicitly
        entered the REQUIRED reconciliation state.

        This keeps trigger eligibility separate from:

            - execution lifecycle
            - evidence collection
            - reconciliation rules
            - Payment synchronization
        """

        cls._validate_execution(execution)

        return (
            execution.reconciliation_state
            == PaymentExecution.ReconciliationState.REQUIRED
        )

    @staticmethod
    def _validate_execution(execution: PaymentExecution) -> None:
        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before evaluating "
                "reconciliation eligibility."
            )