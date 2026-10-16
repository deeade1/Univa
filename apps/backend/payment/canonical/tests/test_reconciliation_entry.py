"""
Tests for the canonical reconciliation entry point.

Architectural contract
----------------------

The entry point is a composition boundary.

It must:

    - validate the PaymentExecution
    - consult ReconciliationEvidencePolicy
    - route Banking-backed executions to
      BankingReconciliationService
    - route non-Banking executions to
      ReconciliationOrchestrator
    - return the downstream reconciliation result unchanged

It must NOT:

    - implement reconciliation rules
    - resolve Banking transactions directly
    - collect evidence directly
    - mutate PaymentExecution
    - mutate Payment
    - create events
    - call providers
    - perform retries
"""

from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_entry import (
    ReconciliationEntryPoint,
)


class ReconciliationEntryPointTests(TestCase):
    """
    Focused tests for the canonical reconciliation entry point.
    """

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(
            email="reconciliation-entry@example.com",
            password="test-password",
        )

    def setUp(self):
        self.payment_counter = 0
        self.execution_counter = 0

    def _payment(self):
        from payment.canonical.models import Payment

        self.payment_counter += 1
        suffix = self.payment_counter

        return Payment.objects.create(
            reference=f"PAY-ENTRY-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"entry-payment-{suffix:03d}",
            beneficiary=self.user,
            amount="100.00",
            currency="NGN",
            idempotency_key=f"entry-payment-idempotency-{suffix:03d}",
        )

    def _execution(self, *, route_type):
        self.execution_counter += 1
        suffix = self.execution_counter

        return PaymentExecution.objects.create(
            reference=f"EXEC-ENTRY-{suffix:03d}",
            payment=self._payment(),
            attempt_number=1,
            idempotency_key=f"entry-execution-idempotency-{suffix:03d}",
            route_type=route_type,
            provider="test_provider",
        )

    def test_univa_internal_routes_to_banking_reconciliation(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
            return_value=expected_result,
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        banking_reconcile.assert_called_once_with(
            execution=execution,
        )

        generic_reconcile.assert_not_called()

    def test_card_routes_to_generic_reconciliation(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        banking_reconcile.assert_not_called()

    def test_wallet_routes_to_generic_reconciliation(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.WALLET,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        banking_reconcile.assert_not_called()

    def test_other_routes_to_generic_reconciliation(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.OTHER,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        banking_reconcile.assert_not_called()

    def test_bank_transfer_routes_to_generic_reconciliation(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        banking_reconcile.assert_not_called()

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEntryPoint.reconcile(
                execution=None,
            )

    def test_non_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEntryPoint.reconcile(
                execution=object(),
            )

    def test_unsaved_execution_is_rejected(self):
        payment = self._payment()

        execution = PaymentExecution(
            reference="EXEC-ENTRY-UNSAVED",
            payment=payment,
            attempt_number=1,
            idempotency_key="entry-unsaved-execution",
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
            provider="test_provider",
        )

        with self.assertRaises(ValidationError):
            ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

    def test_univa_internal_does_not_require_policy_to_inspect_banking_reference(
        self,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        self.assertIsNone(
            execution.banking_transaction_reference,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
            return_value=expected_result,
        ) as banking_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        banking_reconcile.assert_called_once_with(
            execution=execution,
        )

    def test_policy_is_consulted_for_routing(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationEvidencePolicy.requires_banking_evidence",
            return_value=False,
        ) as policy, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        policy.assert_called_once_with(
            execution=execution,
        )

        generic_reconcile.assert_called_once_with(
            execution=execution,
        )

    def test_policy_true_routes_to_banking_service(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationEvidencePolicy.requires_banking_evidence",
            return_value=True,
        ) as policy, patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
            return_value=expected_result,
        ) as banking_reconcile, patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
        ) as generic_reconcile:

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        self.assertIs(result, expected_result)

        policy.assert_called_once_with(
            execution=execution,
        )

        banking_reconcile.assert_called_once_with(
            execution=execution,
        )

        generic_reconcile.assert_not_called()

    def test_entry_point_does_not_mutate_execution(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        before = {
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ):

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        execution.refresh_from_db()

        after = {
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        self.assertIs(result, expected_result)
        self.assertEqual(before, after)

    def test_entry_point_does_not_mutate_payment(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        expected_result = Mock()

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "ReconciliationOrchestrator.reconcile",
            return_value=expected_result,
        ):

            result = ReconciliationEntryPoint.reconcile(
                execution=execution,
            )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertIs(result, expected_result)
        self.assertEqual(before, after)

    def test_downstream_validation_error_is_propagated(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        expected_error = ValidationError(
            "Banking transaction reference is required."
        )

        with patch(
            "payment.canonical.services.reconciliation_entry."
            "BankingReconciliationService.reconcile",
            side_effect=expected_error,
        ):

            with self.assertRaisesMessage(
                ValidationError,
                "Banking transaction reference is required.",
            ):
                ReconciliationEntryPoint.reconcile(
                    execution=execution,
                )