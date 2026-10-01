"""
Univa Wallet Gateway Errors.

This module defines custom exceptions for the Univa wallet gateway.
"""


class UnivaGatewayError(Exception):
    """Base exception for Univa gateway errors."""
    pass


class WalletNotFoundError(UnivaGatewayError):
    """Raised when user's wallet is not found."""
    pass


class InsufficientBalanceError(UnivaGatewayError):
    """Raised when wallet balance is insufficient."""
    pass


class WalletInactiveError(UnivaGatewayError):
    """Raised when wallet is not active."""
    pass


class AmountInvalidError(UnivaGatewayError):
    """Raised when amount is invalid."""
    pass


class DailyLimitExceededError(UnivaGatewayError):
    """Raised when daily limit is exceeded."""
    pass


class TransactionFailedError(UnivaGatewayError):
    """Raised when transaction processing fails."""
    pass


__all__ = [
    "UnivaGatewayError",
    "WalletNotFoundError",
    "InsufficientBalanceError",
    "WalletInactiveError",
    "AmountInvalidError",
    "DailyLimitExceededError",
    "TransactionFailedError",
]