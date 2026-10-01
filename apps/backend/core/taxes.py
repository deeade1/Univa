# apps/backend/core/taxes.py

"""
Core tax data structures and helpers.

Tax calculation primitives belong to core.pricing.

This module provides tax-domain data structures and compatibility
helpers used by applications such as Ecommerce and Payment.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.pricing import Money, TaxedMoney


class TaxError(Exception):
    """
    Default tax error.
    """


class TaxDataError(Exception):
    """
    Error in tax data received from a tax application or provider.
    """


def zero_money(currency: str) -> Money:
    """
    Return a zero-valued Money object.

    This is suitable for model defaults that require a callable.
    """

    return Money.zero(currency)


def zero_taxed_money(
    currency: str,
) -> TaxedMoney:
    """
    Return a zero-valued TaxedMoney object.
    """

    return TaxedMoney.zero(
        currency
    )


@dataclass(frozen=True)
class TaxType:
    """
    Dataclass for a tax type received from a tax gateway.
    """

    code: str
    description: str


@dataclass(frozen=True)
class TaxLineData:
    """
    Tax information for a single line.
    """

    tax_rate: Decimal
    total_gross_amount: Decimal
    total_net_amount: Decimal


@dataclass(frozen=True)
class TaxData:
    """
    Tax data returned by a tax provider.
    """

    shipping_price_gross_amount: Decimal
    shipping_price_net_amount: Decimal
    shipping_tax_rate: Decimal
    lines: list[TaxLineData]


class TaxDataErrorMessage:
    """
    Standard tax-data validation messages.
    """

    EMPTY = "Empty tax data."

    NEGATIVE_VALUE = (
        "Tax data contains negative values."
    )

    LINE_NUMBER = (
        "Number of lines from tax data doesn't match "
        "the line number from order."
    )

    OVERFLOW = (
        "Tax data contains prices exceeding a billion "
        "or tax rate over 100%."
    )
