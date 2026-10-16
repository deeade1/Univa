from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from investors.models import Investment


class InvestmentLifecycle:
    """
    Owns legal lifecycle transitions for Investment.

    Canonical lifecycle:

        PENDING → ACTIVE → MATURED → CLOSED
           │
           └────────────────────→ CANCELLED

    Lifecycle timestamps are owned here:

        ACTIVE    → started_at
        MATURED   → matured_at
        CLOSED    → closed_at
        CANCELLED → cancelled_at

    Business object creation/update belongs to InvestmentService.
    This class owns transition legality and lifecycle timestamps.
    """

    @staticmethod
    def _validate_investment(investment):
        if not isinstance(investment, Investment):
            raise ValidationError(
                {"investment": "A valid Investment instance is required."}
            )

    @staticmethod
    def _validate_transition(investment, allowed_statuses):
        if investment.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot transition Investment from "
                        f"{investment.status}."
                    )
                }
            )

    @classmethod
    @transaction.atomic
    def activate(cls, investment):
        """
        PENDING → ACTIVE
        """
        cls._validate_investment(investment)
        cls._validate_transition(
            investment,
            {Investment.Status.PENDING},
        )

        now = timezone.now()

        investment.status = Investment.Status.ACTIVE
        investment.started_at = now

        investment.full_clean(
            exclude=[
                "investor",
                "opportunity",
                "plan",
                "commitment",
            ]
        )

        investment.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

        return investment

    @classmethod
    @transaction.atomic
    def mature(cls, investment):
        """
        ACTIVE → MATURED
        """
        cls._validate_investment(investment)
        cls._validate_transition(
            investment,
            {Investment.Status.ACTIVE},
        )

        now = timezone.now()

        investment.status = Investment.Status.MATURED
        investment.matured_at = now

        investment.full_clean(
            exclude=[
                "investor",
                "opportunity",
                "plan",
                "commitment",
            ]
        )

        investment.save(
            update_fields=[
                "status",
                "matured_at",
                "updated_at",
            ]
        )

        return investment

    @classmethod
    @transaction.atomic
    def close(cls, investment):
        """
        MATURED → CLOSED
        """
        cls._validate_investment(investment)
        cls._validate_transition(
            investment,
            {Investment.Status.MATURED},
        )

        now = timezone.now()

        investment.status = Investment.Status.CLOSED
        investment.closed_at = now

        investment.full_clean(
            exclude=[
                "investor",
                "opportunity",
                "plan",
                "commitment",
            ]
        )

        investment.save(
            update_fields=[
                "status",
                "closed_at",
                "updated_at",
            ]
        )

        return investment

    @classmethod
    @transaction.atomic
    def cancel(cls, investment):
        """
        PENDING → CANCELLED
        """
        cls._validate_investment(investment)
        cls._validate_transition(
            investment,
            {Investment.Status.PENDING},
        )

        now = timezone.now()

        investment.status = Investment.Status.CANCELLED
        investment.cancelled_at = now

        investment.full_clean(
            exclude=[
                "investor",
                "opportunity",
                "plan",
                "commitment",
            ]
        )

        investment.save(
            update_fields=[
                "status",
                "cancelled_at",
                "updated_at",
            ]
        )

        return investment