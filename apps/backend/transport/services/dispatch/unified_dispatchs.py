"""
EnhancedUnifiedDispatcher — async dispatcher with AI + fallback.

Wraps `DispatchService` for the synchronous fallback path. The AI
batch optimizer is optional; if it fails to initialize, everything
routes through the simple path.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import connection, transaction

from .ai_optimizer import AIDispatchOptimizer, DispatchAssignment
from .config import config
from .dispatch import DispatchService
from .health import health_checker

logger = logging.getLogger("dispatch")


class EnhancedUnifiedDispatcher:
    """Async dispatcher with AI optimization and automatic fallback."""

    def __init__(self):
        self.is_running = False
        self.fallback_dispatcher = DispatchService()
        self.fallback_dispatcher.initialize()
        self.ai_optimizer: Optional[AIDispatchOptimizer] = None
        self.health_status = "healthy"
        self._init_ai_optimizer()

    def _init_ai_optimizer(self) -> None:
        try:
            optimizer = AIDispatchOptimizer()
            if optimizer.initialization_successful:
                self.ai_optimizer = optimizer
                logger.info("AI optimizer initialized")
            else:
                logger.warning("AI optimizer not ready; using fallback")
                self.health_status = "degraded"
        except Exception as exc:
            logger.warning("AI optimizer unavailable: %s", exc)
            self.health_status = "degraded"

    # ------------------------------------------------------------------
    # Single request
    # ------------------------------------------------------------------

    async def dispatch_request(self, request) -> Optional[object]:
        try:
            providers = await self._find_available_providers_async(request)
            if not providers:
                logger.warning("No available providers for request %s", request.id)
                return None

            provider = None
            if self.ai_optimizer and self._should_use_ai(request):
                provider = await self._select_with_ai(request, providers)
            if provider is None:
                provider = await self._select_with_simple(request, providers)

            if provider is None:
                logger.error("All dispatch methods failed for request %s", request.id)
                return None

            await self._assign_provider_async(request, provider)
            return provider

        except Exception as exc:
            logger.error("Enhanced dispatch failed: %s", exc)
            health_checker.record_failure("enhanced")
            try:
                return await self._fallback_to_simple(request)
            except Exception as fallback_exc:
                logger.error("Fallback failed: %s", fallback_exc)
                return None

    def _should_use_ai(self, request) -> bool:
        if self.health_status != "healthy":
            return False
        if request.service_type in ("interstate", "shared"):
            return True
        hour = datetime.now().hour
        return 7 <= hour <= 9 or 16 <= hour <= 18

    async def _select_with_ai(self, request, providers):
        try:
            context = {
                "request": request,
                "providers": providers,
                "timestamp": datetime.now().isoformat(),
            }
            assignments = await self.ai_optimizer.optimize_dispatch_batch(
                [request], providers, context
            )
            if not assignments:
                return None
            target_id = assignments[0].provider_id
            for provider in providers:
                if provider.id == target_id:
                    return provider
            return None
        except Exception as exc:
            logger.error("AI selection failed: %s", exc)
            health_checker.record_failure("ai_optimizer")
            return None

    async def _select_with_simple(self, request, providers):
        try:
            return await sync_to_async(self.fallback_dispatcher._match_provider)(
                providers, request
            )
        except Exception as exc:
            logger.error("Simple selection failed: %s", exc)
            return None

    async def _fallback_to_simple(self, request):
        logger.warning("Falling back to simple dispatch for %s", request.id)
        return await sync_to_async(self.fallback_dispatcher.dispatch_request)(request)

    # ------------------------------------------------------------------
    # Provider lookup
    # ------------------------------------------------------------------

    async def _find_available_providers_async(self, request) -> List:
        from transport.models.core.service_provider import ServiceProviderProfile

        provider_type = self._provider_type_for_service(request.service_type)
        max_meters = config.dispatch.max_assignment_distance_km * 1000

        def _query():
            return list(
                ServiceProviderProfile.objects.filter(
                    is_available=True,
                    is_online=True,
                    provider_type=provider_type,
                    location_point__isnull=False,
                )[:20]
            )

        try:
            candidates = await sync_to_async(_query)()
            # Distance filter in Python to avoid GIS distance annotation
            # complexity — request.pickup_location is a Point.
            pickup = getattr(request, "pickup_location", None)
            if pickup is None:
                return candidates
            result = []
            for provider in candidates:
                try:
                    if provider.location_point is None:
                        continue
                    # Rough metric distance in meters
                    distance_m = provider.location_point.distance(pickup) * 111_000
                    if distance_m <= max_meters:
                        result.append(provider)
                except Exception:
                    continue
            return result[:10]
        except Exception as exc:
            logger.error("Failed to find providers: %s", exc)
            return []

    def _provider_type_for_service(self, service_type: str) -> str:
        mapping = {
            "taxi": "driver",
            "shared": "driver",
            "interstate": "driver",
            "delivery": "courier",
            "food": "courier",
            "cargo": "courier",
        }
        return mapping.get(service_type, "driver")

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    async def _assign_provider_async(self, request, provider) -> None:
        from transport.models.core.service_request import ServiceRequest

        def _sync_assign():
            with transaction.atomic():
                request.provider = provider
                request.status = ServiceRequest.Status.ACCEPTED
                request.save(update_fields=["provider", "status"])

                provider.current_service = request
                provider.is_available = False
                provider.save(update_fields=["current_service", "is_available"])

        await sync_to_async(_sync_assign)()

        try:
            await self._send_assignment_notification(request, provider)
        except Exception as exc:
            logger.warning("Notification dispatch failed: %s", exc)

    async def _send_assignment_notification(self, request, provider) -> None:
        try:
            from channels.layers import get_channel_layer

            layer = get_channel_layer()
            if layer is None:
                return

            payload = {
                "request_id": request.id,
                "provider_id": provider.id,
                "pickup_address": getattr(request, "pickup_address", "") or "Unknown",
                "timestamp": datetime.now().isoformat(),
            }

            await layer.group_send(
                f"provider_{provider.id}",
                {"type": "provider.assignment", "data": payload},
            )
            await layer.group_send(
                f"customer_{request.customer_id}",
                {"type": "customer.assignment", "data": payload},
            )
        except Exception as exc:
            logger.error("Notification sending failed: %s", exc)

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    async def process_dispatch_batch(self, requests_batch):
        from transport.models import ServiceProviderProfile

        providers = await sync_to_async(list)(
            ServiceProviderProfile.objects.filter(
                is_available=True,
                is_online=True,
                last_active__gte=datetime.now() - timedelta(minutes=5),
            ).select_related("user", "current_vehicle")
        )

        if not providers:
            return []

        if self.ai_optimizer and len(requests_batch) > 5:
            context = self._prepare_dispatch_context(requests_batch, providers)
            assignments = await self.ai_optimizer.optimize_dispatch_batch(
                requests_batch, providers, context
            )
        else:
            assignments = []
            pool = list(providers)
            for request in requests_batch:
                provider = await self._select_with_simple(request, pool)
                if provider is None:
                    continue
                assignments.append(
                    DispatchAssignment(
                        request_id=request.id,
                        provider_id=provider.id,
                        match_score=0.5,
                        estimated_eta=15.0,
                    )
                )
                pool = [p for p in pool if p.id != provider.id]

        successful = []
        for assignment in assignments:
            if await self._execute_assignment(assignment):
                successful.append(assignment)

        logger.info(
            "Batch dispatch: %d/%d successful", len(successful), len(assignments)
        )
        return successful

    async def _execute_assignment(self, assignment: DispatchAssignment) -> bool:
        from transport.models import ServiceProviderProfile, ServiceRequest

        def _sync_execute():
            with transaction.atomic():
                try:
                    provider = ServiceProviderProfile.objects.select_for_update().get(
                        pk=assignment.provider_id
                    )
                except ServiceProviderProfile.DoesNotExist:
                    return False
                if not provider.is_available:
                    return False

                try:
                    request = ServiceRequest.objects.select_related(
                        "customer"
                    ).get(pk=assignment.request_id)
                except ServiceRequest.DoesNotExist:
                    return False

                request.provider = provider
                request.status = ServiceRequest.Status.ACCEPTED
                request.save(update_fields=["provider", "status"])

                provider.is_available = False
                provider.current_service = request
                provider.save(update_fields=["is_available", "current_service"])
                return True

        try:
            return await sync_to_async(_sync_execute)()
        except Exception as exc:
            logger.error("Assignment execution failed: %s", exc)
            return False

    def _prepare_dispatch_context(self, requests, providers) -> dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "request_count": len(requests),
            "provider_count": len(providers),
            "time_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
        }

    # ------------------------------------------------------------------
    # Continuous loop
    # ------------------------------------------------------------------

    async def run_continuous_dispatch(self) -> None:
        from transport.models import ServiceRequest

        self.is_running = True
        logger.info("Starting EnhancedUnifiedDispatcher loop")

        while self.is_running:
            try:
                if not await self._health_check():
                    logger.warning("Health check failed, pausing")
                    await asyncio.sleep(30)
                    continue

                pending = await sync_to_async(list)(
                    ServiceRequest.objects.filter(
                        status="requested",
                        created_at__gte=datetime.now() - timedelta(minutes=30),
                    ).select_related("customer")[:50]
                )

                if pending:
                    await self.process_dispatch_batch(pending)
                    logger.info("Processed %d requests", len(pending))
                else:
                    await asyncio.sleep(10)
                    continue

                await asyncio.sleep(await self._calculate_sleep_duration())
            except Exception as exc:
                logger.error("Dispatch cycle error: %s", exc)
                await asyncio.sleep(30)

    async def _health_check(self) -> bool:
        def _db_ok():
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return True
            except Exception:
                return False

        db_ok = await sync_to_async(_db_ok)()
        if not db_ok:
            self.health_status = "unhealthy"
            return False

        try:
            cache.set("dispatch_health", "ok", 1)
            if cache.get("dispatch_health") != "ok":
                return False
        except Exception:
            return False

        if self.ai_optimizer and not self.ai_optimizer.initialization_successful:
            self.health_status = "degraded"
        else:
            self.health_status = "healthy"
        return True

    async def _calculate_sleep_duration(self) -> int:
        from transport.models import ServiceRequest

        try:
            count = await sync_to_async(
                ServiceRequest.objects.filter(status="requested").count
            )()
        except Exception:
            return config.dispatch.dispatch_sleep_medium

        if count > 100:
            return config.dispatch.dispatch_sleep_high
        if count > 20:
            return config.dispatch.dispatch_sleep_medium
        return config.dispatch.dispatch_sleep_low

    async def stop(self) -> None:
        self.is_running = False
        logger.info("EnhancedUnifiedDispatcher stopped")