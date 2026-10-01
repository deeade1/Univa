# apps/backend/notifications/channels/apns.py

"""
Apple Push Notification Service (APNs) provider for Univa.

This provider sends push notifications to iOS devices using Apple's APNs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class APNsProvider:
    """
    Apple Push Notification Service provider.

    Responsibilities:
        - Validate APNs tokens
        - Construct APNs payloads
        - Send notifications to APNs
        - Normalize APNs responses
        - Identify permanent device-token failures
    """

    # APNs error codes that indicate permanent device failure
    PERMANENT_ERRORS = {
        410,  # Device token no longer active
        400,  # Bad request (invalid token format)
        403,  # Invalid token
        404,  # Not found
    }

    def __init__(self):
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize APNs client."""
        try:
            # Try to import and initialize APNs client
            # Using django-push-notifications or pyapns
            from apns2.client import APNsClient
            from apns2.payload import Payload

            self.client_class = APNsClient
            self.payload_class = Payload

            # Load credentials
            self.team_id = getattr(settings, "APNS_TEAM_ID", "")
            self.bundle_id = getattr(settings, "APNS_BUNDLE_ID", "")
            self.key_id = getattr(settings, "APNS_KEY_ID", "")
            self.auth_key_path = getattr(settings, "APNS_AUTH_KEY_PATH", "")

            self.use_sandbox = getattr(settings, "APNS_USE_SANDBOX", False)

            if self.team_id and self.bundle_id and self.key_id and self.auth_key_path:
                self._client = APNsClient(
                    auth_key_path=self.auth_key_path,
                    auth_key_id=self.key_id,
                    team_id=self.team_id,
                    bundle_id=self.bundle_id,
                    use_sandbox=self.use_sandbox,
                )
            else:
                logger.warning("APNs credentials not fully configured")

        except ImportError:
            logger.debug("APNs library not installed (apns2)")
            self.client_class = None
            self.payload_class = None
            self._client = None

    def send(self, notification, device) -> dict[str, Any]:
        """
        Send a UserNotification to one APNs device.

        Returns a normalized result:
            {
                "success": True/False,
                "message": "...",
                "ticket_id": "...",
                "permanent": False,
                "error": "...",
            }
        """
        if not self._client:
            return {
                "success": False,
                "error": "APNs client not initialized",
                "permanent": True,
            }

        token = self._get_token(device)

        if not self.is_valid_token(token):
            return {
                "success": False,
                "error": "Invalid APNs token",
                "permanent": True,
            }

        payload = self.build_payload(notification, device)

        try:
            response = self._client.send_notification(
                token,
                payload,
                topic=self.bundle_id,
            )

            if response:
                return {
                    "success": True,
                    "provider": "apns",
                    "ticket_id": response.get("apns_id", ""),
                    "permanent": False,
                }
            else:
                return {
                    "success": False,
                    "error": "APNs returned empty response",
                    "permanent": False,
                }

        except Exception as exc:
            logger.exception("APNs delivery failed: %s", exc)
            error_str = str(exc).lower()

            # Check if this is a permanent error
            permanent = any(
                str(code) in error_str for code in self.PERMANENT_ERRORS
            ) or "invalid" in error_str

            return {
                "success": False,
                "error": str(exc),
                "permanent": permanent,
            }

    @classmethod
    def is_valid_token(cls, token: str) -> bool:
        """Validate APNs token format."""
        if not token:
            return False

        token = str(token).strip()

        # APNs tokens are 64-character hex strings
        if len(token) != 64:
            return False

        try:
            int(token, 16)
            return True
        except ValueError:
            return False

    def _get_token(self, device) -> str:
        """Extract APNs token from device."""
        token = getattr(device, "device_token", "")
        return str(token).strip()

    def build_payload(self, notification, device) -> dict[str, Any]:
        """Build APNs payload."""
        metadata = dict(notification.metadata or {})

        # Build alert
        alert = {
            "title": notification.title,
            "body": notification.message,
        }

        # Add subtitle if available
        if "subtitle" in metadata:
            alert["subtitle"] = metadata["subtitle"]

        # Build payload
        payload = {
            "aps": {
                "alert": alert,
                "sound": self._get_sound(notification),
                "badge": self._get_badge(notification),
                "category": metadata.get("category_id", ""),
            }
        }

        # Add custom data
        custom_data = {
            "notification_id": str(notification.pk),
            "module": notification.module,
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "action_url": notification.action_url or "",
            "metadata": metadata,
        }

        payload["data"] = custom_data

        # Thread ID for grouping
        if "thread_id" in metadata:
            payload["aps"]["thread-id"] = metadata["thread_id"]

        return payload

    def _get_sound(self, notification) -> str:
        """Get sound from metadata or default."""
        metadata = dict(notification.metadata or {})
        sound = metadata.get("sound", "default")
        return str(sound)

    def _get_badge(self, notification) -> int | None:
        """Get badge count from metadata."""
        metadata = dict(notification.metadata or {})
        badge = metadata.get("badge")

        if badge is None:
            return None

        try:
            return max(0, int(badge))
        except (TypeError, ValueError):
            return None


__all__ = ["APNsProvider"]