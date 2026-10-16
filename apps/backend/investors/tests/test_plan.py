from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import (
    InvestmentOpportunity,
    InvestmentPlan,
)


class InvestmentPlanModelTests(TestCase):

    def create_opportunity(
        self,
        reference="OPP-PLAN-001",
    ):
        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Univa Investment Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def create_plan(self, **kwargs):
        opportunity = kwargs.pop(
            "opportunity",
            None,
        )

        if opportunity is None:
            opportunity = self.create_opportunity()

        defaults = {
            "opportunity": opportunity,
            "reference": "PLAN-000001",
            "name": "Standard Investment Plan",
            "description": "Standard investment plan.",
            "status": InvestmentPlan.Status.DRAFT,
            "minimum_amount": Decimal("100000.00"),
            "maximum_amount": Decimal("5000000.00"),
            "duration_days": 365,
            "expected_return_rate": Decimal("15.0000"),
        }

        defaults.update(kwargs)

        plan = InvestmentPlan(**defaults)
        plan.full_clean()
        plan.save()

        return plan

    def test_plan_can_be_created(self):
        plan = self.create_plan()

        self.assertIsNotNone(plan.id)
        self.assertEqual(
            plan.reference,
            "PLAN-000001",
        )

        self.assertEqual(
            plan.name,
            "Standard Investment Plan",
        )

    def test_plan_belongs_to_opportunity(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-002",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-000002",
        )

        self.assertEqual(
            plan.opportunity,
            opportunity,
        )

        self.assertIn(
            plan,
            opportunity.plans.all(),
        )

    def test_opportunity_is_required(self):
        plan = InvestmentPlan(
            reference="PLAN-000003",
            name="Invalid Plan",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_reference_must_be_unique(self):
        self.create_plan(
            reference="PLAN-UNIQUE-001",
        )

        plan = InvestmentPlan(
            opportunity=self.create_opportunity(
                reference="OPP-PLAN-003",
            ),
            reference="PLAN-UNIQUE-001",
            name="Duplicate Plan",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_name_is_required(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-004",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000005",
            name="",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_default_status_is_draft(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-005",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000006",
            name="Draft Plan",
            minimum_amount=Decimal("100000.00"),
        )

        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.DRAFT,
        )

    def test_minimum_amount_must_be_positive(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-006",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000007",
            name="Invalid Minimum",
            minimum_amount=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_maximum_amount_is_optional(self):
        plan = self.create_plan(
            reference="PLAN-000008",
            maximum_amount=None,
        )

        self.assertIsNone(
            plan.maximum_amount,
        )

    def test_maximum_amount_cannot_be_less_than_minimum(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-007",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000009",
            name="Invalid Range",
            minimum_amount=Decimal("1000000.00"),
            maximum_amount=Decimal("500000.00"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_duration_is_optional(self):
        plan = self.create_plan(
            reference="PLAN-000010",
            duration_days=None,
        )

        self.assertIsNone(
            plan.duration_days,
        )

    def test_duration_must_be_positive(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-008",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000011",
            name="Invalid Duration",
            minimum_amount=Decimal("100000.00"),
            duration_days=0,
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_expected_return_rate_is_optional(self):
        plan = self.create_plan(
            reference="PLAN-000012",
            expected_return_rate=None,
        )

        self.assertIsNone(
            plan.expected_return_rate,
        )

    def test_expected_return_rate_cannot_be_negative(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-009",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000013",
            name="Invalid Return",
            minimum_amount=Decimal("100000.00"),
            expected_return_rate=Decimal("-1.0000"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_metadata_defaults_to_empty_dictionary(self):
        plan = self.create_plan(
            reference="PLAN-000014",
        )

        self.assertEqual(
            plan.metadata,
            {},
        )

    def test_metadata_must_be_dictionary(self):
        opportunity = self.create_opportunity(
            reference="OPP-PLAN-010",
        )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference="PLAN-000015",
            name="Invalid Metadata",
            minimum_amount=Decimal("100000.00"),
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_status_helpers(self):
        draft = self.create_plan(
            reference="PLAN-000016",
            status=InvestmentPlan.Status.DRAFT,
        )

        self.assertTrue(draft.is_draft)
        self.assertFalse(draft.is_active)

        active = self.create_plan(
            opportunity=self.create_opportunity(
                reference="OPP-PLAN-011",
            ),
            reference="PLAN-000017",
            status=InvestmentPlan.Status.ACTIVE,
        )

        self.assertTrue(active.is_active)

        paused = self.create_plan(
            opportunity=self.create_opportunity(
                reference="OPP-PLAN-012",
            ),
            reference="PLAN-000018",
            status=InvestmentPlan.Status.PAUSED,
        )

        self.assertTrue(paused.is_paused)

        closed = self.create_plan(
            opportunity=self.create_opportunity(
                reference="OPP-PLAN-013",
            ),
            reference="PLAN-000019",
            status=InvestmentPlan.Status.CLOSED,
        )

        self.assertTrue(closed.is_closed)

        cancelled = self.create_plan(
            opportunity=self.create_opportunity(
                reference="OPP-PLAN-014",
            ),
            reference="PLAN-000020",
            status=InvestmentPlan.Status.CANCELLED,
        )

        self.assertTrue(cancelled.is_cancelled)

    def test_string_representation_uses_reference(self):
        plan = self.create_plan(
            reference="PLAN-STRING-001",
        )

        self.assertEqual(
            str(plan),
            "PLAN-STRING-001",
        )