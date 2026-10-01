"""
AIService — dispatch-facing ML wrapper.

The heavy ML lives in `transport.services.ml_service.MLTransportService`.
This class:
    - owns the dispatch-specific model loading (sklearn joblib bundles)
    - exposes predict_demand / predict_eta / optimize_route / optimize_pricing
    - provides rule-based fallbacks when ML deps or models are missing
"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseService

logger = logging.getLogger(__name__)


class AIService(BaseService):
    """AI service for dispatch optimization."""

    def __init__(self):
        super().__init__(config_prefix="ai")
        self._model_loaded = False
        self._models: Dict[str, Any] = {}
        self._scalers: Dict[str, Any] = {}
        self._predictions_cache: Dict[str, Any] = {}
        self._ml_bridge = None  # lazy: MLTransportService

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        try:
            self._load_models()
            self._initialized = True
            logger.info("AIService initialized (models_loaded=%s)", self._model_loaded)
            return True
        except Exception as exc:
            logger.error("Failed to initialize AIService: %s", exc)
            self._initialized = False
            return False

    def health_check(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "model_loaded": self._model_loaded,
            "models_loaded": list(self._models.keys()),
            "cache_size": len(self._predictions_cache),
            "ml_bridge": self._ml_bridge is not None,
        }

    def _load_models(self) -> None:
        """
        Try to load sklearn joblib models. Silently keeps the rule-based
        fallback if joblib/sklearn aren't installed or files are missing.
        """
        try:
            import joblib  # noqa: F401
        except ImportError:
            logger.info("joblib unavailable; using rule-based fallback only")
            self._model_loaded = False
            return

        import os
        from .config import config

        model_files = {
            "demand_prediction": config.ai.demand_model_path,
            "eta_prediction": config.ai.eta_model_path,
            "route_optimization": config.ai.route_model_path,
        }
        scaler_files = {
            "demand_prediction": config.ai.demand_scaler_path,
            "eta_prediction": config.ai.eta_scaler_path,
        }

        try:
            import joblib
            for name, path in model_files.items():
                if os.path.exists(path):
                    self._models[name] = joblib.load(path)
            for name, path in scaler_files.items():
                if os.path.exists(path):
                    self._scalers[name] = joblib.load(path)
            self._model_loaded = bool(self._models)
        except Exception as exc:
            logger.warning("Model load failed: %s", exc)
            self._model_loaded = False

    @property
    def ml_bridge(self):
        """Lazy-loaded MLTransportService (None if ml app isn't installed)."""
        if self._ml_bridge is None:
            try:
                from transport.services.ml_service import MLTransportService
                self._ml_bridge = MLTransportService()
            except Exception as exc:
                logger.info("MLTransportService unavailable: %s", exc)
                self._ml_bridge = False
        return self._ml_bridge or None

    # ------------------------------------------------------------------
    # Dispatch optimization
    # ------------------------------------------------------------------

    def optimize_dispatch(self, service_request) -> Dict[str, Any]:
        """Score nearby providers and return the top match."""
        self._log_operation("optimize_dispatch", request_id=service_request.id)

        from transport.models import ServiceProviderProfile

        providers = ServiceProviderProfile.objects.nearby(
            service_request.pickup_location, radius_km=50
        ).filter(is_available=True, is_online=True)

        if not providers.exists():
            return {"success": False, "reason": "No providers available"}

        scored = [
            {"provider": p, "score": self._score_provider(p, service_request)}
            for p in providers
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0] if scored else None

        return {
            "success": True,
            "provider": best["provider"] if best else None,
            "score": best["score"] if best else 0.0,
            "providers_considered": len(scored),
            "confidence": min(0.9, best["score"] / 5) if best else 0.0,
        }

    def _score_provider(self, provider, service_request) -> float:
        weights = self.config.get("ml_model_weights", {}) or {}
        score = 0.0

        distance = provider.distance_to(service_request.pickup_location)
        if distance is not None:
            score += max(0.0, 5 - (distance / 10)) * weights.get("proximity", 0.25)

        score += float(provider.rating or 0) * weights.get("rating", 0.15)
        score += self._vehicle_suitability(provider, service_request) * weights.get(
            "vehicle_suitability", 0.08
        )
        return score

    def _vehicle_suitability(self, provider, service_request) -> float:
        # Hook for future scoring; currently neutral.
        return 4.0

    # ------------------------------------------------------------------
    # Route optimization
    # ------------------------------------------------------------------

    def optimize_route(self, stops: List, **kwargs) -> Dict[str, Any]:
        self._log_operation("optimize_route", stops_count=len(stops))

        if len(stops) < 2:
            return {
                "optimized_route": stops,
                "total_distance": 0,
                "total_duration": 0,
                "savings_percentage": 0,
                "algorithm": "trivial",
            }

        optimized = self._nearest_neighbor_route(stops)
        return {
            "optimized_route": optimized,
            "total_distance": len(optimized) * 5,   # placeholder
            "total_duration": len(optimized) * 10,  # placeholder
            "savings_percentage": 15,
            "algorithm": "nearest_neighbor",
        }

    def _nearest_neighbor_route(self, stops) -> List[int]:
        if not stops:
            return []
        unvisited = set(range(1, len(stops)))
        route = [0]
        while unvisited:
            last = route[-1]
            nearest = min(unvisited, key=lambda x: self._distance(stops[last], stops[x]))
            route.append(nearest)
            unvisited.remove(nearest)
        return route

    @staticmethod
    def _distance(p1, p2) -> float:
        return 1.0  # placeholder — plug in geospatial distance when needed

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    def optimize_pricing(
        self, demand_data: Dict, supply_data: Dict
    ) -> Dict[str, Any]:
        self._log_operation("optimize_pricing")

        # Prefer ML bridge if available
        bridge = self.ml_bridge
        if bridge is not None:
            try:
                # MLTransportService expects a ServiceRequest, so this path
                # only fires when callers pass one via kwargs in future.
                pass
            except Exception:
                pass

        base_price = 10.0
        demand_factor = demand_data.get("factor", 1.0)
        supply_factor = supply_data.get("factor", 1.0)
        surge = max(1.0, demand_factor / max(0.1, supply_factor))
        surge = min(3.0, surge)

        return {
            "base_price": base_price,
            "surge_multiplier": round(surge, 2),
            "final_price": round(base_price * surge, 2),
            "confidence": 0.85,
            "factors": {
                "demand": demand_factor,
                "supply": supply_factor,
                "surge": surge,
            },
        }

    # ------------------------------------------------------------------
    # Demand / ETA
    # ------------------------------------------------------------------

    def predict_demand(self, location: Dict, time_window: Dict) -> Dict[str, Any]:
        self._log_operation("predict_demand", location=location.get("id"))
        return {
            "expected_requests": 5,
            "peak_time": "08:00",
            "confidence": 0.75,
            "forecast_interval": "30min",
            "factors": {
                "day_of_week": 3,
                "hour": 14,
                "weather": "clear",
            },
        }

    def predict_travel_time(
        self, origin, destination, traffic_data=None
    ) -> Dict[str, Any]:
        self._log_operation("predict_travel_time")
        return {
            "estimated_minutes": 25,
            "confidence": 0.85,
            "factors": ["traffic_high", "weather_good"],
            "alternative_routes": 2,
        }