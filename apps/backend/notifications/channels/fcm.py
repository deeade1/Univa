# apps/backend/notifications/channels/fcm.py

"""
Firebase Cloud Messaging (FCM) provider for Univa.

This provider sends push notifications to Android and iOS devices via FCM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class FCMProvider:
    """
    Firebase Cloud Messaging provider.

    Responsibilities:
        - Validate FCM tokens
        - Construct FCM payloads
        - Send notifications to FCM
        - Normalize FCM responses
        - Identify permanent device-token failures
    """

    # FCM error codes that indicate permanent device failure
    PERMANENT_ERRORS = {
        "NotRegistered",
        "InvalidRegistration",
        "RegistrationTokenNotRegistered",
        "InvalidToken",
        "MismatchedSenderId",
        "InvalidPackageName",
    }

    def __init__(self):
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize FCM client."""
        try:
            # Try to import firebase-admin
            import firebase_admin
            from firebase_admin import credentials, messaging

            # Load credentials
            cred_path = getattr(settings, "FCM_CREDENTIALS_PATH", "")
            if cred_path:
                cred = credentials.Certificate(cred_path)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)

            self.messaging = messaging
            self._initialized = True

        except ImportError:
            logger.debug("Firebase Admin SDK not installed")
            self.messaging = None
            self._initialized = False
        except Exception as exc:
            logger.warning("FCM initialization failed: %s", exc)
            self.messaging = None
            self._initialized = False

    def send(self, notification, device) -> dict[str, Any]:
        """
        Send a UserNotification to one FCM device.

        Returns a normalized result:
            {
                "success": True/False,
                "message": "...",
                "ticket_id": "...",
                "permanent": False,
                "error": "...",
            }
        """
        if not self._initialized or not self.messaging:
            return {
                "success": False,
                "error": "FCM client not initialized",
                "permanent": True,
            }

        token = self._get_token(device)

        if not self.is_valid_token(token):
            return {
                "success": False,
                "error": "Invalid FCM token",
                "permanent": True,
            }

        try:
            message = self.build_message(notification, device)

            # Send the message
            response = self.messaging.send(message)

            if response:
                return {
                    "success": True,
                    "provider": "fcm",
                    "ticket_id": response,
                    "permanent": False,
                }
            else:
                return {
                    "success": False,
                    "error": "FCM returned empty response",
                    "permanent": False,
                }

        except Exception as exc:
            logger.exception("FCM delivery failed: %s", exc)
            error_str = str(exc).lower()

            # Check if this is a permanent error
            permanent = any(
                err.lower() in error_str for err in self.PERMANENT_ERRORS
            ) or "invalid" in error_str

            return {
                "success": False,
                "error": str(exc),
                "permanent": permanent,
            }

    @classmethod
    def is_valid_token(cls, token: str) -> bool:
        """Validate FCM token format."""
        if not token:
            return False

        token = str(token).strip()

        # FCM tokens are typically long alphanumeric strings
        # Basic validation: not empty and contains alphanumeric characters
        return len(token) > 20 and all(c.isalnum() or c in ":_-" for c in token)

    def _get_token(self, device) -> str:
        """Extract FCM token from device."""
        token = getattr(device, "device_token", "")
        return str(token).strip()

    def build_message(self, notification, device) -> Any:
        """Build FCM message."""
        from firebase_admin import messaging

        metadata = dict(notification.metadata or {})

        # Build notification
        fcm_notification = messaging.Notification(
            title=notification.title,
            body=notification.message,
            image=metadata.get("image_url"),
        )

        # Build data
        data = {
            "notification_id": str(notification.pk),
            "module": notification.module,
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "action_url": notification.action_url or "",
            "click_action": metadata.get("click_action", ""),
        }

        # Add metadata as JSON string
        data["metadata"] = json.dumps(metadata)

        # Build message
        message = messaging.Message(
            token=self._get_token(device),
            notification=fcm_notification,
            data=data,
            android=self._get_android_config(notification, metadata),
            apns=self._get_apns_config(notification, metadata),
            webpush=self._get_webpush_config(notification, metadata),
        )

        return message

    def _get_android_config(self, notification, metadata) -> Any:
        """Build Android-specific config."""
        from firebase_admin import messaging

        priority = (
            messaging.Priority.HIGH
            if notification.priority in ["high", "urgent"]
            else messaging.Priority.NORMAL
        )

        android_config = messaging.AndroidConfig(
            priority=priority,
            ttl=metadata.get("ttl", 86400),
            notification=messaging.AndroidNotification(
                title=notification.title,
                body=notification.message,
                icon=metadata.get("android_icon", ""),
                sound=metadata.get("android_sound", "default"),
                channel_id=metadata.get("android_channel_id", "default"),
            ),
        )

        return android_config

    def _get_apns_config(self, notification, metadata) -> Any:
        """Build APNs-specific config (for iOS via FCM)."""
        from firebase_admin import messaging

        apns_config = messaging.APNSConfig(
            headers={"apns-priority": "10" if notification.priority in ["high", "urgent"] else "5"},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound=metadata.get("ios_sound", "default"),
                    badge=metadata.get("badge", 0),
                    category=metadata.get("category_id", ""),
                    content_available=metadata.get("content_available", False),
                ),
            ),
        )

        return apns_config

    def _get_webpush_config(self, notification, metadata) -> Any:
        """Build WebPush-specific config."""
        from firebase_admin import messaging

        webpush_config = messaging.WebpushConfig(
            headers={"TTL": str(metadata.get("ttl", 86400))},
            notification=messaging.WebpushNotification(
                title=notification.title,
                body=notification.message,
                icon=metadata.get("webpush_icon", "/static/icons/icon-192x192.png"),
            ),
        )

        return webpush_config


__all__ = ["FCMProvider"]