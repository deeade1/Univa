from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import (
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)


User = get_user_model()


class InvestmentCommitmentModelTests(TestCase):

    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(
        self,
        reference="OPP-COMMIT-001",
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

    def create_plan(
        self,
        opportunity=None,
        reference="PLAN-COMMIT-001",
    ):
        if opportunity is None:
            opportunity = self.create_opportunity()

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

    def create_commitment(self, **kwargs):
        investor = kwargs.pop(
            "investor",
            None,
        )

        if investor is None:
            investor = self.create_user()

        opportunity = kwargs.pop(
            "opportunity",
            None,
        )

        if opportunity is None:
            opportunity = self.create_opportunity()

        plan = kwargs.pop(
            "plan",
            None,
        )

        if plan is None:
            plan = self.create_plan(
                opportunity=opportunity,
            )

        defaults = {
            "investor": investor,
            "opportunity": opportunity,
            "plan": plan,
            "reference": "COMMIT-000001",
            "amount": Decimal("500000.00"),
            "currency": "NGN",
            "status": InvestmentCommitment.Status.PENDING,
        }

        defaults.update(kwargs)

        commitment = InvestmentCommitment(**defaults)
        commitment.full_clean()
        commitment.save()

        return commitment

    def test_commitment_can_be_created(self):
        commitment = self.create_commitment()

        self.assertIsNotNone(commitment.id)

        self.assertEqual(
            commitment.reference,
            "COMMIT-000001",
        )

        self.assertEqual(
            commitment.amount,
            Decimal("500000.00"),
        )

    def test_commitment_belongs_to_investor(self):
        investor = self.create_user(
            "investor-one@example.com",
        )

        commitment = self.create_commitment(
            investor=investor,
            reference="COMMIT-000002",
        )

        self.assertEqual(
            commitment.investor,
            investor,
        )

        self.assertIn(
            commitment,
            investor.investment_commitments.all(),
        )

    def test_commitment_belongs_to_opportunity(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-002",
        )

        commitment = self.create_commitment(
            opportunity=opportunity,
            reference="COMMIT-000003",
        )

        self.assertEqual(
            commitment.opportunity,
            opportunity,
        )

        self.assertIn(
            commitment,
            opportunity.commitments.all(),
        )

    def test_commitment_belongs_to_plan(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-003",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-002",
        )

        commitment = self.create_commitment(
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000004",
        )

        self.assertEqual(
            commitment.plan,
            plan,
        )

        self.assertIn(
            commitment,
            plan.commitments.all(),
        )

    def test_default_status_is_pending(self):
        commitment = self.create_commitment(
            reference="COMMIT-000005",
        )

        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.PENDING,
        )
    
    def test_reference_must_be_unique(self):
        self.create_commitment(
            reference="COMMIT-UNIQUE-001",
        )

        investor = self.create_user(
            "second-investor@example.com",
        )

        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-004",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-003",
        )

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-UNIQUE-001",
            amount=Decimal("500000.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()
    
    def test_amount_must_be_positive(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-005",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-004",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "amount@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000007",
            amount=Decimal("0.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_currency_is_normalized_to_uppercase(self):
        commitment = self.create_commitment(
            reference="COMMIT-000008",
            currency="ngn",
        )

        self.assertEqual(
            commitment.currency,
            "NGN",
        )

    def test_currency_must_be_three_characters(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-006",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-005",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "currency@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000009",
            amount=Decimal("500000.00"),
            currency="NG",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_amount_cannot_be_below_plan_minimum(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-007",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-006",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "below-min@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000010",
            amount=Decimal("50000.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_amount_cannot_exceed_plan_maximum(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-008",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-007",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "above-max@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000011",
            amount=Decimal("6000000.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_plan_must_belong_to_selected_opportunity(self):
        opportunity_one = self.create_opportunity(
            reference="OPP-COMMIT-009",
        )

        opportunity_two = self.create_opportunity(
            reference="OPP-COMMIT-010",
        )

        plan = self.create_plan(
            opportunity=opportunity_two,
            reference="PLAN-COMMIT-008",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "mismatch@example.com",
            ),
            opportunity=opportunity_one,
            plan=plan,
            reference="COMMIT-000012",
            amount=Decimal("500000.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_metadata_defaults_to_empty_dictionary(self):
        commitment = self.create_commitment(
            reference="COMMIT-000013",
        )

        self.assertEqual(
            commitment.metadata,
            {},
        )

    def test_metadata_must_be_dictionary(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-011",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-009",
        )

        commitment = InvestmentCommitment(
            investor=self.create_user(
                "metadata@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000014",
            amount=Decimal("500000.00"),
            currency="NGN",
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            commitment.full_clean()


    def test_status_helpers(self):
        opportunity = self.create_opportunity(
            reference="OPP-COMMIT-STATUS",
        )

        plan = self.create_plan(
            opportunity=opportunity,
            reference="PLAN-COMMIT-STATUS",
        )

        pending = self.create_commitment(
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000015",
            status=InvestmentCommitment.Status.PENDING,
        )

        self.assertTrue(pending.is_pending)
        self.assertFalse(pending.is_confirmed)

        confirmed = self.create_commitment(
            investor=self.create_user(
                "confirmed@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000016",
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        self.assertTrue(confirmed.is_confirmed)

        funded = self.create_commitment(
            investor=self.create_user(
                "funded@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000017",
            status=InvestmentCommitment.Status.FUNDED,
        )

        self.assertTrue(funded.is_funded)

        cancelled = self.create_commitment(
            investor=self.create_user(
                "cancelled@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000018",
            status=InvestmentCommitment.Status.CANCELLED,
        )

        self.assertTrue(cancelled.is_cancelled)

        expired = self.create_commitment(
            investor=self.create_user(
                "expired@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000019",
            status=InvestmentCommitment.Status.EXPIRED,
        )

        self.assertTrue(expired.is_expired)

        rejected = self.create_commitment(
            investor=self.create_user(
                "rejected@example.com",
            ),
            opportunity=opportunity,
            plan=plan,
            reference="COMMIT-000020",
            status=InvestmentCommitment.Status.REJECTED,
        )

        self.assertTrue(rejected.is_rejected)

    def test_string_representation_uses_reference(self):
        commitment = self.create_commitment(
            reference="COMMIT-STRING-001",
        )

        self.assertEqual(
            str(commitment),
            "COMMIT-STRING-001",
        )