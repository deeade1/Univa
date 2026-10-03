"""
Tests for the Banking → Reconciliation orchestration boundary.

Architectural contract
----------------------

BankingReconciliationService is a composition service.

It is responsible for:

    PaymentExecution
        ↓
    BankingTransactionResolver
        ↓
    BankingTransactionEvidenceAdapter
        ↓
    ReconciliationOrchestrator

It is NOT responsible for:

    - resolving Banking identity itself
    - translating Banking fields itself
    - implementing reconciliation rules
    - mutating PaymentExecution
    - mutating Banking.Transaction
    - creating Banking transactions
    - changing Payment
    - calling providers
    - implementing retries
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class BankingReconciliationServiceTests(SimpleTestCase):
    """
    Focused composition tests.

    The resolver, Banking evidence adapter, and generic reconciliation
    orchestrator each have their own dedicated test suites. These tests
    therefore verify only that this service composes those boundaries
    correctly.
    """

    def setUp(self):
        self.execution = SimpleNamespace(
            id="execution-001",
        )

        self.transaction = SimpleNamespace(
            reference="BANK-TXN-001",
        )

        self.banking_evidence = SimpleNamespace(
            source="BANKING",
            status="completed",
        )

        self.orchestration_result = SimpleNamespace(
            execution=self.execution,
            payment=SimpleNamespace(id="payment-001"),
            evidence=(self.banking_evidence,),
            reconciliation=SimpleNamespace(
                outcome="completed",
            ),
        )

    def _service(self):
        from payment.canonical.services.banking_reconciliation import (
            BankingReconciliationService,
        )

        return BankingReconciliationService

    def test_resolves_banking_transaction_from_execution(self):
        """
        BankingReconciliationService must delegate Banking identity
        resolution to BankingTransactionResolver.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(execution=self.execution)

            resolver.resolve.assert_called_once_with(
                execution=self.execution,
            )

    def test_resolved_transaction_is_passed_to_evidence_adapter(self):
        """
        The transaction returned by the resolver must be passed unchanged
        to the Banking evidence adapter.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(execution=self.execution)

            adapter.to_evidence.assert_called_once_with(
                transaction=self.transaction,
                execution=self.execution,
            )

    def test_banking_evidence_is_forwarded_to_orchestrator(self):
        """
        The canonical Banking evidence must be forwarded as additional
        reconciliation evidence.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(execution=self.execution)

            orchestrator.reconcile.assert_called_once_with(
                execution=self.execution,
                additional_evidence=(self.banking_evidence,),
            )

    def test_execution_is_forwarded_to_orchestrator_unchanged(self):
        """
        The original PaymentExecution must reach the generic reconciliation
        orchestrator unchanged.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(execution=self.execution)

            forwarded_execution = (
                orchestrator.reconcile.call_args.kwargs["execution"]
            )

            self.assertIs(
                forwarded_execution,
                self.execution,
            )

    def test_banking_evidence_is_forwarded_without_modification(self):
        """
        BankingReconciliationService must not transform or copy the
        ReconciliationEvidence returned by the adapter.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(execution=self.execution)

            forwarded_evidence = (
                orchestrator.reconcile.call_args.kwargs[
                    "additional_evidence"
                ]
            )[0]

            self.assertIs(
                forwarded_evidence,
                self.banking_evidence,
            )

    def test_returns_orchestration_result_unchanged(self):
        """
        The Banking reconciliation service must return the result produced
        by the generic reconciliation orchestrator.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            result = service.reconcile(
                execution=self.execution,
            )

            self.assertIs(
                result,
                self.orchestration_result,
            )

    def test_resolver_error_is_propagated(self):
        """
        Banking resolution failures must not be swallowed or converted
        into another reconciliation outcome.
        """
        service = self._service()

        error = ValueError("Banking transaction could not be resolved.")

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.side_effect = error

            with self.assertRaises(ValueError) as raised:
                service.reconcile(
                    execution=self.execution,
                )

            self.assertIs(
                raised.exception,
                error,
            )

            adapter.to_evidence.assert_not_called()
            orchestrator.reconcile.assert_not_called()

    def test_adapter_error_is_propagated(self):
        """
        Banking evidence translation failures must propagate unchanged.
        """
        service = self._service()

        error = ValueError("Banking evidence translation failed.")

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.side_effect = error

            with self.assertRaises(ValueError) as raised:
                service.reconcile(
                    execution=self.execution,
                )

            self.assertIs(
                raised.exception,
                error,
            )

            orchestrator.reconcile.assert_not_called()

    def test_orchestrator_error_is_propagated(self):
        """
        Generic reconciliation errors must propagate unchanged.
        """
        service = self._service()

        error = ValueError("Reconciliation failed.")

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.side_effect = error

            with self.assertRaises(ValueError) as raised:
                service.reconcile(
                    execution=self.execution,
                )

            self.assertIs(
                raised.exception,
                error,
            )

    def test_resolver_is_called_once(self):
        """
        Banking transaction resolution must happen exactly once.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(
                execution=self.execution,
            )

            resolver.resolve.assert_called_once()

    def test_adapter_is_called_once(self):
        """
        Banking evidence translation must happen exactly once.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(
                execution=self.execution,
            )

            adapter.to_evidence.assert_called_once()

    def test_orchestrator_is_called_once(self):
        """
        Generic reconciliation orchestration must happen exactly once.
        """
        service = self._service()

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(
                execution=self.execution,
            )

            orchestrator.reconcile.assert_called_once()

    def test_service_does_not_create_or_mutate_banking_transaction(self):
        """
        The service only consumes the transaction returned by the resolver.
        It must not save, update, or create Banking transactions itself.
        """
        service = self._service()

        transaction = MagicMock()
        transaction.reference = "BANK-TXN-001"

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(
                execution=self.execution,
            )

            transaction.save.assert_not_called()
            transaction.delete.assert_not_called()

    def test_service_does_not_mutate_execution(self):
        """
        The service passes the execution through the existing boundaries.
        It does not save or mutate the PaymentExecution itself.
        """
        service = self._service()

        execution = MagicMock()
        execution.id = "execution-001"

        with (
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionResolver"
            ) as resolver,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "BankingTransactionEvidenceAdapter"
            ) as adapter,
            patch(
                "payment.canonical.services.banking_reconciliation."
                "ReconciliationOrchestrator"
            ) as orchestrator,
        ):
            resolver.resolve.return_value = self.transaction
            adapter.to_evidence.return_value = self.banking_evidence
            orchestrator.reconcile.return_value = self.orchestration_result

            service.reconcile(
                execution=execution,
            )

            execution.save.assert_not_called()
            execution.delete.assert_not_called()
