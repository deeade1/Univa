from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution
from dataclasses import dataclass, field
from payment.canonical.services.execution_lifecycle import (
    PaymentExecutionLifecycle,
)

@dataclass(frozen=True)
class ReconciliationEvidence:
    """
    Normalized evidence used to determine the financial outcome
    of a PaymentExecution.

    Evidence is descriptive only.

    This object does not:
        - mutate PaymentExecution
        - mutate Payment
        - call providers
        - create Banking transactions
        - create PaymentExecution events
        - perform retries
    """

    source: str
    status: str
    amount: Decimal
    currency: str
    reference: str = ""
    external_event_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValidationError(
                {"source": "Evidence source is required."}
            )

        if not isinstance(self.status, str) or not self.status.strip():
            raise ValidationError(
                {"status": "Evidence status is required."}
            )

        if not isinstance(self.amount, Decimal):
            raise ValidationError(
                {"amount": "Evidence amount must be a Decimal."}
            )

        if self.amount <= Decimal("0"):
            raise ValidationError(
                {"amount": "Evidence amount must be greater than zero."}
            )

        if not isinstance(self.currency, str):
            raise ValidationError(
                {"currency": "Evidence currency must be a string."}
            )

        currency = self.currency.strip().upper()

        if len(currency) != 3:
            raise ValidationError(
                {"currency": "Evidence currency must contain exactly 3 characters."}
            )

        
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "status", self.status.strip().lower())
        object.__setattr__(self, "currency", currency)

        if self.reference is None:
            object.__setattr__(self, "reference", "")

        if self.external_event_id is None:
            object.__setattr__(self, "external_event_id", "")

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class ReconciliationResult:
    """
    Immutable normalized reconciliation result.

    The result describes what the available evidence establishes.

    It does not change PaymentExecution or Payment state.
    """

    outcome: str
    reconciliation_state: str
    reason: str
    evidence_count: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_reconciled(self):
        return (
            self.reconciliation_state
            == PaymentExecution.ReconciliationState.RECONCILED
        )

    @property
    def requires_reconciliation(self):
        return (
            self.reconciliation_state
            == PaymentExecution.ReconciliationState.REQUIRED
        )

    @property
    def is_conflict(self):
        return self.outcome == ReconciliationService.Outcome.CONFLICT


