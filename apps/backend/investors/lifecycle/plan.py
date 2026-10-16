from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import InvestmentPlan


class InvestmentPlanLifecycle:
    """
    Canonical lifecycle operations for InvestmentPlan.

    Responsibilities:
        - enforce legal status transitions
        - persist lifecycle state changes atomically

    Creation and ordinary field updates belong to InvestmentPlanService.

    Audit belongs to the audit adapter layer.
    """

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_plan(plan):
        if plan is None:
            raise ValidationError(
                {"plan": "Investment plan is required."}
            )

        if not isinstance(plan, InvestmentPlan):
            raise ValidationError(
                {
                    "plan": (
                        "A valid InvestmentPlan instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_transition(plan, allowed_statuses):
        if plan.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"Investment plan cannot transition from "
                        f"'{plan.status}'."
                    )
                }
            )

    # ------------------------------------------------------------------
    # activate
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def activate(cls, plan):
        cls._validate_plan(plan)

        cls._validate_transition(
            plan,
            {
                InvestmentPlan.Status.DRAFT,
                InvestmentPlan.Status.PAUSED,
            },
        )

        plan.status = InvestmentPlan.Status.ACTIVE

        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return plan

    # ------------------------------------------------------------------
    # pause
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def pause(cls, plan):
        cls._validate_plan(plan)

        cls._validate_transition(
            plan,
            {
                InvestmentPlan.Status.ACTIVE,
            },
        )

        plan.status = InvestmentPlan.Status.PAUSED

        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return plan

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def close(cls, plan):
        cls._validate_plan(plan)

        cls._validate_transition(
            plan,
            {
                InvestmentPlan.Status.ACTIVE,
                InvestmentPlan.Status.PAUSED,
            },
        )

        plan.status = InvestmentPlan.Status.CLOSED

        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return plan

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def cancel(cls, plan):
        cls._validate_plan(plan)

        cls._validate_transition(
            plan,
            {
                InvestmentPlan.Status.DRAFT,
                InvestmentPlan.Status.ACTIVE,
                InvestmentPlan.Status.PAUSED,
            },
        )

        plan.status = InvestmentPlan.Status.CANCELLED

        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        return plan