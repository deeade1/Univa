# apps/backend/core/pricing/currency.py

"""
Canonical currency primitives for Univa.

Currency handling belongs to CORE because every financial domain needs
the same currency semantics.

Applications should not implement their own currency validation or
decimal precision rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import CurrencyError


# ISO-4217 style currency exponent definitions.

# Most currencies use 2 decimal places.
# Explicit definitions are provided for currencies whose exponent differs.

_CURRENCY_EXPONENTS: dict[str, int] = {
    # Zero-decimal currencies
    "BIF": 0,
    "CLP": 0,
    "DJF": 0,
    "GNF": 0,
    "ISK": 0,
    "JPY": 0,
    "KMF": 0,
    "KRW": 0,
    "PYG": 0,
    "RWF": 0,
    "UGX": 0,
    "UYI": 0,
    "VND": 0,
    "VUV": 0,
    "XAF": 0,
    "XOF": 0,
    "XPF": 0,

    # Three-decimal currencies
    "BHD": 3,
    "IQD": 3,
    "JOD": 3,
    "KWD": 3,
    "LYD": 3,
    "OMR": 3,
    "TND": 3,

    # Four-decimal currencies
    "CLF": 4,

    # Standard two-decimal currencies
    "AED": 2,
    "AUD": 2,
    "CAD": 2,
    "CHF": 2,
    "CNY": 2,
    "DKK": 2,
    "EGP": 2,
    "EUR": 2,
    "GBP": 2,
    "GHS": 2,
    "HKD": 2,
    "INR": 2,
    "KES": 2,
    "MAD": 2,
    "NGN": 2,
    "NOK": 2,
    "NZD": 2,
    "PKR": 2,
    "QAR": 2,
    "RUB": 2,
    "SAR": 2,
    "SEK": 2,
    "SGD": 2,
    "THB": 2,
    "TRY": 2,
    "TZS": 2,
    "UGX": 0,
    "USD": 2,
    "ZAR": 2,
}


# ISO currency codes that Univa is expected to support initially.
#
# This is deliberately separate from the exponent map so that unsupported
# currencies cannot silently enter the system with an assumed precision.
SUPPORTED_CURRENCIES = frozenset(_CURRENCY_EXPONENTS)


@dataclass(frozen=True, slots=True)
class Currency:
    """
    Immutable canonical currency representation.
    """

    code: str

    def __post_init__(self) -> None:
        normalized = self.code.upper().strip()

        if normalized not in SUPPORTED_CURRENCIES:
            raise CurrencyError(
                f"Unsupported currency code: {self.code!r}."
            )

        object.__setattr__(self, "code", normalized)

    @property
    def exponent(self) -> int:
        """Return the number of decimal places used by the currency."""
        return _CURRENCY_EXPONENTS[self.code]

    @property
    def minor_unit(self) -> int:
        """Return the smallest representable monetary unit."""
        return 10 ** self.exponent

    def __str__(self) -> str:
        return self.code


def normalize_currency(currency: str | Currency) -> str:
    """
    Normalize a currency to its canonical ISO-style code.
    """

    if isinstance(currency, Currency):
        return currency.code

    if not isinstance(currency, str):
        raise CurrencyError(
            f"Currency must be a string or Currency instance, got "
            f"{type(currency).__name__}."
        )

    return Currency(currency).code


def get_currency_exponent(currency: str | Currency) -> int:
    """
    Return currency decimal precision.
    """

    return Currency(normalize_currency(currency)).exponent


def is_supported_currency(currency: str | Currency) -> bool:
    """
    Return whether the currency is supported by Univa.
    """

    try:
        normalize_currency(currency)
    except CurrencyError:
        return False

    return True