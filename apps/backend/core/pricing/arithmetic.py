# apps/backend/core/pricing/arithmetic.py

"""
Canonical pricing arithmetic.

These functions provide explicit, testable operations for pricing
calculations performed by Ecommerce, Transport, Real Estate, Invoice,
Payment, and other domains.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .exceptions import CurrencyMismatchError
from .money import Money
from .taxed_money import TaxedMoney


def sum_money(
    values: Iterable[Money],
) -> Money:
    """
    Sum Money values while enforcing currency consistency.
    """

    values = list(values)

    if not values:
        raise ValueError(
            "sum_money() requires at least one Money value."
        )

    currency = values[0].currency
    total = Money.zero(currency)

    for value in values:
        if value.currency != currency:
            raise CurrencyMismatchError(
                currency,
                value.currency,
            )

        total += value

    return total


def multiply_money(
    money: Money,
    quantity: Decimal | int | str,
) -> Money:
    """
    Multiply a monetary value by a quantity.
    """

    return money * quantity


def calculate_subtotal(
    unit_price: Money,
    quantity: Decimal | int | str,
) -> Money:
    """
    Calculate:

        unit price × quantity
    """

    return multiply_money(
        unit_price,
        quantity,
    )


def calculate_tax(
    net: Money,
    tax_rate: Decimal | int | str,
) -> Money:
    """
    Calculate tax from a net amount.

    tax_rate is expressed as a decimal fraction:

        0.075 = 7.5%
        0.15  = 15%
    """

    rate = Decimal(str(tax_rate))

    if rate < 0:
        raise ValueError(
            "Tax rate cannot be negative."
        )

    return net * rate


def calculate_taxed_money(
    net: Money,
    tax_rate: Decimal | int | str,
) -> TaxedMoney:
    """
    Calculate net, tax and gross values.
    """

    tax = calculate_tax(
        net,
        tax_rate,
    )

    gross = net + tax

    return TaxedMoney(
        net=net,
        gross=gross,
    )
