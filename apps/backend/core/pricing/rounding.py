# apps/backend/core/pricing/rounding.py

"""
Canonical monetary rounding rules.

All financial domains must use these helpers rather than implementing
their own Decimal quantization rules.
"""

from __future__ import annotations

from decimal import (
    ROUND_HALF_UP,
    Decimal,
    InvalidOperation,
)

from .currency import get_currency_exponent
from .exceptions import InvalidAmountError


def decimal_places_for_currency(currency: str) -> int:
    """
    Return the number of decimal places supported by a currency.
    """

    return get_currency_exponent(currency)


def quantizer_for_currency(currency: str) -> Decimal:
    """
    Return the Decimal quantizer for a currency.

    Examples:

        USD -> Decimal("0.01")
        NGN -> Decimal("0.01")
        JPY -> Decimal("1")
        KWD -> Decimal("0.001")
    """

    places = decimal_places_for_currency(currency)

    return Decimal("1").scaleb(-places)


def to_decimal(value: Decimal | int | str) -> Decimal:
    """
    Convert supported numeric input to Decimal.

    Floats are intentionally rejected because they can introduce binary
    floating-point inaccuracies into financial calculations.
    """

    if isinstance(value, Decimal):
        return value

    if isinstance(value, bool):
        raise InvalidAmountError("Boolean values are not valid monetary amounts.")

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise InvalidAmountError(
                f"Invalid monetary amount: {value!r}."
            ) from exc

    raise InvalidAmountError(
        f"Unsupported monetary value type: {type(value).__name__}."
    )


def quantize_amount(
    amount: Decimal | int | str,
    currency: str,
    *,
    rounding=ROUND_HALF_UP,
) -> Decimal:
    """
    Quantize an amount according to the currency exponent.
    """

    value = to_decimal(amount)

    try:
        return value.quantize(
            quantizer_for_currency(currency),
            rounding=rounding,
        )
    except InvalidOperation as exc:
        raise InvalidAmountError(
            f"Unable to quantize amount {amount!r} for {currency}."
        ) from exc