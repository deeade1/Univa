"""
Banking → Reconciliation orchestration boundary.

Architectural responsibility
----------------------------

This service composes the Banking-specific reconciliation steps:

    PaymentExecution
        ↓
    BankingTransactionResolver
        ↓
    BankingTransactionEvidenceAdapter
        ↓
    ReconciliationOrchestrator

This service does NOT:

    - implement reconciliation rules
    - resolve Banking identity itself
    - translate Banking fields itself
    - mutate PaymentExecution
    - mutate Banking.Transaction
    - create Banking transactions
    - mutate Payment
    - call providers
    - perform retries
"""

from payment.canonical.services.banking_transaction_resolver import (
    BankingTransactionResolver,
)
from payment.canonical.services.banking_evidence import (
    BankingTransactionEvidenceAdapter,
)
from payment.canonical.services.reconciliation_orchestrator import (
    ReconciliationOrchestrator,
)


class BankingReconciliationService:
    """
    Compose Banking transaction resolution and evidence translation
    with the generic reconciliation orchestration flow.
    """

    @classmethod
    def reconcile(cls, *, execution):
        """
        Resolve the Banking transaction, translate it into canonical
        reconciliation evidence, and pass that evidence into the
        generic reconciliation orchestrator.
        """

        transaction = BankingTransactionResolver.resolve(
            execution=execution,
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=execution,
        )

        return ReconciliationOrchestrator.reconcile(
            execution=execution,
            additional_evidence=(evidence,),
        )
