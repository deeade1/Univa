"""
Canonical Univa monetary ranges.

A MoneyRange represents an inclusive range:

    start <= value <= stop

Both boundaries must use the same currency.

The implementation is independent of django-prices.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import (
    CurrencyMismatchError,
    InvalidMoneyError,
)
from .money import Money


@dataclass(frozen=True, slots=True)
class MoneyRange:
    """
    Immutable inclusive range of Money values.

    Example:

        price_range = MoneyRange(
            start=Money("1000", "NGN"),
            stop=Money("5000", "NGN"),
        )

        price_range.contains(
            Money("2500", "NGN")
        )
    """

    start: Money
    stop: Money

    def __post_init__(self) -> None:
        # --------------------------------------------------------------
        # Type validation
        # --------------------------------------------------------------

        if not isinstance(self.start, Money):
            raise InvalidMoneyError(
                (
                    "MoneyRange.start must be a Money instance; "
                    f"got {type(self.start).__name__}."
                )
            )

        if not isinstance(self.stop, Money):
            raise InvalidMoneyError(
                (
                    "MoneyRange.stop must be a Money instance; "
                    f"got {type(self.stop).__name__}."
                )
            )

        # --------------------------------------------------------------
        # Currency invariant
        # --------------------------------------------------------------

        if self.start.currency != self.stop.currency:
            raise CurrencyMismatchError(
                self.start.currency,
                self.stop.currency,
            )

        # --------------------------------------------------------------
        # Range invariant
        # --------------------------------------------------------------

        if self.stop.amount < self.start.amount:
            raise InvalidMoneyError(
                (
                    "MoneyRange.stop cannot be less than "
                    f"MoneyRange.start: "
                    f"{self.stop.amount} < {self.start.amount}."
                )
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def currency(self) -> str:
        """Return the range currency."""

        return self.start.currency

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    def contains(
        self,
        value: Money,
    ) -> bool:
        """
        Return True when value falls inside the inclusive range.

        The comparison is:

            start <= value <= stop

        Currency mismatches are errors rather than ordinary
        non-membership because comparing monetary values across
        currencies is undefined without conversion.
        """

        if not isinstance(value, Money):
            raise InvalidMoneyError(
                (
                    "MoneyRange.contains() requires a Money instance; "
                    f"got {type(value).__name__}."
                )
            )

        if value.currency != self.currency:
            raise CurrencyMismatchError(
                self.currency,
                value.currency,
            )

        return (
            self.start.amount
            <= value.amount
            <= self.stop.amount
        )

    def __contains__(
        self,
        value: Money,
    ) -> bool:
        """
        Support Python membership syntax.

        Example:

            money in price_range
        """

        return self.contains(value)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"{self.start} - {self.stop}"
        )

    def __repr__(self) -> str:
        return (
            "MoneyRange("
            f"start={self.start!r}, "
            f"stop={self.stop!r}"
            ")"
        )


@dataclass(frozen=True, slots=True)
class TaxedMoneyRange:
    """
    Inclusive range of TaxedMoney values.

    This remains a lightweight value object. Detailed TaxedMoney
    validation belongs to TaxedMoney itself.
    """

    start: "TaxedMoney"
    stop: "TaxedMoney"

    def __post_init__(self) -> None:
        from .taxed_money import TaxedMoney

        if not isinstance(self.start, TaxedMoney):
            raise TypeError(
                (
                    "TaxedMoneyRange.start must be a TaxedMoney "
                    "instance."
                )
            )

        if not isinstance(self.stop, TaxedMoney):
            raise TypeError(
                (
                    "TaxedMoneyRange.stop must be a TaxedMoney "
                    "instance."
                )
            )

        if self.start.currency != self.stop.currency:
            raise CurrencyMismatchError(
                self.start.currency,
                self.stop.currency,
            )

        if self.stop.gross.amount < self.start.gross.amount:
            raise InvalidMoneyError(
                (
                    "TaxedMoneyRange.stop cannot be less than "
                    "TaxedMoneyRange.start."
                )
            )

    @property
    def currency(self) -> str:
        return self.start.currency
