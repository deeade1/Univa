from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from investors.models import (
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)
from investors.services.commitment import CommitmentService
from investors.models import Investment, InvestmentCommitment
from investors.services.investment import InvestmentService

User = get_user_model()


class CommitmentServiceTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"commitment-service-{index}@example.com"
            ).exists():
                index += 1

            email = f"commitment-service-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"COMMITMENT-SERVICE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-SERVICE-OPP-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Commitment Service Opportunity",
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
                reference=f"COMMITMENT-SERVICE-PLAN-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-SERVICE-PLAN-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Commitment Service Plan",
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
        status=InvestmentCommitment.Status.PENDING,
        expires_at=None,
        metadata=None,
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
                reference=f"COMMITMENT-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-SERVICE-{index:03d}"

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference=reference,
            amount=amount,
            currency=currency,
            status=status,
            expires_at=expires_at,
            metadata={} if metadata is None else metadata,
        )

        commitment.full_clean()
        commitment.save()

        return commitment

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_commitment(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = CommitmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference="COMMITMENT-SERVICE-001",
            amount=Decimal("500000.00"),
        )

        self.assertIsNotNone(commitment.pk)
        self.assertEqual(commitment.investor, investor)
        self.assertEqual(commitment.opportunity, opportunity)
        self.assertEqual(commitment.plan, plan)
        self.assertEqual(
            commitment.reference,
            "COMMITMENT-SERVICE-001",
        )
        self.assertEqual(
            commitment.amount,
            Decimal("500000.00"),
        )
        self.assertEqual(
            commitment.currency,
            "NGN",
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.PENDING,
        )

    def test_create_with_all_fields(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        expires_at = timezone.now() + timedelta(days=7)
        metadata = {
            "channel": "web",
            "source": "campaign",
        }

        commitment = CommitmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference="COMMITMENT-SERVICE-002",
            amount=Decimal("750000.00"),
            currency="USD",
            status=InvestmentCommitment.Status.CONFIRMED,
            expires_at=expires_at,
            metadata=metadata,
        )

        self.assertEqual(commitment.currency, "USD")
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CONFIRMED,
        )
        self.assertEqual(commitment.metadata, metadata)
        self.assertEqual(commitment.expires_at, expires_at)

    def test_create_defaults_metadata(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = CommitmentService.create(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference="COMMITMENT-SERVICE-003",
            amount=Decimal("500000.00"),
        )

        self.assertEqual(commitment.metadata, {})

    def test_create_requires_investor(self):
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=None,
                opportunity=opportunity,
                plan=plan,
                reference="COMMITMENT-SERVICE-004",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_create_requires_opportunity(self):
        investor = self.create_user()
        plan_opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=plan_opportunity)

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=None,
                plan=plan,
                reference="COMMITMENT-SERVICE-005",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_create_requires_plan(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=None,
                reference="COMMITMENT-SERVICE-006",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_create_requires_reference(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                reference="",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "reference",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_amount(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                reference="COMMITMENT-SERVICE-007",
                amount=Decimal("0.00"),
            )

        self.assertIn(
            "amount",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_metadata(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                reference="COMMITMENT-SERVICE-008",
                amount=Decimal("500000.00"),
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_create_rejects_plan_from_different_opportunity(self):
        investor = self.create_user()
        opportunity = self.create_opportunity(
            reference="COMMITMENT-SERVICE-OPP-100",
        )
        other_opportunity = self.create_opportunity(
            reference="COMMITMENT-SERVICE-OPP-101",
        )
        plan = self.create_plan(
            opportunity=other_opportunity,
        )

        with self.assertRaises(ValidationError) as context:
            CommitmentService.create(
                investor=investor,
                opportunity=opportunity,
                plan=plan,
                reference="COMMITMENT-SERVICE-009",
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_amount(self):
        commitment = self.create_commitment()

        CommitmentService.update(
            commitment,
            amount=Decimal("750000.00"),
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.amount,
            Decimal("750000.00"),
        )

    def test_update_reference(self):
        commitment = self.create_commitment(
            reference="COMMITMENT-SERVICE-010",
        )

        CommitmentService.update(
            commitment,
            reference="COMMITMENT-SERVICE-011",
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.reference,
            "COMMITMENT-SERVICE-011",
        )

    def test_update_currency(self):
        commitment = self.create_commitment()

        CommitmentService.update(
            commitment,
            currency="USD",
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.currency,
            "USD",
        )

    def test_update_metadata(self):
        commitment = self.create_commitment(
            metadata={"channel": "web"},
        )

        metadata = {
            "channel": "mobile",
            "campaign": "summer",
        }

        CommitmentService.update(
            commitment,
            metadata=metadata,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.metadata,
            metadata,
        )

    def test_update_expires_at(self):
        commitment = self.create_commitment()

        expires_at = timezone.now() + timedelta(days=14)

        CommitmentService.update(
            commitment,
            expires_at=expires_at,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.expires_at,
            expires_at,
        )

    def test_update_investor(self):
        commitment = self.create_commitment()
        new_investor = self.create_user()

        CommitmentService.update(
            commitment,
            investor=new_investor,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.investor,
            new_investor,
        )

    def test_update_opportunity_and_plan_together(self):
        commitment = self.create_commitment()

        new_opportunity = self.create_opportunity(
            reference="COMMITMENT-SERVICE-OPP-102",
        )
        new_plan = self.create_plan(
            opportunity=new_opportunity,
            reference="COMMITMENT-SERVICE-PLAN-102",
        )

        CommitmentService.update(
            commitment,
            opportunity=new_opportunity,
            plan=new_plan,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            commitment.opportunity,
            new_opportunity,
        )
        self.assertEqual(
            commitment.plan,
            new_plan,
        )

    def test_update_preserves_unspecified_fields(self):
        investor = self.create_user()
        opportunity = self.create_opportunity()
        plan = self.create_plan(opportunity=opportunity)

        commitment = self.create_commitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference="COMMITMENT-SERVICE-012",
            amount=Decimal("500000.00"),
            metadata={"channel": "web"},
        )

        CommitmentService.update(
            commitment,
            amount=Decimal("750000.00"),
        )

        commitment.refresh_from_db()

        self.assertEqual(commitment.investor, investor)
        self.assertEqual(commitment.opportunity, opportunity)
        self.assertEqual(commitment.plan, plan)
        self.assertEqual(
            commitment.reference,
            "COMMITMENT-SERVICE-012",
        )
        self.assertEqual(
            commitment.amount,
            Decimal("750000.00"),
        )
        self.assertEqual(
            commitment.metadata,
            {"channel": "web"},
        )

    def test_update_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            CommitmentService.update(
                None,
                amount=Decimal("500000.00"),
            )

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_plan(self):
        commitment = self.create_commitment()

        with self.assertRaises(ValidationError) as context:
            CommitmentService.update(
                commitment,
                plan="invalid",
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    def test_update_rejects_plan_from_different_opportunity(self):
        commitment = self.create_commitment()

        other_opportunity = self.create_opportunity(
            reference="COMMITMENT-SERVICE-OPP-103",
        )
        other_plan = self.create_plan(
            opportunity=other_opportunity,
            reference="COMMITMENT-SERVICE-PLAN-103",
        )

        with self.assertRaises(ValidationError) as context:
            CommitmentService.update(
                commitment,
                opportunity=commitment.opportunity,
                plan=other_plan,
            )

        self.assertIn(
            "plan",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    def test_confirm(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        result = CommitmentService.confirm(commitment)

        commitment.refresh_from_db()

        self.assertEqual(result.pk, commitment.pk)
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CONFIRMED,
        )

    def test_fund(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        result = CommitmentService.fund(commitment)

        commitment.refresh_from_db()

        self.assertEqual(result.pk, commitment.pk)
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.FUNDED,
        )

    def test_cancel(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        result = CommitmentService.cancel(commitment)

        commitment.refresh_from_db()

        self.assertEqual(result.pk, commitment.pk)
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CANCELLED,
        )

    def test_expire(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        result = CommitmentService.expire(commitment)

        commitment.refresh_from_db()

        self.assertEqual(result.pk, commitment.pk)
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.EXPIRED,
        )

    def test_confirm_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            CommitmentService.confirm(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_fund_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            CommitmentService.fund(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_cancel_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            CommitmentService.cancel(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_expire_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            CommitmentService.expire(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        ) 
    
    def test_update_amount_rejected_when_commitment_has_investment(self):
        commitment = self.create_commitment(
            reference="COMMITMENT-SERVICE-REGRESSION-001",
        )

        # Prepare a funded commitment.
        commitment.status = InvestmentCommitment.Status.FUNDED
        commitment.save(update_fields=["status"])

        # Create the investment through the canonical service.
        investment = InvestmentService.create(
            investor=commitment.investor,
            opportunity=commitment.opportunity,
            plan=commitment.plan,
            commitment=commitment,
            reference="INVESTMENT-COMMITMENT-UPDATE-REGRESSION-001",
            amount=commitment.amount,
            currency=commitment.currency,
        )

        original_amount = commitment.amount

        with self.assertRaises(ValidationError):
            CommitmentService.update(
                commitment,
                amount=Decimal("600000.00"),
            )

        commitment.refresh_from_db()
        investment.refresh_from_db()

        self.assertEqual(commitment.amount, original_amount)
        self.assertEqual(investment.amount, original_amount)