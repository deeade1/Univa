"""
Canonical TaxedMoney value object.

Represents:

    net
    gross
    tax

Tax is derived from:

    gross - net

Invariants
----------

A TaxedMoney value must satisfy:

    1. net and gross use the same currency
    2. gross >= net
    3. tax is derived as gross - net

This module contains domain logic only.

It has no Django dependency and no dependency on django-prices.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import (
    InvalidTaxedMoneyError,
)
from .money import Money


@dataclass(frozen=True, slots=True)
class TaxedMoney:
    """
    Immutable monetary value including tax information.

    Example:

        TaxedMoney(
            net=Money("1000.00", "NGN"),
            gross=Money("1075.00", "NGN"),
        )
    """

    net: Money
    gross: Money

    def __post_init__(self) -> None:
        # --------------------------------------------------------------
        # Type validation
        # --------------------------------------------------------------

        if not isinstance(self.net, Money):
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney.net must be a Money instance; "
                    f"got {type(self.net).__name__}."
                )
            )

        if not isinstance(self.gross, Money):
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney.gross must be a Money instance; "
                    f"got {type(self.gross).__name__}."
                )
            )

        # --------------------------------------------------------------
        # Currency invariant
        # --------------------------------------------------------------

        if self.net.currency != self.gross.currency:
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney net and gross values must use the "
                    "same currency: "
                    f"{self.net.currency} != {self.gross.currency}."
                )
            )

        # --------------------------------------------------------------
        # Tax invariant
        # --------------------------------------------------------------

        if self.gross.amount < self.net.amount:
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney gross amount cannot be less than "
                    f"net amount: {self.gross.amount} < "
                    f"{self.net.amount}."
                )
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def currency(self) -> str:
        """
        Return the shared currency.
        """

        return self.net.currency

    @property
    def tax(self) -> Money:
        """
        Return the derived tax amount.

        tax = gross - net
        """

        return self.gross - self.net

    @property
    def is_taxed(self) -> bool:
        """
        Return True when tax is greater than zero.
        """

        return not self.tax.is_zero

    @property
    def is_zero(self) -> bool:
        """
        Return True when both net and gross are zero.
        """

        return (
            self.net.is_zero
            and self.gross.is_zero
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_net_and_tax(
        cls,
        *,
        net: Money,
        tax: Money,
    ) -> "TaxedMoney":
        """
        Construct TaxedMoney from net amount and tax.

        gross = net + tax

        Both values must use the same currency.

        A negative tax is rejected because TaxedMoney represents
        ordinary tax-inclusive pricing.
        """

        if not isinstance(net, Money):
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney.net must be a Money instance; "
                    f"got {type(net).__name__}."
                )
            )

        if not isinstance(tax, Money):
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney.tax must be a Money instance; "
                    f"got {type(tax).__name__}."
                )
            )

        if net.currency != tax.currency:
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney net and tax values must use the "
                    "same currency: "
                    f"{net.currency} != {tax.currency}."
                )
            )

        if tax.is_negative:
            raise InvalidTaxedMoneyError(
                (
                    "TaxedMoney tax amount cannot be negative: "
                    f"{tax.amount}."
                )
            )

        gross = net + tax

        return cls(
            net=net,
            gross=gross,
        )

    @classmethod
    def zero(
        cls,
        currency: str,
    ) -> "TaxedMoney":
        """
        Return a zero-valued TaxedMoney instance.
        """

        zero = Money.zero(currency)

        return cls(
            net=zero,
            gross=zero,
        )

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __add__(
        self,
        other: "TaxedMoney",
    ) -> "TaxedMoney":
        """
        Add two TaxedMoney values.

        Money arithmetic enforces currency compatibility.
        """

        if not isinstance(other, TaxedMoney):
            return NotImplemented

        return TaxedMoney(
            net=self.net + other.net,
            gross=self.gross + other.gross,
        )

    def __sub__(
        self,
        other: "TaxedMoney",
    ) -> "TaxedMoney":
        """
        Subtract one TaxedMoney value from another.

        The resulting value must still satisfy the TaxedMoney
        invariant that gross >= net.
        """

        if not isinstance(other, TaxedMoney):
            return NotImplemented

        return TaxedMoney(
            net=self.net - other.net,
            gross=self.gross - other.gross,
        )

    def __mul__(
        self,
        multiplier,
    ) -> "TaxedMoney":
        """
        Multiply both net and gross amounts.
        """

        return TaxedMoney(
            net=self.net * multiplier,
            gross=self.gross * multiplier,
        )

    def __rmul__(
        self,
        multiplier,
    ) -> "TaxedMoney":
        return self.__mul__(multiplier)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"TaxedMoney("
            f"net={self.net}, "
            f"gross={self.gross}"
            ")"
        )

    def __repr__(self) -> str:
        return (
            "TaxedMoney("
            f"net={self.net!r}, "
            f"gross={self.gross!r}"
            ")"
        )
