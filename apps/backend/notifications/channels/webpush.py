# apps/backend/notifications/channels/webpush.py

"""
Web Push Notification provider for Univa.

This provider sends push notifications to web browsers using the Web Push API.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class WebPushProvider:
    """
    Web Push API provider.

    Responsibilities:
        - Validate WebPush endpoints
        - Construct WebPush payloads
        - Send notifications via Web Push
        - Normalize responses
        - Identify permanent endpoint failures
    """

    # HTTP status codes that indicate permanent endpoint failure
    PERMANENT_STATUS_CODES = {
        404,  # Endpoint not found
        410,  # Endpoint gone
        403,  # Forbidden
    }

    def __init__(self):
        self.vapid_private_key = getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", "")
        self.vapid_public_key = getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", "")
        self.vapid_subject = getattr(settings, "WEBPUSH_VAPID_SUBJECT", "")
        self._initialized = bool(self.vapid_private_key and self.vapid_public_key)

    def send(self, notification, device) -> dict[str, Any]:
        """
        Send a UserNotification via Web Push.

        Returns a normalized result:
            {
                "success": True/False,
                "message": "...",
                "ticket_id": "...",
                "permanent": False,
                "error": "...",
            }
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "WebPush VAPID keys not configured",
                "permanent": True,
            }

        endpoint = self._get_endpoint(device)

        if not self.is_valid_endpoint(endpoint):
            return {
                "success": False,
                "error": "Invalid WebPush endpoint",
                "permanent": True,
            }

        try:
            # Try to import pywebpush
            from pywebpush import WebPusher, webpush

            payload = self.build_payload(notification)

            # Send the notification
            response = webpush(
                subscription_info={
                    "endpoint": endpoint,
                    "keys": self._get_keys(device),
                },
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims={
                    "sub": self.vapid_subject,
                    "aud": self._get_audience(endpoint),
                },
            )

            if response and response.status_code in [200, 201]:
                return {
                    "success": True,
                    "provider": "webpush",
                    "permanent": False,
                }
            else:
                status_code = getattr(response, "status_code", 0)
                permanent = status_code in self.PERMANENT_STATUS_CODES

                return {
                    "success": False,
                    "error": f"WebPush returned HTTP {status_code}",
                    "permanent": permanent,
                }

        except ImportError:
            return {
                "success": False,
                "error": "pywebpush library not installed",
                "permanent": True,
            }
        except Exception as exc:
            logger.exception("WebPush delivery failed: %s", exc)
            error_str = str(exc).lower()

            permanent = any(
                str(code) in error_str for code in self.PERMANENT_STATUS_CODES
            ) or "invalid" in error_str

            return {
                "success": False,
                "error": str(exc),
                "permanent": permanent,
            }

    @classmethod
    def is_valid_endpoint(cls, endpoint: str) -> bool:
        """Validate WebPush endpoint URL."""
        if not endpoint:
            return False

        endpoint = str(endpoint).strip()

        # Must be a valid HTTPS URL
        return endpoint.startswith("https://") and len(endpoint) > 10

    def _get_endpoint(self, device) -> str:
        """Extract WebPush endpoint from device."""
        endpoint = getattr(device, "device_token", "")
        return str(endpoint).strip()

    def _get_keys(self, device) -> dict[str, str]:
        """Extract VAPID keys from device metadata."""
        metadata = getattr(device, "metadata", {}) or {}
        provider_data = getattr(device, "provider_data", {}) or {}

        keys = {
            "p256dh": provider_data.get("p256dh", ""),
            "auth": provider_data.get("auth", ""),
        }

        # Also check metadata for backward compatibility
        if not keys["p256dh"]:
            keys["p256dh"] = metadata.get("p256dh", "")
        if not keys["auth"]:
            keys["auth"] = metadata.get("auth", "")

        return keys

    def _get_audience(self, endpoint: str) -> str:
        """Extract audience from endpoint URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(endpoint)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return "https://updates.push.services.mozilla.com"

    def build_payload(self, notification) -> dict[str, Any]:
        """Build WebPush payload."""
        metadata = dict(notification.metadata or {})

        payload = {
            "notification": {
                "title": notification.title,
                "body": notification.message,
                "icon": metadata.get("icon", "/static/icons/icon-192x192.png"),
                "badge": metadata.get("badge", "/static/icons/badge-72x72.png"),
                "tag": metadata.get("tag", str(notification.pk)),
                "data": {
                    "url": notification.action_url or "",
                    "notification_id": str(notification.pk),
                    "module": notification.module,
                    "notification_type": notification.notification_type,
                    "priority": notification.priority,
                    "metadata": metadata,
                },
                "requireInteraction": metadata.get("require_interaction", False),
                "vibrate": metadata.get("vibrate", [200, 100, 200]),
            }
        }

        return payload


__all__ = ["WebPushProvider"]