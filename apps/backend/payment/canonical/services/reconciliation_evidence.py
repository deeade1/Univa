"""
Reconciliation evidence collector.

Architectural boundary
----------------------

The collector combines reconciliation evidence from sources that
have already been resolved and translated into ReconciliationEvidence.

Current persisted evidence source:

    PaymentExecutionEvent
        ↓
    PaymentExecutionEventEvidenceAdapter
        ↓
    ReconciliationEvidence

Additional evidence sources may be supplied by their own adapters.

For example:

    Banking Transaction
        ↓
    BankingTransactionEvidenceAdapter
        ↓
    ReconciliationEvidence
        ↓
    ReconciliationEvidenceCollector

The collector is intentionally source-neutral.

It must NOT:

    - resolve Banking transactions
    - query Banking
    - call providers
    - reconcile evidence
    - mutate PaymentExecution
    - mutate Payment
    - create PaymentExecutionEvent records
    - perform lifecycle transitions
"""


from collections.abc import Iterable

from django.core.exceptions import ValidationError

from payment.canonical.models import (
    PaymentExecution,
    PaymentExecutionEvent,
)

from payment.canonical.services.event_evidence import (
    PaymentExecutionEventEvidenceAdapter,
)

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)


class ReconciliationEvidenceCollector:
    """
    Collect reconciliation evidence for a PaymentExecution.

    Persisted PaymentExecutionEvent records are converted into
    ReconciliationEvidence.

    Additional already-resolved evidence may be supplied by callers.

    The collector does not know where additional evidence came from.
    """

    @classmethod
    def collect(
        cls,
        *,
        execution: PaymentExecution,
        additional_evidence: (
            Iterable[ReconciliationEvidence] | None
        ) = None,
    ) -> list[ReconciliationEvidence]:
        """
        Collect all available reconciliation evidence.

        Parameters
        ----------
        execution:
            Persisted PaymentExecution whose evidence is being collected.

        additional_evidence:
            Optional iterable of already-resolved ReconciliationEvidence
            instances supplied by external adapters.

        Returns
        -------
        list[ReconciliationEvidence]
            Combined persisted-event evidence and additional evidence.

        Notes
        -----
        This method only collects evidence.

        It does not reconcile evidence, mutate execution/payment state,
        create events, resolve external records, or call providers.
        """

        cls._validate_execution(execution)

        evidence = cls._collect_event_evidence(
            execution=execution,
        )

        evidence.extend(
            cls._validate_additional_evidence(
                additional_evidence,
            )
        )

        return evidence

    @classmethod
    def _collect_event_evidence(
        cls,
        *,
        execution: PaymentExecution,
    ) -> list[ReconciliationEvidence]:
        """
        Collect evidence from persisted PaymentExecutionEvent records.
        """

        events = (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .order_by("occurred_at", "created_at")
        )

        evidence = []

        for event in events:
            try:
                item = (
                    PaymentExecutionEventEvidenceAdapter.to_evidence(
                        event,
                    )
                )
            except ValidationError:
                continue

            evidence.append(item)

        return evidence

    @staticmethod
    def _validate_additional_evidence(
        additional_evidence,
    ) -> list[ReconciliationEvidence]:
        """
        Validate and normalize caller-supplied evidence.

        The collector accepts any iterable, but every item must already
        be a ReconciliationEvidence instance.

        No source-specific logic belongs here.
        """

        if additional_evidence is None:
            return []

        if isinstance(
            additional_evidence,
            (str, bytes),
        ):
            raise ValidationError(
                "additional_evidence must be an iterable of "
                "ReconciliationEvidence instances."
            )

        try:
            items = list(additional_evidence)
        except TypeError as exc:
            raise ValidationError(
                "additional_evidence must be an iterable of "
                "ReconciliationEvidence instances."
            ) from exc

        for item in items:
            if not isinstance(
                item,
                ReconciliationEvidence,
            ):
                raise ValidationError(
                    "additional_evidence must contain only "
                    "ReconciliationEvidence instances."
                )

        return items

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
                "execution must be persisted before evidence "
                "can be collected."
            )
