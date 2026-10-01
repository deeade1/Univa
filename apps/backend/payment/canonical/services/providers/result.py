from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider_reference: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    reconciliation_required: bool = False
    metadata: Mapping[str, Any] | None = None