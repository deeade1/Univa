from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from commissions.models import (
    Commission,
    CommissionAllocation,
    CommissionPlan,
)
from earnings.models import EarningType
from earnings.services import CommissionEarningService


class CommissionEarningIntegrationTests(TestCase):

    def setUp(self):
        self.beneficiary = User.objects.create_user(
            email="commission-beneficiary@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Commission Integration Plan",
            code="COMMISSION_EARNING_INTEGRATION",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        self.earning_type = EarningType.objects.create(
            code="COMMISSION",
            name="Commission",
        )

    def make_commission(
        self,
        status=Commission.Status.APPROVED,
    ):
        return Commission.objects.create(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.REAL_ESTATE,
            source_id="transaction-001",
            source_reference="TXN-001",
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("10000.00"),
            currency="NGN",
            status=status,
        )

    def test_allocation_becomes_earning(self):
        commission = self.make_commission()

        allocation = CommissionAllocation.objects.create(
            commission=commission,
            beneficiary=self.beneficiary,
            amount=Decimal("10000.00"),
            allocation_percentage=Decimal("100.0000"),
        )

        earning = CommissionEarningService.create_from_allocation(
            allocation=allocation,
            earning_type=self.earning_type,
        )

        self.assertEqual(
            earning.beneficiary,
            self.beneficiary,
        )

        self.assertEqual(
            earning.amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            earning.currency,
            "NGN",
        )

        self.assertEqual(
            earning.source_type,
            "commission_allocation",
        )

        self.assertEqual(
            earning.source_id,
            str(allocation.id),
        )

        self.assertEqual(
            earning.calculation_metadata[
                "commission_id"
            ],
            str(commission.id),
        )

    def test_unapproved_commission_cannot_create_earning(self):
        commission = self.make_commission(
            status=Commission.Status.CALCULATED,
        )

        allocation = CommissionAllocation.objects.create(
            commission=commission,
            beneficiary=self.beneficiary,
            amount=Decimal("10000.00"),
            allocation_percentage=Decimal("100.0000"),
        )

        with self.assertRaises(ValidationError):
            CommissionEarningService.create_from_allocation(
                allocation=allocation,
                earning_type=self.earning_type,
            )