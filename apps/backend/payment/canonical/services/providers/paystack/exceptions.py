# payment/canonical/services/providers/paystack/exceptions.py

"""
Paystack-specific exceptions.

These are transport-layer errors. They never bubble past the adapter —
the adapter converts them into ProviderResult with
reconciliation_required=True when appropriate.
"""

from __future__ import annotations


class PaystackError(Exception):
    """Base error for Paystack integration."""


class PaystackConfigurationError(PaystackError):
    """Raised when required settings are missing."""


class PaystackRequestError(PaystackError):
    """Raised on network failure, timeout, or non-JSON response."""


class PaystackResponseError(PaystackError):
    """Raised when Paystack returns an error body."""