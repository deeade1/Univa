from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from payment.canonical.models import Payment
from payment.canonical.services.lifecycle import PaymentLifecycle
from payment.canonical.services.service import PaymentService


class PaymentLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payer@example.com",
        )

        self.beneficiary = User.objects.create_user(
            email="beneficiary@example.com",
        )

    def create_payment(
        self,
        *,
        direction=Payment.Direction.DISBURSE,
        status=None,
    ):
        payment = PaymentService.create_payment(
            direction=direction,
            purpose=(
                Payment.Purpose.EARNING
                if direction == Payment.Direction.DISBURSE
                else Payment.Purpose.CHECKOUT
            ),
            source_type="settlement",
            source_id="settlement-001",
            beneficiary=(
                self.beneficiary
                if direction == Payment.Direction.DISBURSE
                else None
            ),
            payer=(
                self.user
                if direction == Payment.Direction.RECEIVE
                else None
            ),
            amount=Decimal("10000.00"),
            currency="NGN",
            idempotency_key="payment-lifecycle-001",
        )

        if status is not None:
            payment.status = status
            payment.save(update_fields=["status"])

        return payment

    def test_pending_can_transition_to_processing(self):
        payment = self.create_payment()

        result = PaymentLifecycle.mark_processing(payment)

        self.assertEqual(
            result.status,
            Payment.Status.PROCESSING,
        )
        self.assertIsNotNone(result.processing_at)

    def test_pending_can_be_cancelled(self):
        payment = self.create_payment()

        result = PaymentLifecycle.cancel(payment)

        self.assertEqual(
            result.status,
            Payment.Status.CANCELLED,
        )
        self.assertIsNotNone(result.cancelled_at)

    def test_processing_can_be_completed(self):
        payment = self.create_payment(
            status=Payment.Status.PROCESSING,
        )

        result = PaymentLifecycle.mark_completed(payment)

        self.assertEqual(
            result.status,
            Payment.Status.COMPLETED,
        )
        self.assertIsNotNone(result.completed_at)

    def test_processing_can_fail(self):
        payment = self.create_payment(
            status=Payment.Status.PROCESSING,
        )

        result = PaymentLifecycle.mark_failed(payment)

        self.assertEqual(
            result.status,
            Payment.Status.FAILED,
        )
        self.assertIsNotNone(result.failed_at)

    def test_processing_can_be_cancelled(self):
        payment = self.create_payment(
            status=Payment.Status.PROCESSING,
        )

        result = PaymentLifecycle.cancel(payment)

        self.assertEqual(
            result.status,
            Payment.Status.CANCELLED,
        )
        self.assertIsNotNone(result.cancelled_at)

    def test_failed_can_return_to_processing(self):
        payment = self.create_payment(
            status=Payment.Status.FAILED,
        )

        result = PaymentLifecycle.mark_processing(payment)

        self.assertEqual(
            result.status,
            Payment.Status.PROCESSING,
        )
        self.assertIsNotNone(result.processing_at)

    def test_completed_can_be_reversed(self):
        payment = self.create_payment(
            status=Payment.Status.COMPLETED,
        )

        result = PaymentLifecycle.reverse(payment)

        self.assertEqual(
            result.status,
            Payment.Status.REVERSED,
        )
        self.assertIsNotNone(result.reversed_at)

    def test_pending_cannot_be_completed_directly(self):
        payment = self.create_payment()

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_completed(payment)

    def test_pending_cannot_be_failed_directly(self):
        payment = self.create_payment()

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_failed(payment)

    def test_pending_cannot_be_reversed(self):
        payment = self.create_payment()

        with self.assertRaises(ValidationError):
            PaymentLifecycle.reverse(payment)

    def test_processing_cannot_be_reversed(self):
        payment = self.create_payment(
            status=Payment.Status.PROCESSING,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.reverse(payment)

    def test_failed_cannot_be_completed(self):
        payment = self.create_payment(
            status=Payment.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_completed(payment)

    def test_failed_cannot_be_reversed(self):
        payment = self.create_payment(
            status=Payment.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.reverse(payment)

    def test_cancelled_is_terminal(self):
        payment = self.create_payment(
            status=Payment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_processing(payment)

    def test_cancelled_cannot_be_completed(self):
        payment = self.create_payment(
            status=Payment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_completed(payment)

    def test_cancelled_cannot_be_reversed(self):
        payment = self.create_payment(
            status=Payment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.reverse(payment)

    def test_reversed_is_terminal(self):
        payment = self.create_payment(
            status=Payment.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_processing(payment)

    def test_reversed_cannot_be_completed(self):
        payment = self.create_payment(
            status=Payment.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_completed(payment)

    def test_reversed_cannot_be_failed(self):
        payment = self.create_payment(
            status=Payment.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.mark_failed(payment)

    def test_reversed_cannot_be_cancelled(self):
        payment = self.create_payment(
            status=Payment.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            PaymentLifecycle.cancel(payment)

    def test_lifecycle_preserves_payment_identity(self):
        payment = self.create_payment()

        original_id = payment.id
        original_reference = payment.reference
        original_amount = payment.amount
        original_currency = payment.currency
        original_source_type = payment.source_type
        original_source_id = payment.source_id
        original_beneficiary_id = payment.beneficiary_id

        payment = PaymentLifecycle.mark_processing(payment)

        self.assertEqual(payment.id, original_id)
        self.assertEqual(payment.reference, original_reference)
        self.assertEqual(payment.amount, original_amount)
        self.assertEqual(payment.currency, original_currency)
        self.assertEqual(
            payment.source_type,
            original_source_type,
        )
        self.assertEqual(
            payment.source_id,
            original_source_id,
        )
        self.assertEqual(
            payment.beneficiary_id,
            original_beneficiary_id,
        )

    def test_failed_to_processing_does_not_create_new_payment(self):
        payment = self.create_payment(
            status=Payment.Status.FAILED,
        )

        original_id = payment.id

        result = PaymentLifecycle.mark_processing(payment)

        self.assertEqual(result.id, original_id)
        self.assertEqual(
            Payment.objects.count(),
            1,
        )