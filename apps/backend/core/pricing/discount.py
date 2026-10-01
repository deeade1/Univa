
# apps/backend/core/pricing/discount.py

"""
Canonical discount primitives.

A discount represents a reduction from a monetary price.

Business rules determining whether a discount applies belong to the
owning domain/application.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .exceptions import InvalidDiscountError
from .money import Money


@dataclass(frozen=True, slots=True)
class Discount:
    """
    Monetary discount.

    The amount is always represented as a positive reduction.

    Example:

        Discount(Money("500", "NGN"))
    """

    amount: Money

    def __post_init__(self) -> None:
        if self.amount.is_negative:
            raise InvalidDiscountError(
                "Discount amount cannot be negative."
            )

    @property
    def currency(self) -> str:
        return self.amount.currency

    @property
    def is_zero(self) -> bool:
        return self.amount.is_zero

    def apply(
        self,
        price: Money,
    ) -> Money:
        """
        Apply the discount to a price.

        The result can never be negative.
        """

        if price.currency != self.currency:
            from .exceptions import CurrencyMismatchError

            raise CurrencyMismatchError(
                price.currency,
                self.currency,
            )

        if self.amount >= price:
            return Money.zero(price.currency)

        return price - self.amount

    @classmethod
    def zero(
        cls,
        currency: str,
    ) -> "Discount":
        return cls(
            amount=Money.zero(currency),
        )


def fixed_discount(
    price: Money,
    discount: Money,
) -> Money:
    """
    Calculate a fixed monetary discount.

    Returns the amount to subtract from the price.

    The returned discount is capped at the price amount.
    """

    if not isinstance(price, Money):
        raise InvalidDiscountError(
            "price must be a Money instance."
        )

    if not isinstance(discount, Money):
        raise InvalidDiscountError(
            "discount must be a Money instance."
        )

    if price.currency != discount.currency:
        from .exceptions import CurrencyMismatchError

        raise CurrencyMismatchError(
            price.currency,
            discount.currency,
        )

    if discount.is_negative:
        raise InvalidDiscountError(
            "Discount amount cannot be negative."
        )

    if discount >= price:
        return price

    return discount


def percentage_discount(
    price: Money,
    percentage: Decimal | int | float | str,
    *,
    rounding: str | None = ROUND_HALF_UP,
) -> Money:
    """
    Calculate a percentage discount.

    Examples:

        10  -> 10%
        25  -> 25%
        100 -> 100%

    Returns the monetary amount to subtract from the price.
    """

    if not isinstance(price, Money):
        raise InvalidDiscountError(
            "price must be a Money instance."
        )

    try:
        percentage = Decimal(str(percentage))
    except (TypeError, ValueError) as exc:
        raise InvalidDiscountError(
            f"Invalid discount percentage: {percentage!r}"
        ) from exc

    if percentage < 0:
        raise InvalidDiscountError(
            "Discount percentage cannot be negative."
        )

    if percentage > 100:
        raise InvalidDiscountError(
            "Discount percentage cannot exceed 100."
        )

    discount_amount = (
        price.amount
        * percentage
        / Decimal("100")
    )

    if rounding is not None:
        discount_amount = discount_amount.quantize(
            Decimal("0.01"),
            rounding=rounding,
        )

    discount = Money(
        amount=discount_amount,
        currency=price.currency,
    )

    if discount > price:
        return price

    return discount
