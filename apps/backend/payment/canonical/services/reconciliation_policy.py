"""
Reconciliation evidence policy for canonical PaymentExecution.

Architectural responsibility
----------------------------

This module determines whether Banking is an expected source of
reconciliation evidence for a PaymentExecution.

It does NOT:

    - resolve Banking transactions
    - translate Banking transactions
    - collect evidence
    - reconcile evidence
    - mutate PaymentExecution
    - mutate Payment
    - create Banking transactions
    - call providers
    - perform retries

The policy answers one question:

    Does this PaymentExecution require Banking evidence?
"""

from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution


class ReconciliationEvidencePolicy:
    """
    Determine which reconciliation evidence sources are required for
    a canonical PaymentExecution.
    """

    @classmethod
    def requires_banking_evidence(
        cls,
        *,
        execution: PaymentExecution,
    ) -> bool:
        """
        Return whether Banking is an expected reconciliation evidence
        source for the supplied PaymentExecution.

        Current policy:

            UNIVA_INTERNAL → Banking required
            CARD           → Banking not required
            WALLET         → Banking not required
            OTHER          → Banking not required

        BANK_TRANSFER is intentionally not treated as automatically
        Banking-backed because the route can be executed either through
        Univa Banking or an external banking/payment provider.
        """

        cls._validate_execution(execution)

        return (
            execution.route_type
            == PaymentExecution.RouteType.UNIVA_INTERNAL
        )

    @staticmethod
    def _validate_execution(execution: PaymentExecution) -> None:
        """
        Validate that the policy receives a persisted PaymentExecution.
        """

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                "execution must be a PaymentExecution instance."
            )

        if execution._state.adding:
            raise ValidationError(
                "PaymentExecution must be persisted before evaluating "
                "reconciliation evidence policy."
            )
