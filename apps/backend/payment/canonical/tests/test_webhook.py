# payment/canonical/tests/test_webhook.py

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
    PaymentInstrument,
)
from payment.canonical.services.execution_event import (
    PaymentExecutionEventService,
)
from payment.canonical.services.webhook import (
    WebhookIngestionResult,
    WebhookPayload,
)


class WebhookContractTestCase(TestCase):
    """
    Contract tests for the canonical webhook ingestion boundary.

    These tests intentionally verify the webhook contract before the
    WebhookIngestionService implementation exists.

    Webhook ingestion owns:
        - payload validation
        - canonical status validation
        - provider identity validation
        - evidence construction
        - event creation through PaymentExecutionEventService
        - duplicate detection

    Webhook ingestion does NOT own:
        - PaymentExecution lifecycle transitions
        - Payment lifecycle transitions
        - reconciliation
        - retries
        - provider communication
        - Banking
    """

    provider = "test_provider"
    provider_event_id = "evt_123456"
    provider_reference = "provider_ref_123"

    def setUp(self):
        self.user = self._create_user()

        self.payment = Payment.objects.create(
            reference="PAY-WEBHOOK-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-001",
            source_reference="EARN-001",
            beneficiary=self.user,
            amount=Decimal("2500.00"),
            currency="NGN",
            idempotency_key="pay-webhook-idem-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-WEBHOOK-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="exec-webhook-idem-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider=self.provider,
            status=PaymentExecution.Status.PROCESSING,
        )

        self.occurred_at = timezone.now() - timedelta(minutes=5)

    def _create_user(self):
        User = self._get_user_model()

        return User.objects.create_user(
            email="webhook-test@example.com",
            password="test-password",
        )

    @staticmethod
    def _get_user_model():
        from django.contrib.auth import get_user_model

        return get_user_model()

    def make_payload(
        self,
        *,
        provider=None,
        provider_event_id=None,
        provider_reference=None,
        status=None,
        amount=None,
        currency=None,
        occurred_at=None,
        payload=None,
    ):
        return WebhookPayload(
            provider=(
                self.provider
                if provider is None
                else provider
            ),
            provider_event_id=(
                self.provider_event_id
                if provider_event_id is None
                else provider_event_id
            ),
            provider_reference=(
                self.provider_reference
                if provider_reference is None
                else provider_reference
            ),
            status=(
                PaymentExecution.Status.COMPLETED
                if status is None
                else status
            ),
            amount=(
                self.payment.amount
                if amount is None
                else amount
            ),
            currency=(
                self.payment.currency
                if currency is None
                else currency
            ),
            occurred_at=(
                self.occurred_at
                if occurred_at is None
                else occurred_at
            ),
            payload=(
                {"event": "payment.completed"}
                if payload is None
                else payload
            ),
        )


