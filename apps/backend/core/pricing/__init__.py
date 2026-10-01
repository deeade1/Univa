"""
Canonical Univa pricing API.

This package is the public API for monetary and pricing primitives
used across the platform.

Domain applications should import from:

    from core.pricing import Money

rather than importing implementation modules directly.

The core pricing layer must not depend on django-prices.
"""

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
]

