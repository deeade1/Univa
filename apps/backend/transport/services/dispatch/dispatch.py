"""
DispatchService — synchronous canonical dispatch.

Responsibilities:
    - find nearby eligible providers
    - pick a match (AI-assisted when available)
    - assign the provider and return a result dict

For async/batch dispatch, use `EnhancedUnifiedDispatcher`.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .base import BaseService
from .config import config

logger = logging.getLogger(__name__)


class DispatchService(BaseService):
    """Synchronous dispatcher with AI-assisted provider matching."""

    def __init__(self):
        super().__init__(config_prefix="dispatch")
        self._ai_service = None
        self._dispatch_timeout = 30
        self._max_distance_km = 20.0

    def initialize(self) -> bool:
        try:
            dispatch_config = config.get_dispatch_config()
            self._dispatch_timeout = getattr(dispatch_config, "max_eta_minutes", 30)
            self._max_distance_km = getattr(
                dispatch_config, "max_assignment_distance_km", 20.0
            )

            if config.should_use_ai():
                try:
                    from .ai_service import AIService
                    self._ai_service = AIService()
                    self._ai_service.initialize()
                except Exception as exc:
                    logger.warning("AIService unavailable: %s", exc)
                    self._ai_service = None

            self._initialized = True
            return True
        except Exception as exc:
            logger.error("Failed to initialize DispatchService: %s", exc)
            return False

    def health_check(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "dispatch_timeout": self._dispatch_timeout,
            "max_distance_km": self._max_distance_km,
            "ai_enabled": self._ai_service is not None
            and self._ai_service.is_initialized(),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch_request(self, service_request) -> Dict[str, Any]:
        """Dispatch a single ServiceRequest to an eligible provider."""
        self._log_operation("dispatch_request", request_id=service_request.id)

        if self._ai_service is not None and config.should_use_ai():
            result = self._ai_dispatch(service_request)
            if result.get("success"):
                return result
            logger.info("AI dispatch failed, falling back to standard")

        return self._standard_dispatch(service_request)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _standard_dispatch(self, service_request) -> Dict[str, Any]:
        providers = self._find_nearby_providers(
            service_request.pickup_location, self._max_distance_km
        )
        if not providers.exists():
            return {
                "success": False,
                "reason": "No providers available within radius",
                "providers_found": 0,
            }

        matched = self._match_provider(providers, service_request)
        if not matched:
            return {
                "success": False,
                "reason": "No matching provider found",
                "providers_considered": providers.count(),
            }

        return self._assign_provider(service_request, matched)

    def _ai_dispatch(self, service_request) -> Dict[str, Any]:
        try:
            result = self._ai_service.optimize_dispatch(service_request)
            if not result.get("success"):
                return {"success": False, "reason": result.get("reason")}
            provider = result.get("provider")
            if provider is None:
                return {"success": False, "reason": "AI returned no provider"}
            return self._assign_provider(service_request, provider)
        except Exception as exc:
            self._log_error("ai_dispatch", exc, request_id=service_request.id)
            return {"success": False, "reason": str(exc)}

    def _find_nearby_providers(self, location, radius_km: float):
        from transport.models import ServiceProviderProfile

        if not location:
            return ServiceProviderProfile.objects.none()

        return ServiceProviderProfile.objects.nearby(location, radius_km).filter(
            is_available=True, is_online=True, is_verified=True
        )

    def _match_provider(self, providers, service_request):
        """Return the best provider from the queryset."""
        if not providers.exists():
            return None

        if self._ai_service is not None:
            best = None
            best_score = -1.0
            for provider in providers:
                score = self._ai_service._score_provider(provider, service_request)
                if score > best_score:
                    best_score = score
                    best = provider
            return best

        return providers.first()

    def _assign_provider(self, service_request, provider) -> Dict[str, Any]:
        from transport.models import ServiceRequest

        service_request.provider = provider
        service_request.status = ServiceRequest.Status.ACCEPTED
        service_request.save(update_fields=["provider", "status"])

        eta = self._calculate_eta(provider, service_request.pickup_location)

        return {
            "success": True,
            "provider_id": provider.id,
            "provider_name": getattr(provider, "display_name", str(provider)),
            "estimated_arrival": eta,
            "status": "accepted",
        }

    def _calculate_eta(self, provider, destination) -> Optional[datetime]:
        try:
            distance = provider.distance_to(destination)
        except Exception:
            distance = None

        if distance is None:
            minutes = 10.0
        else:
            minutes = max(1.0, (distance / 30) * 60)

        return datetime.now() + timedelta(minutes=minutes)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_dispatch_status(self, request_id) -> Dict[str, Any]:
        from transport.models import ServiceRequest

        try:
            req = ServiceRequest.objects.get(pk=request_id)
        except ServiceRequest.DoesNotExist:
            return {"error": "Request not found"}

        return {
            "request_id": req.id,
            "status": req.status,
            "provider": getattr(req.provider, "display_name", None)
            if req.provider
            else None,
            "eta": req.estimated_arrival_time,
        }