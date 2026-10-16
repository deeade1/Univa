"""
Investment plan domain services.

This module contains the application/domain operations for InvestmentPlan.

Architectural boundary
----------------------

PlanService is responsible for:

    - creating investment plans
    - updating plan profile data
    - activating plans
    - pausing plans
    - closing plans
    - cancelling plans

The service does NOT own:

    - GraphQL concerns
    - HTTP concerns
    - audit persistence
    - notification delivery
    - investment calculations
    - lifecycle transition policy
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import InvestmentOpportunity, InvestmentPlan


class PlanService:
    """
    Canonical service for InvestmentPlan domain operations.
    """

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
    def _validate_opportunity(opportunity):
        if opportunity is None:
            raise ValidationError(
                {"opportunity": "Investment opportunity is required."}
            )

        if not isinstance(opportunity, InvestmentOpportunity):
            raise ValidationError(
                {"opportunity": "A valid investment opportunity is required."}
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
        opportunity,
        reference,
        name,
        description="",
        status=InvestmentPlan.Status.DRAFT,
        minimum_amount=Decimal("100000.00"),
        maximum_amount=None,
        duration_days=None,
        expected_return_rate=None,
        metadata=None,
    ):
        """
        Create an investment plan for an opportunity.
        """
        PlanService._validate_opportunity(opportunity)
        PlanService._validate_reference(reference)

        if metadata is None:
            metadata = {}

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name=name,
            description=description,
            status=status,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            duration_days=duration_days,
            expected_return_rate=expected_return_rate,
            metadata=metadata,
        )

        plan.full_clean()
        plan.save()

        return plan

    @staticmethod
    @transaction.atomic
    def update(
        plan,
        *,
        opportunity=None,
        reference=None,
        name=None,
        description=None,
        minimum_amount=None,
        maximum_amount=None,
        duration_days=None,
        expected_return_rate=None,
        metadata=None,
    ):
        """
        Update mutable investment plan fields.

        None means that the corresponding field remains unchanged.
        """
        PlanService._validate_plan(plan)

        if opportunity is not None:
            PlanService._validate_opportunity(opportunity)
            plan.opportunity = opportunity

        if reference is not None:
            plan.reference = reference

        if name is not None:
            plan.name = name

        if description is not None:
            plan.description = description

        if minimum_amount is not None:
            plan.minimum_amount = minimum_amount

        if maximum_amount is not None:
            plan.maximum_amount = maximum_amount

        if duration_days is not None:
            plan.duration_days = duration_days

        if expected_return_rate is not None:
            plan.expected_return_rate = expected_return_rate

        if metadata is not None:
            plan.metadata = metadata

        plan.full_clean()
        plan.save()

        return plan

    @staticmethod
    @transaction.atomic
    def activate(plan):
        """
        Set a plan to ACTIVE.
        """
        PlanService._validate_plan(plan)

        plan.status = InvestmentPlan.Status.ACTIVE
        plan.full_clean()
        plan.save(update_fields=["status", "updated_at"])

        return plan

    @staticmethod
    @transaction.atomic
    def pause(plan):
        """
        Set a plan to PAUSED.
        """
        PlanService._validate_plan(plan)

        plan.status = InvestmentPlan.Status.PAUSED
        plan.full_clean()
        plan.save(update_fields=["status", "updated_at"])

        return plan

    @staticmethod
    @transaction.atomic
    def close(plan):
        """
        Set a plan to CLOSED.
        """
        PlanService._validate_plan(plan)

        plan.status = InvestmentPlan.Status.CLOSED
        plan.full_clean()
        plan.save(update_fields=["status", "updated_at"])

        return plan

    @staticmethod
    @transaction.atomic
    def cancel(plan):
        """
        Set a plan to CANCELLED.
        """
        PlanService._validate_plan(plan)

        plan.status = InvestmentPlan.Status.CANCELLED
        plan.full_clean()
        plan.save(update_fields=["status", "updated_at"])

        return plan