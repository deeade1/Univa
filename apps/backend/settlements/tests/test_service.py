"""
SettlementService tests.

These tests cover settlement creation and idempotency.

They intentionally do not test:

    - SettlementLifecycle
    - SettlementAttempt
    - Payment
    - Banking
    - external providers
    - Audit
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from settlements.models import Settlement
from settlements.services import SettlementService


class SettlementServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="settlement-service@example.com",
            password="test-password",
        )

    def build_kwargs(self, **overrides):
        defaults = {
            "reference": "SET-SERVICE-001",
            "beneficiary": self.user,
            "source_type": "earning",
            "source_id": "earning-001",
            "source_reference": "EARN-001",
            "amount": Decimal("50000.00"),
            "currency": "NGN",
            "idempotency_key": "settlement-service-key-001",
            "notes": "",
            "metadata": {},
        }

        defaults.update(overrides)

        return defaults

    def test_creates_pending_settlement(self):
        settlement = SettlementService.create_settlement(
            **self.build_kwargs()
        )

        self.assertIsNotNone(settlement.pk)
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

    def test_normalizes_currency(self):
        settlement = SettlementService.create_settlement(
            **self.build_kwargs(
                currency="usd",
            )
        )

        self.assertEqual(
            settlement.currency,
            "USD",
        )

    def test_normalizes_string_amount(self):
        settlement = SettlementService.create_settlement(
            **self.build_kwargs(
                amount="12500.50",
            )
        )

        self.assertEqual(
            settlement.amount,
            Decimal("12500.50"),
        )

    def test_rejects_missing_amount(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    amount=None,
                )
            )

    def test_rejects_invalid_amount(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    amount="invalid",
                )
            )

    def test_rejects_zero_amount(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    amount=Decimal("0.00"),
                )
            )

    def test_rejects_negative_amount(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    amount=Decimal("-100.00"),
                )
            )

    def test_requires_beneficiary(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    beneficiary=None,
                )
            )

    def test_requires_source_type(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    source_type="",
                )
            )

    def test_requires_source_id(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    source_id="",
                )
            )

    def test_requires_idempotency_key(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    idempotency_key="",
                )
            )

    def test_requires_reference(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    reference="",
                )
            )

    def test_requires_currency(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    currency="",
                )
            )

    def test_rejects_invalid_currency(self):
        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    currency="US",
                )
            )

    def test_idempotency_returns_existing_settlement(self):
        first = SettlementService.create_settlement(
            **self.build_kwargs()
        )

        second = SettlementService.create_settlement(
            **self.build_kwargs()
        )

        self.assertEqual(
            first.pk,
            second.pk,
        )

        self.assertEqual(
            Settlement.objects.count(),
            1,
        )

    def test_idempotency_rejects_different_amount(self):
        SettlementService.create_settlement(
            **self.build_kwargs()
        )

        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    amount=Decimal("75000.00"),
                )
            )

    def test_idempotency_rejects_different_source(self):
        SettlementService.create_settlement(
            **self.build_kwargs()
        )

        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    source_id="earning-999",
                )
            )

    def test_idempotency_rejects_different_beneficiary(self):
        SettlementService.create_settlement(
            **self.build_kwargs()
        )

        other_user = User.objects.create_user(
            email="other-settlement@example.com",
            password="test-password",
        )

        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    beneficiary=other_user,
                )
            )

    def test_idempotency_rejects_different_currency(self):
        SettlementService.create_settlement(
            **self.build_kwargs(
                currency="NGN",
            )
        )

        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    currency="USD",
                )
            )

    def test_idempotency_rejects_different_reference(self):
        SettlementService.create_settlement(
            **self.build_kwargs()
        )

        with self.assertRaises(ValidationError):
            SettlementService.create_settlement(
                **self.build_kwargs(
                    reference="SET-SERVICE-999",
                )
            )

    def test_metadata_is_preserved(self):
        metadata = {
            "origin": "commission",
            "commission_id": "commission-001",
        }

        settlement = SettlementService.create_settlement(
            **self.build_kwargs(
                metadata=metadata,
            )
        )

        self.assertEqual(
            settlement.metadata,
            metadata,
        )

    def test_source_reference_is_preserved(self):
        settlement = SettlementService.create_settlement(
            **self.build_kwargs(
                source_reference="EARNING-REFERENCE-001",
            )
        )

        self.assertEqual(
            settlement.source_reference,
            "EARNING-REFERENCE-001",
        )

    def test_new_settlement_does_not_start_in_processing(self):
        settlement = SettlementService.create_settlement(
            **self.build_kwargs()
        )

        self.assertEqual(
            settlement.status,
            Settlement.Status.PENDING,
        )
        self.assertIsNone(
            settlement.processing_at,
        )