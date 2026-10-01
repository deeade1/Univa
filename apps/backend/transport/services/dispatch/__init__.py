"""
Canonical dispatch system.

Public API:
    get_dispatcher()                — sync DispatchService (singleton)
    get_dispatcher_with_fallback()  — EnhancedUnifiedDispatcher (singleton, async)
    get_dispatch_health()           — health snapshot dict
    DispatchService                 — direct class access
    EnhancedUnifiedDispatcher       — direct class access
    DispatchHealthChecker           — direct class access
    AIService                       — ML wrapper
    AIDispatchOptimizer             — batch dispatcher
"""

from .base import BaseService
from .config import config, DispatchConfig
from .health import DispatchHealthChecker, get_dispatch_health
from .ai_service import AIService
from .ai_optimizer import AIDispatchOptimizer, DispatchAssignment
from .dispatch import DispatchService
from .unified_dispatchs import EnhancedUnifiedDispatcher


_sync_dispatcher = None
_async_dispatcher = None


def get_dispatcher() -> DispatchService:
    """Return a process-wide DispatchService singleton."""
    global _sync_dispatcher
    if _sync_dispatcher is None:
        _sync_dispatcher = DispatchService()
        _sync_dispatcher.initialize()
    return _sync_dispatcher


def get_dispatcher_with_fallback() -> EnhancedUnifiedDispatcher:
    """Return a process-wide EnhancedUnifiedDispatcher singleton."""
    global _async_dispatcher
    if _async_dispatcher is None:
        _async_dispatcher = EnhancedUnifiedDispatcher()
    return _async_dispatcher


__all__ = [
    "BaseService",
    "DispatchConfig",
    "config",
    "DispatchHealthChecker",
    "get_dispatch_health",
    "AIService",
    "AIDispatchOptimizer",
    "DispatchAssignment",
    "DispatchService",
    "EnhancedUnifiedDispatcher",
    "get_dispatcher",
    "get_dispatcher_with_fallback",
]