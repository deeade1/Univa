"""
Canonical Univa Money value object.

Money is the domain representation of:

    amount + currency

This module contains no Django model-field logic and has no dependency
on django-prices or any other third-party pricing package.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .exceptions import (
    CurrencyMismatchError,
    InvalidCurrencyError,
    InvalidMoneyError,
)


@dataclass(frozen=True, slots=True)
class Money:
    """
    Immutable monetary value.

    Example:

        Money("1500.00", "NGN")
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        # --------------------------------------------------------------
        # Amount validation
        # --------------------------------------------------------------

        try:
            amount = Decimal(str(self.amount))
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise InvalidMoneyError(
                f"Invalid monetary amount: {self.amount!r}"
            ) from exc

        if amount.is_nan() or amount.is_infinite():
            raise InvalidMoneyError(
                "Money amount must be finite."
            )

        # --------------------------------------------------------------
        # Currency validation
        # --------------------------------------------------------------

        try:
            currency = str(self.currency).strip().upper()
        except (TypeError, ValueError) as exc:
            raise InvalidCurrencyError(
                f"Invalid currency: {self.currency!r}"
            ) from exc

        if not currency:
            raise InvalidCurrencyError(
                "Currency cannot be empty."
            )

        if len(currency) != 3:
            raise InvalidCurrencyError(
                (
                    "Currency must be a 3-letter ISO code: "
                    f"{currency!r}"
                )
            )

        if not currency.isalpha():
            raise InvalidCurrencyError(
                (
                    "Currency must contain only letters: "
                    f"{currency!r}"
                )
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )

        object.__setattr__(
            self,
            "currency",
            currency,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_zero(self) -> bool:
        """Return True when the amount is exactly zero."""

        return self.amount == Decimal("0")

    @property
    def is_positive(self) -> bool:
        """Return True when the amount is greater than zero."""

        return self.amount > Decimal("0")

    @property
    def is_negative(self) -> bool:
        """Return True when the amount is less than zero."""

        return self.amount < Decimal("0")

    @property
    def is_non_negative(self) -> bool:
        """Return True when the amount is zero or greater."""

        return self.amount >= Decimal("0")

    # ------------------------------------------------------------------
    # Currency validation
    # ------------------------------------------------------------------

    def _assert_same_currency(
        self,
        other: Money,
    ) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                self.currency,
                other.currency,
            )

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __add__(
        self,
        other: Money,
    ) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return Money(
            self.amount + other.amount,
            self.currency,
        )

    def __sub__(
        self,
        other: Money,
    ) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return Money(
            self.amount - other.amount,
            self.currency,
        )

    def __mul__(
        self,
        multiplier: Any,
    ) -> Money:
        try:
            multiplier_decimal = Decimal(
                str(multiplier)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise InvalidMoneyError(
                f"Invalid multiplier: {multiplier!r}"
            ) from exc

        if (
            multiplier_decimal.is_nan()
            or multiplier_decimal.is_infinite()
        ):
            raise InvalidMoneyError(
                "Multiplier must be finite."
            )

        return Money(
            self.amount * multiplier_decimal,
            self.currency,
        )

    def __rmul__(
        self,
        multiplier: Any,
    ) -> Money:
        return self.__mul__(multiplier)

    def __truediv__(
        self,
        divisor: Any,
    ) -> Money:
        try:
            divisor_decimal = Decimal(
                str(divisor)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise InvalidMoneyError(
                f"Invalid divisor: {divisor!r}"
            ) from exc

        if (
            divisor_decimal.is_nan()
            or divisor_decimal.is_infinite()
        ):
            raise InvalidMoneyError(
                "Divisor must be finite."
            )

        if divisor_decimal == 0:
            raise InvalidMoneyError(
                "Money cannot be divided by zero."
            )

        return Money(
            self.amount / divisor_decimal,
            self.currency,
        )

    def __neg__(self) -> Money:
        return Money(
            -self.amount,
            self.currency,
        )

    def __abs__(self) -> Money:
        return Money(
            abs(self.amount),
            self.currency,
        )

    # ------------------------------------------------------------------
    # Comparisons
    # ------------------------------------------------------------------

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return self.amount == other.amount

    def __lt__(
        self,
        other: Money,
    ) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return self.amount < other.amount

    def __le__(
        self,
        other: Money,
    ) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return self.amount <= other.amount

    def __gt__(
        self,
        other: Money,
    ) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return self.amount > other.amount

    def __ge__(
        self,
        other: Money,
    ) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._assert_same_currency(other)

        return self.amount >= other.amount

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def quantize(
        self,
        exponent: Decimal,
    ) -> Money:
        return Money(
            self.amount.quantize(exponent),
            self.currency,
        )

    @classmethod
    def zero(
        cls,
        currency: str,
    ) -> Money:
        return cls(
            amount=Decimal("0"),
            currency=currency,
        )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    def __repr__(self) -> str:
        return (
            "Money("
            f"amount={self.amount!r}, "
            f"currency={self.currency!r}"
            ")"
        )
