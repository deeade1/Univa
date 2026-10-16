# payment/canonical/apps.py

from django.apps import AppConfig


class PaymentCanonicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payment.canonical"
    label = "payment_canonical"

    def ready(self):
        from django.conf import settings
        from payment.canonical.services.providers.registry import (
            ProviderRegistry,
        )
        from payment.canonical.services.providers.paystack import (
            PaystackAdapter,
        )

        if not ProviderRegistry.has("paystack"):
            ProviderRegistry.register(PaystackAdapter())

        if getattr(settings, "ENABLE_STUB_PROVIDER", False):
            from payment.canonical.services.providers.stub import (
                StubProviderAdapter,
            )
            if not ProviderRegistry.has("stub"):
                ProviderRegistry.register(StubProviderAdapter())