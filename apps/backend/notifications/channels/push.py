# apps/backend/notifications/channels/push.py

"""
Push notification channel for Univa.

This module is responsible for:

    - selecting the correct push provider
    - delegating delivery to the provider
    - normalizing provider responses
    - distinguishing retryable failures from permanent failures

This module does NOT:

    - dispatch Celery tasks
    - retry Celery tasks
    - create NotificationPush records
    - create UserNotification records
    - manage notification preferences

Provider implementations live in:

    notifications.channels.expo
    notifications.channels.fcm
    notifications.channels.apns
    notifications.channels.webpush

Celery orchestration lives in:

    notifications.tasks.push
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from .apns import APNsProvider
from .expo import ExpoProvider
from .fcm import FCMProvider
from .webpush import WebPushProvider

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

PROVIDER_EXPO = "expo"
PROVIDER_FCM = "fcm"
PROVIDER_APNS = "apns"
PROVIDER_WEBPUSH = "webpush"


SUPPORTED_PROVIDERS = {
    PROVIDER_EXPO,
    PROVIDER_FCM,
    PROVIDER_APNS,
    PROVIDER_WEBPUSH,
}


# ============================================================================
# EXCEPTIONS
# ============================================================================


class PushChannelError(Exception):
    """Base exception for push-channel failures."""


class RetryablePushError(PushChannelError):
    """
    A temporary push failure.

    The Celery task should retry delivery.
    """


class PermanentPushError(PushChannelError):
    """
    A permanent push failure.

    The Celery task must not repeatedly retry this delivery.
    """


class UnsupportedPushProviderError(PermanentPushError):
    """Raised when a device specifies an unsupported provider."""


# ============================================================================
# RESULT
# ============================================================================


@dataclass(slots=True)
class PushResult:
    """
    Normalized push delivery result.

    Attributes:
        success:
            Whether the provider accepted the notification.

        retryable:
            Whether the failure may succeed if retried.

        permanent:
            Whether the failure should not be retried.

        provider:
            Provider responsible for delivery.

        provider_message_id:
            Provider-generated ticket/message identifier.

        error:
            Human-readable error message.

        error_code:
            Provider-specific error code, when available.

        raw:
            Original normalized provider response.
    """

    success: bool
    retryable: bool = False
    permanent: bool = False
    provider: str = ""
    provider_message_id: str | None = None
    error: str = ""
    error_code: str | None = None
    raw: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return {
            "success": self.success,
            "retryable": self.retryable,
            "permanent": self.permanent,
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "error": self.error,
            "error_code": self.error_code,
            "raw": self.raw or {},
        }


# ============================================================================
# CHANNEL
# ============================================================================


class PushChannel:
    """
    Unified push notification channel.

    Provider selection is based on:

        NotificationDevice.provider
    """

    def __init__(self) -> None:
        self._providers = {
            PROVIDER_EXPO: ExpoProvider(),
            PROVIDER_FCM: FCMProvider(),
            PROVIDER_APNS: APNsProvider(),
            PROVIDER_WEBPUSH: WebPushProvider(),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_to_device(
        self,
        *,
        notification,
        device,
    ) -> dict[str, Any]:
        """
        Deliver one notification to one device.

        Returns a normalized dictionary suitable for the task/service
        layer.

        Provider exceptions are classified here so the Celery task can
        make the retry decision.
        """

        provider_name = self._normalize_provider(
            device.provider
        )

        if not provider_name:
            return self._permanent_result(
                provider="",
                error="Notification device has no push provider.",
                error_code="MISSING_PROVIDER",
            )

        if provider_name not in SUPPORTED_PROVIDERS:
            return self._permanent_result(
                provider=provider_name,
                error=f"Unsupported push provider: {provider_name}",
                error_code="UNSUPPORTED_PROVIDER",
            )

        provider = self._get_provider(
            provider_name
        )

        try:
            response = provider.send(
                notification=notification,
                device=device,
            )

        except PermanentPushError as exc:
            logger.warning(
                "Permanent push failure: notification=%s device=%s provider=%s error=%s",
                notification.pk,
                device.pk,
                provider_name,
                exc,
            )

            return self._permanent_result(
                provider=provider_name,
                error=str(exc),
            )

        except RetryablePushError as exc:
            logger.warning(
                "Retryable push failure: notification=%s device=%s provider=%s error=%s",
                notification.pk,
                device.pk,
                provider_name,
                exc,
            )

            return self._retryable_result(
                provider=provider_name,
                error=str(exc),
            )

        except Exception as exc:
            logger.exception(
                "Unexpected push provider failure: notification=%s device=%s provider=%s",
                notification.pk,
                device.pk,
                provider_name,
            )

            return self._retryable_result(
                provider=provider_name,
                error=str(exc),
                error_code="PROVIDER_EXCEPTION",
            )

        return self._normalize_provider_response(
            provider_name=provider_name,
            response=response,
        )

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------

    def _get_provider(
        self,
        provider_name: str,
    ):
        """
        Resolve the provider implementation.

        Additional providers can be registered here without changing
        the Celery task.
        """

        provider = self._providers.get(
            provider_name
        )

        if provider is None:
            raise UnsupportedPushProviderError(
                f"Unsupported push provider: {provider_name}"
            )

        return provider

    @staticmethod
    def _normalize_provider(
        provider: str | None,
    ) -> str:
        """Normalize provider names."""

        if not provider:
            return ""

        return str(provider).strip().lower()

    # =========================================================================
    # RESPONSE NORMALIZATION
    # =========================================================================

    def _normalize_provider_response(
        self,
        *,
        provider_name: str,
        response: Any,
    ) -> dict[str, Any]:
        """
        Convert a provider response into the common PushResult format.
        """

        if isinstance(response, PushResult):
            result = response

            if not result.provider:
                result.provider = provider_name

            return result.as_dict()

        if not isinstance(response, dict):
            return self._retryable_result(
                provider=provider_name,
                error="Push provider returned an invalid response.",
                error_code="INVALID_PROVIDER_RESPONSE",
            )

        success = bool(
            response.get("success")
        )

        provider_message_id = (
            response.get("provider_message_id")
            or response.get("ticket_id")
            or response.get("message_id")
        )

        error = str(
            response.get("error")
            or response.get("error_message")
            or ""
        )

        error_code = (
            response.get("error_code")
            or response.get("code")
        )

        permanent = bool(
            response.get("permanent")
        )

        retryable = bool(
            response.get("retryable")
        )

        # --------------------------------------------------------------
        # Successful provider response
        # --------------------------------------------------------------

        if success:
            return {
                "success": True,
                "retryable": False,
                "permanent": False,
                "provider": provider_name,
                "provider_message_id": (
                    str(provider_message_id)
                    if provider_message_id
                    else None
                ),
                "error": "",
                "error_code": error_code,
                "raw": response,
            }

        # --------------------------------------------------------------
        # Explicit permanent failure
        # --------------------------------------------------------------

        if permanent:
            return self._permanent_result(
                provider=provider_name,
                error=(
                    error
                    or "Push provider rejected the notification permanently."
                ),
                error_code=error_code,
                raw=response,
                provider_message_id=provider_message_id,
            )

        # --------------------------------------------------------------
        # Explicit retryable failure
        # --------------------------------------------------------------

        if retryable:
            return self._retryable_result(
                provider=provider_name,
                error=(
                    error
                    or "Push provider returned a retryable failure."
                ),
                error_code=error_code,
                raw=response,
                provider_message_id=provider_message_id,
            )

        # --------------------------------------------------------------
        # Default:
        #
        # Unknown provider failures are treated as retryable.
        #
        # This prevents transient network/provider failures from
        # accidentally becoming permanent.
        # --------------------------------------------------------------

        return self._retryable_result(
            provider=provider_name,
            error=(
                error
                or "Push provider returned an unsuccessful response."
            ),
            error_code=error_code,
            raw=response,
            provider_message_id=provider_message_id,
        )

    # =========================================================================
    # RESULT HELPERS
    # =========================================================================

    @staticmethod
    def _successful_result(
        *,
        provider: str,
        provider_message_id: str | None = None,
        raw: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Construct a successful result."""

        return PushResult(
            success=True,
            retryable=False,
            permanent=False,
            provider=provider,
            provider_message_id=(
                str(provider_message_id)
                if provider_message_id
                else None
            ),
            raw=raw,
        ).as_dict()

    @staticmethod
    def _retryable_result(
        *,
        provider: str,
        error: str,
        error_code: str | None = None,
        raw: dict[str, Any] | None = None,
        provider_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Construct a retryable failure result."""

        return PushResult(
            success=False,
            retryable=True,
            permanent=False,
            provider=provider,
            provider_message_id=(
                str(provider_message_id)
                if provider_message_id
                else None
            ),
            error=str(error),
            error_code=error_code,
            raw=raw,
        ).as_dict()

    @staticmethod
    def _permanent_result(
        *,
        provider: str,
        error: str,
        error_code: str | None = None,
        raw: dict[str, Any] | None = None,
        provider_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Construct a permanent failure result."""

        return PushResult(
            success=False,
            retryable=False,
            permanent=True,
            provider=provider,
            provider_message_id=(
                str(provider_message_id)
                if provider_message_id
                else None
            ),
            error=str(error),
            error_code=error_code,
            raw=raw,
        ).as_dict()


# ============================================================================
# FUNCTIONAL API
# ============================================================================


def send_push(
    push,
) -> dict[str, Any]:
    """
    Compatibility helper for the Celery task.

    The task passes a NotificationPush instance.

    Provider delivery is delegated to PushChannel.
    """

    notification = push.notification
    device = push.device

    channel = PushChannel()

    result = channel.send_to_device(
        notification=notification,
        device=device,
    )

    # ------------------------------------------------------------------
    # Persist successful provider information.
    #
    # State transitions themselves remain owned by the service layer.
    # ------------------------------------------------------------------

    if result.get("provider"):
        push.provider = result["provider"]

    provider_message_id = result.get(
        "provider_message_id"
    )

    if provider_message_id:
        push.provider_message_id = str(
            provider_message_id
        )

    if result.get("success"):
        push.status = push.PushStatus.SENT
        push.sent_at = timezone.now()
        push.error_message = ""

        push.save(
            update_fields=[
                "status",
                "sent_at",
                "error_message",
                "provider",
                "provider_message_id",
                "updated_at",
            ]
        )

    elif result.get("permanent"):
        push.status = push.PushStatus.FAILED
        push.error_message = str(
            result.get("error")
            or "Permanent push delivery failure."
        )[:10000]

        push.save(
            update_fields=[
                "status",
                "error_message",
                "provider",
                "provider_message_id",
                "updated_at",
            ]
        )

    else:
        push.error_message = str(
            result.get("error")
            or "Retryable push delivery failure."
        )[:10000]

        push.save(
            update_fields=[
                "error_message",
                "provider",
                "provider_message_id",
                "updated_at",
            ]
        )

    return result


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "PushChannel",
    "PushResult",
    "PushChannelError",
    "RetryablePushError",
    "PermanentPushError",
    "UnsupportedPushProviderError",
    "send_push",
]