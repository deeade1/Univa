# apps/backend/core/pricing/tax.py

"""
Canonical tax primitives.

Tax calculation rules are kept separate from tax data representation.

Domain applications may provide their own tax rules, but the resulting
financial values use these CORE primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .arithmetic import calculate_tax
from .exceptions import InvalidTaxError
from .money import Money


@dataclass(frozen=True, slots=True)
class Tax:
    """
    Tax definition.

    rate is represented as a decimal fraction.

        0.075 = 7.5%
        0.15  = 15%
    """

    rate: Decimal
    name: str = ""
    code: str = ""

    def __post_init__(self) -> None:
        rate = Decimal(str(self.rate))

        if rate < 0:
            raise InvalidTaxError(
                "Tax rate cannot be negative."
            )

        if rate > 1:
            raise InvalidTaxError(
                "Tax rate cannot exceed 100%."
            )

        object.__setattr__(self, "rate", rate)

    @property
    def percentage(self) -> Decimal:
        return self.rate * Decimal("100")

    def calculate(self, net: Money) -> Money:
        return calculate_tax(
            net,
            self.rate,
        )

    @classmethod
    def zero(cls) -> "Tax":
        return cls(rate=Decimal("0"))