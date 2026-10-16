"""
Canonical reconciliation coordinator.

Architectural responsibility
----------------------------

This module coordinates reconciliation eligibility with the canonical
reconciliation entry point.

Flow:

    PaymentExecution
        ↓
    ReconciliationTriggerPolicy
        ↓
    eligible?
        │
        ├── False → structured non-eligible result
        │
        └── True
              ↓
    ReconciliationEntryPoint
              ↓
    reconciliation result

This module does NOT:

    - implement reconciliation rules
    - collect evidence
    - resolve Banking transactions
    - translate Banking evidence
    - mutate PaymentExecution directly
    - mutate Payment directly
    - create PaymentExecutionEvents
    - call providers
    - perform retries
"""


from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_entry import (
    ReconciliationEntryPoint,
)
from payment.canonical.services.reconciliation_trigger import (
    ReconciliationTriggerPolicy,
)


@dataclass(frozen=True)
class ReconciliationCoordinationResult:
    """
    Structured result returned by ReconciliationCoordinator.

    eligible:
        Whether the execution was eligible to enter reconciliation.

    execution:
        The PaymentExecution evaluated by the coordinator.

    reconciliation:
        The downstream reconciliation result when reconciliation was
        performed. None when the execution was not eligible.
    """

    eligible: bool
    execution: PaymentExecution
    reconciliation: Any = None

    @property
    def was_reconciled(self) -> bool:
        """
        Return whether reconciliation was actually performed.
        """

        return (
            self.eligible
            and self.reconciliation is not None
        )


class ReconciliationCoordinator:
    """
    Coordinate reconciliation eligibility and execution.

    The coordinator owns orchestration only.
    """

    @classmethod
    def reconcile(
        cls,
        *,
        execution: PaymentExecution,
    ) -> ReconciliationCoordinationResult:
        """
        Evaluate reconciliation eligibility and, when eligible,
        delegate to ReconciliationEntryPoint.
        """

        cls._validate_execution(execution)

        eligible = ReconciliationTriggerPolicy.is_eligible(
            execution=execution,
        )

        if not eligible:
            return ReconciliationCoordinationResult(
                eligible=False,
                execution=execution,
                reconciliation=None,
            )

        reconciliation = ReconciliationEntryPoint.reconcile(
            execution=execution,
        )

        return ReconciliationCoordinationResult(
            eligible=True,
            execution=execution,
            reconciliation=reconciliation,
        )

    @staticmethod
    def _validate_execution(execution) -> None:
        """
        Validate the coordinator boundary.
        """

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before "
                "reconciliation coordination."
            )