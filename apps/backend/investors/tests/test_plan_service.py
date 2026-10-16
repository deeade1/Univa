from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import InvestmentOpportunity, InvestmentPlan
from investors.services.plan import PlanService


class PlanServiceTests(TestCase):

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"PLAN-SERVICE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-SERVICE-OPP-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Plan Service Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def create_plan(
        self,
        opportunity=None,
        reference=None,
        name="Service Test Plan",
        description="Test investment plan",
        status=InvestmentPlan.Status.DRAFT,
        minimum_amount=Decimal("100000.00"),
        maximum_amount=Decimal("5000000.00"),
        duration_days=365,
        expected_return_rate=Decimal("15.0000"),
        metadata=None,
    ):
        if opportunity is None:
            opportunity = self.create_opportunity()

        if reference is None:
            index = InvestmentPlan.objects.count() + 1

            while InvestmentPlan.objects.filter(
                reference=f"PLAN-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-SERVICE-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name=name,
            description=description,
            status=status,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            duration_days=duration_days,
            expected_return_rate=expected_return_rate,
            metadata={} if metadata is None else metadata,
        )

        plan.full_clean()
        plan.save()

        return plan

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_plan(self):
        opportunity = self.create_opportunity()

        plan = PlanService.create(
            opportunity=opportunity,
            reference="PLAN-SERVICE-001",
            name="New Investment Plan",
        )

        self.assertIsNotNone(plan.pk)
        self.assertEqual(plan.opportunity, opportunity)
        self.assertEqual(plan.reference, "PLAN-SERVICE-001")
        self.assertEqual(plan.name, "New Investment Plan")
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.DRAFT,
        )
        self.assertEqual(
            plan.minimum_amount,
            Decimal("100000.00"),
        )

    def test_create_with_all_fields(self):
        opportunity = self.create_opportunity()

        metadata = {
            "risk": "medium",
            "sector": "real-estate",
        }

        plan = PlanService.create(
            opportunity=opportunity,
            reference="PLAN-SERVICE-002",
            name="Premium Investment Plan",
            description="Premium investment opportunity",
            status=InvestmentPlan.Status.ACTIVE,
            minimum_amount=Decimal("500000.00"),
            maximum_amount=Decimal("10000000.00"),
            duration_days=730,
            expected_return_rate=Decimal("20.0000"),
            metadata=metadata,
        )

        self.assertEqual(plan.description, "Premium investment opportunity")
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.ACTIVE,
        )
        self.assertEqual(
            plan.minimum_amount,
            Decimal("500000.00"),
        )
        self.assertEqual(
            plan.maximum_amount,
            Decimal("10000000.00"),
        )
        self.assertEqual(plan.duration_days, 730)
        self.assertEqual(
            plan.expected_return_rate,
            Decimal("20.0000"),
        )
        self.assertEqual(plan.metadata, metadata)

    def test_create_defaults_metadata(self):
        opportunity = self.create_opportunity()

        plan = PlanService.create(
            opportunity=opportunity,
            reference="PLAN-SERVICE-003",
            name="Metadata Test Plan",
        )

        self.assertEqual(plan.metadata, {})

    def test_create_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.create(
                opportunity=None,
                reference="PLAN-SERVICE-004",
                name="Invalid Plan",
            )

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_create_requires_reference(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            PlanService.create(
                opportunity=opportunity,
                reference="",
                name="Invalid Plan",
            )

        self.assertIn(
            "reference",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_metadata(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            PlanService.create(
                opportunity=opportunity,
                reference="PLAN-SERVICE-005",
                name="Invalid Metadata Plan",
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_amount_range(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            PlanService.create(
                opportunity=opportunity,
                reference="PLAN-SERVICE-006",
                name="Invalid Amount Plan",
                minimum_amount=Decimal("9000000.00"),
                maximum_amount=Decimal("1000000.00"),
            )

        self.assertIn(
            "maximum_amount",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_duration(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            PlanService.create(
                opportunity=opportunity,
                reference="PLAN-SERVICE-007",
                name="Invalid Duration Plan",
                duration_days=0,
            )

        self.assertIn(
            "duration_days",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_name(self):
        plan = self.create_plan()

        result = PlanService.update(
            plan,
            name="Updated Plan",
        )

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(plan.name, "Updated Plan")

    def test_update_description(self):
        plan = self.create_plan()

        PlanService.update(
            plan,
            description="Updated description",
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.description,
            "Updated description",
        )

    def test_update_reference(self):
        plan = self.create_plan(
            reference="PLAN-SERVICE-008",
        )

        PlanService.update(
            plan,
            reference="PLAN-SERVICE-009",
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.reference,
            "PLAN-SERVICE-009",
        )

    def test_update_opportunity(self):
        original_opportunity = self.create_opportunity(
            reference="PLAN-SERVICE-OPP-100",
        )
        new_opportunity = self.create_opportunity(
            reference="PLAN-SERVICE-OPP-101",
        )

        plan = self.create_plan(
            opportunity=original_opportunity,
        )

        PlanService.update(
            plan,
            opportunity=new_opportunity,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.opportunity,
            new_opportunity,
        )

    def test_update_financial_fields(self):
        plan = self.create_plan()

        PlanService.update(
            plan,
            minimum_amount=Decimal("250000.00"),
            maximum_amount=Decimal("7500000.00"),
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.minimum_amount,
            Decimal("250000.00"),
        )
        self.assertEqual(
            plan.maximum_amount,
            Decimal("7500000.00"),
        )

    def test_update_duration_and_return_rate(self):
        plan = self.create_plan()

        PlanService.update(
            plan,
            duration_days=730,
            expected_return_rate=Decimal("18.5000"),
        )

        plan.refresh_from_db()

        self.assertEqual(plan.duration_days, 730)
        self.assertEqual(
            plan.expected_return_rate,
            Decimal("18.5000"),
        )

    def test_update_metadata(self):
        plan = self.create_plan(
            metadata={"risk": "low"},
        )

        metadata = {
            "risk": "medium",
            "sector": "technology",
        }

        PlanService.update(
            plan,
            metadata=metadata,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.metadata,
            metadata,
        )

    def test_update_preserves_unspecified_fields(self):
        opportunity = self.create_opportunity()

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-SERVICE-010",
            name="Original Name",
            description="Original description",
            metadata={"risk": "low"},
        )

        PlanService.update(
            plan,
            name="Updated Name",
        )

        plan.refresh_from_db()

        self.assertEqual(plan.opportunity, opportunity)
        self.assertEqual(
            plan.reference,
            "PLAN-SERVICE-010",
        )
        self.assertEqual(
            plan.name,
            "Updated Name",
        )
        self.assertEqual(
            plan.description,
            "Original description",
        )
        self.assertEqual(
            plan.metadata,
            {"risk": "low"},
        )

    def test_update_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.update(
                None,
                name="Invalid",
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_metadata(self):
        plan = self.create_plan()

        with self.assertRaises(ValidationError) as context:
            PlanService.update(
                plan,
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_amount_range(self):
        plan = self.create_plan()

        with self.assertRaises(ValidationError) as context:
            PlanService.update(
                plan,
                minimum_amount=Decimal("9000000.00"),
                maximum_amount=Decimal("1000000.00"),
            )

        self.assertIn(
            "maximum_amount",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_opportunity(self):
        plan = self.create_plan()

        with self.assertRaises(ValidationError) as context:
            PlanService.update(
                plan,
                opportunity="invalid",
            )

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    def test_activate(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        result = PlanService.activate(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.ACTIVE,
        )

    def test_pause(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        result = PlanService.pause(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.PAUSED,
        )

    def test_close(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        result = PlanService.close(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CLOSED,
        )

    def test_cancel(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        result = PlanService.cancel(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CANCELLED,
        )

    def test_activate_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.activate(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_pause_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.pause(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_close_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.close(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_cancel_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            PlanService.cancel(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )