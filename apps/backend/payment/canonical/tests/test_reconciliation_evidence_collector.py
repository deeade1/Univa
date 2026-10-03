"""
Tests for the ReconciliationEvidenceCollector.

Architectural boundary
----------------------

The collector combines reconciliation evidence from sources that have
already been resolved and translated into ReconciliationEvidence.

The collector is responsible for:

    - validating the PaymentExecution
    - collecting persisted PaymentExecutionEvent evidence
    - accepting additional ReconciliationEvidence
    - returning the combined evidence

The collector must NOT:

    - resolve Banking transactions
    - query Banking
    - call providers
    - reconcile evidence
    - mutate PaymentExecution
    - mutate Payment
    - create PaymentExecutionEvent records
    - perform lifecycle transitions
"""


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

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)

from payment.canonical.services.reconciliation_evidence import (
    ReconciliationEvidenceCollector,
)


class ReconciliationEvidenceCollectorContractTests(TestCase):
    """
    Establish the contract for collecting reconciliation evidence.
    """

    provider = "test_provider"

    def setUp(self):
        self.user = User.objects.create_user(
            email="collector-test@example.com",
            password="test-password",
        )

        self.payment = Payment.objects.create(
            reference="PAY-COLLECTOR-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-collector-001",
            source_reference="EARN-COLLECTOR-001",
            beneficiary=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="pay-collector-idem-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-COLLECTOR-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="exec-collector-idem-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

        self.evidence = ReconciliationEvidence(
            source="BANKING",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("1000.00"),
            currency="NGN",
            reference="BANK-TRANSACTION-001",
            external_event_id="BANK-PROVIDER-001",
            metadata={
                "transaction_type": "TRANSFER",
            },
        )

    def create_event(
        self,
        *,
        event_type=PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        provider_event_id="collector-event-001",
        provider_reference="collector-provider-001",
    ):
        now = timezone.now()

        return PaymentExecutionEvent.objects.create(
            execution=self.execution,
            event_type=event_type,
            source=PaymentExecutionEvent.Source.WEBHOOK,
            provider_event_id=provider_event_id,
            provider_reference=provider_reference,
            payload={
                "event": "payment.completed",
            },
            occurred_at=now,
            received_at=now,
        )

    def test_collect_without_additional_evidence_returns_event_evidence(self):
        event = self.create_event()

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].external_event_id,
            event.provider_event_id,
        )

    def test_collect_accepts_additional_evidence(self):
        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[self.evidence],
        )

        self.assertIn(
            self.evidence,
            evidence,
        )

    def test_collect_combines_event_and_additional_evidence(self):
        event = self.create_event()

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[self.evidence],
        )

        self.assertEqual(len(evidence), 2)

        self.assertEqual(
            evidence[0].external_event_id,
            event.provider_event_id,
        )

        self.assertEqual(
            evidence[1],
            self.evidence,
        )

    def test_collect_accepts_multiple_additional_evidence_items(self):
        first = self.evidence

        second = ReconciliationEvidence(
            source="BANKING",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("1000.00"),
            currency="NGN",
            reference="BANK-TRANSACTION-002",
            external_event_id="BANK-PROVIDER-002",
            metadata={
                "transaction_type": "TRANSFER",
            },
        )

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[
                first,
                second,
            ],
        )

        self.assertEqual(
            evidence,
            [
                first,
                second,
            ],
        )

    def test_none_additional_evidence_behaves_like_existing_contract(self):
        event = self.create_event()

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=None,
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].external_event_id,
            event.provider_event_id,
        )

    def test_empty_additional_evidence_behaves_like_existing_contract(self):
        event = self.create_event()

        evidence = ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[],
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            evidence[0].external_event_id,
            event.provider_event_id,
        )

    def test_invalid_additional_evidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationEvidenceCollector.collect(
                execution=self.execution,
                additional_evidence=[object()],
            )

    def test_non_execution_is_rejected(self):
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
            payment=self.payment,
            attempt_number=2,
            idempotency_key="exec-collector-unsaved-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
        )

        with self.assertRaises(ValidationError):
            ReconciliationEvidenceCollector.collect(
                execution=execution,
            )

    def test_collect_does_not_mutate_execution(self):
        self.create_event()

        original_status = self.execution.status
        original_reconciliation_state = (
            self.execution.reconciliation_state
        )

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[self.evidence],
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

        self.assertEqual(
            self.execution.reconciliation_state,
            original_reconciliation_state,
        )

    def test_collect_does_not_mutate_payment(self):
        self.create_event()

        original_status = self.payment.status

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[self.evidence],
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_collect_does_not_create_payment_execution_events(self):
        self.create_event()

        before_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        ReconciliationEvidenceCollector.collect(
            execution=self.execution,
            additional_evidence=[self.evidence],
        )

        after_count = PaymentExecutionEvent.objects.filter(
            execution=self.execution,
        ).count()

        self.assertEqual(
            before_count,
            after_count,
        )
