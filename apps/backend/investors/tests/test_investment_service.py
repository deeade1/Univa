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
from investors.services.investment import InvestmentService


User = get_user_model()


class InvestmentServiceTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"investment-service-{index}@example.com"
            ).exists():
                index += 1

            email = f"investment-service-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"INVESTMENT-SERVICE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTMENT-SERVICE-OPP-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Investment Service Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def create_plan(self, opportunity=None, reference=None):
        if opportunity is None:
            opportunity = self.create_opportunity()

        if reference is None:
            index = InvestmentPlan.objects.count() + 1

            while InvestmentPlan.objects.filter(
                reference=f"INVESTMENT-SERVICE-PLAN-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTMENT-SERVICE-PLAN-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Investment Service Plan",
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
        reference=None,
        amount=Decimal("500000.00"),
        currency="NGN",
        status=InvestmentCommitment.Status.FUNDED,
    ):
        if investor is None:
            investor = self.create_user()

        if opportunity is None:
            opportunity = self.create_opportunity()

        if plan is None:
            plan = self.create_plan(
                opportunity=opportunity,
            )

        if reference is None:
            index = InvestmentCommitment.objects.count() + 1

            while InvestmentCommitment.objects.filter(
                reference=f"INVESTMENT-SERVICE-COMMIT-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTMENT-SERVICE-COMMIT-{index:03d}"

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference=reference,
            amount=amount,
            currency=currency,
            status=status,
        )

        commitment.full_clean()
        commitment.save()

        return commitment

    def create_investment(
        self,
        investor=None,
        opportunity=None,
        plan=None,
        commitment=None,
        reference=None,
        amount=Decimal("500000.00"),
        currency="NGN",
        status=Investment.Status.PENDING,
        metadata=None,
    ):
        if commitment is None:
            commitment = self.create_commitment(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                amount=amount,
                currency=currency,
            )

        if investor is None:
            investor = commitment.investor

        if opportunity is None:
            opportunity = commitment.opportunity

        if plan is None:
            plan = commitment.plan

        if reference is None:
            index = Investment.objects.count() + 1

            while Investment.objects.filter(
                reference=f"INVESTMENT-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTMENT-SERVICE-{index:03d}"

        investment = Investment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference=reference,
            amount=amount,
            currency=currency,
            status=status,
            metadata={} if metadata is None else metadata,
        )

        investment.full_clean()
        investment.save()

        return investment

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_investment(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        investment = InvestmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference="INVESTMENT-SERVICE-001",
            amount=Decimal("500000.00"),
        )

        self.assertIsNotNone(investment.pk)
        self.assertEqual(investment.investor, investor)
        self.assertEqual(investment.opportunity, opportunity)
        self.assertEqual(investment.plan, plan)
        self.assertEqual(investment.commitment, commitment)
        self.assertEqual(
            investment.reference,
            "INVESTMENT-SERVICE-001",
        )
        self.assertEqual(
            investment.amount,
            Decimal("500000.00"),
        )
        self.assertEqual(
            investment.currency,
            "NGN",
        )
        self.assertEqual(
            investment.status,
            Investment.Status.PENDING,
        )

    def test_create_with_all_fields(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            amount=Decimal("750000.00"),
        )

        metadata = {
            "source": "service-test",
            "channel": "web",
        }

        investment = InvestmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference="INVESTMENT-SERVICE-002",
            amount=Decimal("750000.00"),
            currency="NGN",
            status=Investment.Status.ACTIVE,
            metadata=metadata,
        )

        self.assertEqual(
            investment.status,
            Investment.Status.ACTIVE,
        )
        self.assertEqual(
            investment.metadata,
            metadata,
        )

    def test_create_defaults_metadata(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        investment = InvestmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference="INVESTMENT-SERVICE-003",
            amount=Decimal("500000.00"),
        )

        self.assertEqual(investment.metadata, {})

    def test_create_requires_investor(self):
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            opportunity=opportunity,
            plan=plan,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=None,
                opportunity=opportunity,
                plan=plan,
                commitment=commitment,
                reference="INVESTMENT-SERVICE-004",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_create_requires_opportunity(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=None,
                plan=plan,
                commitment=commitment,
                reference="INVESTMENT-SERVICE-005",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_create_requires_plan(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=None,
                commitment=commitment,
                reference="INVESTMENT-SERVICE-006",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_create_requires_commitment(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                commitment=None,
                reference="INVESTMENT-SERVICE-007",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_create_requires_reference(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                commitment=commitment,
                reference="",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "reference",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_metadata(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                commitment=commitment,
                reference="INVESTMENT-SERVICE-008",
                amount=Decimal("500000.00"),
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_create_rejects_mismatched_commitment(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        other_investor = self.create_user()

        commitment = self.create_commitment(
            investor=other_investor,
            opportunity=opportunity,
            plan=plan,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                commitment=commitment,
                reference="INVESTMENT-SERVICE-009",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_reference(self):
        investment = self.create_investment(
            reference="INVESTMENT-SERVICE-010",
        )

        InvestmentService.update(
            investment,
            reference="INVESTMENT-SERVICE-011",
        )

        investment.refresh_from_db()

        self.assertEqual(
            investment.reference,
            "INVESTMENT-SERVICE-011",
        )

    def test_update_amount_rejects_mismatch_with_commitment(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError) as context:
            InvestmentService.update(
                investment,
                amount=Decimal("750000.00"),
            )

        self.assertIn(
            "amount",
            context.exception.message_dict,
        )

    def test_update_currency_rejects_mismatch_with_commitment(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError) as context:
            InvestmentService.update(
                investment,
                currency="USD",
            )

        self.assertIn(
            "currency",
            context.exception.message_dict,
        )

    def test_update_metadata(self):
        investment = self.create_investment(
            metadata={"channel": "web"},
        )

        metadata = {
            "channel": "mobile",
            "source": "campaign",
        }

        InvestmentService.update(
            investment,
            metadata=metadata,
        )

        investment.refresh_from_db()

        self.assertEqual(
            investment.metadata,
            metadata,
        )

    def test_update_investor_rejects_mismatch_with_commitment(self):
        investment = self.create_investment()
        new_investor = self.create_user()

        with self.assertRaises(ValidationError) as context:
            InvestmentService.update(
                investment,
                investor=new_investor,
            )

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    
    def test_update_commitment_with_matching_relationships(self):
        investment = self.create_investment()
        original_commitment = investment.commitment

        InvestmentService.update(
            investment,
            investor=original_commitment.investor,
            opportunity=original_commitment.opportunity,
            plan=original_commitment.plan,
            commitment=original_commitment,
            amount=original_commitment.amount,
            currency=original_commitment.currency,
        )

        investment.refresh_from_db()

        self.assertEqual(
            investment.investor,
            original_commitment.investor,
        )
        self.assertEqual(
            investment.opportunity,
            original_commitment.opportunity,
        )
        self.assertEqual(
            investment.plan,
            original_commitment.plan,
        )
        self.assertEqual(
            investment.commitment,
            original_commitment,
        )
        self.assertEqual(
            investment.amount,
            original_commitment.amount,
        )
        self.assertEqual(
            investment.currency,
            original_commitment.currency,
        )


    def test_update_preserves_unspecified_fields(self):
        investment = self.create_investment(
            reference="INVESTMENT-SERVICE-012",
            metadata={"channel": "web"},
        )

        original_investor = investment.investor
        original_opportunity = investment.opportunity
        original_plan = investment.plan
        original_commitment = investment.commitment
        original_amount = investment.amount
        original_currency = investment.currency

        InvestmentService.update(
            investment,
            metadata={"channel": "mobile"},
        )

        investment.refresh_from_db()

        self.assertEqual(
            investment.investor,
            original_investor,
        )
        self.assertEqual(
            investment.opportunity,
            original_opportunity,
        )
        self.assertEqual(
            investment.plan,
            original_plan,
        )
        self.assertEqual(
            investment.commitment,
            original_commitment,
        )
        self.assertEqual(
            investment.reference,
            "INVESTMENT-SERVICE-012",
        )
        self.assertEqual(
            investment.amount,
            original_amount,
        )
        self.assertEqual(
            investment.currency,
            original_currency,
        )
        self.assertEqual(
            investment.metadata,
            {"channel": "mobile"},
        )

    def test_update_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentService.update(
                None,
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_commitment(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError) as context:
            InvestmentService.update(
                investment,
                commitment="invalid",
            )

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    def test_activate(self):
        investment = self.create_investment(
            status=Investment.Status.PENDING,
        )

        result = InvestmentService.activate(investment)

        investment.refresh_from_db()

        self.assertEqual(result.pk, investment.pk)
        self.assertEqual(
            investment.status,
            Investment.Status.ACTIVE,
        )

    def test_mature(self):
        investment = self.create_investment(
            status=Investment.Status.ACTIVE,
        )

        result = InvestmentService.mature(investment)

        investment.refresh_from_db()

        self.assertEqual(result.pk, investment.pk)
        self.assertEqual(
            investment.status,
            Investment.Status.MATURED,
        )

    def test_close(self):
        investment = self.create_investment(
            status=Investment.Status.MATURED,
        )

        result = InvestmentService.close(investment)

        investment.refresh_from_db()

        self.assertEqual(result.pk, investment.pk)
        self.assertEqual(
            investment.status,
            Investment.Status.CLOSED,
        )

    def test_cancel(self):
        investment = self.create_investment(
            status=Investment.Status.PENDING,
        )

        result = InvestmentService.cancel(investment)

        investment.refresh_from_db()

        self.assertEqual(result.pk, investment.pk)
        self.assertEqual(
            investment.status,
            Investment.Status.CANCELLED,
        )

    def test_activate_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentService.activate(None)

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_mature_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentService.mature(None)

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_close_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentService.close(None)

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_cancel_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentService.cancel(None)

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )
        
    def test_create_rejects_unfunded_commitment(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            status=InvestmentCommitment.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                commitment=commitment,
                reference="INV-UNFUNDED-001",
                amount=Decimal("1000.00"),
                currency="NGN",
            )

        self.assertIn("funded", str(context.exception).lower())
        
    
    def test_create_rejects_duplicate_investment_for_commitment(self):
        commitment = self.create_commitment()

        first_investment = InvestmentService.create(
            investor=commitment.investor,
            opportunity=commitment.opportunity,
            plan=commitment.plan,
            commitment=commitment,
            reference="INVESTMENT-DUPLICATE-001",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        with self.assertRaises(ValidationError):
            InvestmentService.create(
                investor=commitment.investor,
                opportunity=commitment.opportunity,
                plan=commitment.plan,
                commitment=commitment,
                reference="INVESTMENT-DUPLICATE-002",
                amount=commitment.amount,
                currency=commitment.currency,
            )

        self.assertTrue(
            Investment.objects.filter(pk=first_investment.pk).exists()
        )
        self.assertEqual(
            Investment.objects.filter(commitment=commitment).count(),
            1,
        )
        
    
    def test_update_rejects_reassigning_investment_commitment(self):
        investment = self.create_investment()

        second_commitment = self.create_commitment(
            investor=investment.investor,
            opportunity=investment.opportunity,
            plan=investment.plan,
            amount=investment.amount,
            currency=investment.currency,
            status=InvestmentCommitment.Status.FUNDED,
        )

        original_commitment_id = investment.commitment_id

        with self.assertRaises(ValidationError):
            InvestmentService.update(
                investment,
                commitment=second_commitment,
            )

        investment.refresh_from_db()

        self.assertEqual(
            investment.commitment_id,
            original_commitment_id,
        )
        self.assertNotEqual(
            investment.commitment_id,
            second_commitment.pk,
        )