class WebhookPayloadContractTests(TestCase):
    """
    Tests for the immutable WebhookPayload contract itself.
    """

    def test_payload_accepts_canonical_fields(self):
        occurred_at = timezone.now()

        payload = WebhookPayload(
            provider="test_provider",
            provider_event_id="evt_001",
            provider_reference="ref_001",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("100.00"),
            currency="NGN",
            occurred_at=occurred_at,
            payload={"status": "success"},
        )

        self.assertEqual(payload.provider, "test_provider")
        self.assertEqual(payload.provider_event_id, "evt_001")
        self.assertEqual(payload.provider_reference, "ref_001")
        self.assertEqual(
            payload.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertEqual(payload.amount, Decimal("100.00"))
        self.assertEqual(payload.currency, "NGN")
        self.assertEqual(payload.occurred_at, occurred_at)
        self.assertEqual(
            payload.payload,
            {"status": "success"},
        )

    def test_payload_defaults_payload_to_empty_mapping(self):
        payload = WebhookPayload(
            provider="test_provider",
            provider_event_id="evt_001",
            provider_reference="ref_001",
            status=PaymentExecution.Status.PENDING,
            amount=Decimal("100.00"),
            currency="NGN",
            occurred_at=timezone.now(),
        )

        self.assertEqual(payload.payload, {})

    def test_payload_is_frozen(self):
        payload = WebhookPayload(
            provider="test_provider",
            provider_event_id="evt_001",
            provider_reference="ref_001",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("100.00"),
            currency="NGN",
            occurred_at=timezone.now(),
        )

        with self.assertRaises(AttributeError):
            payload.status = PaymentExecution.Status.FAILED


class WebhookIngestionResultContractTests(TestCase):
    """
    Tests for the immutable WebhookIngestionResult contract.
    """

    def test_accepted_outcome(self):
        self.assertEqual(
            WebhookIngestionResult.Outcome.ACCEPTED,
            "accepted",
        )

    def test_duplicate_outcome(self):
        self.assertEqual(
            WebhookIngestionResult.Outcome.DUPLICATE,
            "duplicate",
        )

    def test_is_accepted(self):
        result = WebhookIngestionResult(
            outcome=WebhookIngestionResult.Outcome.ACCEPTED,
            execution=None,
            event=None,
            evidence=None,
        )

        self.assertTrue(result.is_accepted)
        self.assertFalse(result.is_duplicate)

    def test_is_duplicate(self):
        result = WebhookIngestionResult(
            outcome=WebhookIngestionResult.Outcome.DUPLICATE,
            execution=None,
            event=None,
            evidence=None,
        )

        self.assertTrue(result.is_duplicate)
        self.assertFalse(result.is_accepted)

    def test_result_is_frozen(self):
        result = WebhookIngestionResult(
            outcome=WebhookIngestionResult.Outcome.ACCEPTED,
            execution=None,
            event=None,
            evidence=None,
        )

        with self.assertRaises(AttributeError):
            result.outcome = WebhookIngestionResult.Outcome.DUPLICATE


class WebhookIngestionBehaviorTests(WebhookContractTestCase):
    """
    Behavioral contract tests.

    These tests are intentionally written against the agreed public
    WebhookIngestionService contract.
    """

    def _ingest(self, payload):
        from payment.canonical.services.webhook import (
            WebhookIngestionService,
        )

        return WebhookIngestionService.ingest(
            execution=self.execution,
            payload=payload,
        )

    def test_valid_completed_webhook_is_accepted(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.COMPLETED,
            )
        )

        self.assertTrue(result.is_accepted)
        self.assertFalse(result.is_duplicate)

    def test_valid_pending_webhook_is_accepted(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.PENDING,
            )
        )

        self.assertTrue(result.is_accepted)

    def test_valid_failed_webhook_is_accepted(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.FAILED,
            )
        )

        self.assertTrue(result.is_accepted)

    def test_valid_cancelled_webhook_is_accepted(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.CANCELLED,
            )
        )

        self.assertTrue(result.is_accepted)

    def test_valid_processing_webhook_is_accepted(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.PROCESSING,
            )
        )

        self.assertTrue(result.is_accepted)

    def test_event_source_is_webhook(self):
        result = self._ingest(self.make_payload())

        self.assertEqual(
            result.event.source,
            PaymentExecutionEvent.Source.WEBHOOK,
        )

    def test_completed_status_maps_to_provider_completed_event(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.COMPLETED,
            )
        )

        self.assertEqual(
            result.event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_COMPLETED,
        )

    def test_pending_status_maps_to_provider_pending_event(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.PENDING,
            )
        )

        self.assertEqual(
            result.event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_PENDING,
        )

    def test_failed_status_maps_to_provider_failed_event(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.FAILED,
            )
        )

        self.assertEqual(
            result.event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_FAILED,
        )

    def test_cancelled_status_maps_to_provider_cancelled_event(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.CANCELLED,
            )
        )

        self.assertEqual(
            result.event.event_type,
            PaymentExecutionEvent.EventType.PROVIDER_CANCELLED,
        )

    def test_processing_status_maps_to_processing_event(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.PROCESSING,
            )
        )

        self.assertEqual(
            result.event.event_type,
            PaymentExecutionEvent.EventType.PROCESSING,
        )

    def test_provider_event_id_is_persisted(self):
        result = self._ingest(self.make_payload())

        self.assertEqual(
            result.event.provider_event_id,
            self.provider_event_id,
        )

    def test_provider_reference_is_persisted(self):
        result = self._ingest(self.make_payload())

        self.assertEqual(
            result.event.provider_reference,
            self.provider_reference,
        )

    def test_webhook_payload_is_persisted(self):
        payload = {
            "event": "payment.completed",
            "transaction_id": "trx_123",
            "channel": "bank_transfer",
        }

        result = self._ingest(
            self.make_payload(payload=payload)
        )

        self.assertEqual(result.event.payload, payload)

    def test_occurred_at_is_preserved(self):
        result = self._ingest(self.make_payload())

        self.assertEqual(
            result.event.occurred_at,
            self.occurred_at,
        )

    def test_provider_is_required(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(provider="")
            )

    def test_provider_must_match_execution_provider(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    provider="different_provider"
                )
            )

    def test_provider_event_id_is_required(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    provider_event_id=""
                )
            )

    def test_provider_reference_is_required(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    provider_reference=""
                )
            )

    def test_unsupported_status_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    status="successful"
                )
            )

    def test_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    amount=Decimal("0")
                )
            )

    def test_amount_must_match_payment(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    amount=Decimal("2500.01")
                )
            )

    def test_currency_must_match_payment(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    currency="USD"
                )
            )

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    currency="N"
                )
            )

    def test_occurred_at_must_be_datetime(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    occurred_at="2026-10-01T12:00:00Z"
                )
            )

    def test_duplicate_provider_event_returns_duplicate(self):
        payload = self.make_payload()

        first = self._ingest(payload)
        second = self._ingest(payload)

        self.assertTrue(first.is_accepted)
        self.assertTrue(second.is_duplicate)

    def test_duplicate_does_not_create_another_event(self):
        payload = self.make_payload()

        self._ingest(payload)
        self._ingest(payload)

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
                provider_event_id=self.provider_event_id,
            ).count(),
            1,
        )

    def test_duplicate_returns_existing_event(self):
        payload = self.make_payload()

        first = self._ingest(payload)
        second = self._ingest(payload)

        self.assertEqual(
            first.event.id,
            second.event.id,
        )

    def test_duplicate_does_not_mutate_execution(self):
        payload = self.make_payload()

        self._ingest(payload)

        self.execution.refresh_from_db()

        original_status = self.execution.status

        self._ingest(payload)

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

    def test_ingestion_does_not_mutate_execution_status(self):
        original_status = self.execution.status

        self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.COMPLETED
            )
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )

    def test_ingestion_does_not_mutate_payment_status(self):
        original_status = self.payment.status

        self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.COMPLETED
            )
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_ingestion_creates_one_event(self):
        self._ingest(self.make_payload())

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
            ).count(),
            1,
        )

    def test_invalid_webhook_creates_no_event(self):
        with self.assertRaises(ValidationError):
            self._ingest(
                self.make_payload(
                    amount=Decimal("9999.00")
                )
            )

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
            ).count(),
            0,
        )

    def test_provider_event_id_is_idempotency_boundary(self):
        first_payload = self.make_payload(
            provider_event_id="evt_same",
            provider_reference="ref_one",
        )

        second_payload = self.make_payload(
            provider_event_id="evt_same",
            provider_reference="ref_two",
        )

        first = self._ingest(first_payload)

        with self.assertRaises(ValidationError):
            self._ingest(second_payload)

        self.assertEqual(
            PaymentExecutionEvent.objects.filter(
                execution=self.execution,
                provider_event_id="evt_same",
            ).count(),
            1,
        )

        self.assertEqual(
            first.event.provider_reference,
            "ref_one",
        )

    def test_result_contains_execution(self):
        result = self._ingest(self.make_payload())

        self.assertEqual(
            result.execution.id,
            self.execution.id,
        )

    def test_result_contains_event(self):
        result = self._ingest(self.make_payload())

        self.assertIsNotNone(result.event)
        self.assertEqual(
            result.event.execution_id,
            self.execution.id,
        )

    def test_result_contains_reconciliation_evidence(self):
        result = self._ingest(
            self.make_payload(
                status=PaymentExecution.Status.COMPLETED,
            )
        )

        self.assertIsNotNone(result.evidence)
        self.assertEqual(
            result.evidence.source,
            "WEBHOOK",
        )
        self.assertEqual(
            result.evidence.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertEqual(
            result.evidence.amount,
            self.payment.amount,
        )
        self.assertEqual(
            result.evidence.currency,
            self.payment.currency,
        )
        self.assertEqual(
            result.evidence.reference,
            self.provider_reference,
        )
        self.assertEqual(
            result.evidence.external_event_id,
            self.provider_event_id,
        )

    def test_ingestion_does_not_invoke_reconciliation(self):
        """
        Webhook ingestion ends at evidence/event creation.

        Reconciliation is a separate architectural layer.
        """
        result = self._ingest(self.make_payload())

        self.assertIsNotNone(result.event)
        self.assertIsNotNone(result.evidence)

        self.assertEqual(
            self.execution.status,
            PaymentExecution.Status.PROCESSING,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )