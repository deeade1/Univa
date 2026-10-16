from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from investors.models import InvestmentCommitment


class InvestmentCommitmentLifecycle:
    """
    Canonical lifecycle operations for InvestmentCommitment.

    Responsibilities:
        - enforce legal status transitions
        - manage commitment lifecycle timestamps
        - persist lifecycle changes atomically

    Creation and ordinary field updates belong to InvestmentCommitmentService.

    Audit belongs to the audit adapter layer.
    """

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

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
                        "A valid InvestmentCommitment instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_transition(commitment, allowed_statuses):
        if commitment.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"Investment commitment cannot transition from "
                        f"'{commitment.status}'."
                    )
                }
            )

    # ------------------------------------------------------------------
    # confirm
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def confirm(cls, commitment):
        cls._validate_commitment(commitment)

        cls._validate_transition(
            commitment,
            {
                InvestmentCommitment.Status.PENDING,
            },
        )

        now = timezone.now()

        commitment.status = InvestmentCommitment.Status.CONFIRMED
        commitment.confirmed_at = now

        commitment.full_clean()
        commitment.save(
            update_fields=[
                "status",
                "confirmed_at",
                "updated_at",
            ],
        )

        return commitment

    # ------------------------------------------------------------------
    # fund
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def fund(cls, commitment):
        cls._validate_commitment(commitment)

        cls._validate_transition(
            commitment,
            {
                InvestmentCommitment.Status.CONFIRMED,
            },
        )

        now = timezone.now()

        commitment.status = InvestmentCommitment.Status.FUNDED
        commitment.funded_at = now

        commitment.full_clean()
        commitment.save(
            update_fields=[
                "status",
                "funded_at",
                "updated_at",
            ],
        )

        return commitment

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def cancel(cls, commitment):
        cls._validate_commitment(commitment)

        cls._validate_transition(
            commitment,
            {
                InvestmentCommitment.Status.PENDING,
                InvestmentCommitment.Status.CONFIRMED,
            },
        )

        now = timezone.now()

        commitment.status = InvestmentCommitment.Status.CANCELLED
        commitment.cancelled_at = now

        commitment.full_clean()
        commitment.save(
            update_fields=[
                "status",
                "cancelled_at",
                "updated_at",
            ],
        )

        return commitment

    # ------------------------------------------------------------------
    # expire
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def expire(cls, commitment):
        cls._validate_commitment(commitment)

        cls._validate_transition(
            commitment,
            {
                InvestmentCommitment.Status.PENDING,
            },
        )

        commitment.status = InvestmentCommitment.Status.EXPIRED

        commitment.full_clean()
        commitment.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return commitment