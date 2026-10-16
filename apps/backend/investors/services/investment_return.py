from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import Investment
from investors.models import InvestmentReturn


class InvestmentReturnService:
    """
    Application service for InvestmentReturn.

    Responsibilities:
        - validate service inputs
        - create InvestmentReturn records
        - update InvestmentReturn records
        - perform basic status operations

    Lifecycle transition rules and timestamp management belong
    to the lifecycle layer.
    """

    # ------------------------------------------------------------------
    # validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_return(investment_return):
        if investment_return is None:
            raise ValidationError(
                {"investment_return": "Investment return is required."}
            )

        if not isinstance(investment_return, InvestmentReturn):
            raise ValidationError(
                {
                    "investment_return": (
                        "A valid InvestmentReturn instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_investment(investment):
        if investment is None:
            raise ValidationError(
                {"investment": "Investment is required."}
            )

        if not isinstance(investment, Investment):
            raise ValidationError(
                {
                    "investment": (
                        "A valid Investment instance is required."
                    )
                }
            )

    @staticmethod
    def _validate_reference(reference):
        if reference is None or not str(reference).strip():
            raise ValidationError(
                {"reference": "Investment return reference is required."}
            )

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        investment,
        reference,
        return_type=InvestmentReturn.ReturnType.PROFIT,
        amount=Decimal("0.00"),
        currency="NGN",
        status=InvestmentReturn.Status.PENDING,
        metadata=None,
        earned_at=None,
    ):
        cls._validate_investment(investment)
        cls._validate_reference(reference)

        investment_return = InvestmentReturn(
            investment=investment,
            reference=reference,
            return_type=return_type,
            amount=amount,
            currency=currency,
            status=status,
            metadata={} if metadata is None else metadata,
            earned_at=earned_at,
        )

        investment_return.full_clean()
        investment_return.save()

        return investment_return

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def update(
        cls,
        investment_return,
        *,
        investment=None,
        reference=None,
        return_type=None,
        amount=None,
        currency=None,
        status=None,
        metadata=None,
        earned_at=None,
    ):
        cls._validate_return(investment_return)

        if investment is not None:
            cls._validate_investment(investment)
            investment_return.investment = investment

        if reference is not None:
            cls._validate_reference(reference)
            investment_return.reference = reference

        if return_type is not None:
            investment_return.return_type = return_type

        if amount is not None:
            investment_return.amount = amount

        if currency is not None:
            investment_return.currency = currency

        if status is not None:
            investment_return.status = status

        if metadata is not None:
            investment_return.metadata = metadata

        if earned_at is not None:
            investment_return.earned_at = earned_at

        investment_return.full_clean()
        investment_return.save()

        return investment_return

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def calculate(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.CALCULATED

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def approve(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.APPROVED

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def make_payable(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.PAYABLE

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def mark_paid(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.PAID

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def cancel(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.CANCELLED

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return

    @classmethod
    @transaction.atomic
    def reverse(cls, investment_return):
        cls._validate_return(investment_return)

        investment_return.status = InvestmentReturn.Status.REVERSED

        investment_return.full_clean()
        investment_return.save(
            update_fields=["status", "updated_at"],
        )

        return investment_return