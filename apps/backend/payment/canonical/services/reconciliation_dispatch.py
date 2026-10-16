"""
Canonical reconciliation dispatch boundary.

Architectural responsibility
----------------------------

This module selects the appropriate reconciliation path for a
PaymentExecution.

It does NOT:

    - implement reconciliation rules
    - collect evidence
    - resolve Banking transactions
    - translate evidence
    - call providers
    - process webhooks
    - perform retries
    - mutate PaymentExecution directly
    - mutate Payment directly
    - execute lifecycle transitions
    - contain Celery behavior

The dispatch flow is intentionally small:

    validate
        ↓
    reconciliation state
        ↓
    evidence policy
        ↓
    service selection
        ↓
    delegation
"""

from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution
from payment.canonical.services.banking_reconciliation import (
    BankingReconciliationService,
)
from payment.canonical.services.reconciliation_orchestrator import (
    ReconciliationOrchestrator,
)
from payment.canonical.services.reconciliation_policy import (
    ReconciliationEvidencePolicy,
)


class ReconciliationDispatcher:
    """
    Select and invoke the canonical reconciliation service for an
    eligible PaymentExecution.
    """

    @classmethod
    def dispatch(
        cls,
        *,
        execution: PaymentExecution,
    ):
        """
        Dispatch reconciliation for an execution that requires it.

        Banking-backed executions are routed through
        BankingReconciliationService.

        Other execution routes are routed through the generic
        ReconciliationOrchestrator.

        The delegated result is returned unchanged.
        """

        cls._validate_execution(execution)

        if (
            execution.reconciliation_state
            != PaymentExecution.ReconciliationState.REQUIRED
        ):
            raise ValidationError(
                "PaymentExecution must require reconciliation before "
                "dispatching reconciliation."
            )

        if ReconciliationEvidencePolicy.requires_banking_evidence(
            execution=execution,
        ):
            return BankingReconciliationService.reconcile(
                execution=execution,
            )

        return ReconciliationOrchestrator.reconcile(
            execution=execution,
        )

    @staticmethod
    def _validate_execution(
        execution: PaymentExecution,
    ) -> None:
        """
        Validate the dispatch input.

        Dispatch operates only on persisted PaymentExecution records.
        """

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before "
                "dispatching reconciliation."
            )