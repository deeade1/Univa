from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.lifecycle.opportunity import InvestmentOpportunityLifecycle
from investors.models import InvestmentOpportunity


class InvestmentOpportunityLifecycleTests(TestCase):

    def create_opportunity(
        self,
        status=InvestmentOpportunity.Status.DRAFT,
        reference=None,
    ):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"OPPORTUNITY-LIFECYCLE-{index:03d}"
            ).exists():
                index += 1

            reference = f"OPPORTUNITY-LIFECYCLE-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Lifecycle Investment Opportunity",
            status=status,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
            metadata={},
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    # ------------------------------------------------------------------
    # open
    # ------------------------------------------------------------------

    def test_open_draft_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        result = InvestmentOpportunityLifecycle.open(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.OPEN,
        )

    def test_open_paused_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.PAUSED,
        )

        result = InvestmentOpportunityLifecycle.open(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.OPEN,
        )

    def test_open_rejects_open_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.open(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_open_rejects_closed_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.open(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_open_rejects_cancelled_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.open(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # pause
    # ------------------------------------------------------------------

    def test_pause_open_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        result = InvestmentOpportunityLifecycle.pause(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.PAUSED,
        )

    def test_pause_rejects_draft_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_paused_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.PAUSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_closed_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_pause_rejects_cancelled_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    def test_close_open_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        result = InvestmentOpportunityLifecycle.close(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CLOSED,
        )

    def test_close_paused_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.PAUSED,
        )

        result = InvestmentOpportunityLifecycle.close(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CLOSED,
        )

    def test_close_rejects_draft_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.close(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_close_rejects_closed_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.close(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_close_rejects_cancelled_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.close(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    def test_cancel_draft_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        result = InvestmentOpportunityLifecycle.cancel(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CANCELLED,
        )

    def test_cancel_open_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        result = InvestmentOpportunityLifecycle.cancel(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CANCELLED,
        )

    def test_cancel_paused_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.PAUSED,
        )

        result = InvestmentOpportunityLifecycle.cancel(
            opportunity,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            result.pk,
            opportunity.pk,
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CANCELLED,
        )

    def test_cancel_rejects_closed_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.cancel(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_cancel_rejects_cancelled_opportunity(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.cancel(
                opportunity,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def test_open_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.open(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_pause_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_close_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.close(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_cancel_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.cancel(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_open_rejects_invalid_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.open("invalid")

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_pause_rejects_invalid_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.pause("invalid")

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_close_rejects_invalid_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.close("invalid")

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_cancel_rejects_invalid_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentOpportunityLifecycle.cancel("invalid")

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )