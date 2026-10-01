# apps/backend/earnings/tests/test_earning.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from earnings.models import (
    Earning,
    EarningAdjustment,
    EarningType,
)
from earnings.services import EarningService


class EarningServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="earning-user@example.com",
            password="test-password",
        )

        self.type = EarningType.objects.create(
            code="SERVICE",
            name="Service",
            description="Service earning",
        )

    def test_create_earning(self):
        earned_at = timezone.now()

        earning = EarningService.create_earning(
            beneficiary=self.user,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-001",
            source_reference="DEL-001",
            amount=Decimal("5000.00"),
            currency="ngn",
            earned_at=earned_at,
        )

        self.assertEqual(
            earning.beneficiary,
            self.user,
        )

        self.assertEqual(
            earning.amount,
            Decimal("5000.00"),
        )

        self.assertEqual(
            earning.currency,
            "NGN",
        )

        self.assertEqual(
            earning.status,
            Earning.Status.CALCULATED,
        )

        self.assertIsNotNone(
            earning.calculated_at,
        )

    def test_create_earning_preserves_calculation_snapshot(self):
        earning = EarningService.create_earning(
            beneficiary=self.user,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-002",
            amount=Decimal("5000.00"),
            calculation_basis=Decimal("10000.00"),
            calculation_rate=Decimal("50.0000"),
            calculation_metadata={
                "rule_code": "DELIVERY_V1",
            },
        )

        self.assertEqual(
            earning.calculation_basis,
            Decimal("10000.00"),
        )

        self.assertEqual(
            earning.calculation_rate,
            Decimal("50.0000"),
        )

        self.assertEqual(
            earning.calculation_metadata["rule_code"],
            "DELIVERY_V1",
        )

    def test_create_earning_requires_source_type(self):
        with self.assertRaises(ValidationError):
            EarningService.create_earning(
                beneficiary=self.user,
                earning_type=self.type,
                source_type="",
                source_id="delivery-001",
                amount=Decimal("5000.00"),
            )

    def test_create_earning_requires_source_id(self):
        with self.assertRaises(ValidationError):
            EarningService.create_earning(
                beneficiary=self.user,
                earning_type=self.type,
                source_type="transport",
                source_id="",
                amount=Decimal("5000.00"),
            )

    def test_create_adjustment(self):
        earning = EarningService.create_earning(
            beneficiary=self.user,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-003",
            amount=Decimal("5000.00"),
        )

        adjustment = EarningService.create_adjustment(
            earning=earning,
            adjustment_type=EarningAdjustment.AdjustmentType.CORRECTION,
            amount=Decimal("-500.00"),
            reason="Correction",
            created_by=self.user,
        )

        self.assertEqual(
            adjustment.amount,
            Decimal("-500.00"),
        )

        self.assertEqual(
            adjustment.created_by,
            self.user,
        )

    def test_cancelled_earning_cannot_be_adjusted(self):
        earning = EarningService.create_earning(
            beneficiary=self.user,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-004",
            amount=Decimal("5000.00"),
        )

        earning.status = Earning.Status.CANCELLED
        earning.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            EarningService.create_adjustment(
                earning=earning,
                adjustment_type=EarningAdjustment.AdjustmentType.CORRECTION,
                amount=Decimal("-500.00"),
                reason="Correction",
                created_by=self.user,
            )