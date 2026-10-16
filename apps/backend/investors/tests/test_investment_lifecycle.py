from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from investors.lifecycle.investment import InvestmentLifecycle
from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
    Investor,
)
from accounts.models import User


class InvestmentLifecycleTestCase(TestCase):
    def create_user(self):
        return User.objects.create_user(
            email="investor@example.com",
            password="test-password",
        )

    def create_investor(self, user=None):
        user = user or self.create_user()

        return Investor.objects.create(
            user=user,
            reference="INV-0001",
            display_name="Test Investor",
            status=Investor.Status.ACTIVE,
        )

    def create_opportunity(self):
        return InvestmentOpportunity.objects.create(
            reference="OPP-0001",
            name="Test Opportunity",
            description="Test investment opportunity",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            status=InvestmentOpportunity.Status.OPEN,
        )

    def create_plan(self, opportunity=None):
        opportunity = opportunity or self.create_opportunity()

        return InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference="PLAN-0001",
            name="Test Plan",
            description="Test investment plan",
            status=InvestmentPlan.Status.ACTIVE,
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("1000000.00"),
            duration_days=365,
            expected_return_rate=Decimal("10.00"),
        )

    def create_commitment(
        self,
        investor=None,
        opportunity=None,
        plan=None,
    ):
        investor = investor or self.create_investor()
        opportunity = opportunity or self.create_opportunity()
        plan = plan or self.create_plan(opportunity)

        return InvestmentCommitment.objects.create(
            investor=investor.user,
            opportunity=opportunity,
            plan=plan,
            reference="COM-0001",
            amount=Decimal("100000.00"),
            currency="NGN",
            status=InvestmentCommitment.Status.FUNDED,
        )

    def create_investment(self):
        investor = self.create_investor()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity)
        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        return Investment.objects.create(
            investor=investor.user,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference="INVEST-0001",
            amount=Decimal("100000.00"),
            currency="NGN",
            status=Investment.Status.PENDING,
        )

    def test_activate_changes_pending_to_active(self):
        investment = self.create_investment()

        before = timezone.now()

        result = InvestmentLifecycle.activate(investment)

        after = timezone.now()

        investment.refresh_from_db()

        self.assertIs(result, investment)
        self.assertEqual(
            investment.status,
            Investment.Status.ACTIVE,
        )
        self.assertIsNotNone(investment.started_at)
        self.assertGreaterEqual(investment.started_at, before)
        self.assertLessEqual(investment.started_at, after)

    def test_activate_rejects_non_pending_investment(self):
        investment = self.create_investment()
        investment.status = Investment.Status.ACTIVE
        investment.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.activate(investment)

    def test_mature_changes_active_to_matured(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)

        before = timezone.now()

        result = InvestmentLifecycle.mature(investment)

        after = timezone.now()

        investment.refresh_from_db()

        self.assertIs(result, investment)
        self.assertEqual(
            investment.status,
            Investment.Status.MATURED,
        )
        self.assertIsNotNone(investment.matured_at)
        self.assertGreaterEqual(investment.matured_at, before)
        self.assertLessEqual(investment.matured_at, after)

    def test_mature_rejects_non_active_investment(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.mature(investment)

    def test_close_changes_matured_to_closed(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        InvestmentLifecycle.mature(investment)

        before = timezone.now()

        result = InvestmentLifecycle.close(investment)

        after = timezone.now()

        investment.refresh_from_db()

        self.assertIs(result, investment)
        self.assertEqual(
            investment.status,
            Investment.Status.CLOSED,
        )
        self.assertIsNotNone(investment.closed_at)
        self.assertGreaterEqual(investment.closed_at, before)
        self.assertLessEqual(investment.closed_at, after)

    def test_close_rejects_non_matured_investment(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.close(investment)

    def test_cancel_changes_pending_to_cancelled(self):
        investment = self.create_investment()

        before = timezone.now()

        result = InvestmentLifecycle.cancel(investment)

        after = timezone.now()

        investment.refresh_from_db()

        self.assertIs(result, investment)
        self.assertEqual(
            investment.status,
            Investment.Status.CANCELLED,
        )
        self.assertIsNotNone(investment.cancelled_at)
        self.assertGreaterEqual(investment.cancelled_at, before)
        self.assertLessEqual(investment.cancelled_at, after)

    def test_cancel_rejects_active_investment(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.cancel(investment)

    def test_cancel_rejects_matured_investment(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        InvestmentLifecycle.mature(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.cancel(investment)

    def test_closed_is_terminal(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        InvestmentLifecycle.mature(investment)
        InvestmentLifecycle.close(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.activate(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.mature(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.close(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.cancel(investment)

    def test_cancelled_is_terminal(self):
        investment = self.create_investment()

        InvestmentLifecycle.cancel(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.activate(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.mature(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.close(investment)

        with self.assertRaises(ValidationError):
            InvestmentLifecycle.cancel(investment)

    def test_activate_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            InvestmentLifecycle.activate(None)

    def test_mature_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            InvestmentLifecycle.mature(None)

    def test_close_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            InvestmentLifecycle.close(None)

    def test_cancel_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            InvestmentLifecycle.cancel(None)

    def test_full_lifecycle(self):
        investment = self.create_investment()

        self.assertEqual(
            investment.status,
            Investment.Status.PENDING,
        )

        InvestmentLifecycle.activate(investment)
        investment.refresh_from_db()

        self.assertEqual(
            investment.status,
            Investment.Status.ACTIVE,
        )
        self.assertIsNotNone(investment.started_at)

        InvestmentLifecycle.mature(investment)
        investment.refresh_from_db()

        self.assertEqual(
            investment.status,
            Investment.Status.MATURED,
        )
        self.assertIsNotNone(investment.matured_at)

        InvestmentLifecycle.close(investment)
        investment.refresh_from_db()

        self.assertEqual(
            investment.status,
            Investment.Status.CLOSED,
        )
        self.assertIsNotNone(investment.closed_at)

    def test_lifecycle_preserves_previous_timestamps(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        investment.refresh_from_db()

        started_at = investment.started_at

        InvestmentLifecycle.mature(investment)
        investment.refresh_from_db()

        self.assertEqual(investment.started_at, started_at)

        matured_at = investment.matured_at

        InvestmentLifecycle.close(investment)
        investment.refresh_from_db()

        self.assertEqual(investment.started_at, started_at)
        self.assertEqual(investment.matured_at, matured_at)

    def test_cancel_does_not_create_other_lifecycle_timestamps(self):
        investment = self.create_investment()

        InvestmentLifecycle.cancel(investment)
        investment.refresh_from_db()

        self.assertIsNone(investment.started_at)
        self.assertIsNone(investment.matured_at)
        self.assertIsNone(investment.closed_at)
        self.assertIsNotNone(investment.cancelled_at)

    def test_activate_does_not_create_maturity_or_close_timestamp(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        investment.refresh_from_db()

        self.assertIsNotNone(investment.started_at)
        self.assertIsNone(investment.matured_at)
        self.assertIsNone(investment.closed_at)
        self.assertIsNone(investment.cancelled_at)

    def test_mature_does_not_create_close_timestamp(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        InvestmentLifecycle.mature(investment)
        investment.refresh_from_db()

        self.assertIsNotNone(investment.started_at)
        self.assertIsNotNone(investment.matured_at)
        self.assertIsNone(investment.closed_at)
        self.assertIsNone(investment.cancelled_at)

    def test_close_does_not_create_cancel_timestamp(self):
        investment = self.create_investment()

        InvestmentLifecycle.activate(investment)
        InvestmentLifecycle.mature(investment)
        InvestmentLifecycle.close(investment)
        investment.refresh_from_db()

        self.assertIsNotNone(investment.started_at)
        self.assertIsNotNone(investment.matured_at)
        self.assertIsNotNone(investment.closed_at)
        self.assertIsNone(investment.cancelled_at)