"""
Investment opportunity domain services.

This module contains the application/domain operations for
InvestmentOpportunity.

Architectural boundary
----------------------

InvestmentOpportunityService is responsible for:

    - creating investment opportunities
    - updating opportunity profile data
    - opening opportunities
    - pausing opportunities
    - closing opportunities
    - cancelling opportunities

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

from investors.models import InvestmentOpportunity


class OpportunityService:
    """
    Canonical service for InvestmentOpportunity domain operations.
    """

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
        reference,
        name,
        description="",
        currency="NGN",
        minimum_amount=Decimal("100000.00"),
        maximum_amount=None,
        metadata=None,
        status=InvestmentOpportunity.Status.DRAFT,
    ):
        """
        Create an investment opportunity.
        """
        OpportunityService._validate_reference(reference)

        if metadata is None:
            metadata = {}

        opportunity = InvestmentOpportunity(
            reference=reference,
            name=name,
            description=description,
            currency=currency,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            metadata=metadata,
            status=status,
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    @staticmethod
    @transaction.atomic
    def update(
        opportunity,
        *,
        reference=None,
        name=None,
        description=None,
        currency=None,
        minimum_amount=None,
        maximum_amount=None,
        metadata=None,
    ):
        """
        Update mutable opportunity fields.

        None means that the corresponding field remains unchanged.
        """
        OpportunityService._validate_opportunity(opportunity)

        if reference is not None:
            opportunity.reference = reference

        if name is not None:
            opportunity.name = name

        if description is not None:
            opportunity.description = description

        if currency is not None:
            opportunity.currency = currency

        if minimum_amount is not None:
            opportunity.minimum_amount = minimum_amount

        if maximum_amount is not None:
            opportunity.maximum_amount = maximum_amount

        if metadata is not None:
            opportunity.metadata = metadata

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    @staticmethod
    @transaction.atomic
    def open(opportunity):
        """
        Set an opportunity to OPEN.
        """
        OpportunityService._validate_opportunity(opportunity)

        opportunity.status = InvestmentOpportunity.Status.OPEN
        opportunity.full_clean()
        opportunity.save(update_fields=["status", "updated_at"])

        return opportunity

    @staticmethod
    @transaction.atomic
    def pause(opportunity):
        """
        Set an opportunity to PAUSED.
        """
        OpportunityService._validate_opportunity(opportunity)

        opportunity.status = InvestmentOpportunity.Status.PAUSED
        opportunity.full_clean()
        opportunity.save(update_fields=["status", "updated_at"])

        return opportunity

    @staticmethod
    @transaction.atomic
    def close(opportunity):
        """
        Set an opportunity to CLOSED.
        """
        OpportunityService._validate_opportunity(opportunity)

        opportunity.status = InvestmentOpportunity.Status.CLOSED
        opportunity.full_clean()
        opportunity.save(update_fields=["status", "updated_at"])

        return opportunity

    @staticmethod
    @transaction.atomic
    def cancel(opportunity):
        """
        Set an opportunity to CANCELLED.
        """
        OpportunityService._validate_opportunity(opportunity)

        opportunity.status = InvestmentOpportunity.Status.CANCELLED
        opportunity.full_clean()
        opportunity.save(update_fields=["status", "updated_at"])

        return opportunity