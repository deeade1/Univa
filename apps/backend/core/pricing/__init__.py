"""
Canonical Univa pricing API.

This package is the public API for monetary and pricing primitives
used across the platform.

Domain applications should import from:

    from core.pricing import Money

rather than importing implementation modules directly.

The core pricing layer must not depend on django-prices.
"""


from decimal import ROUND_HALF_UP, Decimal
from .arithmetic import (
    calculate_subtotal,
    calculate_tax,
    calculate_taxed_money,
    multiply_money,
    sum_money,
)

from .comparisons import (
    is_negative,
    is_non_negative,
    is_positive,
    is_zero,
    maximum,
    minimum,
    same_currency,
)

from .currency import (
    Currency,
    get_currency_exponent,
    is_supported_currency,
    normalize_currency,
)

from .discount import Discount

from .exceptions import (
    CurrencyError,
    CurrencyMismatchError,
    InvalidAmountError,
    InvalidCurrencyError,
    InvalidDiscountError,
    InvalidMoneyError,
    InvalidPriceError,
    InvalidTaxError,
    InvalidTaxedMoneyError,
    PricingCalculationError,
    PricingError,
)

from .formatting import format_money

from .money import Money
from .money_field import MoneyField

from .money_range import (
    MoneyRange,
    TaxedMoneyRange,
)

from .price import Price

from .rounding import (
    decimal_places_for_currency,
    quantize_amount,
    quantizer_for_currency,
)

from .serialization import (
    money_from_dict,
    money_range_to_dict,
    money_to_dict,
    taxed_money_from_dict,
    taxed_money_to_dict,
)

from .tax import Tax
from .taxed_money import TaxedMoney
from .taxed_money_field import TaxedMoneyField

# ======================================================================
# Constants
# ======================================================================

#: Upper sanity bound for monetary amounts.
#:
#: Any price exceeding this value is considered invalid and is
#: rejected by validation helpers (e.g. tax data validation). Used
#: to protect against data corruption, arithmetic overflow, or
#: malicious input.
#:
#: The value is a raw Decimal because MAXIMUM_PRICE comparisons are
#: done against raw amount columns (not Money objects).
MAXIMUM_PRICE = Decimal("1000000000")

def quantize_price(value, currency, *, rounding=ROUND_HALF_UP):
    """
    Compatibility shim for the old ``prices.quantize_price`` helper.

    The previous code base imported ``quantize_price`` from ``prices``
    (external) or from ``core.prices`` (never existed). Both are gone.
    This function provides an equivalent API that accepts the same
    argument types and returns the same type.

    Accepted inputs:

        Money       -> Money (quantized)
        TaxedMoney  -> TaxedMoney (both net and gross quantized)
        Decimal     -> Decimal (quantized)
        int / str   -> Decimal (quantized)

    The ``rounding`` keyword matches ``Decimal``'s rounding constants
    and defaults to ``ROUND_HALF_UP``.
    """
    from decimal import Decimal

    if isinstance(value, Money):
        return Money(
            amount=quantize_amount(
                value.amount, currency, rounding=rounding
            ),
            currency=value.currency,
        )

    if isinstance(value, TaxedMoney):
        return TaxedMoney(
            net=quantize_price(value.net, currency, rounding=rounding),
            gross=quantize_price(value.gross, currency, rounding=rounding),
        )

    if isinstance(value, Decimal):
        return quantize_amount(value, currency, rounding=rounding)

    return quantize_amount(Decimal(str(value)), currency, rounding=rounding)


__all__ = [
    # Money
    "Money",
    "MoneyField",

    # Taxed money
    "TaxedMoney",
    "TaxedMoneyField",

    # Ranges
    "MoneyRange",
    "TaxedMoneyRange",

    # Currency
    "Currency",
    "normalize_currency",
    "get_currency_exponent",
    "is_supported_currency",

    # Price
    "Price",

    # Discount
    "Discount",

    # Tax
    "Tax",

    # Arithmetic
    "sum_money",
    "multiply_money",
    "calculate_subtotal",
    "calculate_tax",
    "calculate_taxed_money",

    # Rounding
    "quantize_amount",
    "quantize_price",
    "quantizer_for_currency",
    "decimal_places_for_currency",

    # Comparisons
    "same_currency",
    "is_zero",
    "is_positive",
    "is_negative",
    "is_non_negative",
    "maximum",
    "minimum",

    # Serialization
    "money_to_dict",
    "money_from_dict",
    "taxed_money_to_dict",
    "taxed_money_from_dict",
    "money_range_to_dict",

    # Formatting
    "format_money",

    # Exceptions
    "PricingError",
    "CurrencyError",
    "CurrencyMismatchError",
    "InvalidCurrencyError",
    "InvalidMoneyError",
    "InvalidAmountError",
    "InvalidTaxedMoneyError",
    "InvalidPriceError",
    "InvalidDiscountError",
    "InvalidTaxError",
    "PricingCalculationError",
    
    # Constants
    "MAXIMUM_PRICE",
]