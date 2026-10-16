from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from investors.lifecycle.investment import InvestmentLifecycle
from investors.lifecycle.investment_return import InvestmentReturnLifecycle
from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
    InvestmentReturn,
    Investor,
)


class InvestmentReturnLifecycleTestCase(TestCase):
    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(self, email="investor@example.com"):
        user = self.create_user(email=email)

        return Investor.objects.create(
            user=user,
            reference=f"INV-{Investor.objects.count() + 1:04d}",
            display_name="Test Investor",
            status=Investor.Status.ACTIVE,
        )

    def create_opportunity(self):
        return InvestmentOpportunity.objects.create(
            reference=f"OPP-{InvestmentOpportunity.objects.count() + 1:04d}",
            name="Test Opportunity",
            description="Test investment opportunity",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            status=InvestmentOpportunity.Status.OPEN,
        )

    def create_plan(self, opportunity):
        return InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference=f"PLAN-{InvestmentPlan.objects.count() + 1:04d}",
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
        investor,
        opportunity,
        plan,
    ):
        return InvestmentCommitment.objects.create(
            investor=investor.user,
            opportunity=opportunity,
            plan=plan,
            reference=f"COM-{InvestmentCommitment.objects.count() + 1:04d}",
            amount=Decimal("100000.00"),
            currency="NGN",
            status=InvestmentCommitment.Status.FUNDED,
        )

    def create_investment(self):
        investor = self.create_investor()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity)
        commitment = self.create_commitment(
            investor,
            opportunity,
            plan,
        )

        return Investment.objects.create(
            investor=investor.user,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference=f"INVEST-{Investment.objects.count() + 1:04d}",
            amount=Decimal("100000.00"),
            currency="NGN",
            status=Investment.Status.PENDING,
        )

    def create_return(self):
        investment = self.create_investment()

        return InvestmentReturn.objects.create(
            investment=investment,
            reference=f"RET-{InvestmentReturn.objects.count() + 1:04d}",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("10000.00"),
            currency="NGN",
            status=InvestmentReturn.Status.PENDING,
        )

    def test_calculate_changes_pending_to_calculated(self):
        investment_return = self.create_return()

        result = InvestmentReturnLifecycle.calculate(investment_return)

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CALCULATED,
        )

    def test_calculate_does_not_create_lifecycle_timestamp(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        investment_return.refresh_from_db()

        self.assertIsNone(investment_return.approved_at)
        self.assertIsNone(investment_return.payable_at)
        self.assertIsNone(investment_return.paid_at)
        self.assertIsNone(investment_return.cancelled_at)
        self.assertIsNone(investment_return.reversed_at)

    def test_calculate_rejects_non_pending_return(self):
        investment_return = self.create_return()
        investment_return.status = InvestmentReturn.Status.CALCULATED
        investment_return.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.calculate(investment_return)

    def test_approve_changes_calculated_to_approved(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)

        before = timezone.now()
        result = InvestmentReturnLifecycle.approve(investment_return)
        after = timezone.now()

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.APPROVED,
        )
        self.assertIsNotNone(investment_return.approved_at)
        self.assertGreaterEqual(investment_return.approved_at, before)
        self.assertLessEqual(investment_return.approved_at, after)

    def test_approve_rejects_non_calculated_return(self):
        investment_return = self.create_return()

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.approve(investment_return)

    def test_make_payable_changes_approved_to_payable(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)

        before = timezone.now()
        result = InvestmentReturnLifecycle.make_payable(investment_return)
        after = timezone.now()

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAYABLE,
        )
        self.assertIsNotNone(investment_return.payable_at)
        self.assertGreaterEqual(investment_return.payable_at, before)
        self.assertLessEqual(investment_return.payable_at, after)

    def test_make_payable_rejects_non_approved_return(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.make_payable(investment_return)

    def test_mark_paid_changes_payable_to_paid(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)
        InvestmentReturnLifecycle.make_payable(investment_return)

        before = timezone.now()
        result = InvestmentReturnLifecycle.mark_paid(investment_return)
        after = timezone.now()

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAID,
        )
        self.assertIsNotNone(investment_return.paid_at)
        self.assertGreaterEqual(investment_return.paid_at, before)
        self.assertLessEqual(investment_return.paid_at, after)

    def test_mark_paid_rejects_non_payable_return(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.mark_paid(investment_return)

    def test_cancel_pending_return(self):
        investment_return = self.create_return()

        before = timezone.now()
        result = InvestmentReturnLifecycle.cancel(investment_return)
        after = timezone.now()

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CANCELLED,
        )
        self.assertIsNotNone(investment_return.cancelled_at)
        self.assertGreaterEqual(investment_return.cancelled_at, before)
        self.assertLessEqual(investment_return.cancelled_at, after)

    def test_cancel_calculated_return(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)

        InvestmentReturnLifecycle.cancel(investment_return)

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CANCELLED,
        )
        self.assertIsNotNone(investment_return.cancelled_at)

    def test_cancel_approved_return(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)

        InvestmentReturnLifecycle.cancel(investment_return)

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CANCELLED,
        )
        self.assertIsNotNone(investment_return.cancelled_at)

    def test_cancel_rejects_payable_return(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)
        InvestmentReturnLifecycle.make_payable(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.cancel(investment_return)

    def test_reverse_changes_paid_to_reversed(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)
        InvestmentReturnLifecycle.make_payable(investment_return)
        InvestmentReturnLifecycle.mark_paid(investment_return)

        before = timezone.now()
        result = InvestmentReturnLifecycle.reverse(investment_return)
        after = timezone.now()

        investment_return.refresh_from_db()

        self.assertIs(result, investment_return)
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.REVERSED,
        )
        self.assertIsNotNone(investment_return.reversed_at)
        self.assertGreaterEqual(investment_return.reversed_at, before)
        self.assertLessEqual(investment_return.reversed_at, after)

    def test_reverse_rejects_non_paid_return(self):
        investment_return = self.create_return()

        investment_return.status = InvestmentReturn.Status.PAYABLE
        investment_return.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.reverse(investment_return)

    def test_paid_is_terminal_except_for_reverse(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)
        InvestmentReturnLifecycle.make_payable(investment_return)
        InvestmentReturnLifecycle.mark_paid(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.calculate(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.approve(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.make_payable(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.mark_paid(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.cancel(investment_return)

    def test_cancelled_is_terminal(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.cancel(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.calculate(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.approve(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.make_payable(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.mark_paid(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.cancel(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.reverse(investment_return)

    def test_reversed_is_terminal(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)
        InvestmentReturnLifecycle.make_payable(investment_return)
        InvestmentReturnLifecycle.mark_paid(investment_return)
        InvestmentReturnLifecycle.reverse(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.calculate(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.approve(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.make_payable(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.mark_paid(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.cancel(investment_return)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.reverse(investment_return)

    def test_full_lifecycle(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CALCULATED,
        )

        InvestmentReturnLifecycle.approve(investment_return)
        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.APPROVED,
        )
        self.assertIsNotNone(investment_return.approved_at)

        InvestmentReturnLifecycle.make_payable(investment_return)
        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAYABLE,
        )
        self.assertIsNotNone(investment_return.payable_at)

        InvestmentReturnLifecycle.mark_paid(investment_return)
        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAID,
        )
        self.assertIsNotNone(investment_return.paid_at)

        InvestmentReturnLifecycle.reverse(investment_return)
        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.REVERSED,
        )
        self.assertIsNotNone(investment_return.reversed_at)

    def test_previous_timestamps_are_preserved(self):
        investment_return = self.create_return()

        InvestmentReturnLifecycle.calculate(investment_return)
        InvestmentReturnLifecycle.approve(investment_return)

        approved_at = investment_return.approved_at

        InvestmentReturnLifecycle.make_payable(investment_return)

        payable_at = investment_return.payable_at

        InvestmentReturnLifecycle.mark_paid(investment_return)

        paid_at = investment_return.paid_at

        InvestmentReturnLifecycle.reverse(investment_return)

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.approved_at,
            approved_at,
        )
        self.assertEqual(
            investment_return.payable_at,
            payable_at,
        )
        self.assertEqual(
            investment_return.paid_at,
            paid_at,
        )

    def test_invalid_instance_is_rejected(self):
        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.calculate(None)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.approve(None)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.make_payable(None)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.mark_paid(None)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.cancel(None)

        with self.assertRaises(ValidationError):
            InvestmentReturnLifecycle.reverse(None)