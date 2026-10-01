from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from commissions.models import (
    Commission,
    CommissionAllocation,
    CommissionPlan,
)


class CommissionPlanModelTests(TestCase):
    def setUp(self):
        self.plan = CommissionPlan.objects.create(
            name="Property Agent 10%",
            code="PROPERTY_AGENT_10",
            description="Standard property agent commission.",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

    def test_plan_is_created(self):
        self.assertEqual(
            self.plan.name,
            "Property Agent 10%",
        )

        self.assertEqual(
            self.plan.code,
            "PROPERTY_AGENT_10",
        )

        self.assertEqual(
            self.plan.plan_type,
            CommissionPlan.PlanType.PERCENTAGE,
        )

    def test_percentage_property(self):
        self.assertTrue(self.plan.is_percentage)
        self.assertFalse(self.plan.is_fixed)
        self.assertFalse(self.plan.is_tiered)

    def test_fixed_property(self):
        plan = CommissionPlan.objects.create(
            name="Fixed Referral",
            code="FIXED_REFERRAL",
            plan_type=CommissionPlan.PlanType.FIXED,
            fixed_amount=Decimal("5000.00"),
        )

        self.assertTrue(plan.is_fixed)
        self.assertFalse(plan.is_percentage)
        self.assertFalse(plan.is_tiered)

    def test_tiered_property(self):
        plan = CommissionPlan.objects.create(
            name="Tiered Partner",
            code="TIERED_PARTNER",
            plan_type=CommissionPlan.PlanType.TIERED,
        )

        self.assertTrue(plan.is_tiered)

    def test_negative_percentage_is_rejected(self):
        plan = CommissionPlan(
            name="Invalid Percentage",
            code="INVALID_PERCENTAGE",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("-1.0000"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_percentage_above_100_is_rejected(self):
        plan = CommissionPlan(
            name="Invalid Percentage",
            code="INVALID_PERCENTAGE_100",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("100.0001"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()


class CommissionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="commission@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Transport Agent 10%",
            code="TRANSPORT_AGENT_10",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

    def _create_commission(self, **overrides):
        values = {
            "plan": self.plan,
            "beneficiary": self.user,
            "source_type": Commission.SourceType.TRANSPORT,
            "source_id": "trip-001",
            "calculation_basis": Decimal("100000.00"),
            "rate": Decimal("10.0000"),
            "calculated_amount": Decimal("10000.00"),
            "currency": "NGN",
            "status": Commission.Status.CALCULATED,
        }

        values.update(overrides)

        return Commission.objects.create(**values)

    def test_commission_is_created(self):
        commission = self._create_commission()

        self.assertEqual(
            commission.calculated_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission.status,
            Commission.Status.CALCULATED,
        )

    def test_negative_calculation_basis_is_rejected(self):
        commission = self._create_commission(
            calculation_basis=Decimal("-100.00"),
        )

        with self.assertRaises(ValidationError):
            commission.full_clean()

    def test_negative_calculated_amount_is_rejected(self):
        commission = self._create_commission(
            calculated_amount=Decimal("-100.00"),
        )

        with self.assertRaises(ValidationError):
            commission.full_clean()

    def test_settled_commission_requires_settled_at(self):
        commission = self._create_commission(
            status=Commission.Status.SETTLED,
        )

        with self.assertRaises(ValidationError):
            commission.full_clean()

    def test_reversed_commission_requires_reversed_at(self):
        commission = self._create_commission(
            status=Commission.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            commission.full_clean()

    def test_status_properties(self):
        commission = self._create_commission()

        self.assertFalse(commission.is_pending)
        self.assertTrue(commission.is_calculated)
        self.assertFalse(commission.is_approved)
        self.assertFalse(commission.is_payable)
        self.assertFalse(commission.is_settled)
        self.assertFalse(commission.is_cancelled)
        self.assertFalse(commission.is_reversed)


class CommissionAllocationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="allocation@example.com",
            password="test-password",
        )

        self.second_user = User.objects.create_user(
            email="allocation2@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Property Agent 10%",
            code="PROPERTY_AGENT_10",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        self.commission = Commission.objects.create(
            plan=self.plan,
            beneficiary=self.user,
            source_type=Commission.SourceType.REAL_ESTATE,
            source_id="property-sale-001",
            calculation_basis=Decimal("1000000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("100000.00"),
            currency="NGN",
            status=Commission.Status.CALCULATED,
        )

    def test_allocation_is_created(self):
        allocation = CommissionAllocation.objects.create(
            commission=self.commission,
            beneficiary=self.second_user,
            amount=Decimal("100000.00"),
        )

        self.assertEqual(
            allocation.amount,
            Decimal("100000.00"),
        )

        self.assertEqual(
            allocation.currency,
            "NGN",
        )

    def test_negative_allocation_is_rejected(self):
        allocation = CommissionAllocation(
            commission=self.commission,
            beneficiary=self.second_user,
            amount=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            allocation.full_clean()

    def test_allocation_cannot_exceed_commission(self):
        allocation = CommissionAllocation(
            commission=self.commission,
            beneficiary=self.second_user,
            amount=Decimal("100001.00"),
        )

        with self.assertRaises(ValidationError):
            allocation.full_clean()