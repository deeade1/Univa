"""
Commission calculation service for Univa.

This module is responsible only for calculating a commission amount
from a CommissionPlan and a calculation basis.

It does not:

    - create Commission records
    - create CommissionAllocation records
    - change commission lifecycle state
    - approve commissions
    - settle commissions
    - perform payments
    - emit domain events
    - write audit records

Those responsibilities belong to higher-level services.

The calculator is intentionally deterministic and uses Decimal
throughout to avoid floating-point financial calculations.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..models import CommissionPlan


MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class CommissionCalculationResult:
    """
    Immutable result of a commission calculation.

    The result contains the inputs and calculated value needed by
    the commission service to create a Commission record.
    """

    calculation_basis: Decimal
    calculated_amount: Decimal
    rate: Decimal | None
    plan_type: str


class CommissionCalculator:
    """
    Calculates commission amounts from canonical commission plans.

    The calculator contains no persistence logic.
    """

    @classmethod
    def calculate(
        cls,
        *,
        plan: CommissionPlan,
        calculation_basis: Decimal,
    ) -> CommissionCalculationResult:
        """
        Calculate a commission according to the supplied plan.

        Args:
            plan:
                The CommissionPlan defining the calculation rule.

            calculation_basis:
                The monetary amount against which the commission
                is calculated.

        Returns:
            CommissionCalculationResult

        Raises:
            ValidationError:
                If the calculation inputs or plan configuration
                are invalid.
        """

        basis = cls._normalize_decimal(calculation_basis)

        cls._validate_basis(basis)
        cls._validate_plan(plan)

        if plan.plan_type == CommissionPlan.PlanType.PERCENTAGE:
            return cls._calculate_percentage(
                plan=plan,
                calculation_basis=basis,
            )

        if plan.plan_type == CommissionPlan.PlanType.FIXED:
            return cls._calculate_fixed(
                plan=plan,
                calculation_basis=basis,
            )

        if plan.plan_type == CommissionPlan.PlanType.TIERED:
            raise ValidationError(
                _(
                    "Tiered commission calculation is not yet available. "
                    "A canonical tier structure must be defined before "
                    "tiered calculations are enabled."
                )
            )

        raise ValidationError(
            {
                "plan_type": _(
                    "Unsupported commission plan type: %(plan_type)s."
                )
                % {"plan_type": plan.plan_type}
            }
        )

    @classmethod
    def _calculate_percentage(
        cls,
        *,
        plan: CommissionPlan,
        calculation_basis: Decimal,
    ) -> CommissionCalculationResult:
        """Calculate a percentage-based commission."""

        if plan.percentage is None:
            raise ValidationError(
                {
                    "percentage": _(
                        "A percentage commission plan must define "
                        "a percentage."
                    )
                }
            )

        amount = (
            calculation_basis * plan.percentage / Decimal("100")
        )

        return CommissionCalculationResult(
            calculation_basis=calculation_basis,
            calculated_amount=cls._quantize_money(amount),
            rate=plan.percentage,
            plan_type=plan.plan_type,
        )

    @classmethod
    def _calculate_fixed(
        cls,
        *,
        plan: CommissionPlan,
        calculation_basis: Decimal,
    ) -> CommissionCalculationResult:
        """Calculate a fixed-amount commission."""

        if plan.fixed_amount is None:
            raise ValidationError(
                {
                    "fixed_amount": _(
                        "A fixed commission plan must define "
                        "a fixed amount."
                    )
                }
            )

        return CommissionCalculationResult(
            calculation_basis=calculation_basis,
            calculated_amount=cls._quantize_money(
                plan.fixed_amount
            ),
            rate=None,
            plan_type=plan.plan_type,
        )

    @staticmethod
    def _validate_basis(
        calculation_basis: Decimal,
    ) -> None:
        """Ensure the calculation basis is valid."""

        if calculation_basis < Decimal("0"):
            raise ValidationError(
                {
                    "calculation_basis": _(
                        "Calculation basis cannot be negative."
                    )
                }
            )

    @staticmethod
    def _validate_plan(
        plan: CommissionPlan,
    ) -> None:
        """Validate that a usable commission plan was supplied."""

        if not isinstance(plan, CommissionPlan):
            raise ValidationError(
                _(
                    "CommissionCalculator requires a "
                    "CommissionPlan instance."
                )
            )

        if not plan.plan_type:
            raise ValidationError(
                {
                    "plan_type": _(
                        "Commission plan type is required."
                    )
                }
            )

    @staticmethod
    def _normalize_decimal(value: Decimal) -> Decimal:
        """
        Normalize a numeric calculation input to Decimal.

        Strings and integers are safely converted through Decimal.
        Floats are explicitly rejected to prevent accidental
        floating-point financial calculations.
        """

        if isinstance(value, float):
            raise ValidationError(
                _(
                    "Financial calculations must use Decimal, "
                    "not float."
                )
            )

        try:
            return Decimal(value)
        except Exception as exc:
            raise ValidationError(
                _(
                    "Calculation basis must be a valid decimal value."
                )
            ) from exc

    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        """Round a monetary result to two decimal places."""

        return value.quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )