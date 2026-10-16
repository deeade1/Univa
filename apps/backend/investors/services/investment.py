"""
Investment domain services.

This module contains the application/domain operations for Investment.

Architectural boundary
----------------------

InvestmentService is responsible for:

    - creating investments
    - updating investment data
    - activating investments
    - maturing investments
    - closing investments
    - cancelling investments

The service does NOT own:

    - GraphQL concerns
    - HTTP concerns
    - audit persistence
    - notification delivery
    - investment-return calculations
    - payment processing
    - lifecycle transition policy
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)


class InvestmentService:
    """
    Canonical service for Investment domain operations.
    """

    @staticmethod
    def _validate_investment(investment):
        if investment is None:
            raise ValidationError(
                {"investment": "Investment is required."}
            )

        if not isinstance(investment, Investment):
            raise ValidationError(
                {"investment": "A valid investment is required."}
            )

    @staticmethod
    def _validate_investor(investor):
        if investor is None:
            raise ValidationError(
                {"investor": "Investor is required."}
            )

    @staticmethod
    def _validate_opportunity(opportunity):
        if opportunity is None:
            raise ValidationError(
                {"opportunity": "Investment opportunity is required."}
            )

        if not isinstance(opportunity, InvestmentOpportunity):
            raise ValidationError(
                {
                    "opportunity": (
                        "A valid investment opportunity is required."
                    )
                }
            )

    @staticmethod
    def _validate_plan(plan):
        if plan is None:
            raise ValidationError(
                {"plan": "Investment plan is required."}
            )

        if not isinstance(plan, InvestmentPlan):
            raise ValidationError(
                {"plan": "A valid investment plan is required."}
            )

    @staticmethod
    def _validate_commitment(commitment):
        if commitment is None:
            raise ValidationError(
                {"commitment": "Investment commitment is required."}
            )

        if not isinstance(commitment, InvestmentCommitment):
            raise ValidationError(
                {
                    "commitment": (
                        "A valid investment commitment is required."
                    )
                }
            )

    @staticmethod
    def _validate_funded_commitment(commitment):
        """
        Require a funded commitment before creating an investment.
        """
        InvestmentService._validate_commitment(commitment)

        if commitment.status != InvestmentCommitment.Status.FUNDED:
            raise ValidationError(
                {
                    "commitment": (
                        "An investment can only be created from "
                        "a funded commitment."
                    )
                }
            )

    @staticmethod
    def _validate_reference(reference):
        if not reference:
            raise ValidationError(
                {"reference": "Reference is required."}
            )

    @staticmethod
    @transaction.atomic
    def create(
        *,
        investor,
        opportunity,
        plan,
        commitment,
        reference,
        amount,
        currency="NGN",
        status=Investment.Status.PENDING,
        metadata=None,
    ):
        """
        Create an investment from a funded investment commitment.
        """
        InvestmentService._validate_investor(investor)
        InvestmentService._validate_opportunity(opportunity)
        InvestmentService._validate_plan(plan)
        InvestmentService._validate_funded_commitment(commitment)
        InvestmentService._validate_reference(reference)

        if metadata is None:
            metadata = {}

        investment = Investment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            commitment=commitment,
            reference=reference,
            amount=amount,
            currency=currency,
            status=status,
            metadata=metadata,
        )

        investment.full_clean()
        investment.save()

        return investment

    @staticmethod
    @transaction.atomic
    def update(
        investment,
        *,
        investor=None,
        opportunity=None,
        plan=None,
        commitment=None,
        reference=None,
        amount=None,
        currency=None,
        metadata=None,
    ):
        """
        Update mutable investment fields.

        None means that the corresponding field remains unchanged.
        """
        InvestmentService._validate_investment(investment)

        if investor is not None:
            InvestmentService._validate_investor(investor)
            investment.investor = investor

        if opportunity is not None:
            InvestmentService._validate_opportunity(opportunity)
            investment.opportunity = opportunity

        if plan is not None:
            InvestmentService._validate_plan(plan)
            investment.plan = plan

        
        
        if commitment is not None:
            InvestmentService._validate_commitment(commitment)

            if commitment.pk != investment.commitment_id:
                raise ValidationError(
                    {
                        "commitment": (
                            "An investment cannot be reassigned to a "
                            "different commitment after creation."
                        )
                    }
                )

            investment.commitment = commitment



        if reference is not None:
            investment.reference = reference

        if amount is not None:
            investment.amount = amount

        if currency is not None:
            investment.currency = currency

        if metadata is not None:
            investment.metadata = metadata

        investment.full_clean()
        investment.save()

        return investment

    @staticmethod
    @transaction.atomic
    def activate(investment):
        """
        Set an investment to ACTIVE.
        """
        InvestmentService._validate_investment(investment)

        investment.status = Investment.Status.ACTIVE

        investment.full_clean()
        investment.save(update_fields=["status", "updated_at"])

        return investment

    @staticmethod
    @transaction.atomic
    def mature(investment):
        """
        Set an investment to MATURED.
        """
        InvestmentService._validate_investment(investment)

        investment.status = Investment.Status.MATURED

        investment.full_clean()
        investment.save(update_fields=["status", "updated_at"])

        return investment

    @staticmethod
    @transaction.atomic
    def close(investment):
        """
        Set an investment to CLOSED.
        """
        InvestmentService._validate_investment(investment)

        investment.status = Investment.Status.CLOSED

        investment.full_clean()
        investment.save(update_fields=["status", "updated_at"])

        return investment

    @staticmethod
    @transaction.atomic
    def cancel(investment):
        """
        Set an investment to CANCELLED.
        """
        InvestmentService._validate_investment(investment)

        investment.status = Investment.Status.CANCELLED

        investment.full_clean()
        investment.save(update_fields=["status", "updated_at"])

        return investment
