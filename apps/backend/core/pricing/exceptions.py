"""
Canonical pricing exceptions for Univa.

The core pricing layer owns these exceptions.

Domain applications should catch these exceptions rather than exceptions
from third-party pricing libraries such as django-prices.
"""


class PricingError(Exception):
    """Base exception for the pricing subsystem."""


class CurrencyError(PricingError):
    """Raised when a currency is invalid or incompatible."""


class CurrencyMismatchError(CurrencyError):
    """
    Raised when arithmetic is attempted across different currencies.
    """

    def __init__(
        self,
        currency_a: str,
        currency_b: str,
    ) -> None:
        self.currency_a = currency_a
        self.currency_b = currency_b

        super().__init__(
            (
                f"Currency mismatch: {currency_a} "
                f"cannot be combined with {currency_b}."
            )
        )


class InvalidCurrencyError(CurrencyError):
    """Raised when a currency code is invalid."""


class InvalidMoneyError(PricingError):
    """Raised when a Money value is invalid."""


class InvalidAmountError(InvalidMoneyError):
    """Raised when a monetary amount is invalid."""


class InvalidTaxedMoneyError(PricingError):
    """
    Raised when a TaxedMoney value is invalid.

    Examples include:

        - net and gross using different currencies
        - gross being less than net
        - invalid tax relationships
    """


class InvalidDiscountError(PricingError):
    """Raised when a discount is invalid."""


class InvalidPriceError(PricingError):
    """Raised when a price is invalid."""


class InvalidTaxError(PricingError):
    """Raised when tax data is invalid."""


class PricingCalculationError(PricingError):
    """Raised when a pricing calculation cannot be completed."""

