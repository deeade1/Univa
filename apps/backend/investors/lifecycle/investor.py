from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import Investor


class InvestorLifecycle:
    """
    Canonical lifecycle operations for Investor.

    Responsibilities:
        - enforce legal state transitions
        - manage lifecycle timestamps
        - persist lifecycle changes atomically

    Creation, field updates, and validation of ordinary model data
    belong to InvestorService.

    Audit belongs to the audit adapter layer.
    """

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_investor(investor):
        if investor is None:
            raise ValidationError(
                {"investor": "Investor is required."}
            )

        if not isinstance(investor, Investor):
            raise ValidationError(
                {
                    "investor": (
                        "A valid Investor instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_transition(investor, allowed_statuses):
        if investor.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"Investor cannot transition from "
                        f"'{investor.status}'."
                    )
                }
            )

    # ------------------------------------------------------------------
    # activate
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def activate(cls, investor):
        cls._validate_investor(investor)

        cls._validate_transition(
            investor,
            {
                Investor.Status.PENDING,
                Investor.Status.SUSPENDED,
            },
        )

        investor.status = Investor.Status.ACTIVE

        investor.full_clean()
        investor.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return investor

    # ------------------------------------------------------------------
    # suspend
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def suspend(cls, investor):
        cls._validate_investor(investor)

        cls._validate_transition(
            investor,
            {
                Investor.Status.ACTIVE,
            },
        )

        investor.status = Investor.Status.SUSPENDED

        investor.full_clean()
        investor.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return investor

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def close(cls, investor):
        cls._validate_investor(investor)

        cls._validate_transition(
            investor,
            {
                Investor.Status.ACTIVE,
                Investor.Status.SUSPENDED,
            },
        )

        investor.status = Investor.Status.CLOSED

        investor.full_clean()
        investor.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return investor