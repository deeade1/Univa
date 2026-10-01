from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from commissions.models import CommissionPlan
from commissions.services import (
    CommissionCalculationResult,
    CommissionCalculator,
)


class CommissionCalculatorTests(TestCase):
    def test_percentage_commission(self):
        plan = CommissionPlan.objects.create(
            name="Percentage 10%",
            code="TEST_PERCENTAGE_10",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("100000.00"),
        )

        self.assertIsInstance(
            result,
            CommissionCalculationResult,
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

        self.assertEqual(
            result.plan_type,
            CommissionPlan.PlanType.PERCENTAGE,
        )

    def test_percentage_commission_is_rounded_to_two_decimal_places(self):
        plan = CommissionPlan.objects.create(
            name="Percentage 7.5%",
            code="TEST_PERCENTAGE_7_5",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("7.5000"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("100.01"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("7.50"),
        )

    def test_fixed_commission(self):
        plan = CommissionPlan.objects.create(
            name="Fixed 5000",
            code="TEST_FIXED_5000",
            plan_type=CommissionPlan.PlanType.FIXED,
            fixed_amount=Decimal("5000.00"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("100000.00"),
        )

        self.assertEqual(
            result.calculation_basis,
            Decimal("100000.00"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("5000.00"),
        )

        self.assertIsNone(result.rate)

        self.assertEqual(
            result.plan_type,
            CommissionPlan.PlanType.FIXED,
        )

    def test_fixed_commission_is_independent_of_calculation_basis(self):
        plan = CommissionPlan.objects.create(
            name="Fixed 2500",
            code="TEST_FIXED_2500",
            plan_type=CommissionPlan.PlanType.FIXED,
            fixed_amount=Decimal("2500.00"),
        )

        first = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("10000.00"),
        )

        second = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("1000000.00"),
        )

        self.assertEqual(
            first.calculated_amount,
            Decimal("2500.00"),
        )

        self.assertEqual(
            second.calculated_amount,
            Decimal("2500.00"),
        )

    def test_zero_calculation_basis_is_valid(self):
        plan = CommissionPlan.objects.create(
            name="Percentage Zero Basis",
            code="TEST_ZERO_BASIS",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=Decimal("0.00"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("0.00"),
        )

    def test_negative_calculation_basis_is_rejected(self):
        plan = CommissionPlan.objects.create(
            name="Negative Basis Test",
            code="TEST_NEGATIVE_BASIS",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan=plan,
                calculation_basis=Decimal("-100.00"),
            )

    def test_float_calculation_basis_is_rejected(self):
        plan = CommissionPlan.objects.create(
            name="Float Basis Test",
            code="TEST_FLOAT_BASIS",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan=plan,
                calculation_basis=100000.00,
            )

    def test_percentage_plan_requires_percentage(self):
        plan = CommissionPlan.objects.create(
            name="Missing Percentage",
            code="TEST_MISSING_PERCENTAGE",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
        )

        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan=plan,
                calculation_basis=Decimal("100000.00"),
            )

    def test_fixed_plan_requires_fixed_amount(self):
        plan = CommissionPlan.objects.create(
            name="Missing Fixed Amount",
            code="TEST_MISSING_FIXED_AMOUNT",
            plan_type=CommissionPlan.PlanType.FIXED,
        )

        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan=plan,
                calculation_basis=Decimal("100000.00"),
            )

    def test_tiered_plan_is_not_yet_supported(self):
        plan = CommissionPlan.objects.create(
            name="Tiered Test",
            code="TEST_TIERED",
            plan_type=CommissionPlan.PlanType.TIERED,
        )

        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan=plan,
                calculation_basis=Decimal("100000.00"),
            )

    def test_invalid_plan_object_is_rejected(self):
        with self.assertRaises(ValidationError):
            CommissionCalculator.calculate(
                plan="not-a-plan",
                calculation_basis=Decimal("100000.00"),
            )

    def test_decimal_string_basis_is_supported(self):
        plan = CommissionPlan.objects.create(
            name="Decimal String Test",
            code="TEST_DECIMAL_STRING",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis="100000.00",
        )

        self.assertEqual(
            result.calculation_basis,
            Decimal("100000.00"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("10000.00"),
        )

    def test_integer_basis_is_supported(self):
        plan = CommissionPlan.objects.create(
            name="Integer Basis Test",
            code="TEST_INTEGER_BASIS",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=100000,
        )

        self.assertEqual(
            result.calculation_basis,
            Decimal("100000"),
        )

        self.assertEqual(
            result.calculated_amount,
            Decimal("10000.00"),
        )