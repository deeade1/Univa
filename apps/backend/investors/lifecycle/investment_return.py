from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from investors.models import InvestmentReturn


class InvestmentReturnLifecycle:
    """
    Owns legal lifecycle transitions for InvestmentReturn.

    Canonical lifecycle:

        PENDING → CALCULATED → APPROVED → PAYABLE → PAID
           │          │           │
           └──────────┴───────────┴────→ CANCELLED

        PAID → REVERSED

    Lifecycle timestamps are owned here where they exist on the model:

        APPROVED  → approved_at
        PAYABLE   → payable_at
        PAID      → paid_at
        CANCELLED → cancelled_at
        REVERSED  → reversed_at

    There is intentionally no calculated_at field because the
    InvestmentReturn model does not define one.

    Business creation/update belongs to InvestmentReturnService.
    """

    @staticmethod
    def _validate_return(investment_return):
        if not isinstance(investment_return, InvestmentReturn):
            raise ValidationError(
                {
                    "investment_return": (
                        "A valid InvestmentReturn instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_transition(investment_return, allowed_statuses):
        if investment_return.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        "Cannot transition InvestmentReturn from "
                        f"{investment_return.status}."
                    )
                }
            )

    @classmethod
    @transaction.atomic
    def calculate(cls, investment_return):
        """
        PENDING → CALCULATED

        No lifecycle timestamp is created because the model does not
        define calculated_at.
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {InvestmentReturn.Status.PENDING},
        )

        investment_return.status = InvestmentReturn.Status.CALCULATED

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def approve(cls, investment_return):
        """
        CALCULATED → APPROVED
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {InvestmentReturn.Status.CALCULATED},
        )

        investment_return.status = InvestmentReturn.Status.APPROVED
        investment_return.approved_at = timezone.now()

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "approved_at",
                "updated_at",
            ]
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def make_payable(cls, investment_return):
        """
        APPROVED → PAYABLE
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {InvestmentReturn.Status.APPROVED},
        )

        investment_return.status = InvestmentReturn.Status.PAYABLE
        investment_return.payable_at = timezone.now()

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "payable_at",
                "updated_at",
            ]
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def mark_paid(cls, investment_return):
        """
        PAYABLE → PAID
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {InvestmentReturn.Status.PAYABLE},
        )

        investment_return.status = InvestmentReturn.Status.PAID
        investment_return.paid_at = timezone.now()

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "paid_at",
                "updated_at",
            ]
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def cancel(cls, investment_return):
        """
        PENDING / CALCULATED / APPROVED → CANCELLED
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {
                InvestmentReturn.Status.PENDING,
                InvestmentReturn.Status.CALCULATED,
                InvestmentReturn.Status.APPROVED,
            },
        )

        investment_return.status = InvestmentReturn.Status.CANCELLED
        investment_return.cancelled_at = timezone.now()

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "cancelled_at",
                "updated_at",
            ]
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def reverse(cls, investment_return):
        """
        PAID → REVERSED
        """
        cls._validate_return(investment_return)
        cls._validate_transition(
            investment_return,
            {InvestmentReturn.Status.PAID},
        )

        investment_return.status = InvestmentReturn.Status.REVERSED
        investment_return.reversed_at = timezone.now()

        investment_return.full_clean(
            exclude=["investment"],
        )

        investment_return.save(
            update_fields=[
                "status",
                "reversed_at",
                "updated_at",
            ]
        )

        return investment_return