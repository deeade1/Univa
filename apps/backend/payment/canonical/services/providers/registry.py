from django.core.exceptions import ValidationError

from .adapter import ProviderAdapter


class ProviderRegistry:
    """
    Registry of canonical payment provider adapters.

    The registry is responsible only for mapping a stable provider
    identifier to a ProviderAdapter implementation.

    It does not:
        - execute payments
        - select providers
        - mutate Payment
        - mutate PaymentExecution
        - perform provider API calls
        - contain provider-specific logic
    """

    _adapters = {}

    @classmethod
    def register(cls, adapter):
        if not isinstance(adapter, ProviderAdapter):
            raise ValidationError(
                {"adapter": "A valid ProviderAdapter instance is required."}
            )

        provider_name = adapter.provider_name

        if not isinstance(provider_name, str) or not provider_name.strip():
            raise ValidationError(
                {"provider_name": "Provider name is required."}
            )

        provider_name = provider_name.strip().lower()

        if provider_name in cls._adapters:
            raise ValidationError(
                {
                    "provider_name": (
                        f"Provider '{provider_name}' is already registered."
                    )
                }
            )

        cls._adapters[provider_name] = adapter

        return adapter

    @classmethod
    def get(cls, provider_name):
        if not isinstance(provider_name, str) or not provider_name.strip():
            raise ValidationError(
                {"provider_name": "Provider name is required."}
            )

        provider_name = provider_name.strip().lower()

        try:
            return cls._adapters[provider_name]
        except KeyError:
            raise ValidationError(
                {
                    "provider_name": (
                        f"Provider '{provider_name}' is not registered."
                    )
                }
            )

    @classmethod
    def has(cls, provider_name):
        if not isinstance(provider_name, str) or not provider_name.strip():
            return False

        return provider_name.strip().lower() in cls._adapters

    @classmethod
    def clear(cls):
        cls._adapters.clear()