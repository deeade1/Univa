# apps/backend/earnings/tests/test_models.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from earnings.models import (
    Earning,
    EarningAdjustment,
    EarningType,
)


class EarningModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="model-user@example.com",
            password="test-password",
        )

        self.type = EarningType.objects.create(
            code="SERVICE",
            name="Service",
        )

    def make_earning(self, **overrides):
        values = {
            "beneficiary": self.user,
            "earning_type": self.type,
            "source_type": "transport",
            "source_id": "delivery-model-001",
            "amount": Decimal("5000.00"),
            "currency": "NGN",
            "status": Earning.Status.CALCULATED,
            "earned_at": "2026-09-27T10:00:00Z",
            "calculated_at": "2026-09-27T10:01:00Z",
        }

        values.update(overrides)

        return Earning.objects.create(**values)

    def test_earning_type_string(self):
        self.assertEqual(
            str(self.type),
            "Service (SERVICE)",
        )

    def test_earning_string(self):
        earning = self.make_earning()

        self.assertIn(
            "5000.00",
            str(earning),
        )

    def test_negative_amount_is_rejected(self):
        earning = self.make_earning(
            amount=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            earning.full_clean()

    def test_confirmed_requires_timestamp(self):
        earning = self.make_earning(
            status=Earning.Status.CONFIRMED,
            confirmed_at=None,
        )

        with self.assertRaises(ValidationError):
            earning.full_clean()

    def test_payable_requires_timestamp(self):
        earning = self.make_earning(
            status=Earning.Status.PAYABLE,
            payable_at=None,
        )

        with self.assertRaises(ValidationError):
            earning.full_clean()

    def test_settled_requires_timestamp(self):
        earning = self.make_earning(
            status=Earning.Status.SETTLED,
            settled_at=None,
        )

        with self.assertRaises(ValidationError):
            earning.full_clean()

    def test_reversed_requires_timestamp(self):
        earning = self.make_earning(
            status=Earning.Status.REVERSED,
            reversed_at=None,
        )

        with self.assertRaises(ValidationError):
            earning.full_clean()

    def test_zero_adjustment_is_rejected(self):
        earning = self.make_earning()

        adjustment = EarningAdjustment(
            earning=earning,
            adjustment_type=(
                EarningAdjustment.AdjustmentType.CORRECTION
            ),
            amount=Decimal("0.00"),
            reason="No-op",
        )

        with self.assertRaises(ValidationError):
            adjustment.full_clean()

    def test_negative_adjustment_is_allowed(self):
        earning = self.make_earning()

        adjustment = EarningAdjustment(
            earning=earning,
            adjustment_type=(
                EarningAdjustment.AdjustmentType.CORRECTION
            ),
            amount=Decimal("-500.00"),
            reason="Correction",
        )

        adjustment.full_clean()