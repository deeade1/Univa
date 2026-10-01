# transport/services/ml_service.py
"""
ML Service — bridge between Transport and ML modules.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.db import models, transaction

from ..models import (
    ServiceRequest,
    ServiceProviderProfile,
    Vehicle,
    Delivery,
    Package,
)

# ---- Corrected import paths to match the on-disk tree ----
from ml.transport.analytics import TransportAnalytics
from ml.transport.driver_optimization import DriverEarningOptimizer
from ml.transport.pricing.optimizer import MLPricingOptimizer
from ml.transport.interstate.compatibility import InterstateCompatibilityEngine
from ml.models import MLModelVersion

logger = logging.getLogger(__name__)


class MLTransportService:
    """
    Unified ML service for transport operations.
    Singleton — imported by AIService and other callers.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.analytics = TransportAnalytics()
        self.driver_optimizer = DriverEarningOptimizer()
        self.pricing_optimizer = MLPricingOptimizer()
        self.interstate_engine = InterstateCompatibilityEngine(ml_enabled=True)

        self._initialized = True
        logger.info("ML Transport Service initialized")

    # ============================================================
    # PRICING
    # ============================================================

    def get_optimal_price(
        self,
        service_request: ServiceRequest,
        base_price: Optional[float] = None,
        objective: str = "revenue",
    ) -> Dict[str, Any]:
        context = self._build_pricing_context(service_request)
        if base_price is None:
            base_price = self._get_base_price(service_request)

        result = self.pricing_optimizer.calculate_optimal_price(
            context=context, base_price=base_price, objective=objective
        )
        result["service_request_id"] = service_request.id
        return result

    def _build_pricing_context(self, request: ServiceRequest) -> Dict:
        now = datetime.now()
        return {
            "service_type": request.service_type,
            "distance_km": request.estimated_distance or 10,
            "duration_min": request.estimated_duration or 20,
            "time_of_day": now.hour,
            "day_of_week": now.weekday(),
            "traffic_level": self._estimate_traffic(now),
            "vehicle_type": self._get_vehicle_type(request),
            "customer_segment": self._get_customer_segment(request),
        }

    def _get_base_price(self, request: ServiceRequest) -> float:
        if getattr(request, "base_fare", None):
            return float(request.base_fare)
        distance = request.estimated_distance or 10
        return distance * 5.0

    def _get_vehicle_type(self, request: ServiceRequest) -> str:
        vehicle = getattr(request, "vehicle", None)
        if vehicle is not None:
            return vehicle.vehicle_type or "standard"
        return "standard"

    def _get_customer_segment(self, request: ServiceRequest) -> str:
        return "regular"

    def _estimate_traffic(self, time: datetime) -> float:
        hour = time.hour
        if 7 <= hour <= 9 or 16 <= hour <= 19:
            return 0.8
        if 10 <= hour <= 15:
            return 0.4
        return 0.2

    # ============================================================
    # DRIVER OPTIMIZATION
    # ============================================================

    def optimize_driver_commission(
        self,
        provider: ServiceProviderProfile,
        market_conditions: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        performance = self._build_driver_performance(provider)
        if market_conditions is None:
            market_conditions = self._get_market_conditions()

        result = self.driver_optimizer.optimize_commission(
            driver_id=str(provider.id),
            performance=performance,
            market_conditions=market_conditions,
        )

        if result.get("commission_rate") and hasattr(provider, "commission_rate"):
            provider.commission_rate = result["commission_rate"]
            provider.save(update_fields=["commission_rate"])

        return result

    def predict_driver_earnings(
        self, provider: ServiceProviderProfile, days: int = 7
    ) -> Dict[str, Any]:
        return self.driver_optimizer.predict_earnings(
            driver_id=str(provider.id), period_days=days
        )

    def _build_driver_performance(self, provider: ServiceProviderProfile):
        from ml.transport.driver_optimization import DriverPerformance

        completed = ServiceRequest.objects.filter(
            provider=provider, status="completed"
        )
        total = completed.count()
        total_earnings = (
            completed.aggregate(total=models.Sum("total_fare"))["total"] or 0
        )

        rating = float(provider.rating or 4.5)
        online_hours = 40.0

        return DriverPerformance(
            rating=rating,
            acceptance_rate=0.85,
            completion_rate=0.90 if total > 0 else 0.85,
            earnings_per_hour=float(total_earnings) / max(online_hours, 1),
            total_rides=total,
            online_hours=online_hours,
            cancellation_rate=0.05,
            customer_satisfaction=rating / 5 * 100,
        )

    def _get_market_conditions(self) -> Dict:
        return {
            "demand_supply_ratio": 1.2,
            "competitor_commission": 20.0,
            "market_growth_rate": 0.1,
            "peak_hour_multiplier": 1.5,
        }

    # ============================================================
    # INTERSTATE MATCHING
    # ============================================================

    def find_interstate_compatible_groups(
        self, trip_requests: List[Dict], max_group_size: int = 4
    ) -> List[Dict]:
        trips = self._create_interstate_trips(trip_requests)
        return self.interstate_engine.find_compatible_groups(
            trips=trips, max_group_size=max_group_size
        )

    def _create_interstate_trips(self, trip_data: List[Dict]) -> List:
        from ml.transport.interstate.compatibility import InterstateTrip

        return [
            InterstateTrip(
                trip_id=data["trip_id"],
                user_id=data["user_id"],
                departure_city=data["departure_city"],
                destination_city=data["destination_city"],
                departure_time=datetime.fromisoformat(data["departure_time"]),
                passengers=data.get("passengers", 1),
                max_group_size=data.get("max_group_size", 4),
            )
            for data in trip_data
        ]

    # ============================================================
    # ANALYTICS
    # ============================================================

    def predict_trip_duration(self, request: ServiceRequest) -> Dict[str, Any]:
        features = {
            "distance_km": request.estimated_distance or 10,
            "traffic_level": self._estimate_traffic(datetime.now()),
            "time_of_day": datetime.now().hour,
            "service_type": request.service_type,
        }
        return self.analytics.predict_trip_duration(features)

    def predict_demand(
        self, location: Dict[str, float], time_window: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if time_window is None:
            time_window = {
                "start": datetime.now(),
                "end": datetime.now() + timedelta(hours=4),
            }
        historical = self._get_historical_demand(location)
        return self.analytics.predict_demand(
            location=location, time_window=time_window, historical_data=historical
        )

    def _get_historical_demand(self, location: Dict):
        return None

    # ============================================================
    # MODEL MANAGEMENT
    # ============================================================

    def get_model_status(self, model_type: str) -> Dict[str, Any]:
        try:
            model = MLModelVersion.objects.filter(
                model_type=model_type, is_production=True, is_active=True
            ).first()
            if model:
                return {
                    "model_type": model_type,
                    "version": model.version,
                    "is_production": model.is_production,
                    "created_at": model.created_at,
                    "performance": model.performance_metrics,
                }
        except Exception as exc:
            logger.error("Error getting model status: %s", exc)
        return {"model_type": model_type, "status": "not_found"}

    def train_model(self, model_type: str, data: Dict) -> Dict[str, Any]:
        logger.info("Training %s model...", model_type)
        return {
            "model_type": model_type,
            "status": "training_started",
            "estimated_completion": datetime.now() + timedelta(hours=1),
        }