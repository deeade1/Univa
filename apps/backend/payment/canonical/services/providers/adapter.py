from abc import ABC, abstractmethod

from payment.canonical.models import PaymentExecution

from .result import ProviderResult


class ProviderAdapter(ABC):
    """
    Canonical interface for payment provider execution.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def initiate(
        self,
        execution: PaymentExecution,
    ) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def get_status(
        self,
        execution: PaymentExecution,
    ) -> ProviderResult:
        raise NotImplementedError

    def cancel(
        self,
        execution: PaymentExecution,
    ) -> ProviderResult:
        raise NotImplementedError(
            f"{self.provider_name} does not support cancellation."
        )