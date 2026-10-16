# payment/canonical/services/providers/stub.py

"""
Deterministic stub provider for dev/test.

Always returns COMPLETED. Register only in dev/test settings.
"""

from __future__ import annotations

from payment.canonical.models import PaymentExecution
from payment.canonical.services.providers.adapter import ProviderAdapter
from payment.canonical.services.providers.result import ProviderResult


class StubProviderAdapter(ProviderAdapter):

    @property
    def provider_name(self) -> str:
        return "stub"

    def initiate(self, execution: PaymentExecution) -> ProviderResult:
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference=f"STUB-{execution.reference}",
            reconciliation_required=False,
            metadata={"stub": True},
        )

    def get_status(self, execution: PaymentExecution) -> ProviderResult:
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference=execution.provider_reference or "",
            reconciliation_required=False,
            metadata={"stub": True},
        )