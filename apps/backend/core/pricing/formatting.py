# apps/backend/core/pricing/formatting.py

"""
Canonical monetary formatting.

Formatting is presentation logic, not calculation logic.
"""

from __future__ import annotations

from .currency import get_currency_exponent
from .money import Money


_CURRENCY_SYMBOLS = {
    "NGN": "₦",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "INR": "₹",
    "GHS": "₵",
    "KES": "KSh",
    "ZAR": "R",
}


def format_money(
    money: Money,
    *,
    symbol: bool = True,
    thousands_separator: str = ",",
) -> str:
    """
    Format Money for human-readable presentation.

    This function does not change the underlying value.
    """

    places = get_currency_exponent(
        money.currency
    )

    amount = (
        f"{money.amount:,.{places}f}"
    )

    if thousands_separator != ",":
        amount = amount.replace(
            ",",
            thousands_separator,
        )

    if not symbol:
        return amount

    currency_symbol = _CURRENCY_SYMBOLS.get(
        money.currency,
        money.currency,
    )

    return f"{currency_symbol}{amount}"
