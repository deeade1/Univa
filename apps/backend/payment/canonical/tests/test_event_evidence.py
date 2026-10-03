from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)


class PaymentExecutionEventEvidenceAdapterContractTests(TestCase):
    """
    Contract tests for converting PaymentExecutionEvent into
    ReconciliationEvidence.

    The adapter must normalize persisted event data into evidence.

    It must NOT:
        - mutate the event
        - mutate the execution
        - mutate the payment
        - transition lifecycle state
        - perform reconciliation
        - create another event
    """

    provider = "test_provider"

    def setUp(self):
        self.user = self._create_user()

        self.payment = Payment.objects.create(
            reference="PAY-EVIDENCE-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-001",
            source_reference="EARN-001",
            beneficiary=self.user,
            amount=Decimal("2500.00"),
            currency="NGN",
            idempotency_key="pay-evidence-idem-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-EVIDENCE-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="exec-evidence-idem-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

    @staticmethod
    def _create_user():
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="evidence-test@example.com",
            password="test-password",
        )

    
    def create_event(
        self,
        *,
        event_type,
        provider_event_id="evt-evidence-001",
        provider_reference="provider-ref-001",
        payload=None,
    ):
        now = timezone.now()

        return PaymentExecutionEvent.objects.create(
            execution=self.execution,
            event_type=event_type,
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id=provider_event_id,
            provider_reference=provider_reference,
            payload=payload or {
                "event": "payment.completed",
            },
            occurred_at=now,
            received_at=now,
        )
    
    def adapter(self):
        from payment.canonical.services.event_evidence import (
            PaymentExecutionEventEvidenceAdapter,
        )

        return PaymentExecutionEventEvidenceAdapter


class EventToEvidenceMappingTests(
    PaymentExecutionEventEvidenceAdapterContractTests
):

    def test_processing_event_maps_to_processing_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROCESSING
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.PROCESSING,
        )

    def test_pending_event_maps_to_pending_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_PENDING
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.PENDING,
        )

    def test_completed_event_maps_to_completed_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_failed_event_maps_to_failed_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_FAILED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.FAILED,
        )

    def test_cancelled_event_maps_to_cancelled_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_CANCELLED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.CANCELLED,
        )

    def test_created_event_is_not_reconciliation_status_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.CREATED
        )

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)

    def test_provider_accepted_event_is_not_reconciliation_status_evidence(
        self,
    ):
        event = self.create_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_ACCEPTED
            )
        )

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)

    def test_reconciliation_required_event_is_not_status_evidence(self):
        event = self.create_event(
            event_type=(
                PaymentExecutionEvent.EventType.RECONCILIATION_REQUIRED
            )
        )

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)

    def test_reconciled_event_is_not_status_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.RECONCILED
        )

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)


class EventEvidenceFieldMappingTests(
    PaymentExecutionEventEvidenceAdapterContractTests
):

    def test_source_is_preserved(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.source,
            PaymentExecutionEvent.Source.WEBHOOK,
        )

    def test_amount_comes_from_payment(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.amount,
            self.payment.amount,
        )

    def test_currency_comes_from_payment(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.currency,
            self.payment.currency,
        )

    def test_provider_reference_becomes_reference(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            provider_reference="provider-ref-999",
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.reference,
            "provider-ref-999",
        )

    def test_provider_event_id_becomes_external_event_id(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            provider_event_id="evt-999",
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.external_event_id,
            "evt-999",
        )

    def test_payload_becomes_metadata(self):
        payload = {
            "transaction_id": "trx-999",
            "channel": "bank_transfer",
            "provider_status": "successful",
        }

        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            payload=payload,
        )

        evidence = self.adapter().to_evidence(event)

        self.assertEqual(
            evidence.metadata,
            payload,
        )

    def test_result_is_reconciliation_evidence(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        evidence = self.adapter().to_evidence(event)

        self.assertIsInstance(
            evidence,
            ReconciliationEvidence,
        )


class EventEvidenceValidationTests(
    PaymentExecutionEventEvidenceAdapterContractTests
):

    def test_non_event_object_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(object())

    def test_none_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(None)

    def test_event_without_execution_is_rejected(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        event.execution = None

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)

    def test_event_with_missing_payment_is_rejected(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        event.execution.payment = None

        with self.assertRaises(ValidationError):
            self.adapter().to_evidence(event)


class EventEvidenceSideEffectTests(
    PaymentExecutionEventEvidenceAdapterContractTests
):

    def test_adapter_does_not_mutate_event(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        original_event_type = event.event_type
        original_source = event.source
        original_payload = dict(event.payload)

        self.adapter().to_evidence(event)

        event.refresh_from_db()

        self.assertEqual(
            event.event_type,
            original_event_type,
        )
        self.assertEqual(
            event.source,
            original_source,
        )
        self.assertEqual(
            event.payload,
            original_payload,
        )

    def test_adapter_does_not_mutate_execution(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        original_status = self.execution.status

        self.adapter().to_evidence(event)

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

    def test_adapter_does_not_mutate_payment(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        original_status = self.payment.status

        self.adapter().to_evidence(event)

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_adapter_does_not_create_another_event(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        before_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        self.adapter().to_evidence(event)

        after_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        self.assertEqual(
            before_count,
            after_count,
        )

    def test_adapter_does_not_reconcile(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )

        self.adapter().to_evidence(event)

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.PROCESSING,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )