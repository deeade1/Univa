from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.execution import (
    PaymentExecutionService,
)
from payment.canonical.services.execution_event import (
    PaymentExecutionEventService,
)
from payment.canonical.services.execution_orchestrator import (
    ExecutionOrchestrator,
)
from payment.canonical.services.providers import (
    ProviderAdapter,
    ProviderRegistry,
    ProviderResult,
)


class FakeProviderAdapter(ProviderAdapter):
    """Test-only provider adapter."""

    def __init__(self, result):
        self._result = result
        self.initiate_called = False
        self.get_status_called = False

    @property
    def provider_name(self):
        return "fake_provider"

    def initiate(self, execution):
        self.initiate_called = True
        return self._result

    def get_status(self, execution):
        self.get_status_called = True
        return self._result


class ExecutionOrchestratorTests(TestCase):

    def setUp(self):
        ProviderRegistry.clear()

        self.user = self.create_user()

        self.payment = Payment.objects.create(
            reference="PAY-ORCH-001",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="CHECKOUT-ORCH-001",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="PAY-ORCH-IDEMPOTENCY-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="PEXEC-ORCH-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="PEXEC-ORCH-IDEMPOTENCY-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="fake_provider",
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
        )

    def tearDown(self):
        ProviderRegistry.clear()

    def create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="orchestrator@example.com",
            password="test-password",
        )

    def register_adapter(self, result):
        adapter = FakeProviderAdapter(result)
        ProviderRegistry.register(adapter)
        return adapter

    def test_execute_resolves_provider_through_router(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-001",
        )

        adapter = self.register_adapter(result)

        returned_execution = ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertTrue(adapter.initiate_called)
        self.assertEqual(
            returned_execution.id,
            self.execution.id,
        )

    def test_execute_calls_provider_initiate(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-002",
        )

        adapter = self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        self.assertTrue(adapter.initiate_called)
        self.assertFalse(adapter.get_status_called)

    def test_execute_returns_execution_after_lifecycle_transition(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-003",
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_processing_result_transitions_execution_to_processing(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PROCESSING,
            provider_reference="FAKE-PROCESSING-001",
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PROCESSING,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PROCESSING,
        )

        self.assertIsNotNone(execution.processing_at)

    def test_pending_result_transitions_execution_to_pending(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PENDING,
            provider_reference="FAKE-PENDING-001",
            reconciliation_required=False,
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        self.assertIsNotNone(execution.pending_at)

    def test_pending_result_requires_reconciliation_when_requested(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PENDING,
            provider_reference="FAKE-PENDING-002",
            reconciliation_required=True,
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        self.assertEqual(
            execution.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

    def test_completed_result_transitions_execution_to_completed(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-COMPLETED-001",
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.COMPLETED,
        )

        self.assertIsNotNone(execution.completed_at)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-COMPLETED-001",
        )


    def test_failed_result_transitions_execution_to_failed(self):
        result = ProviderResult(
            status=PaymentExecution.Status.FAILED,
            provider_reference="FAKE-FAILED-001",
            failure_code="DECLINED",
            failure_reason="Provider declined the payment.",
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.FAILED,
        )

        self.assertEqual(
            execution.failure_code,
            "DECLINED",
        )

        self.assertEqual(
            execution.failure_reason,
            "Provider declined the payment.",
        )

        self.assertIsNotNone(execution.failed_at)

    def test_cancelled_result_transitions_execution_to_cancelled(self):
        result = ProviderResult(
            status=PaymentExecution.Status.CANCELLED,
            provider_reference="FAKE-CANCELLED-001",
        )

        self.register_adapter(result)

        execution = ExecutionOrchestrator.execute(
            self.execution
        )

        execution.refresh_from_db()

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CANCELLED,
        )

        self.assertIsNotNone(execution.cancelled_at)

    def test_processing_result_records_processing_event(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PROCESSING,
            provider_reference="FAKE-EVENT-PROCESSING",
            metadata={
                "provider_status": "processing",
            },
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = (
            PaymentExecutionEvent.objects
            .filter(
                execution=self.execution,
                event_type=PaymentExecutionEvent.EventType.PROCESSING,
                provider_reference="FAKE-EVENT-PROCESSING",
            )
            .get()
        )

        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROCESSING,
        )

        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-EVENT-PROCESSING",
        )

        self.assertEqual(
            event.payload,
            {
                "provider_status": "processing",
            },
        )

    def test_pending_result_records_provider_pending_event(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PENDING,
            provider_reference="FAKE-EVENT-PENDING",
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_PENDING
            ),
        )

        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_PENDING,
        )

        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-EVENT-PENDING",
        )

    def test_completed_result_records_provider_completed_event(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-EVENT-COMPLETED",
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
        )

        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-EVENT-COMPLETED",
        )

    def test_failed_result_records_provider_failed_event(self):
        result = ProviderResult(
            status=PaymentExecution.Status.FAILED,
            provider_reference="FAKE-EVENT-FAILED",
            failure_code="DECLINED",
            failure_reason="Payment declined.",
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_FAILED
            ),
        )

        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_FAILED,
        )

        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-EVENT-FAILED",
        )

    def test_cancelled_result_records_provider_cancelled_event(self):
        result = ProviderResult(
            status=PaymentExecution.Status.CANCELLED,
            provider_reference="FAKE-EVENT-CANCELLED",
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_CANCELLED
            ),
        )

        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_CANCELLED,
        )

        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertEqual(
            event.provider_reference,
            "FAKE-EVENT-CANCELLED",
        )

    def test_provider_metadata_is_recorded_in_event_payload(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-METADATA-001",
            metadata={
                "provider_status": "successful",
                "transaction_id": "TX-123",
            },
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(self.execution)

        event = PaymentExecutionEvent.objects.get(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
        )

        self.assertEqual(
            event.payload,
            {
                "provider_status": "successful",
                "transaction_id": "TX-123",
            },
        )

    def test_none_provider_result_is_rejected(self):
        adapter = self.register_adapter(None)

        with self.assertRaises(ValidationError):
            ExecutionOrchestrator.execute(
                self.execution
            )

        self.assertTrue(adapter.initiate_called)

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

        self.assertFalse(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution
            ).exists()
        )

    def test_missing_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ExecutionOrchestrator.execute(None)

    def test_invalid_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ExecutionOrchestrator.execute(object())

    def test_unknown_provider_is_rejected(self):
        self.execution.provider = "unknown_provider"
        self.execution.save(update_fields=["provider"])

        with self.assertRaises(ValidationError):
            ExecutionOrchestrator.execute(
                self.execution
            )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

    def test_unsupported_provider_result_status_is_rejected(self):
        class InvalidStatusResult:
            status = "unsupported_status"
            provider_reference = "FAKE-INVALID-001"
            failure_code = None
            failure_reason = None
            reconciliation_required = False
            metadata = {}

        adapter = FakeProviderAdapter(
            InvalidStatusResult()
        )

        ProviderRegistry.register(adapter)

        with self.assertRaises(ValidationError):
            ExecutionOrchestrator.execute(
                self.execution
            )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

        self.assertFalse(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution
            ).exists()
        )

    def test_orchestrator_does_not_call_get_status(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-STATUS-001",
        )

        adapter = self.register_adapter(result)

        ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertFalse(
            adapter.get_status_called
        )

    def test_orchestrator_synchronizes_payment_through_synchronization_service(
        self,
    ):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="PROVIDER-COMPLETED-123",
        )

        self.register_adapter(result)

        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="fake_provider",
            idempotency_key="orchestrator-payment-sync",
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

        returned_execution = ExecutionOrchestrator.execute(
            execution
        )

        self.payment.refresh_from_db()
        returned_execution.refresh_from_db()

        self.assertEqual(
            returned_execution.status,
            PaymentExecution.Status.COMPLETED,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.COMPLETED,
        )
    
    def test_orchestrator_does_not_create_retry_execution(self):
        result = ProviderResult(
            status=PaymentExecution.Status.FAILED,
            provider_reference="FAKE-RETRY-001",
            failure_code="DECLINED",
            failure_reason="Payment declined.",
        )

        self.register_adapter(result)

        ExecutionOrchestrator.execute(
            self.execution
        )

        self.assertEqual(
            PaymentExecution.objects.filter(
                payment=self.payment
            ).count(),
            1,
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.attempt_number,
            1,
        )

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.FAILED,
        )

    def test_failed_execution_is_atomic_when_event_recording_fails(self):
        result = ProviderResult(
            status=PaymentExecution.Status.FAILED,
            provider_reference="FAKE-ATOMIC-001",
            failure_code="DECLINED",
            failure_reason="Payment declined.",
        )

        self.register_adapter(result)

        original_record_event = (
            PaymentExecutionEventService.record_event
        )

        def failing_record_event(*args, **kwargs):
            raise RuntimeError("Event recording failed.")

        PaymentExecutionEventService.record_event = (
            failing_record_event
        )

        try:
            with self.assertRaises(RuntimeError):
                ExecutionOrchestrator.execute(
                    self.execution
                )
        finally:
            PaymentExecutionEventService.record_event = (
                original_record_event
            )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

        self.assertFalse(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution
            ).exists()
        )