"""
Dispatch configuration.

Reads Django settings first, falls back to sane defaults. Provides
both attribute access (`config.dispatch.max_assignment_distance_km`)
and helper methods (`config.get_dispatch_config()`) used across the
package.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict

from django.conf import settings


@dataclass
class DispatchConfig:
    max_eta_minutes: int = 30
    max_assignment_distance_km: float = 20.0
    use_enhanced_mode: bool = True
    ai_enabled: bool = True
    ai_health_check_interval_seconds: int = 300
    ai_model_path: str = "models/dispatch_ai.pkl"
    dispatch_batch_size: int = 50
    dispatch_sleep_low: int = 15
    dispatch_sleep_medium: int = 10
    dispatch_sleep_high: int = 5


@dataclass
class AIConfig:
    ml_model_weights: Dict[str, float] = field(default_factory=lambda: {
        "proximity": 0.25,
        "rating": 0.15,
        "vehicle_suitability": 0.08,
    })
    demand_model_path: str = "models/demand_prediction.pkl"
    demand_scaler_path: str = "models/demand_scaler.pkl"
    eta_model_path: str = "models/eta_prediction.pkl"
    eta_scaler_path: str = "models/eta_scaler.pkl"
    route_model_path: str = "models/route_optimization.pkl"


class _Config:
    """Root config object. Reads overrides from `settings.DISPATCH`."""

    def __init__(self):
        overrides = getattr(settings, "DISPATCH", {}) or {}
        self.dispatch = DispatchConfig(**{**self._dispatch_defaults(), **overrides.get("dispatch", {})})
        self.ai = AIConfig(**{**self._ai_defaults(), **overrides.get("ai", {})})
        # Attribute-style access used by unified_dispatchs.py
        self.dispatch_ns = SimpleNamespace(**self.dispatch.__dict__)

    @staticmethod
    def _dispatch_defaults() -> Dict[str, Any]:
        return DispatchConfig().__dict__

    @staticmethod
    def _ai_defaults() -> Dict[str, Any]:
        return AIConfig().__dict__

    # ---- API used by DispatchService ----
    def get_dispatch_config(self) -> DispatchConfig:
        return self.dispatch

    def get_ai_config(self) -> AIConfig:
        return self.ai

    def get_section(self, name: str) -> Dict[str, Any]:
        section = getattr(self, name, None)
        if section is None:
            return {}
        return getattr(section, "__dict__", {}) or {}

    def should_use_enhanced_mode(self) -> bool:
        return bool(self.dispatch.use_enhanced_mode)

    def should_use_ai(self) -> bool:
        return bool(self.dispatch.ai_enabled)


config = _Config()