from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from payment.canonical.models import Payment, PaymentExecution

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
    ReconciliationResult,
    ReconciliationService,
)
from payment.canonical.services.reconciliation_orchestrator import (
    ReconciliationOrchestrationResult,
    ReconciliationOrchestrator,
)


class ReconciliationOrchestrationResultTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="orchestrator-result@example.com",
        )

        self.payment = Payment.objects.create(
            reference="PAY-ORCH-RESULT-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-result-001",
            source_reference="EARNING-RESULT-001",
            beneficiary=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="orch-result-payment-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-ORCH-RESULT-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="orch-result-execution-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.COMPLETED,
        )

        self.evidence = ReconciliationEvidence(
            source="PROVIDER",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("1000.00"),
            currency="NGN",
            reference="PROVIDER-001",
            external_event_id="EVENT-001",
            metadata={"test": True},
        )

        self.reconciliation = ReconciliationResult(
            outcome=PaymentExecution.Status.COMPLETED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.RECONCILED
            ),
            reason="Reconciled successfully.",
            evidence_count=1,
            metadata={"sources": ["PROVIDER"]},
        )

    def test_result_is_immutable(self):
        result = ReconciliationOrchestrationResult(
            execution=self.execution,
            payment=self.payment,
            evidence=(self.evidence,),
            reconciliation=self.reconciliation,
        )

        with self.assertRaises(AttributeError):
            result.payment = self.payment

    def test_result_converts_evidence_to_tuple(self):
        result = ReconciliationOrchestrationResult(
            execution=self.execution,
            payment=self.payment,
            evidence=[self.evidence],
            reconciliation=self.reconciliation,
        )

        self.assertIsInstance(result.evidence, tuple)
        self.assertEqual(result.evidence, (self.evidence,))

    def test_is_reconciled_property(self):
        result = ReconciliationOrchestrationResult(
            execution=self.execution,
            payment=self.payment,
            evidence=(self.evidence,),
            reconciliation=self.reconciliation,
        )

        self.assertTrue(result.is_reconciled)

    def test_requires_reconciliation_property(self):
        reconciliation = ReconciliationResult(
            outcome=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
            reason="Evidence is incomplete.",
            evidence_count=1,
            metadata={},
        )

        result = ReconciliationOrchestrationResult(
            execution=self.execution,
            payment=self.payment,
            evidence=(self.evidence,),
            reconciliation=reconciliation,
        )

        self.assertTrue(result.requires_reconciliation)

    def test_is_conflict_property(self):
        reconciliation = ReconciliationResult(
            outcome=ReconciliationService.Outcome.CONFLICT,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
            reason="Evidence conflicts.",
            evidence_count=2,
            metadata={},
        )

        result = ReconciliationOrchestrationResult(
            execution=self.execution,
            payment=self.payment,
            evidence=(self.evidence,),
            reconciliation=reconciliation,
        )

        self.assertTrue(result.is_conflict)


class ReconciliationOrchestratorValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="orchestrator-validation@example.com",
        )

        self.payment = Payment.objects.create(
            reference="PAY-ORCH-VALIDATION-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-validation-001",
            beneficiary=self.user,
            amount=Decimal("500.00"),
            currency="NGN",
            idempotency_key="orch-validation-payment-001",
        )

    def test_non_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationOrchestrator.reconcile(
                execution=object(),
            )

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationOrchestrator.reconcile(
                execution=None,
            )

    def test_unsaved_execution_is_rejected(self):
        execution = PaymentExecution(
            payment=self.payment,
            attempt_number=1,
            idempotency_key="orch-validation-unsaved-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
        )

        with self.assertRaises(ValidationError):
            ReconciliationOrchestrator.reconcile(
                execution=execution,
            )


class ReconciliationOrchestratorFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="orchestrator-flow@example.com",
        )

        self.payment = Payment.objects.create(
            reference="PAY-ORCH-FLOW-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-flow-001",
            beneficiary=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="orch-flow-payment-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-ORCH-FLOW-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="orch-flow-execution-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.PROCESSING,
        )

        self.evidence = ReconciliationEvidence(
            source="PROVIDER",
            status=PaymentExecution.Status.COMPLETED,
            amount=Decimal("1000.00"),
            currency="NGN",
            reference="PROVIDER-FLOW-001",
            external_event_id="EVENT-FLOW-001",
            metadata={},
        )

        self.reconciliation = ReconciliationResult(
            outcome=PaymentExecution.Status.COMPLETED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.RECONCILED
            ),
            reason="Reconciled successfully.",
            evidence_count=1,
            metadata={"sources": ["PROVIDER"]},
        )

    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_pipeline_runs_in_exact_order(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        calls = []

        mock_collect.side_effect = lambda **kwargs: (
            calls.append("collect"),
            [self.evidence],
        )[1]

        mock_reconcile.side_effect = lambda **kwargs: (
            calls.append("reconcile"),
            self.reconciliation,
        )[1]

        mock_apply.side_effect = lambda execution, result: (
            calls.append("apply"),
            execution,
        )[1]

        mock_synchronize.side_effect = lambda execution: (
            calls.append("synchronize"),
            execution,
        )[1]

        result = ReconciliationOrchestrator.reconcile(
            execution=self.execution,
        )

        self.assertEqual(
            calls,
            [
                "collect",
                "reconcile",
                "apply",
                "synchronize",
            ],
        )

        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.payment, self.payment)
        self.assertEqual(result.evidence, (self.evidence,))
        self.assertEqual(result.reconciliation, self.reconciliation)

    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_collector_output_is_passed_to_reconcile(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        ReconciliationOrchestrator.reconcile(
            execution=self.execution,
        )

        mock_reconcile.assert_called_once_with(
            execution=self.execution,
            evidence=[self.evidence],
        )

    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_reconciliation_result_is_passed_to_apply_result(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        ReconciliationOrchestrator.reconcile(
            execution=self.execution,
        )

        mock_apply.assert_called_once_with(
            self.execution,
            self.reconciliation,
        )

    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_applied_execution_is_passed_to_synchronization(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        ReconciliationOrchestrator.reconcile(
            execution=self.execution,
        )

        mock_synchronize.assert_called_once_with(
            self.execution,
        )

    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_result_contains_all_pipeline_outputs(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        result = ReconciliationOrchestrator.reconcile(
            execution=self.execution,
        )

        self.assertIsInstance(
            result,
            ReconciliationOrchestrationResult,
        )
        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.payment, self.payment)
        self.assertEqual(result.evidence, (self.evidence,))
        self.assertEqual(
            result.reconciliation,
            self.reconciliation,
        )
    
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_additional_evidence_is_forwarded_to_collector(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        additional_evidence = [
            ReconciliationEvidence(
                source="BANKING",
                status=PaymentExecution.Status.COMPLETED,
                amount=Decimal("1000.00"),
                currency="NGN",
                reference="BANK-001",
                external_event_id="BANK-EVENT-001",
                metadata={"transaction_type": "TRANSFER"},
            )
        ]

        ReconciliationOrchestrator.reconcile(
            execution=self.execution,
            additional_evidence=additional_evidence,
        )

        mock_collect.assert_called_once_with(
            execution=self.execution,
            additional_evidence=additional_evidence,
        )


    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "PaymentExecutionSynchronization.synchronize"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.apply_result"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_orchestrator."
        "ReconciliationEvidenceCollector.collect"
    )
    def test_additional_evidence_is_forwarded_without_modification(
        self,
        mock_collect,
        mock_reconcile,
        mock_apply,
        mock_synchronize,
    ):
        mock_collect.return_value = [self.evidence]
        mock_reconcile.return_value = self.reconciliation
        mock_apply.return_value = self.execution
        mock_synchronize.return_value = self.execution

        additional_evidence = (
            ReconciliationEvidence(
                source="BANKING",
                status=PaymentExecution.Status.COMPLETED,
                amount=Decimal("1000.00"),
                currency="NGN",
                reference="BANK-002",
                external_event_id="BANK-EVENT-002",
                metadata={"transaction_type": "TRANSFER"},
            ),
        )

        ReconciliationOrchestrator.reconcile(
            execution=self.execution,
            additional_evidence=additional_evidence,
        )

        forwarded = mock_collect.call_args.kwargs[
            "additional_evidence"
        ]

        self.assertIs(
            forwarded,
            additional_evidence,
        )