from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import InvestmentOpportunity


class InvestmentOpportunityLifecycle:
    """
    Canonical lifecycle operations for InvestmentOpportunity.

    Responsibilities:
        - enforce legal status transitions
        - persist lifecycle state changes atomically

    Creation and ordinary field updates belong to InvestmentOpportunityService.

    Audit belongs to the audit adapter layer.
    """

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

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
                        "A valid InvestmentOpportunity instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_transition(opportunity, allowed_statuses):
        if opportunity.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"Investment opportunity cannot transition from "
                        f"'{opportunity.status}'."
                    )
                }
            )

    # ------------------------------------------------------------------
    # open
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def open(cls, opportunity):
        cls._validate_opportunity(opportunity)

        cls._validate_transition(
            opportunity,
            {
                InvestmentOpportunity.Status.DRAFT,
                InvestmentOpportunity.Status.PAUSED,
            },
        )

        opportunity.status = InvestmentOpportunity.Status.OPEN

        opportunity.full_clean()
        opportunity.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return opportunity

    # ------------------------------------------------------------------
    # pause
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def pause(cls, opportunity):
        cls._validate_opportunity(opportunity)

        cls._validate_transition(
            opportunity,
            {
                InvestmentOpportunity.Status.OPEN,
            },
        )

        opportunity.status = InvestmentOpportunity.Status.PAUSED

        opportunity.full_clean()
        opportunity.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return opportunity

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def close(cls, opportunity):
        cls._validate_opportunity(opportunity)

        cls._validate_transition(
            opportunity,
            {
                InvestmentOpportunity.Status.OPEN,
                InvestmentOpportunity.Status.PAUSED,
            },
        )

        opportunity.status = InvestmentOpportunity.Status.CLOSED

        opportunity.full_clean()
        opportunity.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return opportunity

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def cancel(cls, opportunity):
        cls._validate_opportunity(opportunity)

        cls._validate_transition(
            opportunity,
            {
                InvestmentOpportunity.Status.DRAFT,
                InvestmentOpportunity.Status.OPEN,
                InvestmentOpportunity.Status.PAUSED,
            },
        )

        opportunity.status = InvestmentOpportunity.Status.CANCELLED

        opportunity.full_clean()
        opportunity.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return opportunity