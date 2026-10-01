# apps/backend/earnings/tests/test_calculator.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from earnings.services import (
    EarningCalculator,
)


class EarningCalculatorTests(SimpleTestCase):

    def test_percentage_calculation(self):
        result = EarningCalculator.calculate_percentage(
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
        )

        self.assertEqual(
            result.calculation_basis,
            Decimal("100000.00"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            result.rate,
            Decimal("10.0000"),
        )

    def test_percentage_calculation_preserves_metadata(self):
        result = EarningCalculator.calculate_percentage(
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            metadata={
                "rule_code": "SERVICE_V1",
            },
        )

        self.assertEqual(
            result.calculation_metadata["rule_code"],
            "SERVICE_V1",
        )

    def test_fixed_calculation(self):
        result = EarningCalculator.calculate_fixed(
            amount=Decimal("5000.00"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("5000.00"),
        )

        self.assertIsNone(result.rate)
        self.assertIsNone(result.calculation_basis)

    def test_percentage_rounds_to_money_precision(self):
        result = EarningCalculator.calculate_percentage(
            calculation_basis=Decimal("100.00"),
            rate=Decimal("33.3333"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("33.33"),
        )

    def test_float_is_rejected(self):
        with self.assertRaises(ValidationError):
            EarningCalculator.calculate_percentage(
                calculation_basis=1000.0,
                rate=Decimal("10.00"),
            )

    def test_negative_basis_is_rejected(self):
        with self.assertRaises(ValidationError):
            EarningCalculator.calculate_percentage(
                calculation_basis=Decimal("-100.00"),
                rate=Decimal("10.00"),
            )

    def test_negative_rate_is_rejected(self):
        with self.assertRaises(ValidationError):
            EarningCalculator.calculate_percentage(
                calculation_basis=Decimal("100.00"),
                rate=Decimal("-10.00"),
            )

    def test_rate_above_one_hundred_is_rejected(self):
        with self.assertRaises(ValidationError):
            EarningCalculator.calculate_percentage(
                calculation_basis=Decimal("100.00"),
                rate=Decimal("100.01"),
            )

    def test_negative_fixed_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            EarningCalculator.calculate_fixed(
                amount=Decimal("-1.00"),
            )