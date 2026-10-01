"""
Settlement model tests.

These tests cover only the Settlement model contract.

They intentionally do not test:

    - SettlementService
    - SettlementLifecycle
    - SettlementAttempt
    - Payment
    - Banking
    - external providers
"""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from settlements.models import Settlement


class SettlementModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="settlement@example.com",
            password="test-password",
        )

    def build_settlement(self, **overrides):
        defaults = {
            "reference": "SET-TEST-001",
            "beneficiary": self.user,
            "source_type": "earning",
            "source_id": "earning-001",
            "source_reference": "EARN-001",
            "amount": Decimal("50000.00"),
            "currency": "NGN",
            "status": Settlement.Status.PENDING,
            "idempotency_key": "settlement-test-key-001",
        }

        defaults.update(overrides)

        return Settlement(**defaults)

    def test_creates_valid_pending_settlement(self):
        settlement = self.build_settlement()

        settlement.full_clean()
        settlement.save()

        self.assertIsInstance(settlement.id, UUID)
        self.assertEqual(
            settlement.status,
            Settlement.Status.PENDING,
        )
        self.assertEqual(
            settlement.amount,
            Decimal("50000.00"),
        )
        self.assertEqual(
            settlement.currency,
            "NGN",
        )

    def test_default_status_is_pending(self):
        settlement = self.build_settlement()

        self.assertEqual(
            settlement.status,
            Settlement.Status.PENDING,
        )

    def test_default_currency_is_ngn(self):
        settlement = self.build_settlement()

        self.assertEqual(
            settlement.currency,
            "NGN",
        )

    def test_currency_is_normalized_to_uppercase(self):
        settlement = self.build_settlement(
            currency="usd",
        )

        settlement.full_clean()

        self.assertEqual(
            settlement.currency,
            "USD",
        )

    def test_amount_must_be_positive(self):
        settlement = self.build_settlement(
            amount=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_negative_amount_is_invalid(self):
        settlement = self.build_settlement(
            amount=Decimal("-100.00"),
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_source_type_is_required(self):
        settlement = self.build_settlement(
            source_type="",
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_source_id_is_required(self):
        settlement = self.build_settlement(
            source_id="",
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_idempotency_key_is_required(self):
        settlement = self.build_settlement(
            idempotency_key="",
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_settled_requires_settled_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.SETTLED,
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_settled_accepts_settled_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.SETTLED,
            settled_at=timezone.now(),
        )

        settlement.full_clean()

    def test_failed_requires_failed_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.FAILED,
            failure_reason="Provider rejected settlement.",
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_failed_requires_failure_reason(self):
        settlement = self.build_settlement(
            status=Settlement.Status.FAILED,
            failed_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_failed_accepts_failure_information(self):
        settlement = self.build_settlement(
            status=Settlement.Status.FAILED,
            failed_at=timezone.now(),
            failure_code="PROVIDER_REJECTED",
            failure_reason="Provider rejected settlement.",
        )

        settlement.full_clean()

    def test_failure_information_is_not_allowed_for_non_failed_status(self):
        settlement = self.build_settlement(
            failure_code="PROVIDER_ERROR",
            failure_reason="Unexpected failure.",
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_eligible_requires_eligible_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.ELIGIBLE,
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_processing_requires_processing_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.PROCESSING,
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_cancelled_requires_cancelled_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_reversed_requires_reversed_at(self):
        settlement = self.build_settlement(
            status=Settlement.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_reference_is_unique(self):
        first = self.build_settlement()

        first.full_clean()
        first.save()

        second = self.build_settlement(
            idempotency_key="settlement-test-key-002",
        )

        with self.assertRaises(IntegrityError):
            second.save()

    def test_idempotency_key_is_unique(self):
        first = self.build_settlement()

        first.full_clean()
        first.save()

        second = self.build_settlement(
            reference="SET-TEST-002",
        )

        with self.assertRaises(IntegrityError):
            second.save()

    def test_beneficiary_uses_protect_delete_behavior(self):
        settlement = self.build_settlement()

        settlement.full_clean()
        settlement.save()

        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_financial_identity_cannot_change_after_processing(self):
        settlement = self.build_settlement(
            status=Settlement.Status.PROCESSING,
            processing_at=timezone.now(),
        )

        settlement.full_clean()
        settlement.save()

        settlement.amount = Decimal("75000.00")

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_source_cannot_change_after_processing(self):
        settlement = self.build_settlement(
            status=Settlement.Status.PROCESSING,
            processing_at=timezone.now(),
        )

        settlement.full_clean()
        settlement.save()

        settlement.source_id = "different-source"

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_beneficiary_cannot_change_after_processing(self):
        settlement = self.build_settlement(
            status=Settlement.Status.PROCESSING,
            processing_at=timezone.now(),
        )

        settlement.full_clean()
        settlement.save()

        other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        settlement.beneficiary = other_user

        with self.assertRaises(ValidationError):
            settlement.full_clean()

    def test_status_properties(self):
        statuses = {
            Settlement.Status.PENDING: "is_pending",
            Settlement.Status.ELIGIBLE: "is_eligible",
            Settlement.Status.PROCESSING: "is_processing",
            Settlement.Status.SETTLED: "is_settled",
            Settlement.Status.FAILED: "is_failed",
            Settlement.Status.CANCELLED: "is_cancelled",
            Settlement.Status.REVERSED: "is_reversed",
        }

        for status, property_name in statuses.items():
            settlement = self.build_settlement(
                status=status,
            )

            if status == Settlement.Status.ELIGIBLE:
                settlement.eligible_at = timezone.now()

            elif status == Settlement.Status.PROCESSING:
                settlement.processing_at = timezone.now()

            elif status == Settlement.Status.SETTLED:
                settlement.settled_at = timezone.now()

            elif status == Settlement.Status.FAILED:
                settlement.failed_at = timezone.now()
                settlement.failure_reason = "Test failure."

            elif status == Settlement.Status.CANCELLED:
                settlement.cancelled_at = timezone.now()

            elif status == Settlement.Status.REVERSED:
                settlement.reversed_at = timezone.now()

            settlement.full_clean()

            self.assertTrue(
                getattr(settlement, property_name)
            )

    def test_string_representation_uses_reference(self):
        settlement = self.build_settlement()

        self.assertEqual(
            str(settlement),
            "SET-TEST-001",
        )

    def test_metadata_defaults_to_empty_dict(self):
        settlement = self.build_settlement()

        self.assertEqual(
            settlement.metadata,
            {},
        )

    def test_source_reference_is_optional(self):
        settlement = self.build_settlement(
            source_reference="",
        )

        settlement.full_clean()
