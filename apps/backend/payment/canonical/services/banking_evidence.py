"""
Banking Transaction → ReconciliationEvidence adapter.

Architectural boundary
----------------------

Banking owns its financial transaction records.

Payment owns reconciliation semantics.

This adapter translates an existing Banking Transaction into
ReconciliationEvidence.

It is intentionally translation-only.

It must NOT:

    - create Banking transactions
    - mutate Banking transactions
    - mutate PaymentExecution
    - mutate Payment
    - reconcile evidence
    - execute lifecycle transitions
    - synchronize Payment state
    - call providers
    - create reconciliation records
"""

from django.core.exceptions import ValidationError

from banking.models.payments import Transaction

from payment.canonical.models import PaymentExecution

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)


class BankingTransactionEvidenceAdapter:
    """
    Translate a Banking Transaction into reconciliation evidence.

    The caller is responsible for resolving the relevant Banking
    transaction and PaymentExecution.
    """

    STATUS_TO_RECONCILIATION_STATUS = {
        Transaction.PENDING: PaymentExecution.Status.PENDING,
        Transaction.SUCCESS: PaymentExecution.Status.COMPLETED,
        Transaction.FAILED: PaymentExecution.Status.FAILED,
    }

    @classmethod
    def to_evidence(
        cls,
        *,
        transaction,
        execution,
    ) -> ReconciliationEvidence:
        cls._validate_transaction(transaction)
        cls._validate_execution(execution)

        canonical_status = cls.STATUS_TO_RECONCILIATION_STATUS.get(
            transaction.status
        )

        if canonical_status is None:
            raise ValidationError(
                f"Unsupported Banking transaction status: "
                f"{transaction.status!r}."
            )

        amount = transaction.amount

        if amount is None or amount <= 0:
            raise ValidationError(
                "Banking transaction amount must be greater than zero."
            )

        currency = execution.payment.currency.upper()

        metadata = {
            "transaction_type": transaction.type,
            "narration": transaction.narration,
            "fee": str(transaction.fee),
            "balance_after": (
                str(transaction.balance_after)
                if transaction.balance_after is not None
                else None
            ),
        }

        return ReconciliationEvidence(
            source="BANKING",
            status=canonical_status,
            amount=amount,
            currency=currency,
            reference=transaction.reference,
            external_event_id=transaction.provider_reference or "",
            metadata=metadata,
        )

    @staticmethod
    def _validate_transaction(transaction):
        if not isinstance(transaction, Transaction):
            raise ValidationError(
                "transaction must be a Banking Transaction."
            )

        if transaction._state.adding:
            raise ValidationError(
                "transaction must be persisted before evidence "
                "can be created."
            )

    @staticmethod
    def _validate_execution(execution):
        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution."
            )

        if execution._state.adding:
            raise ValidationError(
                "execution must be persisted before evidence "
                "can be created."
            )

        if not execution.payment_id:
            raise ValidationError(
                "execution must reference a persisted Payment."
            )
