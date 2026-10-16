from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from audit.constants import AuditAction
from accounts.models import User
from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
    InvestmentReturn,
    Investor,
)
from investors.services.audit import InvestorAuditService


class InvestorAuditServiceTestCase(TestCase):
    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(self):
        user = self.create_user()

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
            description="Test opportunity",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            status=InvestmentOpportunity.Status.OPEN,
        )

    def create_plan(self, opportunity):
        return InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference="PLAN-0001",
            name="Test Plan",
            description="Test plan",
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
            investor,
            opportunity,
            plan,
        )

        return Investment.objects.create(
            investor=investor.user,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference="INVEST-0001",
            amount=Decimal("100000.00"),
            currency="NGN",
            status=Investment.Status.ACTIVE,
        )

    def create_return(self):
        investment = self.create_investment()

        return InvestmentReturn.objects.create(
            investment=investment,
            reference="RET-0001",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("10000.00"),
            currency="NGN",
            status=InvestmentReturn.Status.PENDING,
        )

    @patch("investors.services.audit.record_audit")
    def test_investor_created_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        investor = self.create_investor()
        actor = investor.user

        expected = object()
        record_audit.return_value = expected

        result = InvestorAuditService.created(
            investor,
            actor=actor,
        )

        self.assertIs(result, expected)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTOR_CREATED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_investor_activated_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        investor = self.create_investor()
        actor = investor.user

        InvestorAuditService.activated(
            investor,
            actor=actor,
        )

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTOR_ACTIVATED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_investor_suspended_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        investor = self.create_investor()

        InvestorAuditService.suspended(investor)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTOR_SUSPENDED,
            actor=None,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_opportunity_opened_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        opportunity = self.create_opportunity()

        InvestorAuditService.opportunity_opened(opportunity)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_OPPORTUNITY_OPENED,
            actor=None,
            target_user=None,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_plan_activated_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity)

        InvestorAuditService.plan_activated(plan)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_PLAN_ACTIVATED,
            actor=None,
            target_user=None,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_commitment_funded_targets_investor(
        self,
        record_audit,
    ):
        investor = self.create_investor()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity)
        commitment = self.create_commitment(
            investor,
            opportunity,
            plan,
        )

        InvestorAuditService.commitment_funded(commitment)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_COMMITMENT_FUNDED,
            actor=None,
            target_user=investor.user,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_investment_matured_targets_investor(
        self,
        record_audit,
    ):
        investment = self.create_investment()

        InvestorAuditService.investment_matured(investment)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_MATURED,
            actor=None,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_return_paid_targets_investor(
        self,
        record_audit,
    ):
        investment_return = self.create_return()

        InvestorAuditService.return_paid(investment_return)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_RETURN_PAID,
            actor=None,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @patch("investors.services.audit.record_audit")
    def test_return_reversed_delegates_to_canonical_audit(
        self,
        record_audit,
    ):
        investment_return = self.create_return()

        expected = object()
        record_audit.return_value = expected

        result = InvestorAuditService.return_reversed(
            investment_return,
        )

        self.assertIs(result, expected)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTMENT_RETURN_REVERSED,
            actor=None,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )
        
    @patch("investors.services.audit.record_audit")
    def test_actor_is_optional(
        self,
        record_audit,
    ):
        investor = self.create_investor()

        InvestorAuditService.closed(investor)

        record_audit.assert_called_once_with(
            action=AuditAction.INVESTOR_CLOSED,
            actor=None,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )