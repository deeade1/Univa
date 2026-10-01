# apps/backend/core/pricing/price.py

"""
Canonical Price value object.

Price is intentionally lightweight.

Money represents an amount.

Price represents the business concept of an amount offered for a
product, service, property, fare, or similar domain object.

Domain-specific pricing rules remain in the owning application.
"""

from __future__ import annotations

from dataclasses import dataclass

from .money import Money


@dataclass(frozen=True, slots=True)
class Price:
    """
    A monetary price.
    """

    money: Money

    @property
    def amount(self):
        return self.money.amount

    @property
    def currency(self) -> str:
        return self.money.currency

    def __str__(self) -> str:
        return str(self.money)

    def __repr__(self) -> str:
        return (
            f"Price(money={self.money!r})"
        )

    @classmethod
    def zero(
        cls,
        currency: str,
    ) -> "Price":
        return cls(
            Money.zero(currency)
        )