class ReconciliationService:
    """
    Determines the normalized outcome of a PaymentExecution
    from independent financial evidence.

    This service is intentionally pure with respect to persistence.

    It does not:
        - mutate PaymentExecution
        - mutate Payment
        - create PaymentExecutionEvent records
        - call providers
        - perform Banking operations
        - create retries
        - perform state transitions

    State changes remain owned by:

        PaymentExecutionLifecycle
        PaymentExecutionSynchronization
    """

    class Source:
        PROVIDER = "provider"
        WEBHOOK = "webhook"
        BANKING = "banking"
        INTERNAL = "internal"

    class Outcome:
        COMPLETED = PaymentExecution.Status.COMPLETED
        FAILED = PaymentExecution.Status.FAILED
        CANCELLED = PaymentExecution.Status.CANCELLED
        PENDING = PaymentExecution.Status.PENDING
        CONFLICT = "conflict"

    _VALID_SOURCES = {
        Source.PROVIDER,
        Source.WEBHOOK,
        Source.BANKING,
        Source.INTERNAL,
    }

    _VALID_OUTCOMES = {
        Outcome.COMPLETED,
        Outcome.FAILED,
        Outcome.CANCELLED,
        Outcome.PENDING,
        Outcome.CONFLICT,
    }

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
    def _validate_evidence(cls, evidence):
        if not isinstance(evidence, ReconciliationEvidence):
            raise ValidationError(
                {
                    "evidence": (
                        "Evidence must be a ReconciliationEvidence instance."
                    )
                }
            )

        source = evidence.source.strip().lower()

        if source not in cls._VALID_SOURCES:
            raise ValidationError(
                {
                    "source": (
                        f"Unsupported reconciliation evidence source: "
                        f"{evidence.source}."
                    )
                }
            )

        if evidence.status not in {
            cls.Outcome.COMPLETED,
            cls.Outcome.FAILED,
            cls.Outcome.CANCELLED,
            cls.Outcome.PENDING,
        }:
            raise ValidationError(
                {
                    "status": (
                        f"Unsupported reconciliation evidence status: "
                        f"{evidence.status}."
                    )
                }
            )

    @classmethod
    def _validate_amount_and_currency(
        cls,
        execution,
        evidence,
    ):
        payment = execution.payment

        if evidence.amount != payment.amount:
            raise ValidationError(
                {
                    "amount": (
                        "Reconciliation evidence amount does not match "
                        "the Payment amount."
                    )
                }
            )

        if evidence.currency != payment.currency.upper():
            raise ValidationError(
                {
                    "currency": (
                        "Reconciliation evidence currency does not match "
                        "the Payment currency."
                    )
                }
            )

    @classmethod
    def _validate_all_evidence(cls, execution, evidence):
        if not evidence:
            raise ValidationError(
                {
                    "evidence": (
                        "At least one reconciliation evidence item is required."
                    )
                }
            )

        for item in evidence:
            cls._validate_evidence(item)
            cls._validate_amount_and_currency(
                execution,
                item,
            )

    @classmethod
    def _determine_outcome(cls, evidence):
        statuses = {item.status for item in evidence}

        if len(statuses) == 1:
            return next(iter(statuses))

        return cls.Outcome.CONFLICT

    @classmethod
    def _determine_reconciliation_state(cls, outcome):
        if outcome == cls.Outcome.CONFLICT:
            return PaymentExecution.ReconciliationState.REQUIRED

        if outcome == cls.Outcome.PENDING:
            return PaymentExecution.ReconciliationState.REQUIRED

        return PaymentExecution.ReconciliationState.RECONCILED

    @classmethod
    def _build_reason(cls, outcome, evidence):
        sources = ", ".join(
            sorted({item.source for item in evidence})
        )

        if outcome == cls.Outcome.CONFLICT:
            return (
                "Reconciliation evidence contains conflicting outcomes "
                f"from: {sources}."
            )

        if outcome == cls.Outcome.PENDING:
            return (
                "Available evidence does not establish a final financial "
                f"outcome. Evidence sources: {sources}."
            )

        return (
            f"Reconciliation established {outcome} from evidence sources: "
            f"{sources}."
        )

    @classmethod
    def reconcile(
        cls,
        execution,
        evidence,
    ):
        """
        Determine the normalized reconciliation result.

        No database state is changed.
        """

        cls._validate_execution(execution)
        cls._validate_all_evidence(
            execution,
            evidence,
        )

        outcome = cls._determine_outcome(evidence)

        reconciliation_state = cls._determine_reconciliation_state(
            outcome
        )

        reason = cls._build_reason(
            outcome,
            evidence,
        )

        metadata = {
            "sources": sorted(
                {item.source for item in evidence}
            ),
            "statuses": sorted(
                {item.status for item in evidence}
            ),
        }

        return ReconciliationResult(
            outcome=outcome,
            reconciliation_state=reconciliation_state,
            reason=reason,
            evidence_count=len(evidence),
            metadata=metadata,
        )
        
    @classmethod
    def apply_result(
        cls,
        execution,
        result,
    ):
        """
        Apply a reconciled result through PaymentExecutionLifecycle.

        Reconciliation determines the outcome.

        PaymentExecutionLifecycle owns the actual execution state
        transition.

        Unresolved outcomes are intentionally left unresolved:

            PENDING  → no terminal transition
            CONFLICT → no terminal transition

        This method does not:
            - mutate Payment directly
            - create retries
            - call providers
            - perform Banking operations
            - bypass PaymentExecutionLifecycle
        """

        cls._validate_execution(execution)

        if not isinstance(result, ReconciliationResult):
            raise ValidationError(
                {
                    "result": (
                        "A valid ReconciliationResult instance is required."
                    )
                }
            )

        if result.evidence_count < 1:
            raise ValidationError(
                {
                    "result": (
                        "Reconciliation result must contain evidence."
                    )
                }
            )

        if result.outcome == cls.Outcome.COMPLETED:
            if not result.is_reconciled:
                raise ValidationError(
                    {
                        "result": (
                            "A completed reconciliation outcome must "
                            "be reconciled."
                        )
                    }
                )

            return PaymentExecutionLifecycle.mark_completed(
                execution
            )

        if result.outcome == cls.Outcome.FAILED:
            if not result.is_reconciled:
                raise ValidationError(
                    {
                        "result": (
                            "A failed reconciliation outcome must "
                            "be reconciled."
                        )
                    }
                )

            return PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_reason=result.reason,
            )

        if result.outcome == cls.Outcome.CANCELLED:
            if not result.is_reconciled:
                raise ValidationError(
                    {
                        "result": (
                            "A cancelled reconciliation outcome must "
                            "be reconciled."
                        )
                    }
                )

            return PaymentExecutionLifecycle.cancel(
                execution
            )

        if result.outcome in {
            cls.Outcome.PENDING,
            cls.Outcome.CONFLICT,
        }:
            if not result.requires_reconciliation:
                raise ValidationError(
                    {
                        "result": (
                            "Pending or conflicting reconciliation "
                            "outcomes must require reconciliation."
                        )
                    }
                )

            # The execution remains unresolved.
            #
            # We deliberately do not mutate the execution here.
            # The execution should already be PENDING when an
            # unresolved reconciliation is being performed.
            return execution

        raise ValidationError(
            {
                "outcome": (
                    "Unsupported reconciliation outcome: "
                    f"{result.outcome}."
                )
            }
        )