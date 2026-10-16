"""
Investment commitment domain services.

This module contains the application/domain operations for
InvestmentCommitment.

Architectural boundary
----------------------

CommitmentService is responsible for:

    - creating investment commitments
    - updating commitment data
    - confirming commitments
    - funding commitments
    - cancelling commitments
    - expiring commitments

The service does NOT own:

    - GraphQL concerns
    - HTTP concerns
    - audit persistence
    - notification delivery
    - payment processing
    - investment creation
    - lifecycle transition policy
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import (
    Investment,
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)
from investors.lifecycle.commitment import (
    InvestmentCommitmentLifecycle,
)

class CommitmentService:
    """
    Canonical service for InvestmentCommitment domain operations.
    """

    @staticmethod
    def _validate_commitment(commitment):
        if commitment is None:
            raise ValidationError(
                {"commitment": "Investment commitment is required."}
            )

        if not isinstance(commitment, InvestmentCommitment):
            raise ValidationError(
                {"commitment": "A valid investment commitment is required."}
            )

    @staticmethod
    def _validate_investor(investor):
        User = get_user_model()

        if investor is None:
            raise ValidationError(
                {"investor": "Investor is required."}
            )

        if not isinstance(investor, User):
            raise ValidationError(
                {"investor": "A valid user instance is required."}
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
    def _validate_reference(reference):
        if not reference:
            raise ValidationError(
                {"reference": "Reference is required."}
            )

    @staticmethod
    def _validate_update_types(
        *,
        investor=None,
        opportunity=None,
        plan=None,
    ):
        """Validate related model instances before foreign-key assignment."""
        errors = {}

        if investor is not None:
            try:
                CommitmentService._validate_investor(investor)
            except ValidationError as exc:
                errors.update(exc.message_dict)

        if opportunity is not None:
            try:
                CommitmentService._validate_opportunity(opportunity)
            except ValidationError as exc:
                errors.update(exc.message_dict)

        if plan is not None:
            try:
                CommitmentService._validate_plan(plan)
            except ValidationError as exc:
                errors.update(exc.message_dict)

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _validate_no_existing_investment_for_core_changes(
        commitment,
        *,
        investor=None,
        opportunity=None,
        plan=None,
        amount=None,
        currency=None,
    ):
        """
        Prevent changes to investment-defining fields once an investment
        has been created for this commitment.
        """
        changes_core_fields = any(
            value is not None
            for value in (
                investor,
                opportunity,
                plan,
                amount,
                currency,
            )
        )

        if not changes_core_fields:
            return

        try:
            commitment.investment
        except Investment.DoesNotExist:
            return

        raise ValidationError(
            {
                "commitment": (
                    "Investor, opportunity, plan, amount, and currency "
                    "cannot be changed after an investment has been created."
                )
            }
        )

    @staticmethod
    @transaction.atomic
    def create(
        *,
        investor,
        opportunity,
        plan,
        reference,
        amount,
        currency="NGN",
        status=InvestmentCommitment.Status.PENDING,
        expires_at=None,
        metadata=None,
    ):
        """Create an investment commitment."""
        CommitmentService._validate_investor(investor)
        CommitmentService._validate_opportunity(opportunity)
        CommitmentService._validate_plan(plan)
        CommitmentService._validate_reference(reference)

        if metadata is None:
            metadata = {}

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference=reference,
            amount=amount,
            currency=currency,
            status=status,
            expires_at=expires_at,
            metadata=metadata,
        )

        commitment.full_clean()
        commitment.save()

        return commitment

    @staticmethod
    @transaction.atomic
    def update(
        commitment,
        *,
        investor=None,
        opportunity=None,
        plan=None,
        reference=None,
        amount=None,
        currency=None,
        expires_at=None,
        metadata=None,
    ):
        """
        Update commitment data.

        Once an investment exists, its investor, opportunity, plan, amount,
        and currency cannot be changed through this service.

        Reference, expiry, and metadata remain independently updateable.
        """
        CommitmentService._validate_commitment(commitment)

        # Validate before assigning foreign-key values.
        CommitmentService._validate_update_types(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
        )

        # Prevent changes to investment-defining fields after investment
        # creation.
        CommitmentService._validate_no_existing_investment_for_core_changes(
            commitment,
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            amount=amount,
            currency=currency,
        )

        if reference is not None:
            CommitmentService._validate_reference(reference)
            commitment.reference = reference

        if investor is not None:
            commitment.investor = investor

        if opportunity is not None:
            commitment.opportunity = opportunity

        if plan is not None:
            commitment.plan = plan

        if amount is not None:
            commitment.amount = amount

        if currency is not None:
            commitment.currency = currency

        if expires_at is not None:
            commitment.expires_at = expires_at

        if metadata is not None:
            commitment.metadata = metadata

        commitment.full_clean()
        commitment.save()

        return commitment

    
    @staticmethod
    @transaction.atomic
    def confirm(commitment):
        """
        Confirm a pending commitment through the canonical lifecycle.
        """
        CommitmentService._validate_commitment(commitment)

        return InvestmentCommitmentLifecycle.confirm(commitment)

    @staticmethod
    @transaction.atomic
    def fund(commitment):
        """
        Fund a confirmed commitment through the canonical lifecycle.
        """
        CommitmentService._validate_commitment(commitment)

        return InvestmentCommitmentLifecycle.fund(commitment)

    @staticmethod
    @transaction.atomic
    def cancel(commitment):
        """
        Cancel an eligible commitment through the canonical lifecycle.
        """
        CommitmentService._validate_commitment(commitment)

        return InvestmentCommitmentLifecycle.cancel(commitment)

    @staticmethod
    @transaction.atomic
    def expire(commitment):
        """
        Expire a pending commitment through the canonical lifecycle.
        """
        CommitmentService._validate_commitment(commitment)

        return InvestmentCommitmentLifecycle.expire(commitment)
