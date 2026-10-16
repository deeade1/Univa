# payment/canonical/tests/test_reconciliation_enqueue.py

from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.reconciliation_enqueue import (
    ReconciliationEnqueueAdapter,
)


class ReconciliationEnqueueAdapterTests(TestCase):
    def setUp(self):
        self.payment = Payment.objects.create(
            reference="PAY-ENQUEUE-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earnings",
            source_id="earning-001",
            source_reference="EARN-001",
            amount=Decimal("10000.00"),
            currency="NGN",
            idempotency_key="enqueue-payment-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-ENQUEUE-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="enqueue-execution-001",
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
            provider="univa_banking",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "reconcile_payment_execution_task.delay"
    )
    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_eligible_execution_is_enqueued(
        self,
        mock_is_eligible,
        mock_delay,
    ):
        mock_is_eligible.return_value = True

        expected_result = Mock()
        mock_delay.return_value = expected_result

        result = ReconciliationEnqueueAdapter.enqueue(
            execution=self.execution,
        )

        mock_is_eligible.assert_called_once_with(
            execution=self.execution,
        )
        mock_delay.assert_called_once_with(
            self.execution.pk,
        )
        self.assertIs(result, expected_result)

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "reconcile_payment_execution_task.delay"
    )
    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_ineligible_execution_is_not_enqueued(
        self,
        mock_is_eligible,
        mock_delay,
    ):
        mock_is_eligible.return_value = False

        result = ReconciliationEnqueueAdapter.enqueue(
            execution=self.execution,
        )

        mock_is_eligible.assert_called_once_with(
            execution=self.execution,
        )
        mock_delay.assert_not_called()
        self.assertIsNone(result)

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "reconcile_payment_execution_task.delay"
    )
    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_exact_persisted_execution_id_is_enqueued(
        self,
        mock_is_eligible,
        mock_delay,
    ):
        mock_is_eligible.return_value = True

        ReconciliationEnqueueAdapter.enqueue(
            execution=self.execution,
        )

        args, kwargs = mock_delay.call_args

        self.assertEqual(args, (self.execution.pk,))
        self.assertEqual(kwargs, {})

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_policy_exception_propagates(
        self,
        mock_is_eligible,
    ):
        error = ValidationError("policy failure")
        mock_is_eligible.side_effect = error

        with self.assertRaises(ValidationError) as context:
            ReconciliationEnqueueAdapter.enqueue(
                execution=self.execution,
            )

        self.assertIs(context.exception, error)

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "reconcile_payment_execution_task.delay"
    )
    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_enqueue_exception_propagates(
        self,
        mock_is_eligible,
        mock_delay,
    ):
        mock_is_eligible.return_value = True

        error = RuntimeError("queue unavailable")
        mock_delay.side_effect = error

        with self.assertRaises(RuntimeError) as context:
            ReconciliationEnqueueAdapter.enqueue(
                execution=self.execution,
            )

        self.assertIs(context.exception, error)

    def test_invalid_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEnqueueAdapter.enqueue(
                execution=object(),
            )

    def test_unsaved_execution_is_rejected(self):
        execution = PaymentExecution(
            reference="EXEC-UNSAVED",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="unsaved-execution-001",
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
            provider="univa_banking",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

        with self.assertRaises(ValidationError):
            ReconciliationEnqueueAdapter.enqueue(
                execution=execution,
            )

    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "reconcile_payment_execution_task.delay"
    )
    @patch(
        "payment.canonical.services.reconciliation_enqueue."
        "ReconciliationTriggerPolicy.is_eligible"
    )
    def test_enqueue_does_not_mutate_execution_or_payment(
        self,
        mock_is_eligible,
        mock_delay,
    ):
        mock_is_eligible.return_value = True
        mock_delay.return_value = Mock()

        execution_before = {
            "status": self.execution.status,
            "reconciliation_state": self.execution.reconciliation_state,
            "provider": self.execution.provider,
            "attempt_number": self.execution.attempt_number,
        }

        payment_before = {
            "status": self.payment.status,
            "amount": self.payment.amount,
            "currency": self.payment.currency,
        }

        ReconciliationEnqueueAdapter.enqueue(
            execution=self.execution,
        )

        self.execution.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            execution_before["status"],
        )
        self.assertEqual(
            self.execution.reconciliation_state,
            execution_before["reconciliation_state"],
        )
        self.assertEqual(
            self.execution.provider,
            execution_before["provider"],
        )
        self.assertEqual(
            self.execution.attempt_number,
            execution_before["attempt_number"],
        )

        self.assertEqual(
            self.payment.status,
            payment_before["status"],
        )
        self.assertEqual(
            self.payment.amount,
            payment_before["amount"],
        )
        self.assertEqual(
            self.payment.currency,
            payment_before["currency"],
        )

    