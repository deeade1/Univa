"""
Payment Gateways for Univa.

This module provides gateway implementations for various payment providers.
"""

from payment.gateways.univa.plugin import UnivaGatewayPlugin


def get_gateway(gateway_name):
    """
    Get a gateway plugin by name.

    Args:
        gateway_name: Name of the gateway (e.g., 'paystack', 'stripe', 'univa')

    Returns:
        Gateway plugin class
    """
    gateway_map = {
        "univa": UnivaGatewayPlugin,
        # Add other gateways as they are implemented
        # "paystack": PaystackGatewayPlugin,
        # "stripe": StripeGatewayPlugin,
        # "flutterwave": FlutterwaveGatewayPlugin,
    }

    return gateway_map.get(gateway_name)


def get_gateway_names():
    """
    Get list of available gateway names.

    Returns:
        List of gateway names
    """
    return ["univa"]  # Add more as they are implemented


__all__ = [
    "UnivaGatewayPlugin",
    "get_gateway",
    "get_gateway_names",
]