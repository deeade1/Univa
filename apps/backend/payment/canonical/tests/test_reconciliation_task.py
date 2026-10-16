"""
Tests for the canonical asynchronous reconciliation task.

Architectural contract
----------------------

The Celery task is an asynchronous adapter.

It is responsible only for:

    - receiving a PaymentExecution identifier
    - loading the persisted PaymentExecution
    - checking reconciliation trigger eligibility
    - delegating eligible executions to ReconciliationEntryPoint
    - returning the downstream result

It does NOT:

    - implement reconciliation rules
    - select Banking vs generic reconciliation
    - collect evidence
    - resolve Banking transactions
    - call providers
    - process webhooks
    - perform lifecycle transitions
    - mutate PaymentExecution directly
    - mutate Payment directly
    - implement retry policy

A stale queued task is a safe no-op when the execution is no longer
eligible for reconciliation.
"""

from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import Payment, PaymentExecution


class ReconciliationTaskTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(
            email="reconciliation-task@example.com",
            password="test-password",
        )

    def setUp(self):
        self.payment_counter = 0
        self.execution_counter = 0

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _payment(self):
        self.payment_counter += 1
        suffix = self.payment_counter

        return Payment.objects.create(
            reference=f"PAY-TASK-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"task-payment-{suffix:03d}",
            beneficiary=self.user,
            amount="100.00",
            currency="NGN",
            idempotency_key=(
                f"task-payment-idempotency-{suffix:03d}"
            ),
        )

    def _execution(self):
        self.execution_counter += 1
        suffix = self.execution_counter

        return PaymentExecution.objects.create(
            reference=f"EXEC-TASK-{suffix:03d}",
            payment=self._payment(),
            attempt_number=1,
            idempotency_key=(
                f"task-execution-idempotency-{suffix:03d}"
            ),
            route_type=PaymentExecution.RouteType.CARD,
            provider="test_provider",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

    # ------------------------------------------------------------------
    # Import contract
    # ------------------------------------------------------------------

    def test_reconciliation_task_is_importable(self):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        self.assertTrue(
            callable(reconcile_payment_execution_task),
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    def test_valid_execution_id_loads_execution(
        self,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()
        mock_reconcile.return_value = object()

        reconcile_payment_execution_task(
            str(execution.pk),
        )

        delegated_execution = (
            mock_reconcile.call_args.kwargs["execution"]
        )

        self.assertEqual(
            delegated_execution.pk,
            execution.pk,
        )

    def test_missing_execution_raises_does_not_exist(self):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()
        execution_id = execution.pk
        execution.delete()

        with self.assertRaises(
            PaymentExecution.DoesNotExist,
        ):
            reconcile_payment_execution_task(
                str(execution_id),
            )

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_eligible_execution_enters_reconciliation(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = True
        expected_result = Mock()
        mock_reconcile.return_value = expected_result

        result = reconcile_payment_execution_task(
            str(execution.pk),
        )

        self.assertIs(
            result,
            expected_result,
        )

        mock_is_eligible.assert_called_once_with(
            execution=mock_reconcile.call_args.kwargs["execution"],
        )

        mock_reconcile.assert_called_once_with(
            execution=mock_reconcile.call_args.kwargs["execution"],
        )

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_ineligible_execution_is_safe_no_op(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = False

        result = reconcile_payment_execution_task(
            str(execution.pk),
        )

        self.assertIsNone(result)

        mock_is_eligible.assert_called_once()
        mock_reconcile.assert_not_called()

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_entry_point_is_called_exactly_once(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = True
        mock_reconcile.return_value = object()

        reconcile_payment_execution_task(
            str(execution.pk),
        )

        mock_reconcile.assert_called_once()

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_same_persisted_execution_is_passed_to_entry_point(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = True
        mock_reconcile.return_value = object()

        reconcile_payment_execution_task(
            str(execution.pk),
        )

        delegated_execution = (
            mock_reconcile.call_args.kwargs["execution"]
        )

        self.assertIsInstance(
            delegated_execution,
            PaymentExecution,
        )

        self.assertEqual(
            delegated_execution.pk,
            execution.pk,
        )

    # ------------------------------------------------------------------
    # Result and exception propagation
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_entry_point_result_is_returned_unchanged(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = True
        expected_result = object()
        mock_reconcile.return_value = expected_result

        result = reconcile_payment_execution_task(
            str(execution.pk),
        )

        self.assertIs(
            result,
            expected_result,
        )

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_entry_point_exception_propagates_unchanged(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        mock_is_eligible.return_value = True

        error = ValidationError(
            "reconciliation entry point failed"
        )
        mock_reconcile.side_effect = error

        with self.assertRaises(ValidationError) as context:
            reconcile_payment_execution_task(
                str(execution.pk),
            )

        self.assertIs(
            context.exception,
            error,
        )

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_trigger_policy_exception_propagates_unchanged(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        error = ValidationError(
            "trigger policy failed"
        )
        mock_is_eligible.side_effect = error

        with self.assertRaises(ValidationError) as context:
            reconcile_payment_execution_task(
                str(execution.pk),
            )

        self.assertIs(
            context.exception,
            error,
        )

        mock_reconcile.assert_not_called()

    # ------------------------------------------------------------------
    # Non-mutation
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_task_does_not_mutate_execution(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()

        before = {
            "status": str(execution.status),
            "reconciliation_state": str(
                execution.reconciliation_state
            ),
            "route_type": str(execution.route_type),
            "provider": execution.provider,
        }

        mock_is_eligible.return_value = True
        mock_reconcile.return_value = object()

        reconcile_payment_execution_task(
            str(execution.pk),
        )

        execution.refresh_from_db()

        after = {
            "status": str(execution.status),
            "reconciliation_state": str(
                execution.reconciliation_state
            ),
            "route_type": str(execution.route_type),
            "provider": execution.provider,
        }

        self.assertEqual(before, after)

    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationEntryPoint.reconcile"
    )
    @patch(
        "payment.canonical.tasks.reconciliation."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_task_does_not_mutate_payment(
        self,
        mock_is_eligible,
        mock_reconcile,
    ):
        from payment.canonical.tasks.reconciliation import (
            reconcile_payment_execution_task,
        )

        execution = self._execution()
        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        mock_is_eligible.return_value = True
        mock_reconcile.return_value = object()

        reconcile_payment_execution_task(
            str(execution.pk),
        )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertEqual(before, after)