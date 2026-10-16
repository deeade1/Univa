"""
Canonical reconciliation entry point.

Architectural responsibility
----------------------------

This module is the production entry point for reconciliation.

It decides which reconciliation composition should be used based on
ReconciliationEvidencePolicy.

Routing:

    UNIVA_INTERNAL
        ↓
    BankingReconciliationService
        ↓
    Banking evidence + persisted event evidence
        ↓
    ReconciliationOrchestrator

    CARD / WALLET / OTHER / BANK_TRANSFER
        ↓
    ReconciliationOrchestrator
        ↓
    Persisted event evidence

This module does NOT:

    - implement reconciliation rules
    - resolve Banking transactions directly
    - translate Banking transactions
    - collect provider evidence directly
    - mutate PaymentExecution
    - mutate Payment
    - create PaymentExecutionEvents
    - call providers
    - perform retries
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


class ReconciliationEntryPoint:
    """
    Canonical production entry point for PaymentExecution reconciliation.

    The entry point owns composition only.

    Evidence requirements and reconciliation rules remain owned by their
    respective services.
    """

    @classmethod
    def reconcile(cls, *, execution):
        """
        Reconcile a PaymentExecution using the appropriate evidence path.

        Banking-backed executions are routed through
        BankingReconciliationService.

        Non-Banking executions are routed through the generic
        ReconciliationOrchestrator.

        The selected downstream service owns all evidence collection and
        reconciliation behavior.
        """

        cls._validate_execution(execution)

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
    def _validate_execution(execution) -> None:
        """
        Validate the entry-point boundary.

        The execution must be persisted before reconciliation can begin.
        """

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before reconciliation."
            )