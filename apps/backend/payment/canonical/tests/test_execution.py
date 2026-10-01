from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentInstrument,
)
from payment.canonical.services.execution import PaymentExecutionService
from payment.canonical.services.service import PaymentService


class PaymentExecutionServiceTests(TestCase):
    def setUp(self):
        self.payer = User.objects.create_user(
            email="payer@example.com",
        )

        self.beneficiary = User.objects.create_user(
            email="beneficiary@example.com",
        )

        self.payment = PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="settlement-001",
            source_reference="SET-001",
            beneficiary=self.beneficiary,
            amount=Decimal("10000.00"),
            currency="NGN",
            idempotency_key="payment-execution-payment-001",
        )

    def create_receive_payment(self):
        return PaymentService.create_payment(
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-001",
            source_reference="CHK-001",
            payer=self.payer,
            amount=Decimal("5000.00"),
            currency="NGN",
            idempotency_key="payment-execution-payment-002",
        )

    def create_instrument(
        self,
        *,
        owner,
        instrument_type=PaymentInstrument.InstrumentType.BANK_ACCOUNT,
        can_fund=True,
        can_receive=True,
        secure_reference="secure-ref-001",
    ):
        return PaymentInstrument.objects.create(
            reference=f"PINS-{secure_reference}",
            owner=owner,
            instrument_type=instrument_type,
            institution="test_bank",
            can_fund=can_fund,
            can_receive=can_receive,
            secure_reference=secure_reference,
            display_reference="****1234",
            verification_status=(
                PaymentInstrument.VerificationStatus.VERIFIED
            ),
            verified_at=self._now(),
            status=PaymentInstrument.Status.ACTIVE,
            activated_at=self._now(),
        )

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()

    def test_create_first_execution(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-001",
        )

        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.payment_id, self.payment.id)
        self.assertEqual(execution.attempt_number, 1)
        self.assertEqual(
            execution.route_type,
            PaymentExecution.RouteType.BANK_TRANSFER,
        )
        self.assertEqual(execution.provider, "test_provider")
        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CREATED,
        )
        self.assertEqual(
            execution.reconciliation_state,
            PaymentExecution.ReconciliationState.NOT_REQUIRED,
        )

    def test_first_execution_is_attempt_one(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-002",
        )

        self.assertEqual(execution.attempt_number, 1)

    def test_second_execution_automatically_gets_attempt_two(self):
        first = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-003",
        )

        second = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-004",
        )

        self.assertEqual(first.attempt_number, 1)
        self.assertEqual(second.attempt_number, 2)

    def test_third_execution_gets_attempt_three(self):
        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-005",
        )

        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-006",
        )

        third = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-007",
        )

        self.assertEqual(third.attempt_number, 3)

    def test_explicit_attempt_number_is_respected(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            attempt_number=5,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-008",
        )

        self.assertEqual(execution.attempt_number, 5)

    def test_attempt_number_must_be_positive(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                attempt_number=0,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="execution-idempotency-009",
            )

    def test_negative_attempt_number_is_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                attempt_number=-1,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="execution-idempotency-010",
            )

    def test_provider_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="",
                idempotency_key="execution-idempotency-011",
            )

    def test_route_type_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type="",
                provider="test_provider",
                idempotency_key="execution-idempotency-012",
            )

    def test_idempotency_key_is_required(self):
        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="",
            )

    def test_same_idempotency_key_returns_existing_execution(self):
        first = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-013",
        )

        second = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-013",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            PaymentExecution.objects.filter(
                idempotency_key="execution-idempotency-013",
            ).count(),
            1,
        )

    def test_same_idempotency_key_with_different_payment_is_rejected(self):
        other_payment = PaymentService.create_payment(
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="settlement-002",
            beneficiary=self.beneficiary,
            amount=Decimal("20000.00"),
            currency="NGN",
            idempotency_key="payment-execution-payment-003",
        )

        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-014",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=other_payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="execution-idempotency-014",
            )

    def test_same_idempotency_key_with_different_route_is_rejected(self):
        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-015",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.CARD,
                provider="test_provider",
                idempotency_key="execution-idempotency-015",
            )

    def test_same_idempotency_key_with_different_provider_is_rejected(self):
        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="provider_a",
            idempotency_key="execution-idempotency-016",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="provider_b",
                idempotency_key="execution-idempotency-016",
            )

    def test_same_idempotency_key_with_different_instrument_is_rejected(self):
        instrument_one = self.create_instrument(
            owner=self.beneficiary,
            secure_reference="secure-ref-002",
        )

        instrument_two = self.create_instrument(
            owner=self.beneficiary,
            secure_reference="secure-ref-003",
        )

        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            instrument=instrument_one,
            idempotency_key="execution-idempotency-017",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                instrument=instrument_two,
                idempotency_key="execution-idempotency-017",
            )

    def test_cancelled_payment_cannot_create_execution(self):
        self.payment.status = Payment.Status.CANCELLED
        self.payment.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="execution-idempotency-018",
            )

    def test_reversed_payment_cannot_create_execution(self):
        self.payment.status = Payment.Status.REVERSED
        self.payment.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                idempotency_key="execution-idempotency-019",
            )

    def test_execution_reference_is_generated(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-020",
        )

        self.assertTrue(execution.reference)
        self.assertLessEqual(len(execution.reference), 50)
        self.assertTrue(
            execution.reference.startswith("PEXEC-")
        )

    def test_execution_is_persisted(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-021",
        )

        self.assertTrue(
            PaymentExecution.objects.filter(
                id=execution.id,
            ).exists()
        )

    def test_metadata_is_persisted(self):
        metadata = {
            "source": "settlement",
            "priority": "normal",
        }

        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-022",
            metadata=metadata,
        )

        self.assertEqual(
            execution.metadata,
            metadata,
        )

    def test_execution_starts_as_created(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-023",
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CREATED,
        )

    def test_creating_execution_does_not_change_payment_status(self):
        original_status = self.payment.status

        PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-024",
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )

    def test_disbursement_instrument_must_belong_to_beneficiary(self):
        instrument = self.create_instrument(
            owner=self.payer,
            can_receive=True,
            secure_reference="secure-ref-004",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                instrument=instrument,
                idempotency_key="execution-idempotency-025",
            )

    def test_disbursement_instrument_must_be_receive_capable(self):
        instrument = self.create_instrument(
            owner=self.beneficiary,
            can_fund=True,
            can_receive=False,
            secure_reference="secure-ref-005",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                instrument=instrument,
                idempotency_key="execution-idempotency-026",
            )

    def test_receive_instrument_must_belong_to_payer(self):
        payment = self.create_receive_payment()

        instrument = self.create_instrument(
            owner=self.beneficiary,
            can_fund=True,
            secure_reference="secure-ref-006",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=payment,
                route_type=PaymentExecution.RouteType.CARD,
                provider="test_provider",
                instrument=instrument,
                idempotency_key="execution-idempotency-027",
            )

    def test_receive_instrument_must_be_funding_capable(self):
        payment = self.create_receive_payment()

        instrument = self.create_instrument(
            owner=self.payer,
            can_fund=False,
            can_receive=True,
            secure_reference="secure-ref-007",
        )

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=payment,
                route_type=PaymentExecution.RouteType.CARD,
                provider="test_provider",
                instrument=instrument,
                idempotency_key="execution-idempotency-028",
            )

    def test_active_verified_instrument_can_be_used(self):
        instrument = self.create_instrument(
            owner=self.beneficiary,
            can_receive=True,
            secure_reference="secure-ref-008",
        )

        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            instrument=instrument,
            idempotency_key="execution-idempotency-029",
        )

        self.assertEqual(
            execution.instrument_id,
            instrument.id,
        )

    def test_unusable_instrument_is_rejected(self):
        instrument = self.create_instrument(
            owner=self.beneficiary,
            can_receive=True,
            secure_reference="secure-ref-009",
        )

        instrument.status = PaymentInstrument.Status.BLOCKED
        instrument.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            PaymentExecutionService.create_execution(
                payment=self.payment,
                route_type=PaymentExecution.RouteType.BANK_TRANSFER,
                provider="test_provider",
                instrument=instrument,
                idempotency_key="execution-idempotency-030",
            )

    def test_execution_without_instrument_is_allowed(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            instrument=None,
            idempotency_key="execution-idempotency-031",
        )

        self.assertIsNone(execution.instrument_id)

    def test_execution_does_not_call_provider(self):
        execution = PaymentExecutionService.create_execution(
            payment=self.payment,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            idempotency_key="execution-idempotency-032",
        )

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CREATED,
        )

        self.assertEqual(
            execution.provider_reference,
            "",
        )