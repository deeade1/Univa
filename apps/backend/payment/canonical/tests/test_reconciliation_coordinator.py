"""
Tests for the canonical reconciliation coordinator.

Architectural contract
----------------------

The coordinator:

    - validates the PaymentExecution
    - consults ReconciliationTriggerPolicy
    - stops when reconciliation is not eligible
    - delegates eligible executions to ReconciliationEntryPoint
    - returns a structured coordination result
    - returns the downstream reconciliation result unchanged

The coordinator does NOT:

    - implement reconciliation rules
    - collect evidence
    - resolve Banking transactions
    - translate Banking evidence
    - mutate PaymentExecution directly
    - mutate Payment directly
    - create events
    - call providers
    - perform retries
"""


from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_coordinator import (
    ReconciliationCoordinator,
    ReconciliationCoordinationResult,
)


class ReconciliationCoordinatorTests(TestCase):
    """
    Focused tests for the canonical reconciliation coordinator.
    """

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(
            email="reconciliation-coordinator@example.com",
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
            reference=f"PAY-COORD-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"coordinator-payment-{suffix:03d}",
            beneficiary=self.user,
            amount="100.00",
            currency="NGN",
            idempotency_key=(
                f"coordinator-payment-idempotency-{suffix:03d}"
            ),
        )

    def _execution(self):
        self.execution_counter += 1
        suffix = self.execution_counter

        return PaymentExecution.objects.create(
            reference=f"EXEC-COORD-{suffix:03d}",
            payment=self._payment(),
            attempt_number=1,
            idempotency_key=(
                f"coordinator-execution-idempotency-{suffix:03d}"
            ),
            route_type=PaymentExecution.RouteType.CARD,
            provider="test_provider",
        )

    def _required_execution(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        execution.save(
            update_fields=[
                "reconciliation_state",
                "updated_at",
            ]
        )

        return execution

    def test_ineligible_execution_returns_structured_result(self):
        execution = self._execution()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
        ) as entry_point:

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertIsInstance(
            result,
            ReconciliationCoordinationResult,
        )

        self.assertFalse(result.eligible)
        self.assertIs(result.execution, execution)
        self.assertIsNone(result.reconciliation)
        self.assertFalse(result.was_reconciled)

        entry_point.assert_not_called()

    def test_eligible_execution_delegates_to_entry_point(self):
        execution = self._required_execution()

        expected_reconciliation = Mock()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=expected_reconciliation,
        ) as entry_point:

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertIsInstance(
            result,
            ReconciliationCoordinationResult,
        )

        self.assertTrue(result.eligible)
        self.assertIs(result.execution, execution)
        self.assertIs(
            result.reconciliation,
            expected_reconciliation,
        )
        self.assertTrue(result.was_reconciled)

        entry_point.assert_called_once_with(
            execution=execution,
        )

    def test_trigger_policy_is_consulted(self):
        execution = self._execution()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationTriggerPolicy.is_eligible",
            return_value=False,
        ) as trigger_policy:

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        trigger_policy.assert_called_once_with(
            execution=execution,
        )

        self.assertFalse(result.eligible)
        self.assertIsNone(result.reconciliation)

    def test_policy_true_routes_to_entry_point(self):
        execution = self._execution()

        expected_reconciliation = Mock()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationTriggerPolicy.is_eligible",
            return_value=True,
        ) as trigger_policy, patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=expected_reconciliation,
        ) as entry_point:

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        trigger_policy.assert_called_once_with(
            execution=execution,
        )

        entry_point.assert_called_once_with(
            execution=execution,
        )

        self.assertTrue(result.eligible)
        self.assertIs(
            result.reconciliation,
            expected_reconciliation,
        )

    def test_policy_false_does_not_call_entry_point(self):
        execution = self._execution()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationTriggerPolicy.is_eligible",
            return_value=False,
        ) as trigger_policy, patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
        ) as entry_point:

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        trigger_policy.assert_called_once_with(
            execution=execution,
        )

        entry_point.assert_not_called()

        self.assertFalse(result.eligible)
        self.assertIsNone(result.reconciliation)

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationCoordinator.reconcile(
                execution=None,
            )

    def test_non_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationCoordinator.reconcile(
                execution=object(),
            )

    def test_unsaved_execution_is_rejected(self):
        payment = self._payment()

        execution = PaymentExecution(
            reference="EXEC-COORD-UNSAVED",
            payment=payment,
            attempt_number=1,
            idempotency_key="coordinator-unsaved-execution",
            route_type=PaymentExecution.RouteType.CARD,
            provider="test_provider",
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

        with self.assertRaises(ValidationError):
            ReconciliationCoordinator.reconcile(
                execution=execution,
            )

    def test_result_contains_same_execution_instance(self):
        execution = self._required_execution()

        expected_reconciliation = Mock()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=expected_reconciliation,
        ):

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertIs(result.execution, execution)

    def test_downstream_result_is_returned_unchanged(self):
        execution = self._required_execution()

        expected_reconciliation = Mock(
            outcome="completed",
        )

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=expected_reconciliation,
        ):

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertIs(
            result.reconciliation,
            expected_reconciliation,
        )

    def test_downstream_validation_error_is_propagated(self):
        execution = self._required_execution()

        expected_error = ValidationError(
            "Banking transaction reference is required."
        )

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            side_effect=expected_error,
        ):

            with self.assertRaisesMessage(
                ValidationError,
                "Banking transaction reference is required.",
            ):
                ReconciliationCoordinator.reconcile(
                    execution=execution,
                )

    def test_coordinator_does_not_mutate_execution(self):
        execution = self._required_execution()

        before = {
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=Mock(),
        ):

            ReconciliationCoordinator.reconcile(
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

        self.assertEqual(before, after)

    def test_coordinator_does_not_mutate_payment(self):
        execution = self._required_execution()

        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=Mock(),
        ):

            ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertEqual(before, after)

    def test_was_reconciled_is_false_for_ineligible_result(self):
        execution = self._execution()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
        ):

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertFalse(result.was_reconciled)

    def test_was_reconciled_is_true_when_reconciliation_result_exists(
        self,
    ):
        execution = self._required_execution()

        expected_reconciliation = Mock()

        with patch(
            "payment.canonical.services.reconciliation_coordinator."
            "ReconciliationEntryPoint.reconcile",
            return_value=expected_reconciliation,
        ):

            result = ReconciliationCoordinator.reconcile(
                execution=execution,
            )

        self.assertTrue(result.was_reconciled)