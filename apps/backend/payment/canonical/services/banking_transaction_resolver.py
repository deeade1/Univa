"""
Resolve a Banking Transaction for a canonical PaymentExecution.

Architectural boundary
----------------------

This service establishes the deterministic identity bridge between:

    PaymentExecution
        ↓
    Banking.Transaction

The canonical identity is:

    PaymentExecution.banking_transaction_reference
        →
    Transaction.reference

This resolver is intentionally translation-only.

It MUST NOT:

    - create Banking transactions
    - mutate PaymentExecution
    - mutate Banking.Transaction
    - reconcile evidence
    - change execution status
    - change Payment status
    - call providers
    - infer identity from amount/status/account/narration
    - use provider_reference as a fallback identity
"""

from django.core.exceptions import ValidationError

from banking.models.payments import Transaction
from payment.canonical.models import PaymentExecution


class BankingTransactionResolver:
    """
    Resolve the existing Banking Transaction identified by a
    PaymentExecution.banking_transaction_reference.
    """

    @classmethod
    def resolve(cls, *, execution: PaymentExecution) -> Transaction:
        cls._validate_execution(execution)

        banking_reference = execution.banking_transaction_reference

        if not banking_reference:
            raise ValidationError(
                "PaymentExecution.banking_transaction_reference is required."
            )

        try:
            return Transaction.objects.get(
                reference=banking_reference,
            )
        except Transaction.DoesNotExist as exc:
            raise ValidationError(
                "No Banking transaction exists for the supplied "
                "banking transaction reference."
            ) from exc

    @staticmethod
    def _validate_execution(execution: PaymentExecution) -> None:
        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before resolution."
            )
