"""
Univa Wallet Gateway Plugin.

This is the gateway plugin that integrates Univa wallet with the Payment app.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from django.contrib.auth import get_user_model

from payment.gateways.univa.api import UnivaWalletAPI
from payment.gateways.univa.consts import *
from payment.gateways.univa.errors import *

User = get_user_model()
logger = logging.getLogger(__name__)


class UnivaGatewayPlugin:
    """
    Univa Wallet Gateway Plugin.

    This plugin implements the gateway interface for Univa wallet payments.
    It bridges the Payment app with the Banking app.
    """

    name = GATEWAY_NAME
    display_name = GATEWAY_DISPLAY_NAME
    supports_refunds = True
    supports_capture = True
    supports_authorization = False  # Wallet payments are direct

    @classmethod
    def process_payment(
        cls,
        user,
        amount: Decimal,
        currency: str = "NGN",
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a payment using Univa wallet.

        This is the main entry point for wallet payments.
        Supports both NGN (primary wallet) and foreign currencies.
        """
        return UnivaWalletAPI.initiate_payment(
            user=user,
            amount=amount,
            currency=currency,
            payment_reference=payment_reference,
            metadata=metadata,
        )

    @classmethod
    def process_refund(
        cls,
        user,
        amount: Decimal,
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a refund to Univa wallet.
        """
        return UnivaWalletAPI.process_refund(
            user=user,
            amount=amount,
            payment_reference=payment_reference,
            metadata=metadata,
        )

    @classmethod
    def get_balance(
        cls,
        user,
        currency: str = "NGN",
    ) -> Dict[str, Any]:
        """
        Get user's wallet balance for a specific currency.

        Args:
            user: The user
            currency: Currency code (default: NGN)

        Returns:
            Dict with balance information
        """
        return UnivaWalletAPI.get_wallet_balance(user, currency=currency)

    @classmethod
    def validate_payment(
        cls,
        user,
        amount: Decimal,
        currency: str = "NGN",
    ) -> Dict[str, Any]:
        """
        Validate if a payment can be processed.

        Supports validation for both NGN and foreign currencies.
        """
        try:
            result = UnivaWalletAPI.get_wallet_balance(user, currency=currency)

            if not result.get("success"):
                return {
                    "valid": False,
                    "error": result.get("error"),
                    "message": result.get("message"),
                }

            balance = Decimal(str(result.get("balance", 0)))

            if balance < amount:
                return {
                    "valid": False,
                    "error": ERROR_INSUFFICIENT_BALANCE,
                    "message": f"Insufficient balance. Available: {currency} {balance:,.2f}",
                }

            return {
                "valid": True,
                "balance": balance,
                "currency": currency,
                "message": "Payment can be processed.",
            }

        except Exception as exc:
            return {
                "valid": False,
                "error": "VALIDATION_FAILED",
                "message": str(exc),
            }


__all__ = [
    "UnivaGatewayPlugin",
]