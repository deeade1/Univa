# apps/backend/earnings/services/calculator.py

"""
Canonical earning calculation primitives.

This service performs arithmetic only.

Domain-specific earning rules belong to the originating domain.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class EarningCalculationResult:
    calculation_basis: Decimal | None
    calculated_amount: Decimal
    rate: Decimal | None
    calculation_metadata: dict


class EarningCalculator:
    """
    Primitive financial calculation service for earnings.
    """

    @classmethod
    def calculate_percentage(
        cls,
        *,
        calculation_basis: Decimal,
        rate: Decimal,
        metadata: dict | None = None,
    ) -> EarningCalculationResult:
        basis = cls._normalize_decimal(calculation_basis)
        percentage = cls._normalize_decimal(rate)

        cls._validate_non_negative(
            basis,
            "calculation_basis",
        )

        cls._validate_non_negative(
            percentage,
            "rate",
        )

        if percentage > Decimal("100"):
            raise ValidationError(
                {
                    "rate": _(
                        "Earning rate cannot exceed 100 percent."
                    )
                }
            )

        amount = (
            basis
            * percentage
            / Decimal("100")
        )

        return EarningCalculationResult(
            calculation_basis=basis,
            calculated_amount=cls._quantize_money(amount),
            rate=percentage,
            calculation_metadata=metadata or {},
        )

    @classmethod
    def calculate_fixed(
        cls,
        *,
        amount: Decimal,
        metadata: dict | None = None,
    ) -> EarningCalculationResult:
        normalized_amount = cls._normalize_decimal(amount)

        cls._validate_non_negative(
            normalized_amount,
            "amount",
        )

        return EarningCalculationResult(
            calculation_basis=None,
            calculated_amount=cls._quantize_money(
                normalized_amount
            ),
            rate=None,
            calculation_metadata=metadata or {},
        )

    @staticmethod
    def _normalize_decimal(value):
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
                    "Financial calculation value must be a "
                    "valid decimal value."
                )
            ) from exc

    @staticmethod
    def _validate_non_negative(value, field_name):
        if value < Decimal("0"):
            raise ValidationError(
                {
                    field_name: _(
                        "%(field)s cannot be negative."
                    )
                    % {
                        "field": field_name,
                    }
                }
            )

    @staticmethod
    def _quantize_money(value):
        return value.quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )