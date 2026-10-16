"""
Tests for the canonical reconciliation trigger policy.

Architectural contract
----------------------

The trigger policy answers only:

    Can this PaymentExecution enter reconciliation now?

Current policy:

    RECONCILIATION_REQUIRED → True
    all other reconciliation states → False

The policy does not:

    - perform reconciliation
    - collect evidence
    - resolve Banking transactions
    - create events
    - mutate PaymentExecution
    - mutate Payment
    - call providers
    - perform retries
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_trigger import (
    ReconciliationTriggerPolicy,
)


class ReconciliationTriggerPolicyTests(TestCase):
    """
    Focused tests for reconciliation trigger eligibility.
    """

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(
            email="reconciliation-trigger@example.com",
            password="test-password",
        )

    def setUp(self):
        self.payment_counter = 0
        self.execution_counter = 0

    def _payment(self):
        from payment.canonical.models import Payment

        self.payment_counter += 1
        suffix = self.payment_counter

        return Payment.objects.create(
            reference=f"PAY-TRIGGER-{suffix:03d}",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id=f"trigger-payment-{suffix:03d}",
            beneficiary=self.user,
            amount="100.00",
            currency="NGN",
            idempotency_key=(
                f"trigger-payment-idempotency-{suffix:03d}"
            ),
        )

    def _execution(self):
        self.execution_counter += 1
        suffix = self.execution_counter

        return PaymentExecution.objects.create(
            reference=f"EXEC-TRIGGER-{suffix:03d}",
            payment=self._payment(),
            attempt_number=1,
            idempotency_key=(
                f"trigger-execution-idempotency-{suffix:03d}"
            ),
            route_type=PaymentExecution.RouteType.CARD,
            provider="test_provider",
        )

    def test_required_reconciliation_is_eligible(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        self.assertTrue(
            ReconciliationTriggerPolicy.is_eligible(
                execution=execution,
            )
        )

    def test_not_required_is_not_eligible(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.NOT_REQUIRED
        )
        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        self.assertFalse(
            ReconciliationTriggerPolicy.is_eligible(
                execution=execution,
            )
        )

    def test_pending_reconciliation_state_is_not_eligible(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.PENDING
        )
        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        self.assertFalse(
            ReconciliationTriggerPolicy.is_eligible(
                execution=execution,
            )
        )

    def test_required_is_independent_of_execution_status(self):
        """
        Once reconciliation has explicitly been required, the trigger
        policy does not duplicate PaymentExecutionLifecycle rules.
        """

        for status in (
            PaymentExecution.Status.CREATED,
            PaymentExecution.Status.PROCESSING,
            PaymentExecution.Status.PENDING,
            PaymentExecution.Status.FAILED,
            PaymentExecution.Status.CANCELLED,
        ):
            with self.subTest(status=status):
                execution = self._execution()

                execution.status = status
                execution.reconciliation_state = (
                    PaymentExecution.ReconciliationState.REQUIRED
                )
                execution.save(
                    update_fields=[
                        "status",
                        "reconciliation_state",
                        "updated_at",
                    ]
                )

                self.assertTrue(
                    ReconciliationTriggerPolicy.is_eligible(
                        execution=execution,
                    )
                )

    def test_completed_without_required_reconciliation_is_not_eligible(self):
        execution = self._execution()

        execution.status = PaymentExecution.Status.COMPLETED
        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.RECONCILED
        )
        execution.save(
            update_fields=[
                "status",
                "reconciliation_state",
                "updated_at",
            ]
        )

        self.assertFalse(
            ReconciliationTriggerPolicy.is_eligible(
                execution=execution,
            )
        )

    def test_none_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationTriggerPolicy.is_eligible(
                execution=None,
            )

    def test_non_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ReconciliationTriggerPolicy.is_eligible(
                execution=object(),
            )

    def test_unsaved_execution_is_rejected(self):
        payment = self._payment()

        execution = PaymentExecution(
            reference="EXEC-TRIGGER-UNSAVED",
            payment=payment,
            attempt_number=1,
            idempotency_key="trigger-unsaved-execution",
            route_type=PaymentExecution.RouteType.CARD,
            provider="test_provider",
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

        with self.assertRaises(ValidationError):
            ReconciliationTriggerPolicy.is_eligible(
                execution=execution,
            )

    def test_policy_returns_boolean(self):
        execution = self._execution()

        result = ReconciliationTriggerPolicy.is_eligible(
            execution=execution,
        )

        self.assertIs(type(result), bool)

    def test_policy_does_not_mutate_execution(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        before = {
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        result = ReconciliationTriggerPolicy.is_eligible(
            execution=execution,
        )

        execution.refresh_from_db()

        after = {
            "status": execution.status,
            "reconciliation_state": execution.reconciliation_state,
            "banking_transaction_reference": (
                execution.banking_transaction_reference
            ),
        }

        self.assertTrue(result)
        self.assertEqual(before, after)

    def test_policy_does_not_change_payment(self):
        execution = self._execution()

        execution.reconciliation_state = (
            PaymentExecution.ReconciliationState.REQUIRED
        )
        execution.save(
            update_fields=["reconciliation_state", "updated_at"]
        )

        payment = execution.payment

        before = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        ReconciliationTriggerPolicy.is_eligible(
            execution=execution,
        )

        payment.refresh_from_db()

        after = {
            "status": str(payment.status),
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        self.assertEqual(before, after)