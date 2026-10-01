from django.core.exceptions import ValidationError

from payment.canonical.models import PaymentExecution
from payment.canonical.services.providers import ProviderAdapter
from payment.canonical.services.providers import ProviderRegistry


class ExecutionRouter:
    """
    Resolves the ProviderAdapter responsible for a PaymentExecution.

    The router is intentionally limited to provider resolution.

    It does not:
        - execute payments
        - mutate Payment
        - mutate PaymentExecution
        - perform provider API calls
        - perform lifecycle transitions
        - create execution events
    """

    @classmethod
    def _validate_execution(cls, execution):
        if execution is None:
            raise ValidationError(
                {"execution": "Payment execution is required."}
            )

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                {
                    "execution": (
                        "A valid PaymentExecution instance is required."
                    )
                }
            )

    @classmethod
    def _validate_provider(cls, provider):
        if provider is None or not str(provider).strip():
            raise ValidationError(
                {"provider": "Payment execution provider is required."}
            )

    @classmethod
    def resolve(cls, execution):
        """
        Resolve the registered ProviderAdapter for an execution.
        """
        cls._validate_execution(execution)

        provider = execution.provider

        cls._validate_provider(provider)

        adapter = ProviderRegistry.get(provider)

        if not isinstance(adapter, ProviderAdapter):
            raise ValidationError(
                {
                    "provider": (
                        "Registered provider must resolve to a "
                        "ProviderAdapter."
                    )
                }
            )

        return adapter