from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.execution import PaymentExecutionService
from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
    ReconciliationResult,
    ReconciliationService,
)


class ReconciliationServiceTests(TestCase):

    def setUp(self):
        self.user = self.create_user()

        self.payment = Payment.objects.create(
            reference="PAY-RECON-001",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="CHECKOUT-RECON-001",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="PAY-RECON-IDEMPOTENCY-001",
        )

        self.execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="PEXEC-RECON-IDEMPOTENCY-001",
        )

    def create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="reconciliation@example.com",
            password="test-password",
        )

    def evidence(
        self,
        *,
        source=ReconciliationService.Source.PROVIDER,
        status=ReconciliationService.Outcome.COMPLETED,
        amount=Decimal("1000.00"),
        currency="NGN",
        reference="PROVIDER-001",
        external_event_id="EVENT-001",
        metadata=None,
    ):
        return ReconciliationEvidence(
            source=source,
            status=status,
            amount=amount,
            currency=currency,
            reference=reference,
            external_event_id=external_event_id,
            metadata=metadata or {},
        )

    def test_completed_evidence_is_reconciled(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.COMPLETED
                )
            ],
        )

        self.assertIsInstance(
            result,
            ReconciliationResult,
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.COMPLETED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

        self.assertTrue(result.is_reconciled)
        self.assertFalse(result.requires_reconciliation)
        self.assertFalse(result.is_conflict)

    def test_failed_evidence_is_reconciled(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.FAILED
                )
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.FAILED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

    def test_cancelled_evidence_is_reconciled(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.CANCELLED
                )
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.CANCELLED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

    def test_pending_evidence_requires_reconciliation(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.PENDING
                )
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.PENDING,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

        self.assertTrue(result.requires_reconciliation)
        self.assertFalse(result.is_reconciled)

    def test_provider_and_banking_completed_evidence_agree(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.COMPLETED,
                    reference="PROVIDER-001",
                    external_event_id="PROVIDER-EVENT-001",
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.COMPLETED,
                    reference="BANK-001",
                    external_event_id="BANK-EVENT-001",
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.COMPLETED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

        self.assertEqual(
            result.evidence_count,
            2,
        )

    def test_provider_and_banking_failed_evidence_agree(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.FAILED,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.FAILED,
                    reference="BANK-FAILED-001",
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.FAILED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

    def test_conflicting_provider_and_banking_evidence_requires_reconciliation(
        self,
    ):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.FAILED,
                    reference="BANK-FAILED-001",
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.CONFLICT,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

        self.assertTrue(result.is_conflict)
        self.assertTrue(result.requires_reconciliation)
        self.assertFalse(result.is_reconciled)

    def test_pending_and_completed_evidence_resolves_to_completed(self):
        """
        Terminal evidence overrides non-terminal evidence:
        a PROVIDER PENDING alongside a BANKING COMPLETED
        resolves to COMPLETED, not CONFLICT.
        """

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.PENDING,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.COMPLETED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

        self.assertFalse(result.is_conflict)

    def test_pending_and_failed_evidence_resolves_to_failed(self):
        """
        Terminal evidence overrides non-terminal evidence:
        a PROVIDER PENDING alongside a BANKING FAILED
        resolves to FAILED, not CONFLICT.
        """

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.PENDING,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.FAILED,
                    reference="BANK-FAILED-PENDING-001",
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.FAILED,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.RECONCILED,
        )

        self.assertFalse(result.is_conflict)

    def test_two_different_terminal_evidence_is_conflict(self):
        """
        Two different terminal statuses from independent
        authoritative sources are a genuine conflict.
        """

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.FAILED,
                    reference="BANK-FAILED-002",
                ),
            ],
        )

        self.assertEqual(
            result.outcome,
            ReconciliationService.Outcome.CONFLICT,
        )

        self.assertEqual(
            result.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

        self.assertTrue(result.is_conflict)
        self.assertTrue(result.requires_reconciliation)
        self.assertFalse(result.is_reconciled)

    def test_amount_mismatch_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [
                    self.evidence(
                        amount=Decimal("999.00"),
                    )
                ],
            )

    def test_currency_mismatch_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [
                    self.evidence(
                        currency="USD",
                    )
                ],
            )

    def test_empty_evidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [],
            )

    def test_invalid_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                object(),
                [
                    self.evidence(),
                ],
            )

    def test_invalid_evidence_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [object()],
            )

    def test_invalid_evidence_source_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [
                    self.evidence(
                        source="unknown_source",
                    )
                ],
            )

    def test_invalid_evidence_status_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.reconcile(
                self.execution,
                [
                    self.evidence(
                        status="not_a_real_status",
                    )
                ],
            )

    def test_evidence_currency_is_normalized(self):
        evidence = self.evidence(
            currency="ngn",
        )

        self.assertEqual(
            evidence.currency,
            "NGN",
        )

    def test_reconciliation_does_not_mutate_execution(self):
        original_status = self.execution.status
        original_reconciliation_state = (
            self.execution.reconciliation_state
        )

        ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.COMPLETED,
                )
            ],
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

    def test_result_contains_evidence_sources(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    reference="BANK-001",
                ),
            ],
        )

        self.assertEqual(
            result.metadata["sources"],
            [
                ReconciliationService.Source.BANKING,
                ReconciliationService.Source.PROVIDER,
            ],
        )

    def test_result_contains_evidence_statuses(self):
        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
            ],
        )

        self.assertEqual(
            result.metadata["statuses"],
            [
                ReconciliationService.Outcome.COMPLETED,
            ],
        )

    def test_completed_result_uses_execution_lifecycle(self):
        self.execution.status = PaymentExecution.Status.PROCESSING
        self.execution.save(
            update_fields=["status"]
        )

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.COMPLETED,
                )
            ],
        )

        execution = ReconciliationService.apply_result(
            self.execution,
            result,
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.COMPLETED,
        )

        self.assertIsNotNone(
            execution.completed_at,
        )

    def test_failed_result_uses_execution_lifecycle(self):
        self.execution.status = PaymentExecution.Status.PROCESSING
        self.execution.save(
            update_fields=["status"]
        )

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.FAILED,
                )
            ],
        )

        execution = ReconciliationService.apply_result(
            self.execution,
            result,
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.FAILED,
        )

        self.assertIsNotNone(
            execution.failed_at,
        )

        self.assertEqual(
            execution.failure_reason,
            result.reason,
        )

    def test_cancelled_result_uses_execution_lifecycle(self):
        self.execution.status = PaymentExecution.Status.PROCESSING
        self.execution.save(
            update_fields=["status"]
        )

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.CANCELLED,
                )
            ],
        )

        execution = ReconciliationService.apply_result(
            self.execution,
            result,
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CANCELLED,
        )

        self.assertIsNotNone(
            execution.cancelled_at,
        )

    def test_pending_result_does_not_terminalize_execution(self):
        self.execution.status = PaymentExecution.Status.PENDING
        self.execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        self.execution.save(
            update_fields=[
                "status",
                "reconciliation_state",
            ]
        )

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    status=ReconciliationService.Outcome.PENDING,
                )
            ],
        )

        execution = ReconciliationService.apply_result(
            self.execution,
            result,
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        self.assertEqual(
            execution.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

    def test_conflict_does_not_terminalize_execution(self):
        self.execution.status = PaymentExecution.Status.PENDING
        self.execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        self.execution.save(
            update_fields=[
                "status",
                "reconciliation_state",
            ]
        )

        result = ReconciliationService.reconcile(
            self.execution,
            [
                self.evidence(
                    source=ReconciliationService.Source.PROVIDER,
                    status=ReconciliationService.Outcome.COMPLETED,
                ),
                self.evidence(
                    source=ReconciliationService.Source.BANKING,
                    status=ReconciliationService.Outcome.FAILED,
                    reference="BANK-CONFLICT-001",
                ),
            ],
        )

        self.assertTrue(
            result.is_conflict
        )

        execution = ReconciliationService.apply_result(
            self.execution,
            result,
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        self.assertEqual(
            execution.reconciliation_state,
            PaymentExecution.ReconciliationState.REQUIRED,
        )

    def test_invalid_result_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationService.apply_result(
                self.execution,
                object(),
            )

    def test_completed_result_must_be_reconciled(self):
        result = ReconciliationResult(
            outcome=ReconciliationService.Outcome.COMPLETED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
            reason="Completion is not yet fully established.",
            evidence_count=1,
        )

        with self.assertRaises(ValidationError):
            ReconciliationService.apply_result(
                self.execution,
                result,
            )

    def test_failed_result_must_be_reconciled(self):
        result = ReconciliationResult(
            outcome=ReconciliationService.Outcome.FAILED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
            reason="Failure remains unresolved.",
            evidence_count=1,
        )

        with self.assertRaises(ValidationError):
            ReconciliationService.apply_result(
                self.execution,
                result,
            )

    def test_cancelled_result_must_be_reconciled(self):
        result = ReconciliationResult(
            outcome=ReconciliationService.Outcome.CANCELLED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
            reason="Cancellation remains unresolved.",
            evidence_count=1,
        )

        with self.assertRaises(ValidationError):
            ReconciliationService.apply_result(
                self.execution,
                result,
            )