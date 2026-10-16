"""
Tests for the canonical reconciliation dispatch boundary.

Architectural responsibility
----------------------------

ReconciliationDispatcher is responsible only for:

    - validating the PaymentExecution
    - validating reconciliation eligibility
    - selecting the appropriate reconciliation service
    - delegating reconciliation
    - returning the delegated result unchanged

It must NOT:

    - implement reconciliation rules
    - collect evidence
    - resolve Banking transactions
    - translate Banking evidence
    - call providers
    - process webhooks
    - perform retries
    - mutate PaymentExecution directly
    - mutate Payment directly
    - contain Celery behavior
"""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.reconciliation_dispatch import (
    ReconciliationDispatcher,
)


class ReconciliationDispatcherTests(TestCase):
    """Tests for the canonical reconciliation dispatch boundary."""

    def setUp(self):
        self.payment_counter = 0
        self.execution_counter = 0

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _payment(self):
        self.payment_counter += 1
        suffix = self.payment_counter

        return Payment.objects.create(
            reference=f"PAY-DISPATCH-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"dispatch-payment-{suffix:03d}",
            beneficiary_id=None,
            amount="100.00",
            currency="NGN",
            idempotency_key=(
                f"dispatch-payment-idempotency-{suffix:03d}"
            ),
        )

    def _execution(self, *, route_type):
        self.execution_counter += 1
        suffix = self.execution_counter

        payment = self._payment()

        return PaymentExecution.objects.create(
            reference=f"EXEC-DISPATCH-{suffix:03d}",
            payment=payment,
            attempt_number=1,
            idempotency_key=f"dispatch-execution-{suffix:03d}",
            route_type=route_type,
            provider="test-provider",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_non_payment_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationDispatcher.dispatch(
                execution=object(),
            )

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationDispatcher.dispatch(
                execution=None,
            )

    def test_unsaved_execution_is_rejected(self):
        payment = self._payment()

        execution = PaymentExecution(
            payment=payment,
            reference="EXEC-DISPATCH-UNSAVED",
            attempt_number=1,
            idempotency_key="dispatch-unsaved-execution",
            route_type=PaymentExecution.RouteType.CARD,
            provider="test-provider",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

        with self.assertRaises(ValidationError):
            ReconciliationDispatcher.dispatch(
                execution=execution,
            )

    def test_execution_not_requiring_reconciliation_is_rejected(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.NOT_REQUIRED
        )

        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        with self.assertRaises(ValidationError):
            ReconciliationDispatcher.dispatch(
                execution=execution,
            )

    def test_pending_reconciliation_state_is_rejected(self):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.PENDING
        )

        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        with self.assertRaises(ValidationError):
            ReconciliationDispatcher.dispatch(
                execution=execution,
            )

    # ------------------------------------------------------------------
    # Banking-backed routing
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_univa_internal_delegates_to_banking_reconciliation(
        self,
        mock_generic_reconcile,
        mock_banking_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        expected_result = object()
        mock_banking_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(result, expected_result)

        mock_banking_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_generic_reconcile.assert_not_called()

    # ------------------------------------------------------------------
    # Non-Banking routing
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_card_delegates_to_generic_reconciliation(
        self,
        mock_generic_reconcile,
        mock_banking_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        expected_result = object()
        mock_generic_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(result, expected_result)

        mock_generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_banking_reconcile.assert_not_called()

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_wallet_delegates_to_generic_reconciliation(
        self,
        mock_generic_reconcile,
        mock_banking_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.WALLET,
        )

        expected_result = object()
        mock_generic_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(result, expected_result)

        mock_generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_banking_reconcile.assert_not_called()

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    def test_other_route_delegates_to_generic_reconciliation(
        self,
        mock_banking_reconcile,
        mock_generic_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.OTHER,
        )

        expected_result = object()
        mock_generic_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(result, expected_result)

        mock_generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_banking_reconcile.assert_not_called()

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    def test_bank_transfer_does_not_automatically_use_banking(
        self,
        mock_banking_reconcile,
        mock_generic_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
        )

        expected_result = object()
        mock_generic_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(result, expected_result)

        mock_generic_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_banking_reconcile.assert_not_called()

    # ------------------------------------------------------------------
    # Delegation contract
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    def test_banking_path_receives_same_execution_object(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        mock_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        delegated_execution = (
            mock_reconcile.call_args.kwargs["execution"]
        )

        self.assertIs(
            delegated_execution,
            execution,
        )

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_generic_path_receives_same_execution_object(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        mock_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        delegated_execution = (
            mock_reconcile.call_args.kwargs["execution"]
        )

        self.assertIs(
            delegated_execution,
            execution,
        )

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_selected_service_is_called_exactly_once(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        mock_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        mock_reconcile.assert_called_once()

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_result_is_returned_unchanged(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        expected_result = object()
        mock_reconcile.return_value = expected_result

        result = ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        self.assertIs(
            result,
            expected_result,
        )

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_service_exception_propagates_unchanged(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        error = RuntimeError("reconciliation failed")
        mock_reconcile.side_effect = error

        with self.assertRaisesRegex(
            RuntimeError,
            "reconciliation failed",
        ):
            ReconciliationDispatcher.dispatch(
                execution=execution,
            )

        mock_reconcile.assert_called_once_with(
            execution=execution,
        )

    # ------------------------------------------------------------------
    # Non-mutation contract
    # ------------------------------------------------------------------

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    def test_dispatcher_does_not_mutate_execution(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        before = {
            "status": str(execution.status),
            "reconciliation_state": str(
                execution.reconciliation_state
            ),
            "route_type": str(execution.route_type),
            "provider": execution.provider,
        }

        mock_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        execution.refresh_from_db()

        after = {
            "status": str(execution.status),
            "reconciliation_state": str(
                execution.reconciliation_state
            ),
            "route_type": str(execution.route_type),
            "provider": execution.provider,
        }

        self.assertEqual(before, after)

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_dispatcher_does_not_mutate_payment(
        self,
        mock_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.CARD,
        )

        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        mock_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertEqual(before, after)

    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "BankingReconciliationService.reconcile"
    )
    @patch(
        "payment.canonical.services.reconciliation_dispatch."
        "ReconciliationOrchestrator.reconcile"
    )
    def test_other_reconciliation_path_is_not_called(
        self,
        mock_generic_reconcile,
        mock_banking_reconcile,
    ):
        execution = self._execution(
            route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        )

        mock_banking_reconcile.return_value = object()

        ReconciliationDispatcher.dispatch(
            execution=execution,
        )
        
        mock_banking_reconcile.assert_called_once_with(
            execution=execution,
        )

        mock_generic_reconcile.assert_not_called()