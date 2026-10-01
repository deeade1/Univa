"""
Health check for the dispatch stack.

Verifies DB connectivity, cache, and optional AI availability.
Records per-mode failures in cache so the dispatcher can fall back
automatically.
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Dict, List

from django.core.cache import cache

logger = logging.getLogger(__name__)


class DispatchHealthChecker:
    """Monitor and report on dispatch system health."""

    MAX_FAILURES = 3
    FAILURE_WINDOW_SECONDS = 3600

    def __init__(self):
        self.health_status = {
            "simple_mode": True,
            "ai_mode": False,
            "enhanced_mode": False,
            "last_check": None,
            "failure_count": 0,
            "current_mode": "simple",
        }

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_database_health(self) -> bool:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.error("Database health check failed: %s", exc)
            return False

    def check_cache_health(self) -> bool:
        try:
            key = f"health_check_{datetime.now().timestamp()}"
            cache.set(key, "test", 1)
            return cache.get(key) == "test"
        except Exception as exc:
            logger.error("Cache health check failed: %s", exc)
            return False

    def check_ai_system_health(self) -> bool:
        """Return True if ML dependencies + model file are usable."""
        try:
            from .config import config
            model_path = config.dispatch.ai_model_path

            if not os.path.exists(model_path):
                logger.info("No AI model found at %s", model_path)
                return self.can_train_simple_model()

            try:
                with open(model_path, "rb") as fh:
                    model = pickle.load(fh)
            except (pickle.UnpicklingError, EOFError) as exc:
                logger.warning("AI model corrupted: %s", exc)
                return False

            if not hasattr(model, "predict"):
                logger.warning("AI model has no predict() method")
                return False

            return True
        except Exception as exc:
            logger.error("AI health check failed: %s", exc)
            return False

    def can_train_simple_model(self) -> bool:
        """Cheap probe: can we import numpy + sklearn and fit a tiny model?"""
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestRegressor

            X = np.random.rand(10, 5)
            y = np.random.rand(10)
            model = RandomForestRegressor(n_estimators=5, random_state=42)
            model.fit(X, y)
            model.predict([[0.5] * 5])
            return True
        except ImportError as exc:
            logger.warning("ML dependencies missing: %s", exc)
            return False
        except Exception as exc:
            logger.warning("Simple model training probe failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------

    def check_overall_health(self) -> Dict:
        checks = {
            "database": self.check_database_health(),
            "cache": self.check_cache_health(),
            "ai_system": self.check_ai_system_health(),
            "timestamp": datetime.now().isoformat(),
        }

        self.health_status["ai_mode"] = checks["ai_system"]
        self.health_status["last_check"] = checks["timestamp"]

        if checks["database"] and checks["cache"]:
            self.health_status["simple_mode"] = True
            self.health_status["enhanced_mode"] = checks["ai_system"]
        else:
            self.health_status["simple_mode"] = False
            self.health_status["enhanced_mode"] = False

        checks["available_modes"] = self.get_available_modes()
        try:
            cache.set("dispatch_health_status", checks, 300)
        except Exception:
            pass
        return checks

    def get_available_modes(self) -> List[str]:
        modes = []
        if self.health_status["simple_mode"]:
            modes.append("simple")
        if self.health_status["ai_mode"]:
            modes.append("ai_optimizer")
        if self.health_status["enhanced_mode"]:
            modes.append("enhanced")
        return modes

    # ------------------------------------------------------------------
    # Failure tracking / fallback
    # ------------------------------------------------------------------

    def record_failure(self, mode: str) -> None:
        key = f"dispatch_failure_{mode}"
        try:
            count = cache.get(key, 0) + 1
            cache.set(key, count, self.FAILURE_WINDOW_SECONDS)
        except Exception:
            count = self.health_status["failure_count"] + 1
            self.health_status["failure_count"] = count
            return

        self.health_status["failure_count"] += 1
        if count >= 5:
            logger.warning("Too many failures for %s — disabling temporarily", mode)
            if mode == "ai_optimizer":
                self.health_status["ai_mode"] = False
            elif mode == "enhanced":
                self.health_status["enhanced_mode"] = False

    def should_fallback(self, mode: str) -> bool:
        if mode == "simple":
            return False
        try:
            count = cache.get(f"dispatch_failure_{mode}", 0)
        except Exception:
            count = 0
        return count >= self.MAX_FAILURES


health_checker = DispatchHealthChecker()


def get_dispatch_health() -> Dict:
    """Public helper: return the current health snapshot."""
    return health_checker.check_overall_health()