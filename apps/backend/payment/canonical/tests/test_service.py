from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from payment.canonical.models import Payment
from payment.canonical.services.service import PaymentService


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payer@example.com",
        )

        self.beneficiary = User.objects.create_user(
            email="beneficiary@example.com",
        )

    def test_create_receive_payment(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-001",
            source_reference="CHK-001",
            payer=self.user,
            amount=Decimal("15000.00"),
            currency="ngn",
            idempotency_key="payment-idempotency-001",
        )

        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.direction, Payment.Direction.RECEIVE)
        self.assertEqual(payment.purpose, Payment.Purpose.CHECKOUT)
        self.assertEqual(payment.source_type, "checkout")
        self.assertEqual(payment.source_id, "checkout-001")
        self.assertEqual(payment.source_reference, "CHK-001")
        self.assertEqual(payment.payer, self.user)
        self.assertIsNone(payment.beneficiary)
        self.assertEqual(payment.amount, Decimal("15000.00"))
        self.assertEqual(payment.currency, "NGN")
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(
            payment.idempotency_key,
            "payment-idempotency-001",
        )

    def test_create_disbursement_payment(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="settlement-001",
            source_reference="SET-001",
            beneficiary=self.beneficiary,
            amount=Decimal("25000.00"),
            currency="ngn",
            idempotency_key="payment-idempotency-002",
        )

        self.assertEqual(payment.direction, Payment.Direction.DISBURSE)
        self.assertEqual(payment.purpose, Payment.Purpose.EARNING)
        self.assertIsNone(payment.payer)
        self.assertEqual(payment.beneficiary, self.beneficiary)
        self.assertEqual(payment.amount, Decimal("25000.00"))
        self.assertEqual(payment.currency, "NGN")
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_new_payment_always_starts_pending(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-002",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-003",
        )

        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_currency_is_normalized_to_uppercase(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-003",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="usd",
            idempotency_key="payment-idempotency-004",
        )

        self.assertEqual(payment.currency, "USD")

    def test_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-004",
                payer=self.user,
                amount=Decimal("0.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-005",
            )

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-005",
                payer=self.user,
                amount=Decimal("-100.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-006",
            )

    def test_source_type_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="",
                source_id="checkout-006",
                payer=self.user,
                amount=Decimal("1000.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-007",
            )

    def test_source_id_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="",
                payer=self.user,
                amount=Decimal("1000.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-008",
            )

    def test_disbursement_requires_beneficiary(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.DISBURSE,
                purpose=Payment.Purpose.EARNING,
                source_type="settlement",
                source_id="settlement-002",
                beneficiary=None,
                amount=Decimal("5000.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-009",
            )

    def test_receive_payment_can_have_no_payer(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-007",
            payer=None,
            amount=Decimal("5000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-010",
        )

        self.assertIsNone(payment.payer)
        self.assertEqual(payment.direction, Payment.Direction.RECEIVE)

    def test_same_idempotency_key_returns_existing_payment(self):
        first = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-008",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-011",
        )

        second = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-008",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-011",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            Payment.objects.filter(
                idempotency_key="payment-idempotency-011"
            ).count(),
            1,
        )

    def test_same_idempotency_key_with_different_amount_is_rejected(self):
        PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-009",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-012",
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-009",
                payer=self.user,
                amount=Decimal("8500.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-012",
            )

    def test_same_idempotency_key_with_different_currency_is_rejected(self):
        PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-010",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-013",
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-010",
                payer=self.user,
                amount=Decimal("7500.00"),
                currency="USD",
                idempotency_key="payment-idempotency-013",
            )

    def test_same_idempotency_key_with_different_source_is_rejected(self):
        PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-011",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-014",
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-012",
                payer=self.user,
                amount=Decimal("7500.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-014",
            )

    def test_same_idempotency_key_with_different_direction_is_rejected(self):
        PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-013",
            payer=self.user,
            amount=Decimal("7500.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-015",
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.DISBURSE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-013",
                beneficiary=self.beneficiary,
                amount=Decimal("7500.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-015",
            )

    def test_same_idempotency_key_with_different_beneficiary_is_rejected(self):
        another_beneficiary = User.objects.create_user(
            email="another-beneficiary@example.com",
        )

        PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="settlement-003",
            beneficiary=self.beneficiary,
            amount=Decimal("9000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-016",
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.DISBURSE,
                purpose=Payment.Purpose.EARNING,
                source_type="settlement",
                source_id="settlement-003",
                beneficiary=another_beneficiary,
                amount=Decimal("9000.00"),
                currency="NGN",
                idempotency_key="payment-idempotency-016",
            )

    def test_idempotency_key_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                direction=Payment.Direction.RECEIVE,
                purpose=Payment.Purpose.CHECKOUT,
                source_type="checkout",
                source_id="checkout-014",
                payer=self.user,
                amount=Decimal("1000.00"),
                currency="NGN",
                idempotency_key="",
            )

    def test_payment_is_persisted(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-015",
            payer=self.user,
            amount=Decimal("3000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-017",
        )

        self.assertTrue(
            Payment.objects.filter(
                id=payment.id,
            ).exists()
        )

    def test_payment_reference_is_generated(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-016",
            payer=self.user,
            amount=Decimal("3000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-018",
        )

        self.assertTrue(payment.reference)
        self.assertLessEqual(len(payment.reference), 50)

    def test_metadata_is_persisted(self):
        metadata = {
            "checkout_id": "CHK-100",
            "customer_type": "external",
        }

        payment = PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-017",
            payer=self.user,
            amount=Decimal("4000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-019",
            metadata=metadata,
        )

        self.assertEqual(payment.metadata, metadata)

    def test_source_reference_is_persisted(self):
        payment = PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.COMMISSION,
            source_type="settlement",
            source_id="settlement-004",
            source_reference="SET-20260930-0001",
            beneficiary=self.beneficiary,
            amount=Decimal("12000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-020",
        )

        self.assertEqual(
            payment.source_reference,
            "SET-20260930-0001",
        )