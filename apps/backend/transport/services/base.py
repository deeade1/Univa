"""Base class for configurable dispatch services."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseService:
    """Minimal lifecycle + config plumbing for services."""

    def __init__(self, config_prefix: str = ""):
        self.config_prefix = config_prefix
        self._initialized = False
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        try:
            from .config import config
            self._config = config.get_section(self.config_prefix) or {}
        except Exception:
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def is_initialized(self) -> bool:
        return self._initialized

    def health_check(self) -> Dict[str, Any]:
        return {"initialized": self._initialized}

    def _log_operation(self, operation: str, **kwargs) -> None:
        logger.debug("op=%s %s", operation, kwargs)

    def _log_error(self, operation: str, error: Exception, **kwargs) -> None:
        logger.error("op=%s error=%s %s", operation, error, kwargs)