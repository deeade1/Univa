from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)
from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)
from payment.canonical.services.reconciliation_evidence import (
    ReconciliationEvidenceCollector,
)


class ReconciliationEvidenceCollectorContractTests(TestCase):
    """
    Contract tests for collecting reconciliation evidence.

    The collector must:
        - accept a persisted PaymentExecution
        - collect supported PaymentExecutionEvent evidence
        - return ReconciliationEvidence objects

    It must NOT:
        - mutate the execution
        - mutate the payment
        - mutate events
        - create events
        - reconcile
        - transition lifecycle state
    """

    provider = "test_provider"

    def setUp(self):
        self.user = self._create_user()

        self.payment = Payment.objects.create(
            reference="PAY-RECON-EVIDENCE-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-recon-001",
            source_reference="EARN-RECON-001",
            beneficiary=self.user,
            amount=Decimal("2500.00"),
            currency="NGN",
            idempotency_key="pay-recon-evidence-idem-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-RECON-EVIDENCE-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="exec-recon-evidence-idem-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

    @staticmethod
    def _create_user():
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="reconciliation-evidence@example.com",
            password="test-password",
        )

    def create_event(
        self,
        *,
        event_type,
        provider_event_id="evt-recon-001",
        provider_reference="provider-recon-001",
        payload=None,
        occurred_at=None,
    ):
        occurred_at = occurred_at or timezone.now()
        received_at = occurred_at

        return PaymentExecutionEvent.objects.create(
            execution=self.execution,
            event_type=event_type,
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id=provider_event_id,
            provider_reference=provider_reference,
            payload=payload or {
                "event": "payment.completed",
            },
            occurred_at=occurred_at,
            received_at=received_at,
        )


class ReconciliationEvidenceCollectorValidationTests(
    ReconciliationEvidenceCollectorContractTests,
):
    def test_non_execution_object_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEvidenceCollector.collect(
                execution=object(),
            )

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEvidenceCollector.collect(
                execution=None,
            )

    def test_unsaved_execution_is_rejected(self):
        execution = PaymentExecution(
            reference="EXEC-UNSAVED",
            payment=self.payment,
            attempt_number=2,
            idempotency_key="exec-unsaved-idem",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

        with self.assertRaises(ValidationError):
            ReconciliationEvidenceCollector.collect(
                execution=execution,
            )


class ReconciliationEvidenceCollectorCollectionTests(
    ReconciliationEvidenceCollectorContractTests,
):
    def test_completed_event_becomes_evidence(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertIsInstance(
            evidence[0],
            ReconciliationEvidence,
        )
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_processing_event_becomes_evidence(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROCESSING,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.PROCESSING,
        )

    def test_pending_event_becomes_evidence(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_PENDING,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.PENDING,
        )

    def test_failed_event_becomes_evidence(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_FAILED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.FAILED,
        )

    def test_cancelled_event_becomes_evidence(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_CANCELLED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.CANCELLED,
        )

    def test_multiple_supported_events_produce_multiple_evidence_records(
        self,
    ):
        first = timezone.now()
        second = first + timezone.timedelta(seconds=1)

        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROCESSING,
            provider_event_id="evt-processing",
            occurred_at=first,
        )

        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            provider_event_id="evt-completed",
            occurred_at=second,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 2)

        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.PROCESSING,
        )

        self.assertEqual(
            evidence[1].status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_events_from_another_execution_are_not_collected(self):
        other_payment = Payment.objects.create(
            reference="PAY-RECON-EVIDENCE-002",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-recon-002",
            source_reference="EARN-RECON-002",
            beneficiary=self.user,
            amount=Decimal("3000.00"),
            currency="NGN",
            idempotency_key="pay-recon-evidence-idem-002",
        )

        other_execution = PaymentExecution.objects.create(
            reference="EXEC-RECON-EVIDENCE-002",
            payment=other_payment,
            attempt_number=1,
            idempotency_key="exec-recon-evidence-idem-002",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            provider_event_id="evt-own",
        )

        PaymentExecutionEvent.objects.create(
            execution=other_execution,
            event_type=PaymentExecutionEvent.EventType.PROVIDER_FAILED,
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id="evt-other",
            provider_reference="provider-other",
            payload={"event": "payment.failed"},
            occurred_at=timezone.now(),
            received_at=timezone.now(),
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].status,
            PaymentExecution.Status.COMPLETED,
        )


class ReconciliationEvidenceCollectorFilteringTests(
    ReconciliationEvidenceCollectorContractTests,
):
    def test_created_event_is_not_collected(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.CREATED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(evidence, [])

    def test_provider_accepted_event_is_not_collected(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_ACCEPTED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(evidence, [])

    def test_reconciliation_required_event_is_not_collected(self):
        self.create_event(
            event_type=(
                PaymentExecutionEvent.EventType.RECONCILIATION_REQUIRED
            ),
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(evidence, [])

    def test_reconciled_event_is_not_collected(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.RECONCILED,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(evidence, [])


class ReconciliationEvidenceCollectorFieldTests(
    ReconciliationEvidenceCollectorContractTests,
):
    def test_event_evidence_fields_are_preserved(self):
        payload = {
            "transaction_id": "trx-collector-001",
            "provider_status": "successful",
        }

        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
            provider_event_id="evt-field-001",
            provider_reference="provider-field-001",
            payload=payload,
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)

        item = evidence[0]

        self.assertEqual(
            item.source,
            PaymentExecutionEvent.Source.WEBHOOK,
        )

        self.assertEqual(
            item.amount,
            self.payment.amount,
        )

        self.assertEqual(
            item.currency,
            self.payment.currency,
        )

        self.assertEqual(
            item.reference,
            "provider-field-001",
        )

        self.assertEqual(
            item.external_event_id,
            "evt-field-001",
        )

        self.assertEqual(
            item.metadata,
            payload,
        )


class ReconciliationEvidenceCollectorSideEffectTests(
    ReconciliationEvidenceCollectorContractTests,
):
    def test_collector_does_not_mutate_execution(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        original_status = self.execution.status
        original_id = self.execution.id

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

        self.assertEqual(
            self.execution.id,
            original_id,
        )

    def test_collector_does_not_mutate_payment(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        original_status = self.payment.status
        original_amount = self.payment.amount

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

        self.assertEqual(
            self.payment.amount,
            original_amount,
        )

    def test_collector_does_not_mutate_events(self):
        event = self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        original_event_type = event.event_type
        original_source = event.source
        original_payload = dict(event.payload)

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

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

    def test_collector_does_not_create_events(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        before_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        after_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        self.assertEqual(
            before_count,
            after_count,
        )

    def test_collector_does_not_reconcile(self):
        self.create_event(
            event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.execution.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.PROCESSING,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )