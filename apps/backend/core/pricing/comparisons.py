# apps/backend/core/pricing/comparisons.py

"""
Canonical monetary comparison helpers.
"""

from __future__ import annotations

from .exceptions import CurrencyMismatchError
from .money import Money


def same_currency(
    left: Money,
    right: Money,
) -> bool:
    return left.currency == right.currency


def is_zero(
    money: Money,
) -> bool:
    return money.amount == 0


def is_positive(
    money: Money,
) -> bool:
    return money.amount > 0


def is_negative(
    money: Money,
) -> bool:
    return money.amount < 0


def is_non_negative(
    money: Money,
) -> bool:
    return money.amount >= 0


def maximum(
    left: Money,
    right: Money,
) -> Money:
    if left.currency != right.currency:
        raise CurrencyMismatchError(
            left.currency,
            right.currency,
        )

    return max(left, right)


def minimum(
    left: Money,
    right: Money,
) -> Money:
    if left.currency != right.currency:
        raise CurrencyMismatchError(
            left.currency,
            right.currency,
        )

    return min(left, right)
