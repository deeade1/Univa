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


User = get_user_model()


class InvestmentReturnModelTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"return-investor-{index}@example.com"
            ).exists():
                index += 1

            email = f"return-investor-{index}@example.com"

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
                reference=f"OPP-RETURN-{index:03d}"
            ).exists():
                index += 1

            reference = f"OPP-RETURN-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Univa Return Opportunity",
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
                reference=f"PLAN-RETURN-{index:03d}"
            ).exists():
                index += 1

            reference = f"PLAN-RETURN-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Return Investment Plan",
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
                reference=f"COMMIT-RETURN-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMIT-RETURN-{index:03d}"

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
        commitment=None,
        reference=None,
    ):
        if commitment is None:
            commitment = self.create_commitment()

        if reference is None:
            index = Investment.objects.count() + 1

            while Investment.objects.filter(
                reference=f"INVESTMENT-RETURN-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTMENT-RETURN-{index:03d}"

        investment = Investment(
            investor_id=commitment.investor_id,
            opportunity_id=commitment.opportunity_id,
            plan_id=commitment.plan_id,
            commitment=commitment,
            reference=reference,
            amount=commitment.amount,
            currency=commitment.currency,
            status=Investment.Status.ACTIVE,
        )

        investment.full_clean()
        investment.save()

        return investment
    
    def create_return(self, **kwargs):
        investment = kwargs.pop(
            "investment",
            None,
        )

        if investment is None:
            investment = self.create_investment()

        defaults = {
            "investment": investment,
            "reference": "RETURN-000001",
            "return_type": InvestmentReturn.ReturnType.PROFIT,
            "amount": Decimal("75000.00"),
            "currency": investment.currency,
            "status": InvestmentReturn.Status.PENDING,
        }

        defaults.update(kwargs)

        investment_return = InvestmentReturn(**defaults)
        investment_return.full_clean()
        investment_return.save()

        return investment_return

    def test_return_can_be_created(self):
        investment_return = self.create_return()

        self.assertIsNotNone(
            investment_return.id,
        )

        self.assertEqual(
            investment_return.reference,
            "RETURN-000001",
        )

        self.assertEqual(
            investment_return.amount,
            Decimal("75000.00"),
        )

    def test_return_belongs_to_investment(self):
        investment = self.create_investment()

        investment_return = self.create_return(
            investment=investment,
        )

        self.assertEqual(
            investment_return.investment,
            investment,
        )

        self.assertEqual(
            investment.returns.first(),
            investment_return,
        )

    def test_multiple_returns_can_belong_to_same_investment(self):
        investment = self.create_investment()

        first = self.create_return(
            investment=investment,
            reference="RETURN-000002",
        )

        second = self.create_return(
            investment=investment,
            reference="RETURN-000003",
        )

        self.assertEqual(
            investment.returns.count(),
            2,
        )

        self.assertIn(
            first,
            investment.returns.all(),
        )

        self.assertIn(
            second,
            investment.returns.all(),
        )

    def test_reference_is_required(self):
        investment = self.create_investment()

        investment_return = InvestmentReturn(
            investment=investment,
            reference="",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("75000.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            investment_return.full_clean()

    def test_amount_must_be_positive(self):
        investment = self.create_investment()

        investment_return = InvestmentReturn(
            investment=investment,
            reference="RETURN-000004",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("0.00"),
            currency="NGN",
        )

        with self.assertRaises(ValidationError):
            investment_return.full_clean()

    def test_currency_is_normalized_to_uppercase(self):
        investment = self.create_investment()

        investment_return = InvestmentReturn(
            investment=investment,
            reference="RETURN-000005",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("75000.00"),
            currency="ngn",
        )

        investment_return.full_clean()

        self.assertEqual(
            investment_return.currency,
            "NGN",
        )

    def test_currency_must_be_three_characters(self):
        investment = self.create_investment()

        investment_return = InvestmentReturn(
            investment=investment,
            reference="RETURN-000006",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("75000.00"),
            currency="NG",
        )

        with self.assertRaises(ValidationError):
            investment_return.full_clean()

    def test_metadata_defaults_to_empty_dictionary(self):
        investment_return = self.create_return(
            reference="RETURN-000007",
        )

        self.assertEqual(
            investment_return.metadata,
            {},
        )

    def test_metadata_must_be_dictionary(self):
        investment = self.create_investment()

        investment_return = InvestmentReturn(
            investment=investment,
            reference="RETURN-000008",
            return_type=InvestmentReturn.ReturnType.PROFIT,
            amount=Decimal("75000.00"),
            currency="NGN",
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            investment_return.full_clean()

    def test_default_status_is_pending(self):
        investment_return = self.create_return(
            reference="RETURN-000009",
        )

        self.assertEqual(
            investment_return.status,
            InvestmentReturn.Status.PENDING,
        )

    def test_status_helpers(self):
        pending = self.create_return(
            reference="RETURN-000010",
            status=InvestmentReturn.Status.PENDING,
        )

        self.assertTrue(pending.is_pending)
        self.assertFalse(pending.is_calculated)

        calculated = self.create_return(
            reference="RETURN-000011",
            status=InvestmentReturn.Status.CALCULATED,
        )

        self.assertTrue(calculated.is_calculated)

        approved = self.create_return(
            reference="RETURN-000012",
            status=InvestmentReturn.Status.APPROVED,
        )

        self.assertTrue(approved.is_approved)

        payable = self.create_return(
            reference="RETURN-000013",
            status=InvestmentReturn.Status.PAYABLE,
        )

        self.assertTrue(payable.is_payable)

        paid = self.create_return(
            reference="RETURN-000014",
            status=InvestmentReturn.Status.PAID,
        )

        self.assertTrue(paid.is_paid)

        cancelled = self.create_return(
            reference="RETURN-000015",
            status=InvestmentReturn.Status.CANCELLED,
        )

        self.assertTrue(cancelled.is_cancelled)

        reversed_return = self.create_return(
            reference="RETURN-000016",
            status=InvestmentReturn.Status.REVERSED,
        )

        self.assertTrue(reversed_return.is_reversed)

    def test_all_return_types_are_supported(self):
        return_types = [
            InvestmentReturn.ReturnType.PROFIT,
            InvestmentReturn.ReturnType.INTEREST,
            InvestmentReturn.ReturnType.DIVIDEND,
            InvestmentReturn.ReturnType.CAPITAL_GAIN,
            InvestmentReturn.ReturnType.OTHER,
        ]

        for index, return_type in enumerate(return_types, start=17):
            investment = self.create_investment(
                reference=f"INVESTMENT-RETURN-{index:03d}",
            )

            investment_return = self.create_return(
                investment=investment,
                reference=f"RETURN-{index:06d}",
                return_type=return_type,
            )

            self.assertEqual(
                investment_return.return_type,
                return_type,
            )

    def test_string_representation_uses_reference(self):
        investment_return = self.create_return(
            reference="RETURN-STRING-001",
        )

        self.assertEqual(
            str(investment_return),
            "RETURN-STRING-001",
        )