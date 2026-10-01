from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from commissions.models import (
    Commission,
    CommissionAllocation,
    CommissionPlan,
)
from commissions.services import CommissionService


class CommissionServiceTests(TestCase):
    def setUp(self):
        self.beneficiary = User.objects.create_user(
            email="service@example.com",
            password="test-password",
        )

        self.second_beneficiary = User.objects.create_user(
            email="service2@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Service Percentage 10%",
            code="SERVICE_PERCENTAGE_10",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        self.fixed_plan = CommissionPlan.objects.create(
            name="Service Fixed 5000",
            code="SERVICE_FIXED_5000",
            plan_type=CommissionPlan.PlanType.FIXED,
            fixed_amount=Decimal("5000.00"),
        )

    def test_create_commission_calculates_and_persists_commission(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-001",
            calculation_basis=Decimal("100000.00"),
            currency="NGN",
        )

        self.assertIsNotNone(commission.pk)

        self.assertEqual(
            commission.calculation_basis,
            Decimal("100000.00"),
        )

        self.assertEqual(
            commission.calculated_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission.rate,
            Decimal("10.0000"),
        )

        self.assertEqual(
            commission.status,
            Commission.Status.CALCULATED,
        )

        self.assertIsNotNone(commission.calculated_at)

    def test_create_commission_persists_source_information(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.REAL_ESTATE,
            source_id="property-sale-001",
            source_reference="SALE-2026-001",
            calculation_basis=Decimal("500000.00"),
            currency="NGN",
            notes="Property commission",
            metadata={
                "property_id": "property-001",
            },
        )

        self.assertEqual(
            commission.source_type,
            Commission.SourceType.REAL_ESTATE,
        )

        self.assertEqual(
            commission.source_id,
            "property-sale-001",
        )

        self.assertEqual(
            commission.source_reference,
            "SALE-2026-001",
        )

        self.assertEqual(
            commission.notes,
            "Property commission",
        )

        self.assertEqual(
            commission.metadata,
            {
                "property_id": "property-001",
            },
        )

    def test_create_fixed_commission(self):
        commission = CommissionService.create_commission(
            plan=self.fixed_plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.REFERRAL,
            source_id="referral-001",
            calculation_basis=Decimal("1000000.00"),
            currency="NGN",
        )

        self.assertEqual(
            commission.calculated_amount,
            Decimal("5000.00"),
        )

        self.assertIsNone(commission.rate)

    def test_create_commission_requires_source_type(self):
        with self.assertRaises(ValidationError):
            CommissionService.create_commission(
                plan=self.plan,
                beneficiary=self.beneficiary,
                source_type="",
                source_id="trip-001",
                calculation_basis=Decimal("100000.00"),
            )

    def test_create_commission_requires_source_id(self):
        with self.assertRaises(ValidationError):
            CommissionService.create_commission(
                plan=self.plan,
                beneficiary=self.beneficiary,
                source_type=Commission.SourceType.TRANSPORT,
                source_id="",
                calculation_basis=Decimal("100000.00"),
            )

    def test_create_commission_requires_currency(self):
        with self.assertRaises(ValidationError):
            CommissionService.create_commission(
                plan=self.plan,
                beneficiary=self.beneficiary,
                source_type=Commission.SourceType.TRANSPORT,
                source_id="trip-001",
                calculation_basis=Decimal("100000.00"),
                currency="",
            )

    def test_create_commission_requires_three_character_currency(self):
        with self.assertRaises(ValidationError):
            CommissionService.create_commission(
                plan=self.plan,
                beneficiary=self.beneficiary,
                source_type=Commission.SourceType.TRANSPORT,
                source_id="trip-001",
                calculation_basis=Decimal("100000.00"),
                currency="NG",
            )

    def test_create_allocations(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-002",
            calculation_basis=Decimal("100000.00"),
            currency="NGN",
        )

        allocations = CommissionService.create_allocations(
            commission=commission,
            allocations=[
                {
                    "beneficiary": self.beneficiary,
                    "amount": Decimal("6000.00"),
                    "allocation_percentage": Decimal("60.0000"),
                },
                {
                    "beneficiary": self.second_beneficiary,
                    "amount": Decimal("4000.00"),
                    "allocation_percentage": Decimal("40.0000"),
                },
            ],
        )

        self.assertEqual(len(allocations), 2)

        self.assertEqual(
            CommissionAllocation.objects.filter(
                commission=commission,
            ).count(),
            2,
        )

        total = sum(
            allocation.amount
            for allocation in allocations
        )

        self.assertEqual(
            total,
            commission.calculated_amount,
        )

    def test_create_allocations_requires_at_least_one_allocation(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-003",
            calculation_basis=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            CommissionService.create_allocations(
                commission=commission,
                allocations=[],
            )

    def test_create_allocations_must_equal_commission_amount(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-004",
            calculation_basis=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            CommissionService.create_allocations(
                commission=commission,
                allocations=[
                    {
                        "beneficiary": self.beneficiary,
                        "amount": Decimal("9000.00"),
                    },
                ],
            )

        self.assertEqual(
            CommissionAllocation.objects.filter(
                commission=commission,
            ).count(),
            0,
        )

    def test_create_allocations_rejects_allocations_above_commission(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-005",
            calculation_basis=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            CommissionService.create_allocations(
                commission=commission,
                allocations=[
                    {
                        "beneficiary": self.beneficiary,
                        "amount": Decimal("10001.00"),
                    },
                ],
            )

    def test_create_allocations_requires_calculated_or_approved_status(self):
        commission = Commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-006",
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("10000.00"),
            currency="NGN",
            status=Commission.Status.PENDING,
        )
        commission.save()

        with self.assertRaises(ValidationError):
            CommissionService.create_allocations(
                commission=commission,
                allocations=[
                    {
                        "beneficiary": self.beneficiary,
                        "amount": Decimal("10000.00"),
                    },
                ],
            )

    def test_approve(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-007",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.approve(
            commission=commission,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.APPROVED,
        )

        self.assertIsNotNone(
            commission.approved_at,
        )

    def test_approve_rejects_non_calculated_commission(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-008",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.approve(
            commission=commission,
        )

        with self.assertRaises(ValidationError):
            CommissionService.approve(
                commission=commission,
            )

    def test_mark_payable(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-009",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.approve(
            commission=commission,
        )

        CommissionService.mark_payable(
            commission=commission,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.PAYABLE,
        )

        self.assertIsNotNone(
            commission.payable_at,
        )

    def test_mark_payable_requires_approval(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-010",
            calculation_basis=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            CommissionService.mark_payable(
                commission=commission,
            )

    def test_cancel(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-011",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.cancel(
            commission=commission,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CANCELLED,
        )

    def test_cancel_cannot_cancel_settled_commission(self):
        commission = Commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-012",
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("10000.00"),
            currency="NGN",
            status=Commission.Status.SETTLED,
        )
        commission.save()

        with self.assertRaises(ValidationError):
            CommissionService.cancel(
                commission=commission,
            )

    def test_reverse(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-013",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.reverse(
            commission=commission,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.REVERSED,
        )

        self.assertIsNotNone(
            commission.reversed_at,
        )

    def test_reverse_cancelled_commission_is_rejected(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-014",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.cancel(
            commission=commission,
        )

        with self.assertRaises(ValidationError):
            CommissionService.reverse(
                commission=commission,
            )

    def test_reverse_already_reversed_commission_is_rejected(self):
        commission = CommissionService.create_commission(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-015",
            calculation_basis=Decimal("100000.00"),
        )

        CommissionService.reverse(
            commission=commission,
        )

        with self.assertRaises(ValidationError):
            CommissionService.reverse(
                commission=commission,
            )