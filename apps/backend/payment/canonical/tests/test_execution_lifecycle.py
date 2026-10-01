from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.execution import PaymentExecutionService
from payment.canonical.services.execution_lifecycle import (
    PaymentExecutionLifecycle,
)
from payment.canonical.services.service import PaymentService


class PaymentExecutionLifecycleTests(TestCase):
    def setUp(self):
        self.payer = User.objects.create_user(
            email="payer@example.com",
        )

        self.beneficiary = User.objects.create_user(
            email="beneficiary@example.com",
        )

        self.payment = PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="settlement-001",
            source_reference="SET-001",
            beneficiary=self.beneficiary,
            amount=Decimal("10000.00"),
            currency="NGN",
            idempotency_key="execution-lifecycle-payment-001",
        )

    def create_execution(self):
        return PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key=(
                f"execution-lifecycle-{PaymentExecution.objects.count() + 1}"
            ),
        )

    def create_execution_with_status(self, status):
        execution = self.create_execution()

        execution.status = status

        if status == PaymentExecution.Status.PROCESSING:
            execution.processing_at = self._now()

        elif status == PaymentExecution.Status.PENDING:
            execution.pending_at = self._now()
            execution.reconciliation_state = (
                PaymentExecution.ReconciliationState.PENDING
            )

        elif status == PaymentExecution.Status.FAILED:
            execution.failure_reason = "Provider rejected transaction."
            execution.failed_at = self._now()

        elif status == PaymentExecution.Status.CANCELLED:
            execution.cancelled_at = self._now()

        elif status == PaymentExecution.Status.COMPLETED:
            execution.completed_at = self._now()

        execution.save()

        return execution

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()

    # ------------------------------------------------------------------
    # CREATED
    # ------------------------------------------------------------------

    def test_created_can_transition_to_processing(self):
        execution = self.create_execution()

        result = PaymentExecutionLifecycle.mark_processing(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.PROCESSING,
        )
        self.assertIsNotNone(result.processing_at)

    def test_created_can_be_cancelled(self):
        execution = self.create_execution()

        result = PaymentExecutionLifecycle.cancel(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.CANCELLED,
        )
        self.assertIsNotNone(result.cancelled_at)

    def test_created_cannot_be_completed(self):
        execution = self.create_execution()

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_completed(
                execution,
            )

    def test_created_cannot_be_failed(self):
        execution = self.create_execution()

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_reason="Provider failure.",
            )

    def test_created_cannot_be_pending(self):
        execution = self.create_execution()

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_pending(
                execution,
            )

    # ------------------------------------------------------------------
    # PROCESSING
    # ------------------------------------------------------------------

    def test_processing_can_transition_to_pending(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_pending(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.PENDING,
        )
        self.assertIsNotNone(result.pending_at)
        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.PENDING,
        )

    def test_processing_can_transition_to_pending_with_reconciliation_required(
        self,
    ):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_pending(
            execution,
            reconciliation_required=True,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.PENDING,
        )
        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

    def test_processing_can_complete(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_completed(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertIsNotNone(result.completed_at)

    def test_processing_can_fail(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_failed(
            execution,
            failure_code="PROVIDER_DECLINED",
            failure_reason="Provider rejected transaction.",
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            result.failure_code,
            "PROVIDER_DECLINED",
        )
        self.assertEqual(
            result.failure_reason,
            "Provider rejected transaction.",
        )
        self.assertIsNotNone(result.failed_at)

    def test_processing_can_be_cancelled(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.cancel(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.CANCELLED,
        )
        self.assertIsNotNone(result.cancelled_at)

    # ------------------------------------------------------------------
    # PENDING
    # ------------------------------------------------------------------

    def test_pending_can_complete(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PENDING,
        )

        result = PaymentExecutionLifecycle.mark_completed(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertIsNotNone(result.completed_at)

    def test_pending_can_fail(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PENDING,
        )

        result = PaymentExecutionLifecycle.mark_failed(
            execution,
            failure_code="TIMEOUT",
            failure_reason="Provider timeout.",
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            result.failure_code,
            "TIMEOUT",
        )
        self.assertEqual(
            result.failure_reason,
            "Provider timeout.",
        )

    def test_pending_can_be_cancelled(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PENDING,
        )

        result = PaymentExecutionLifecycle.cancel(
            execution,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.CANCELLED,
        )
        self.assertIsNotNone(result.cancelled_at)

    def test_pending_cannot_return_to_processing(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_processing(
                execution,
            )

    # ------------------------------------------------------------------
    # FAILED
    # ------------------------------------------------------------------

    def test_failed_is_terminal(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_processing(
                execution,
            )

    def test_failed_cannot_complete(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_completed(
                execution,
            )

    def test_failed_cannot_be_cancelled(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.cancel(
                execution,
            )

    def test_failed_cannot_return_to_pending(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_pending(
                execution,
            )

    # ------------------------------------------------------------------
    # CANCELLED
    # ------------------------------------------------------------------

    def test_cancelled_is_terminal(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_processing(
                execution,
            )

    def test_cancelled_cannot_complete(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_completed(
                execution,
            )

    def test_cancelled_cannot_fail(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_reason="Provider failure.",
            )

    def test_cancelled_cannot_be_pending(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_pending(
                execution,
            )

    # ------------------------------------------------------------------
    # COMPLETED
    # ------------------------------------------------------------------

    def test_completed_is_terminal(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_processing(
                execution,
            )

    def test_completed_cannot_fail(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_reason="Provider failure.",
            )

    def test_completed_cannot_be_cancelled(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.cancel(
                execution,
            )

    def test_completed_cannot_be_pending(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_pending(
                execution,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_failed_requires_failure_reason(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionLifecycle.mark_failed(
                execution,
                failure_code="PROVIDER_ERROR",
                failure_reason="",
            )

    def test_failed_without_failure_code_is_allowed(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_failed(
            execution,
            failure_reason="Provider rejected transaction.",
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            result.failure_code,
            "",
        )

    # ------------------------------------------------------------------
    # Payment boundary
    # ------------------------------------------------------------------

    def test_execution_lifecycle_does_not_change_payment_status(self):
        original_status = self.payment.status

        execution = self.create_execution()

        PaymentExecutionLifecycle.mark_processing(
            execution,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_completion_does_not_directly_change_payment_status(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        PaymentExecutionLifecycle.mark_completed(
            execution,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    # ------------------------------------------------------------------
    # Identity preservation
    # ------------------------------------------------------------------

    def test_lifecycle_preserves_execution_identity(self):
        execution = self.create_execution()

        original_id = execution.id
        original_reference = execution.reference
        original_payment_id = execution.payment_id
        original_attempt_number = execution.attempt_number
        original_provider = execution.provider
        original_route_type = execution.route_type

        result = PaymentExecutionLifecycle.mark_processing(
            execution,
        )

        self.assertEqual(result.id, original_id)
        self.assertEqual(
            result.reference,
            original_reference,
        )
        self.assertEqual(
            result.payment_id,
            original_payment_id,
        )
        self.assertEqual(
            result.attempt_number,
            original_attempt_number,
        )
        self.assertEqual(
            result.provider,
            original_provider,
        )
        self.assertEqual(
            result.route_type,
            original_route_type,
        )

    def test_failed_transition_preserves_failure_information(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        result = PaymentExecutionLifecycle.mark_failed(
            execution,
            failure_code="PROVIDER_TIMEOUT",
            failure_reason="Provider did not respond.",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.failure_code,
            "PROVIDER_TIMEOUT",
        )
        self.assertEqual(
            result.failure_reason,
            "Provider did not respond.",
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def test_processing_transition_is_persisted(self):
        execution = self.create_execution()

        PaymentExecutionLifecycle.mark_processing(
            execution,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PROCESSING,
        )
        self.assertIsNotNone(
            execution.processing_at,
        )

    def test_pending_transition_is_persisted(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        PaymentExecutionLifecycle.mark_pending(
            execution,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )
        self.assertIsNotNone(
            execution.pending_at,
        )

    def test_completed_transition_is_persisted(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        PaymentExecutionLifecycle.mark_completed(
            execution,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertIsNotNone(
            execution.completed_at,
        )

    def test_failed_transition_is_persisted(self):
        execution = self.create_execution_with_status(
            PaymentExecution.Status.PROCESSING,
        )

        PaymentExecutionLifecycle.mark_failed(
            execution,
            failure_code="FAILED",
            failure_reason="Execution failed.",
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            execution.failure_code,
            "FAILED",
        )
        self.assertEqual(
            execution.failure_reason,
            "Execution failed.",
        )

    def test_cancelled_transition_is_persisted(self):
        execution = self.create_execution()

        PaymentExecutionLifecycle.cancel(
            execution,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CANCELLED,
        )
        self.assertIsNotNone(
            execution.cancelled_at,
        )