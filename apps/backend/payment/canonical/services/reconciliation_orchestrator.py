from dataclasses import dataclass
from typing import Tuple

from django.core.exceptions import ValidationError

from payment.canonical.models import Payment, PaymentExecution

from payment.canonical.services.synchronization import (
    PaymentExecutionSynchronization,
)

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
    ReconciliationResult,
    ReconciliationService,
)

from payment.canonical.services.reconciliation_evidence import (
    ReconciliationEvidenceCollector,
)


class ReconciliationOrchestrator:
    """
    Orchestrate reconciliation for a PaymentExecution.

    Architectural boundary
    ----------------------

    The orchestrator owns ordering only:

        PaymentExecution
            ↓
        ReconciliationEvidenceCollector
            ↓
        ReconciliationService.reconcile()
            ↓
        ReconciliationService.apply_result()
            ↓
        PaymentExecutionSynchronization
            ↓
        Payment

    It does NOT:

        - implement reconciliation rules
        - resolve Banking transactions
        - call providers
        - create webhook events
        - implement lifecycle rules
        - mutate Payment directly
        - implement retries
        - persist reconciliation records
    """

    @classmethod
    def reconcile(
        cls,
        *,
        execution: PaymentExecution,
        additional_evidence=None,
    ) -> "ReconciliationOrchestrationResult":
        """
        Reconcile a PaymentExecution and synchronize its Payment.

        additional_evidence contains already-resolved and already-
        translated ReconciliationEvidence supplied by external
        adapters.
        """

        cls._validate_execution(execution)

        evidence = ReconciliationEvidenceCollector.collect(
            execution=execution,
            additional_evidence=additional_evidence,
        )

        reconciliation = ReconciliationService.reconcile(
            execution=execution,
            evidence=evidence,
        )

        execution = ReconciliationService.apply_result(
            execution,
            reconciliation,
        )

        # PaymentExecutionSynchronization.synchronize() returns the
        # synchronized Payment, NOT the PaymentExecution. Do not
        # rebind `execution` to its return value.
        PaymentExecutionSynchronization.synchronize(
            execution,
        )

        execution.refresh_from_db()

        payment = execution.payment
        payment.refresh_from_db()

        return ReconciliationOrchestrationResult(
            execution=execution,
            payment=payment,
            evidence=tuple(evidence),
            reconciliation=reconciliation,
        )

    @staticmethod
    def _validate_execution(
        execution: PaymentExecution,
    ) -> None:
        """
        Validate that execution is a persisted PaymentExecution.
        """

        if not isinstance(
            execution,
            PaymentExecution,
        ):
            raise ValidationError(
                "execution must be a PaymentExecution."
            )

        if execution._state.adding:
            raise ValidationError(
                "execution must be persisted before reconciliation "
                "can be orchestrated."
            )


@dataclass(frozen=True)
class ReconciliationOrchestrationResult:
    """
    Result returned by ReconciliationOrchestrator.reconcile().
    """

    execution: PaymentExecution
    payment: Payment
    evidence: Tuple[ReconciliationEvidence, ...]
    reconciliation: ReconciliationResult

    def __post_init__(self):
        object.__setattr__(
            self,
            "evidence",
            tuple(self.evidence),
        )

    @property
    def is_reconciled(self) -> bool:
        return self.reconciliation.is_reconciled

    @property
    def requires_reconciliation(self) -> bool:
        return self.reconciliation.requires_reconciliation

    @property
    def is_conflict(self) -> bool:
        return self.reconciliation.is_conflict