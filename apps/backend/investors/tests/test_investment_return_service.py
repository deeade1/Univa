from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
    InvestmentReturn,
)
from investors.services.investment_return import InvestmentReturnService


User = get_user_model()


class InvestmentReturnServiceTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"investment-return-service-{index}@example.com"
            ).exists():
                index += 1

            email = f"investment-return-service-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"INVESTMENT-RETURN-SERVICE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = (
                f"INVESTMENT-RETURN-SERVICE-OPP-{index:03d}"
            )

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Investment Return Service Opportunity",
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
                reference=f"INVESTMENT-RETURN-SERVICE-PLAN-{index:03d}"
            ).exists():
                index += 1

            reference = (
                f"INVESTMENT-RETURN-SERVICE-PLAN-{index:03d}"
            )

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Investment Return Service Plan",
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
                reference=f"INVESTMENT-RETURN-SERVICE-COMMIT-{index:03d}"
            ).exists():
                index += 1

            reference = (
                f"INVESTMENT-RETURN-SERVICE-COMMIT-{index:03d}"
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

    def create_investment(
        self,
        investor=None,
        opportunity=None,
        plan=None,
        commitment=None,
        reference=None,
        amount=Decimal("500000.00"),
        currency="NGN",
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
                reference=f"INVESTMENT-RETURN-SERVICE-INV-{index:03d}"
            ).exists():
                index += 1

            reference = (
                f"INVESTMENT-RETURN-SERVICE-INV-{index:03d}"
            )

        investment = Investment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference=reference,
            amount=amount,
            currency=currency,
            status=Investment.Status.ACTIVE,
            metadata={},
        )

        investment.full_clean()
        investment.save()

        return investment

    def create_investment_return(
        self,
        investment=None,
        reference=None,
        return_type=InvestmentReturn.ReturnType.PROFIT,
        amount=Decimal("75000.00"),
        currency="NGN",
        status=InvestmentReturn.Status.PENDING,
        metadata=None,
    ):
        if investment is None:
            investment = self.create_investment()

        if reference is None:
            index = InvestmentReturn.objects.count() + 1

            while InvestmentReturn.objects.filter(
                reference=f"INVESTMENT-RETURN-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = (
                f"INVESTMENT-RETURN-SERVICE-{index:03d}"
            )

        investment_return = InvestmentReturn(
            investment=investment,
            reference=reference,
            return_type=return_type,
            amount=amount,
            currency=currency,
            status=status,
            metadata={} if metadata is None else metadata,
        )

        investment_return.full_clean()
        investment_return.save()

        return investment_return

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_investment_return(self):
        investment = self.create_investment()

        investment_return = InvestmentReturnService.create(
            investment=investment,
            reference="INVESTMENT-RETURN-SERVICE-001",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("75000.00"),
        )

        self.assertIsNotNone(investment_return.pk)
        self.assertEqual(
            investment_return.investment,
            investment,
        )
        self.assertEqual(
            investment_return.reference,
            "INVESTMENT-RETURN-SERVICE-001",
        )
        self.assertEqual(
            investment_return.return_type,
            InvestmentReturn.ReturnType.PROFIT,
        )
        self.assertEqual(
            investment_return.amount,
            Decimal("75000.00"),
        )
        self.assertEqual(
            investment_return.currency,
            "NGN",
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PENDING,
        )

    def test_create_with_all_fields(self):
        investment = self.create_investment()

        metadata = {
            "source": "investment-service",
            "channel": "web",
        }

        investment_return = InvestmentReturnService.create(
            investment=investment,
            reference="INVESTMENT-RETURN-SERVICE-002",
            return_type=InvestmentReturn.ReturnType.INTEREST,
            amount=Decimal("85000.00"),
            currency="NGN",
            status=InvestmentReturn.Status.CALCULATED,
            metadata=metadata,
        )

        self.assertEqual(
            investment_return.return_type,
            InvestmentReturn.ReturnType.INTEREST,
        )
        self.assertEqual(
            investment_return.amount,
            Decimal("85000.00"),
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CALCULATED,
        )
        self.assertEqual(
            investment_return.metadata,
            metadata,
        )

    def test_create_defaults_metadata(self):
        investment = self.create_investment()

        investment_return = InvestmentReturnService.create(
            investment=investment,
            reference="INVESTMENT-RETURN-SERVICE-003",
            amount=Decimal("75000.00"),
        )

        self.assertEqual(
            investment_return.metadata,
            {},
        )

    def test_create_requires_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.create(
                investment=None,
                reference="INVESTMENT-RETURN-SERVICE-004",
                amount=Decimal("75000.00"),
            )

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_investment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.create(
                investment="invalid",
                reference="INVESTMENT-RETURN-SERVICE-005",
                amount=Decimal("75000.00"),
            )

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    def test_create_requires_reference(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.create(
                investment=investment,
                reference="",
                amount=Decimal("75000.00"),
            )

        self.assertIn(
            "reference",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_metadata(self):
        investment = self.create_investment()

        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.create(
                investment=investment,
                reference="INVESTMENT-RETURN-SERVICE-006",
                amount=Decimal("75000.00"),
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_reference(self):
        investment_return = self.create_investment_return(
            reference="INVESTMENT-RETURN-SERVICE-007",
        )

        InvestmentReturnService.update(
            investment_return,
            reference="INVESTMENT-RETURN-SERVICE-008",
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.reference,
            "INVESTMENT-RETURN-SERVICE-008",
        )

    def test_update_amount(self):
        investment_return = self.create_investment_return()

        InvestmentReturnService.update(
            investment_return,
            amount=Decimal("90000.00"),
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.amount,
            Decimal("90000.00"),
        )

    def test_update_currency(self):
        investment_return = self.create_investment_return()

        InvestmentReturnService.update(
            investment_return,
            currency="USD",
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.currency,
            "USD",
        )

    def test_update_return_type(self):
        investment_return = self.create_investment_return()

        InvestmentReturnService.update(
            investment_return,
            return_type=InvestmentReturn.ReturnType.DIVIDEND,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.return_type,
            InvestmentReturn.ReturnType.DIVIDEND,
        )

    def test_update_metadata(self):
        investment_return = self.create_investment_return(
            metadata={"channel": "web"},
        )

        metadata = {
            "channel": "mobile",
            "source": "campaign",
        }

        InvestmentReturnService.update(
            investment_return,
            metadata=metadata,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.metadata,
            metadata,
        )

    def test_update_investment(self):
        investment_return = self.create_investment_return()

        new_investment = self.create_investment(
            reference="INVESTMENT-RETURN-SERVICE-INV-100",
        )

        InvestmentReturnService.update(
            investment_return,
            investment=new_investment,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.investment,
            new_investment,
        )

    def test_update_preserves_unspecified_fields(self):
        investment_return = self.create_investment_return(
            reference="INVESTMENT-RETURN-SERVICE-009",
            amount=Decimal("75000.00"),
            metadata={"channel": "web"},
        )

        original_investment = investment_return.investment
        original_reference = investment_return.reference
        original_return_type = investment_return.return_type
        original_amount = investment_return.amount
        original_currency = investment_return.currency
        original_status = investment_return.status

        InvestmentReturnService.update(
            investment_return,
            metadata={"channel": "mobile"},
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            investment_return.investment,
            original_investment,
        )
        self.assertEqual(
            investment_return.reference,
            original_reference,
        )
        self.assertEqual(
            investment_return.return_type,
            original_return_type,
        )
        self.assertEqual(
            investment_return.amount,
            original_amount,
        )
        self.assertEqual(
            investment_return.currency,
            original_currency,
        )
        self.assertEqual(
            investment_return.status,
            original_status,
        )
        self.assertEqual(
            investment_return.metadata,
            {"channel": "mobile"},
        )

    def test_update_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.update(
                None,
                amount=Decimal("75000.00"),
            )

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_investment(self):
        investment_return = self.create_investment_return()

        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.update(
                investment_return,
                investment="invalid",
            )

        self.assertIn(
            "investment",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    def test_calculate(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.PENDING,
        )

        result = InvestmentReturnService.calculate(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CALCULATED,
        )

    def test_approve(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.CALCULATED,
        )

        result = InvestmentReturnService.approve(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.APPROVED,
        )

    def test_make_payable(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.APPROVED,
        )

        result = InvestmentReturnService.make_payable(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAYABLE,
        )

    def test_mark_paid(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.PAYABLE,
        )

        result = InvestmentReturnService.mark_paid(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PAID,
        )

    def test_cancel(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.PENDING,
        )

        result = InvestmentReturnService.cancel(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.CANCELLED,
        )

    def test_reverse(self):
        investment_return = self.create_investment_return(
            status=InvestmentReturn.Status.PAID,
        )

        result = InvestmentReturnService.reverse(
            investment_return,
        )

        investment_return.refresh_from_db()

        self.assertEqual(
            result.pk,
            investment_return.pk,
        )
        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.REVERSED,
        )

    def test_calculate_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.calculate(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_approve_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.approve(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_make_payable_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.make_payable(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_mark_paid_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.mark_paid(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_cancel_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.cancel(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )

    def test_reverse_requires_investment_return(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentReturnService.reverse(None)

        self.assertIn(
            "investment_return",
            context.exception.message_dict,
        )