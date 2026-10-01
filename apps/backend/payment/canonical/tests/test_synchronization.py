from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.lifecycle import PaymentLifecycle
from payment.canonical.services.synchronization import (
    PaymentExecutionSynchronization,
)


class PaymentExecutionSynchronizationTests(TestCase):

    def setUp(self):
        self.user = self.create_user()

        self.payment = Payment.objects.create(
            reference="PAY-SYNC-001",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="CHECKOUT-SYNC-001",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="PAY-SYNC-IDEMPOTENCY-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="PEXEC-SYNC-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="PEXEC-SYNC-IDEMPOTENCY-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="fake_provider",
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
        )

    def create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="sync@example.com",
            password="test-password",
        )

    def set_execution_status(self, status):
        self.execution.status = status

        if status == PaymentExecution.Status.PROCESSING:
            self.execution.processing_at = (
                self.execution.created_at
            )

        elif status == PaymentExecution.Status.PENDING:
            self.execution.processing_at = (
                self.execution.created_at
            )
            self.execution.pending_at = (
                self.execution.created_at
            )

        elif status == PaymentExecution.Status.COMPLETED:
            self.execution.processing_at = (
                self.execution.created_at
            )
            self.execution.completed_at = (
                self.execution.created_at
            )

        elif status == PaymentExecution.Status.FAILED:
            self.execution.processing_at = (
                self.execution.created_at
            )
            self.execution.failed_at = (
                self.execution.created_at
            )
            self.execution.failure_code = "DECLINED"
            self.execution.failure_reason = "Payment declined."

        elif status == PaymentExecution.Status.CANCELLED:
            self.execution.processing_at = (
                self.execution.created_at
            )
            self.execution.cancelled_at = (
                self.execution.created_at
            )

        self.execution.save()

    def test_missing_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(None)

    def test_invalid_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                object()
            )

    def test_created_execution_does_not_change_payment(self):
        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            returned_payment.id,
            self.payment.id,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_processing_execution_moves_pending_payment_to_processing(self):
        self.set_execution_status(
            PaymentExecution.Status.PROCESSING
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PROCESSING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )

        self.assertIsNotNone(
            self.payment.processing_at
        )

    def test_processing_execution_does_not_repeat_processing_transition(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.PROCESSING
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PROCESSING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )

    def test_pending_execution_does_not_change_payment(self):
        self.set_execution_status(
            PaymentExecution.Status.PENDING
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PENDING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_pending_execution_does_not_change_processing_payment(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.PENDING
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PROCESSING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )

    def test_completed_execution_moves_processing_payment_to_completed(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.COMPLETED,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.COMPLETED,
        )

        self.assertIsNotNone(
            self.payment.completed_at
        )

    def test_completed_execution_does_not_repeat_completed_transition(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )
        self.payment = PaymentLifecycle.mark_completed(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.COMPLETED,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.COMPLETED,
        )

    def test_completed_execution_cannot_complete_pending_payment_directly(self):
        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_failed_execution_does_not_fail_payment(self):
        self.set_execution_status(
            PaymentExecution.Status.FAILED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PENDING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_failed_execution_does_not_change_processing_payment(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.FAILED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PROCESSING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )

    def test_cancelled_execution_does_not_cancel_payment(self):
        self.set_execution_status(
            PaymentExecution.Status.CANCELLED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PENDING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_cancelled_execution_does_not_change_processing_payment(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.CANCELLED
        )

        returned_payment = (
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )
        )

        self.assertEqual(
            returned_payment.status,
            Payment.Status.PROCESSING,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )

    def test_completed_execution_does_not_mutate_payment_fields(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        original_amount = self.payment.amount
        original_currency = self.payment.currency
        original_source_type = self.payment.source_type
        original_source_id = self.payment.source_id
        original_payer_id = self.payment.payer_id
        original_beneficiary_id = self.payment.beneficiary_id

        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        PaymentExecutionSynchronization.synchronize(
            self.execution
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.amount,
            original_amount,
        )

        self.assertEqual(
            self.payment.currency,
            original_currency,
        )

        self.assertEqual(
            self.payment.source_type,
            original_source_type,
        )

        self.assertEqual(
            self.payment.source_id,
            original_source_id,
        )

        self.assertEqual(
            self.payment.payer_id,
            original_payer_id,
        )

        self.assertEqual(
            self.payment.beneficiary_id,
            original_beneficiary_id,
        )

    def test_synchronization_does_not_mutate_execution(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        original_status = self.execution.status
        original_attempt_number = self.execution.attempt_number
        original_provider = self.execution.provider
        original_route_type = self.execution.route_type

        PaymentExecutionSynchronization.synchronize(
            self.execution
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

        self.assertEqual(
            self.execution.attempt_number,
            original_attempt_number,
        )

        self.assertEqual(
            self.execution.provider,
            original_provider,
        )

        self.assertEqual(
            self.execution.route_type,
            original_route_type,
        )

    def test_unknown_execution_status_is_rejected(self):
        self.execution.status = "unsupported_status"
        self.execution.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_completed_payment_rejects_processing_execution(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )
        self.payment = PaymentLifecycle.mark_completed(
            self.payment
        )

        self.set_execution_status(
            PaymentExecution.Status.PROCESSING
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.COMPLETED,
        )

    def test_cancelled_payment_rejects_processing_execution(self):
        self.payment.status = Payment.Status.CANCELLED
        self.payment.cancelled_at = self.payment.created_at
        self.payment.save(
            update_fields=["status", "cancelled_at", "updated_at"]
        )

        self.set_execution_status(
            PaymentExecution.Status.PROCESSING
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.CANCELLED,
        )

    def test_reversed_payment_rejects_processing_execution(self):
        self.payment = PaymentLifecycle.mark_processing(
            self.payment
        )

        self.payment = PaymentLifecycle.mark_completed(
            self.payment
        )

        self.payment.status = Payment.Status.REVERSED
        self.payment.reversed_at = self.payment.created_at
        self.payment.save(
            update_fields=["status", "reversed_at", "updated_at"]
        )

        self.set_execution_status(
            PaymentExecution.Status.PROCESSING
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.REVERSED,
        )
 
    def test_synchronization_is_atomic_when_payment_transition_fails(self):
        self.set_execution_status(
            PaymentExecution.Status.COMPLETED
        )

        original_status = self.payment.status

        with self.assertRaises(ValidationError):
            PaymentExecutionSynchronization.synchronize(
                self.execution
            )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )