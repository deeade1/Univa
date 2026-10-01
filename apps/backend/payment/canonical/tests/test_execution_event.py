from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.execution import PaymentExecutionService
from payment.canonical.services.execution_event import (
    PaymentExecutionEventService,
)
from payment.canonical.services.service import PaymentService


class PaymentExecutionEventServiceTests(TestCase):
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
            idempotency_key="event-payment-001",
        )

        self.execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="event-execution-001",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def record_event(self, **overrides):
        data = {
            "execution": self.execution,
            "event_type": (
                PaymentExecutionEvent.EventType.PROCESSING
            ),
            "source": PaymentExecutionEvent.Source.SYSTEM,
            "payload": {
                "message": "Execution processing started.",
            },
        }

        data.update(overrides)

        return PaymentExecutionEventService.record_event(
            **data,
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def test_record_system_event(self):
        event = self.record_event()

        self.assertIsNotNone(event.id)
        self.assertEqual(
            event.execution_id,
            self.execution.id,
        )
        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.PROCESSING,
        )
        self.assertEqual(
            event.source,
            PaymentExecutionEvent.Source.SYSTEM,
        )

    def test_event_is_persisted(self):
        event = self.record_event()

        self.assertTrue(
            PaymentExecutionEvent.objects.filter(
                id=event.id,
            ).exists()
        )

    def test_event_payload_is_persisted(self):
        payload = {
            "provider_status": "processing",
            "transaction_reference": "TXN-001",
        }

        event = self.record_event(
            payload=payload,
        )

        self.assertEqual(
            event.payload,
            payload,
        )

    def test_empty_payload_defaults_to_dict(self):
        event = self.record_event()

        self.assertEqual(
            event.payload,
            {
                "message": "Execution processing started.",
            },
        )

    def test_event_reference_is_persisted(self):
        event = self.record_event(
            provider_reference="PROVIDER-001",
        )

        self.assertEqual(
            event.provider_reference,
            "PROVIDER-001",
        )

    # ------------------------------------------------------------------
    # Provider events
    # ------------------------------------------------------------------

    def test_provider_event_requires_provider_event_id(self):
        with self.assertRaises(ValidationError):
            self.record_event(
                event_type=(
                    PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
                ),
                source=PaymentExecutionEvent.Source.PROVIDER,
            )

    def test_webhook_event_requires_provider_event_id(self):
        with self.assertRaises(ValidationError):
            self.record_event(
                event_type=(
                    PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
                ),
                source=PaymentExecutionEvent.Source.WEBHOOK,
            )

    def test_provider_event_with_provider_event_id_is_allowed(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_ACCEPTED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-001",
            provider_reference="provider-ref-001",
        )

        self.assertEqual(
            event.provider_event_id,
            "provider-event-001",
        )
        self.assertEqual(
            event.provider_reference,
            "provider-ref-001",
        )

    def test_webhook_event_with_provider_event_id_is_allowed(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_PENDING
            ),
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id="webhook-event-001",
            provider_reference="provider-ref-002",
        )

        self.assertEqual(
            event.provider_event_id,
            "webhook-event-001",
        )

    # ------------------------------------------------------------------
    # Non-provider events
    # ------------------------------------------------------------------

    def test_system_event_does_not_require_provider_event_id(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.CREATED
            ),
            source=PaymentExecutionEvent.Source.SYSTEM,
        )

        self.assertIsNone(
            event.provider_event_id,
        )

    def test_reconciliation_event_does_not_require_provider_event_id(
        self,
    ):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.RECONCILIATION_REQUIRED
            ),
            source=PaymentExecutionEvent.Source.RECONCILIATION,
        )

        self.assertIsNone(
            event.provider_event_id,
        )

    def test_banking_event_does_not_require_provider_event_id(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.RECONCILED
            ),
            source=PaymentExecutionEvent.Source.BANKING,
        )

        self.assertIsNone(
            event.provider_event_id,
        )

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_same_provider_event_id_returns_existing_event(self):
        first = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-002",
            provider_reference="provider-ref-003",
        )

        second = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-002",
            provider_reference="provider-ref-003",
            payload={
                "different": "payload",
            },
        )

        self.assertEqual(
            first.id,
            second.id,
        )

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
                provider_event_id="provider-event-002",
            ).count(),
            1,
        )

    def test_same_provider_event_id_with_different_event_type_is_rejected(
        self,
    ):
        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-003",
            provider_reference="provider-ref-004",
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                event_type=(
                    PaymentExecutionEvent.EventType.PROVIDER_FAILED
                ),
                source=PaymentExecutionEvent.Source.PROVIDER,
                provider_event_id="provider-event-003",
                provider_reference="provider-ref-004",
            )

    def test_same_provider_event_id_with_different_source_is_rejected(
        self,
    ):
        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-004",
            provider_reference="provider-ref-005",
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                event_type=(
                    PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
                ),
                source=PaymentExecutionEvent.Source.WEBHOOK,
                provider_event_id="provider-event-004",
                provider_reference="provider-ref-005",
            )

    def test_same_provider_event_id_with_different_reference_is_rejected(
        self,
    ):
        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-005",
            provider_reference="provider-ref-006",
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                event_type=(
                    PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
                ),
                source=PaymentExecutionEvent.Source.PROVIDER,
                provider_event_id="provider-event-005",
                provider_reference="provider-ref-007",
            )

    # ------------------------------------------------------------------
    # Multiple events
    # ------------------------------------------------------------------

    def test_different_provider_event_ids_create_different_events(self):
        first = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_ACCEPTED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-006",
        )

        second = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-007",
        )

        self.assertNotEqual(
            first.id,
            second.id,
        )

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
            ).count(),
            2,
        )

    def test_events_are_scoped_to_execution(self):
        second_execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="event-execution-002",
        )

        first = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-008",
        )

        second = PaymentExecutionEventService.record_event(
            execution=second_execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-008",
        )

        self.assertNotEqual(
            first.id,
            second.id,
        )

        self.assertEqual(
            first.execution_id,
            self.execution.id,
        )

        self.assertEqual(
            second.execution_id,
            second_execution.id,
        )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    def test_occurred_at_is_generated_when_not_provided(self):
        before = timezone.now()

        event = self.record_event()

        after = timezone.now()

        self.assertIsNotNone(
            event.occurred_at,
        )
        self.assertGreaterEqual(
            event.occurred_at,
            before,
        )
        self.assertLessEqual(
            event.occurred_at,
            after,
        )

    def test_received_at_is_generated_when_not_provided(self):
        before = timezone.now()

        event = self.record_event()

        after = timezone.now()

        self.assertIsNotNone(
            event.received_at,
        )
        self.assertGreaterEqual(
            event.received_at,
            before,
        )
        self.assertLessEqual(
            event.received_at,
            after,
        )

    def test_explicit_occurred_at_is_preserved(self):
        occurred_at = timezone.now() - timedelta(minutes=5)

        event = self.record_event(
            occurred_at=occurred_at,
        )

        self.assertEqual(
            event.occurred_at,
            occurred_at,
        )

    def test_explicit_received_at_is_preserved(self):
        received_at = timezone.now() - timedelta(minutes=2)

        event = self.record_event(
            received_at=received_at,
        )

        self.assertEqual(
            event.received_at,
            received_at,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_execution_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionEventService.record_event(
                execution=None,
                event_type=(
                    PaymentExecutionEvent.EventType.CREATED
                ),
                source=PaymentExecutionEvent.Source.SYSTEM,
            )

    def test_invalid_execution_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionEventService.record_event(
                execution="invalid",
                event_type=(
                    PaymentExecutionEvent.EventType.CREATED
                ),
                source=PaymentExecutionEvent.Source.SYSTEM,
            )

    def test_event_type_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionEventService.record_event(
                execution=self.execution,
                event_type="",
                source=PaymentExecutionEvent.Source.SYSTEM,
            )

    def test_source_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionEventService.record_event(
                execution=self.execution,
                event_type=(
                    PaymentExecutionEvent.EventType.CREATED
                ),
                source="",
            )

    # ------------------------------------------------------------------
    # Lifecycle boundaries
    # ------------------------------------------------------------------

    def test_recording_event_does_not_change_execution_status(self):
        original_status = self.execution.status

        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-009",
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

    def test_recording_event_does_not_change_payment_status(self):
        original_status = self.payment.status

        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-010",
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_provider_completed_event_does_not_complete_execution(
        self,
    ):
        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-011",
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

    def test_provider_failed_event_does_not_fail_execution(self):
        self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_FAILED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-012",
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.CREATED,
        )

    # ------------------------------------------------------------------
    # Provider references
    # ------------------------------------------------------------------

    def test_provider_reference_can_be_blank(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_ACCEPTED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-013",
        )

        self.assertEqual(
            event.provider_reference,
            "",
        )

    def test_provider_reference_is_preserved(self):
        event = self.record_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id="provider-event-014",
            provider_reference="FLW-123456",
        )

        self.assertEqual(
            event.provider_reference,
            "FLW-123456",
        )