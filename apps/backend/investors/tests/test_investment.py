from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)


User = get_user_model()


class InvestmentModelTests(TestCase):

    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(
        self,
        reference=None,
    ):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"OPP-INVEST-{index:03d}"
            ).exists():
                index += 1

            reference = f"OPP-INVEST-{index:03d}"

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

    def create_plan(
        self,
        opportunity=None,
        reference=None,
    ):
        if opportunity is None:
            opportunity = self.create_opportunity()

        if reference is None:
            index = InvestmentPlan.objects.count() + 1

            while InvestmentPlan.objects.filter(
                reference=f"PLAN-INVEST-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-INVEST-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Standard Investment Plan",
            status=InvestmentPlan.Status.ACTIVE,
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("5000000.00"),
            duration_days=365,
            expected_return_rate=Decimal("15.0000"),
        )

        plan.full_clean()
        plan.save()

        return plan

    def create_commitment(
        self,
        investor=None,
        opportunity=None,
        plan=None,
        reference="COMMIT-INVEST-001",
        amount=Decimal("500000.00"),
        currency="NGN",
    ):
        if investor is None:
            investor = self.create_user()

        if opportunity is None:
            opportunity = self.create_opportunity()

        if plan is None:
            plan = self.create_plan(
                opportunity=opportunity,
            )

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference=reference,
            amount=amount,
            currency=currency,
            status=InvestmentCommitment.Status.FUNDED,
        )

        commitment.full_clean()
        commitment.save()

        return commitment

    def create_investment(self, **kwargs):
        commitment = kwargs.pop(
            "commitment",
            None,
        )

        if commitment is None:
            commitment = self.create_commitment()

        defaults = {
            "investor_id": commitment.investor_id,
            "opportunity_id": commitment.opportunity_id,
            "plan_id": commitment.plan_id,
            "commitment": commitment,
            "reference": "INVESTMENT-000001",
            "amount": commitment.amount,
            "currency": commitment.currency,
            "status": Investment.Status.PENDING,
        }

        defaults.update(kwargs)

        investment = Investment(**defaults)
        investment.full_clean()
        investment.save()

        return investment

    def test_investment_can_be_created(self):
        investment = self.create_investment()

        self.assertIsNotNone(
            investment.id,
        )

        self.assertEqual(
            investment.reference,
            "INVESTMENT-000001",
        )

        self.assertEqual(
            investment.amount,
            Decimal("500000.00"),
        )

    def test_investment_belongs_to_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-002",
        )

        investment = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000002",
        )

        self.assertEqual(
            investment.commitment,
            commitment,
        )

        self.assertEqual(
            commitment.investment,
            investment,
        )

    def test_commitment_can_have_only_one_investment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-003",
        )

        self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000003",
        )

        duplicate = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000004",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_investment_inherits_investor_from_commitment(self):
        investor = self.create_user(
            "investment-investor@example.com",
        )

        commitment = self.create_commitment(
            investor=investor,
            reference="COMMIT-INVEST-004",
        )

        investment = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000005",
        )

        self.assertEqual(
            investment.investor,
            investor,
        )

    def test_investor_must_match_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-005",
        )

        another_investor = self.create_user(
            "different-investor@example.com",
        )

        investment = Investment(
            investor=another_investor,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000006",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_opportunity_must_match_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-006",
        )

        another_opportunity = self.create_opportunity(
            reference="OPP-INVEST-002",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity=another_opportunity,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000007",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()


    def test_plan_must_match_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-007",
        )

        another_plan_opportunity = self.create_opportunity(
            reference="OPP-INVEST-003",
        )

        another_plan = self.create_plan(
            opportunity=another_plan_opportunity,
            reference="PLAN-INVEST-002",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan=another_plan,
            commitment=commitment,
            reference="INVESTMENT-000008",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_amount_must_match_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-008",
            amount=Decimal("500000.00"),
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000009",
            amount=Decimal("600000.00"),
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_currency_must_match_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-009",
            currency="NGN",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000010",
            amount=commitment.amount,
            currency="USD",
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_default_status_is_pending(self):
        investment = self.create_investment(
            reference="INVESTMENT-000011",
        )

        self.assertEqual(
            investment.status,
            Investment.Status.PENDING,
        )

    def test_amount_must_be_positive(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-010",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000012",
            amount=Decimal("0.00"),
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_currency_is_normalized_to_uppercase(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-011",
            currency="ngn",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000013",
            amount=commitment.amount,
            currency="ngn",
        )

        investment.full_clean()

        self.assertEqual(
            investment.currency,
            "NGN",
        )

    def test_currency_must_be_three_characters(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-012",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000014",
            amount=commitment.amount,
            currency="NG",
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_metadata_defaults_to_empty_dictionary(self):
        investment = self.create_investment(
            reference="INVESTMENT-000015",
        )

        self.assertEqual(
            investment.metadata,
            {},
        )

    def test_metadata_must_be_dictionary(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-013",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000016",
            amount=commitment.amount,
            currency=commitment.currency,
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            investment.full_clean()

    def test_status_helpers(self):
        pending = self.create_investment(
            reference="INVESTMENT-000017",
            status=Investment.Status.PENDING,
        )

        self.assertTrue(pending.is_pending)
        self.assertFalse(pending.is_active)

        commitment = self.create_commitment(
            investor=self.create_user(
                "active-investor@example.com",
            ),
            reference="COMMIT-INVEST-014",
        )

        active = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000018",
            status=Investment.Status.ACTIVE,
        )

        self.assertTrue(active.is_active)

        commitment = self.create_commitment(
            investor=self.create_user(
                "matured-investor@example.com",
            ),
            reference="COMMIT-INVEST-015",
        )

        matured = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000019",
            status=Investment.Status.MATURED,
        )

        self.assertTrue(matured.is_matured)

        commitment = self.create_commitment(
            investor=self.create_user(
                "closed-investor@example.com",
            ),
            reference="COMMIT-INVEST-016",
        )

        closed = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000020",
            status=Investment.Status.CLOSED,
        )

        self.assertTrue(closed.is_closed)

        commitment = self.create_commitment(
            investor=self.create_user(
                "cancelled-investor@example.com",
            ),
            reference="COMMIT-INVEST-017",
        )

        cancelled = self.create_investment(
            commitment=commitment,
            reference="INVESTMENT-000021",
            status=Investment.Status.CANCELLED,
        )

        self.assertTrue(cancelled.is_cancelled)

    def test_string_representation_uses_reference(self):
        investment = self.create_investment(
            reference="INVESTMENT-STRING-001",
        )

        self.assertEqual(
            str(investment),
            "INVESTMENT-STRING-001",
        )
    
        
    def test_investment_requires_funded_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-018",
        )

        # The fixture starts as FUNDED; change it to PENDING.
        commitment.status = InvestmentCommitment.Status.PENDING
        commitment.save(update_fields=["status"])

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000022",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError) as context:
            investment.full_clean()

        self.assertIn("commitment", context.exception.message_dict)
        self.assertEqual(
            context.exception.message_dict["commitment"],
            [
                "An investment can only be created from a funded commitment."
            ],
        )


    def test_investment_accepts_funded_commitment(self):
        commitment = self.create_commitment(
            reference="COMMIT-INVEST-019",
        )

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference="INVESTMENT-000023",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        investment.full_clean()

        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.FUNDED,
        )
