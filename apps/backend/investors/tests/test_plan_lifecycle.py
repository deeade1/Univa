from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.lifecycle.plan import InvestmentPlanLifecycle
from investors.models import InvestmentOpportunity, InvestmentPlan


class InvestmentPlanLifecycleTests(TestCase):

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"PLAN-LIFECYCLE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-LIFECYCLE-OPP-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Plan Lifecycle Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
            metadata={},
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def create_plan(
        self,
        status=InvestmentPlan.Status.DRAFT,
        reference=None,
        opportunity=None,
    ):
        if opportunity is None:
            opportunity = self.create_opportunity()

        if reference is None:
            index = InvestmentPlan.objects.count() + 1

            while InvestmentPlan.objects.filter(
                reference=f"PLAN-LIFECYCLE-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-LIFECYCLE-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Plan Lifecycle Test Plan",
            status=status,
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("5000000.00"),
            duration_days=365,
            expected_return_rate=Decimal("15.0000"),
            metadata={},
        )

        plan.full_clean()
        plan.save()

        return plan

    # ------------------------------------------------------------------
    # activate
    # ------------------------------------------------------------------

    def test_activate_draft_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        result = InvestmentPlanLifecycle.activate(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.ACTIVE,
        )

    def test_activate_paused_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.PAUSED,
        )

        result = InvestmentPlanLifecycle.activate(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.ACTIVE,
        )

    def test_activate_rejects_active_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.activate(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_activate_rejects_closed_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.activate(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_activate_rejects_cancelled_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.activate(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # pause
    # ------------------------------------------------------------------

    def test_pause_active_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        result = InvestmentPlanLifecycle.pause(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.PAUSED,
        )

    def test_pause_rejects_draft_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_paused_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.PAUSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_closed_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_cancelled_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    def test_close_active_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        result = InvestmentPlanLifecycle.close(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CLOSED,
        )

    def test_close_paused_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.PAUSED,
        )

        result = InvestmentPlanLifecycle.close(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CLOSED,
        )

    def test_close_rejects_draft_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.close(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_close_rejects_closed_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.close(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_close_rejects_cancelled_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.close(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    def test_cancel_draft_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.DRAFT,
        )

        result = InvestmentPlanLifecycle.cancel(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CANCELLED,
        )

    def test_cancel_active_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.ACTIVE,
        )

        result = InvestmentPlanLifecycle.cancel(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CANCELLED,
        )

    def test_cancel_paused_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.PAUSED,
        )

        result = InvestmentPlanLifecycle.cancel(plan)

        plan.refresh_from_db()

        self.assertEqual(result.pk, plan.pk)
        self.assertEqual(
            plan.status,
            InvestmentPlan.Status.CANCELLED,
        )

    def test_cancel_rejects_closed_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.cancel(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_cancel_rejects_cancelled_plan(self):
        plan = self.create_plan(
            status=InvestmentPlan.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.cancel(plan)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def test_activate_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.activate(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_pause_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_close_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.close(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_cancel_requires_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.cancel(None)

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_activate_rejects_invalid_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.activate("invalid")

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_pause_rejects_invalid_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.pause("invalid")

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_close_rejects_invalid_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.close("invalid")

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_cancel_rejects_invalid_plan(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentPlanLifecycle.cancel("invalid")

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )