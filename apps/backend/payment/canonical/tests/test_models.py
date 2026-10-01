from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from payment.canonical.execution import PaymentExecution
from payment.canonical.execution_event import PaymentExecutionEvent
from payment.canonical.instrument import PaymentInstrument
from payment.canonical.payment import Payment


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payment-user@example.com",
        )

    def make_payment(self, **overrides):
        data = {
            "reference": "PAY-TEST-001",
            "direction": Payment.Direction.DISBURSE,
            "purpose": Payment.Purpose.EARNING,
            "source_type": "settlement",
            "source_id": "SET-001",
            "source_reference": "SET-REF-001",
            "beneficiary": self.user,
            "amount": Decimal("10000.00"),
            "currency": "NGN",
            "idempotency_key": "payment-idempotency-001",
        }
        data.update(overrides)

        payment = Payment(**data)
        payment.full_clean()
        payment.save()

        return payment

    def test_valid_payment(self):
        payment = self.make_payment()

        self.assertEqual(payment.reference, "PAY-TEST-001")
        self.assertEqual(payment.amount, Decimal("10000.00"))
        self.assertEqual(payment.currency, "NGN")
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_payment_amount_must_be_greater_than_zero(self):
        payment = Payment(
            reference="PAY-TEST-002",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-002",
            beneficiary=self.user,
            amount=Decimal("0.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-002",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_amount_cannot_be_negative(self):
        payment = Payment(
            reference="PAY-TEST-003",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-003",
            beneficiary=self.user,
            amount=Decimal("-1.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-003",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_currency_is_normalized_to_uppercase(self):
        payment = Payment(
            reference="PAY-TEST-004",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-004",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="ngn",
            idempotency_key="payment-idempotency-004",
        )

        payment.full_clean()

        self.assertEqual(payment.currency, "NGN")

    def test_currency_must_have_three_characters(self):
        payment = Payment(
            reference="PAY-TEST-005",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-005",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="US",
            idempotency_key="payment-idempotency-005",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_source_type_is_required(self):
        payment = Payment(
            reference="PAY-TEST-006",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="",
            source_id="SET-006",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-006",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_source_id_is_required(self):
        payment = Payment(
            reference="PAY-TEST-007",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-007",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_disbursement_requires_beneficiary(self):
        payment = Payment(
            reference="PAY-TEST-008",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-008",
            beneficiary=None,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-008",
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_receive_payment_may_have_external_payer(self):
        payment = Payment(
            reference="PAY-TEST-009",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="ORDER-009",
            payer=None,
            beneficiary=None,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-009",
        )

        payment.full_clean()

        self.assertIsNone(payment.payer_id)
        self.assertIsNone(payment.beneficiary_id)

    def test_payment_starts_pending(self):
        payment = self.make_payment()

        self.assertTrue(payment.is_pending)
        self.assertFalse(payment.is_processing)
        self.assertFalse(payment.is_completed)
        self.assertFalse(payment.is_failed)
        self.assertFalse(payment.is_cancelled)
        self.assertFalse(payment.is_reversed)

    def test_status_helpers(self):
        payment = self.make_payment()

        statuses = [
            (Payment.Status.PENDING, "is_pending"),
            (Payment.Status.PROCESSING, "is_processing"),
            (Payment.Status.COMPLETED, "is_completed"),
            (Payment.Status.FAILED, "is_failed"),
            (Payment.Status.CANCELLED, "is_cancelled"),
            (Payment.Status.REVERSED, "is_reversed"),
        ]

        for status, property_name in statuses:
            with self.subTest(status=status):
                payment.status = status
                self.assertTrue(getattr(payment, property_name))

    def test_terminal_status_property(self):
        payment = self.make_payment()

        for status in (
            Payment.Status.COMPLETED,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
            Payment.Status.REVERSED,
        ):
            with self.subTest(status=status):
                payment.status = status
                self.assertTrue(payment.is_terminal)

        payment.status = Payment.Status.PENDING
        self.assertFalse(payment.is_terminal)

        payment.status = Payment.Status.PROCESSING
        self.assertFalse(payment.is_terminal)

    def test_payment_business_fields_are_immutable_after_processing(self):
        payment = self.make_payment()

        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["status"])

        payment.amount = Decimal("20000.00")

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_direction_is_immutable_after_processing(self):
        payment = self.make_payment()

        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["status"])

        payment.direction = Payment.Direction.RECEIVE

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_source_is_immutable_after_processing(self):
        payment = self.make_payment()

        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["status"])

        payment.source_id = "OTHER-SOURCE"

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_currency_is_immutable_after_processing(self):
        payment = self.make_payment()

        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["status"])

        payment.currency = "USD"

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_reference_is_unique(self):
        self.make_payment()

        duplicate = Payment(
            reference="PAY-TEST-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-DUPLICATE",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-duplicate",
        )

        with self.assertRaises(IntegrityError):
            duplicate.save()

    def test_payment_idempotency_key_is_unique(self):
        self.make_payment()

        duplicate = Payment(
            reference="PAY-TEST-IDEMP-002",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-IDEMP-002",
            beneficiary=self.user,
            amount=Decimal("100.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-001",
        )

        with self.assertRaises(IntegrityError):
            duplicate.save()


class PaymentExecutionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="execution-user@example.com",
        )

        self.payment = Payment.objects.create(
            reference="PAY-EXEC-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-EXEC-001",
            beneficiary=self.user,
            amount=Decimal("10000.00"),
            currency="NGN",
            idempotency_key="payment-exec-idempotency-001",
        )

    def make_execution(self, **overrides):
        data = {
            "reference": "PEXEC-TEST-001",
            "payment": self.payment,
            "attempt_number": 1,
            "idempotency_key": "execution-idempotency-001",
            "route_type": PaymentExecution.RouteType.BANK_TRANSFER,
            "provider": "test_provider",
        }
        data.update(overrides)

        execution = PaymentExecution(**data)
        execution.full_clean()
        execution.save()

        return execution

    def test_valid_execution(self):
        execution = self.make_execution()

        self.assertEqual(execution.payment, self.payment)
        self.assertEqual(execution.attempt_number, 1)
        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CREATED,
        )

    def test_attempt_number_must_be_positive(self):
        execution = PaymentExecution(
            reference="PEXEC-TEST-002",
            payment=self.payment,
            attempt_number=0,
            idempotency_key="execution-idempotency-002",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
        )

        with self.assertRaises(ValidationError):
            execution.full_clean()

    def test_provider_is_required(self):
        execution = PaymentExecution(
            reference="PEXEC-TEST-003",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-idempotency-003",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="",
        )

        with self.assertRaises(ValidationError):
            execution.full_clean()

    def test_failed_execution_requires_failure_reason(self):
        execution = PaymentExecution(
            reference="PEXEC-TEST-004",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-idempotency-004",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            execution.full_clean()

    def test_failed_execution_accepts_failure_information(self):
        execution = self.make_execution(
            reference="PEXEC-TEST-005",
            idempotency_key="execution-idempotency-005",
            status=PaymentExecution.Status.FAILED,
            failure_code="PROVIDER_ERROR",
            failure_reason="Provider rejected the operation.",
        )

        self.assertTrue(execution.is_failed)

    def test_failure_information_is_not_allowed_for_non_failed_execution(
        self,
    ):
        execution = PaymentExecution(
            reference="PEXEC-TEST-006",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-idempotency-006",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            failure_reason="Unexpected failure information.",
        )

        with self.assertRaises(ValidationError):
            execution.full_clean()

    def test_pending_execution_requires_reconciliation_state(self):
        execution = PaymentExecution(
            reference="PEXEC-TEST-007",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-idempotency-007",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
        )

        with self.assertRaises(ValidationError):
            execution.full_clean()

    def test_pending_execution_with_required_reconciliation_is_valid(self):
        execution = self.make_execution(
            reference="PEXEC-TEST-008",
            idempotency_key="execution-idempotency-008",
            status=PaymentExecution.Status.PENDING,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.REQUIRED
            ),
        )

        self.assertTrue(execution.is_pending)
        self.assertTrue(execution.requires_reconciliation)

    def test_execution_identity_is_immutable(self):
        execution = self.make_execution(
            reference="PEXEC-TEST-009",
            idempotency_key="execution-idempotency-009",
        )

        execution.provider = "another_provider"

        with self.assertRaises(ValidationError):
            execution.full_clean()


    def test_execution_attempt_number_is_unique_per_payment(self):
        self.make_execution()

        duplicate = PaymentExecution(
            reference="PEXEC-TEST-010",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-idempotency-010",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_execution_status_helpers(self):
        execution = self.make_execution()

        statuses = [
            (PaymentExecution.Status.CREATED, "is_created"),
            (PaymentExecution.Status.PROCESSING, "is_processing"),
            (PaymentExecution.Status.PENDING, "is_pending"),
            (PaymentExecution.Status.COMPLETED, "is_completed"),
            (PaymentExecution.Status.FAILED, "is_failed"),
            (PaymentExecution.Status.CANCELLED, "is_cancelled"),
        ]

        for status, property_name in statuses:
            with self.subTest(status=status):
                execution.status = status

                if status == PaymentExecution.Status.PENDING:
                    execution.reconciliation_state = (
                        PaymentExecution.ReconciliationState.REQUIRED
                    )

                if status == PaymentExecution.Status.FAILED:
                    execution.failure_reason = "Test failure."

                self.assertTrue(getattr(execution, property_name))


class PaymentExecutionEventModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="event-user@example.com",
        )

        self.payment = Payment.objects.create(
            reference="PAY-EVENT-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="settlement",
            source_id="SET-EVENT-001",
            beneficiary=self.user,
            amount=Decimal("5000.00"),
            currency="NGN",
            idempotency_key="payment-event-idempotency-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="PEXEC-EVENT-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="execution-event-idempotency-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
        )

    def make_event(self, **overrides):
        now = timezone.now()

        data = {
            "execution": self.execution,
            "event_type": (
                PaymentExecutionEvent.EventType.CREATED
            ),
            "source": PaymentExecutionEvent.Source.SYSTEM,
            "occurred_at": now,
            "received_at": now,
        }
        data.update(overrides)

        event = PaymentExecutionEvent(**data)
        event.full_clean()
        event.save()

        return event

    def test_valid_system_event(self):
        event = self.make_event()

        self.assertEqual(event.execution, self.execution)
        self.assertEqual(
            event.event_type,
            PaymentExecutionEvent.EventType.CREATED,
        )

    def test_provider_event_requires_provider_event_id(self):
        event = PaymentExecutionEvent(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            occurred_at=timezone.now(),
            received_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_webhook_event_requires_provider_event_id(self):
        event = PaymentExecutionEvent(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.WEBHOOK,
            occurred_at=timezone.now(),
            received_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_provider_event_with_provider_event_id_is_valid(self):
        event = self.make_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-001",
            provider_reference="provider-ref-001",
        )

        self.assertEqual(
            event.provider_event_id,
            "provider-event-001",
        )
    
    
    def test_provider_event_id_is_unique_per_execution(self):
        self.make_event(
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-002",
        )

        duplicate = PaymentExecutionEvent(
            execution=self.execution,
            event_type=(
                PaymentExecutionEvent.EventType.PROVIDER_PENDING
            ),
            source=PaymentExecutionEvent.Source.PROVIDER,
            provider_event_id="provider-event-002",
            occurred_at=timezone.now(),
            received_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

class PaymentInstrumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="instrument-user@example.com",
        )

    def make_instrument(self, **overrides):
        data = {
            "reference": "PINS-TEST-001",
            "owner": self.user,
            "instrument_type": (
                PaymentInstrument.InstrumentType.BANK_ACCOUNT
            ),
            "institution": "test_bank",
            "can_fund": True,
            "can_receive": True,
            "secure_reference": "secure-ref-001",
            "display_reference": "****1234",
        }
        data.update(overrides)

        instrument = PaymentInstrument(**data)
        instrument.full_clean()
        instrument.save()

        return instrument

    def test_valid_instrument(self):
        instrument = self.make_instrument()

        self.assertEqual(instrument.owner, self.user)
        self.assertEqual(
            instrument.instrument_type,
            PaymentInstrument.InstrumentType.BANK_ACCOUNT,
        )
        self.assertTrue(instrument.can_fund)
        self.assertTrue(instrument.can_receive)

    def test_instrument_requires_institution(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-002",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="",
            can_fund=True,
            secure_reference="secure-ref-002",
            display_reference="****5678",
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_instrument_requires_secure_reference(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-003",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=True,
            secure_reference="",
            display_reference="****5678",
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_instrument_requires_display_reference(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-004",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=True,
            secure_reference="secure-ref-004",
            display_reference="",
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_instrument_requires_at_least_one_capability(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-005",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=False,
            can_receive=False,
            secure_reference="secure-ref-005",
            display_reference="****5678",
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_verified_instrument_requires_verified_at(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-006",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=True,
            secure_reference="secure-ref-006",
            display_reference="****5678",
            verification_status=(
                PaymentInstrument.VerificationStatus.VERIFIED
            ),
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_active_instrument_requires_verification(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-007",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=True,
            secure_reference="secure-ref-007",
            display_reference="****5678",
            status=PaymentInstrument.Status.ACTIVE,
            activated_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_active_instrument_requires_activation_timestamp(self):
        instrument = PaymentInstrument(
            reference="PINS-TEST-008",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.CARD,
            institution="test_bank",
            can_fund=True,
            secure_reference="secure-ref-008",
            display_reference="****5678",
            verification_status=(
                PaymentInstrument.VerificationStatus.VERIFIED
            ),
            verified_at=timezone.now(),
            status=PaymentInstrument.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_active_verified_instrument_is_valid(self):
        now = timezone.now()

        instrument = self.make_instrument(
            reference="PINS-TEST-009",
            secure_reference="secure-ref-009",
            verification_status=(
                PaymentInstrument.VerificationStatus.VERIFIED
            ),
            verified_at=now,
            status=PaymentInstrument.Status.ACTIVE,
            activated_at=now,
        )

        self.assertTrue(instrument.is_verified)
        self.assertTrue(instrument.is_active)
        self.assertTrue(instrument.can_be_used)

    def test_instrument_identity_is_immutable(self):
        instrument = self.make_instrument()

        instrument.institution = "another_bank"

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_instrument_secure_reference_is_immutable(self):
        instrument = self.make_instrument()

        instrument.secure_reference = "replacement-reference"

        with self.assertRaises(ValidationError):
            instrument.full_clean()

    def test_instrument_identity_is_unique(self):
        self.make_instrument()

        duplicate = PaymentInstrument(
            reference="PINS-TEST-010",
            owner=self.user,
            instrument_type=(
                PaymentInstrument.InstrumentType.BANK_ACCOUNT
            ),
            institution="test_bank",
            can_fund=True,
            can_receive=True,
            secure_reference="secure-ref-001",
            display_reference="****9999",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


    def test_instrument_status_helpers(self):
        instrument = self.make_instrument()

        instrument.status = PaymentInstrument.Status.BLOCKED
        self.assertTrue(instrument.is_blocked)

        instrument.status = PaymentInstrument.Status.EXPIRED
        self.assertTrue(instrument.is_expired)

        instrument.status = PaymentInstrument.Status.INACTIVE
        self.assertFalse(instrument.is_active)