"""
Tests for the canonical reconciliation evidence policy.

Architectural contract
----------------------

The policy answers only:

    Does this PaymentExecution require Banking evidence?

Current policy:

    UNIVA_INTERNAL → True
    CARD           → False
    WALLET         → False
    OTHER          → False
    BANK_TRANSFER  → False

The policy does not:

    - resolve Banking transactions
    - translate Banking evidence
    - reconcile evidence
    - mutate PaymentExecution
    - mutate Payment
    - create Banking transactions
    - call providers
    - perform retries
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import PaymentExecution


class ReconciliationEvidencePolicyTests(TestCase):
    """
    Focused tests for Banking evidence requirement policy.
    """

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(
            email="policy-test@example.com",
            password="test-password",
        )

    def setUp(self):
        self.payment_counter = 0

    def _payment(self):
        from payment.canonical.models import Payment

        self.payment_counter += 1
        suffix = self.payment_counter

        return Payment.objects.create(
            reference=f"PAY-POLICY-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"policy-payment-{suffix:03d}",
            beneficiary=self.user,
            amount="100.00",
            currency="NGN",
            idempotency_key=f"policy-payment-idempotency-{suffix:03d}",
        )

    def _execution(self, *, route_type):
        from payment.canonical.models import PaymentExecution

        return PaymentExecution.objects.create(
            reference=f"EXEC-POLICY-{route_type}",
            payment=self._payment(),
            attempt_number=1,
            idempotency_key=f"policy-execution-{route_type}",
            route_type=route_type,
            provider="test_provider",
        )

    def _policy(self):
        from payment.canonical.services.reconciliation_policy import (
            ReconciliationEvidencePolicy,
        )

        return ReconciliationEvidencePolicy

    def test_univa_internal_requires_banking_evidence(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        self.assertTrue(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_card_does_not_require_banking_evidence(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        self.assertFalse(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_wallet_does_not_require_banking_evidence(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.WALLET,
        )

        self.assertFalse(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_other_does_not_require_banking_evidence(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.OTHER,
        )

        self.assertFalse(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_bank_transfer_does_not_automatically_require_banking_evidence(
        self,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
        )

        self.assertFalse(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._policy().requires_banking_evidence(
                execution=None,
            )

    def test_non_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._policy().requires_banking_evidence(
                execution=object(),
            )

    def test_unsaved_execution_is_rejected(self):
        payment = self._payment()

        execution = PaymentExecution(
            reference="EXEC-POLICY-UNSAVED",
            payment=payment,
            attempt_number=1,
            idempotency_key="policy-unsaved-execution",
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
            provider="test_provider",
        )

        with self.assertRaises(ValidationError):
            self._policy().requires_banking_evidence(
                execution=execution,
            )

    def test_policy_does_not_require_banking_reference(self):
        """
        The policy decides whether Banking evidence is expected.

        It must not inspect banking_transaction_reference itself.
        """

        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        self.assertTrue(
            self._policy().requires_banking_evidence(
                execution=execution,
            )
        )

    def test_policy_does_not_mutate_execution(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        before = {
            "route_type": execution.route_type,
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        result = self._policy().requires_banking_evidence(
            execution=execution,
        )

        execution.refresh_from_db()

        after = {
            "route_type": execution.route_type,
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        self.assertTrue(result)
        self.assertEqual(before, after)

    def test_policy_returns_boolean(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        result = self._policy().requires_banking_evidence(
            execution=execution,
        )

        self.assertIs(type(result), bool)

    def test_non_banking_routes_return_false_without_banking_reference(
        self,
    ):
        """
        Non-Banking routes must remain valid even when they have no
        Banking transaction reference.
        """

        for index, route_type in enumerate(
            (
                PaymentExecution.RouteType.CARD,
                PaymentExecution.RouteType.WALLET,
                PaymentExecution.RouteType.BANK_TRANSFER,
                PaymentExecution.RouteType.OTHER,
            ),
            start=1,
        ):
            with self.subTest(route_type=route_type):
                execution = self._execution(
                    route_type=route_type,
                )

                self.assertFalse(
                    self._policy().requires_banking_evidence(
                        execution=execution,
                    )
                )

    def test_policy_does_not_change_payment(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self._policy().requires_banking_evidence(
            execution=execution,
        )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertEqual(before, after)