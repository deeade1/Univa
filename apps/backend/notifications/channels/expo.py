# apps/backend/notifications/channels/expo.py

"""
Expo Push Notification Provider.

This provider sends push notifications for NotificationDevice records
whose provider is "expo".

Expected Expo Push Token formats:

    ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]
    ExpoPushToken[xxxxxxxxxxxxxxxxxxxxxx]

This provider is intentionally independent of the legacy
push_notifications Django package.
"""

import logging
from typing import Optional

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class ExpoProvider:
    """
    Expo Push API provider.

    Responsibilities:

        - validate Expo push tokens
        - construct Expo notification payloads
        - send notifications to Expo
        - normalize Expo responses
        - identify permanent device-token failures
    """

    ENDPOINT = "https://exp.host/--/api/v2/push/send"

    DEFAULT_TIMEOUT = 10

    VALID_TOKEN_PREFIXES = (
        "ExponentPushToken[",
        "ExpoPushToken[",
    )

    # These are Expo error codes that may be returned by the API.
    # Only DeviceNotRegistered should normally cause the individual
    # NotificationDevice to be deactivated.
    DEVICE_PERMANENT_ERRORS = {
        "DeviceNotRegistered",
    }

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.endpoint = (
            endpoint
            or getattr(
                settings,
                "EXPO_PUSH_ENDPOINT",
                self.ENDPOINT,
            )
        )

        self.timeout = (
            timeout
            if timeout is not None
            else getattr(
                settings,
                "EXPO_PUSH_TIMEOUT",
                self.DEFAULT_TIMEOUT,
            )
        )

        self.access_token = getattr(
            settings,
            "EXPO_PUSH_ACCESS_TOKEN",
            "",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, notification, device):
        """
        Send a UserNotification to one Expo NotificationDevice.

        Returns a normalized result:

            {
                "success": True/False,
                "message": "...",
                "ticket_id": "...",
                "permanent": False,
                "error": "...",
            }
        """

        token = self._get_token(device)

        if not self.is_valid_token(token):
            return {
                "success": False,
                "error": "Invalid Expo push token.",
                "permanent": True,
            }

        payload = self.build_payload(
            notification=notification,
            device=device,
        )

        return self._send_payload(payload)

    # ------------------------------------------------------------------
    # Token handling
    # ------------------------------------------------------------------

    @classmethod
    def is_valid_token(cls, token):
        """
        Perform structural validation of an Expo push token.

        Valid examples:

            ExpoPushToken[xxxxxxxx]
            ExponentPushToken[xxxxxxxx]

        Invalid examples:

            ""
            None
            ExpoPushToken[]
            ExponentPushToken[]
            ExpoPushToken[abc
            InvalidToken[abc]
        """

        if not token:
            return False

        token = str(token).strip()

        for prefix in cls.VALID_TOKEN_PREFIXES:
            if not token.startswith(prefix):
                continue

            if not token.endswith("]"):
                return False

            token_body = token[len(prefix):-1].strip()

            return bool(token_body)

        return False

    @staticmethod
    def _get_token(device):
        """
        Extract and normalize the Expo token from NotificationDevice.
        """

        return str(
            device.device_token or ""
        ).strip()

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    def build_payload(self, notification, device):
        """
        Build an Expo Push API payload.

        Notification metadata is preserved inside `data` so the
        React Native / Expo client can use it for navigation and
        contextual behavior.
        """

        metadata = dict(
            notification.metadata or {}
        )

        data = {
            "notification_id": str(notification.pk),
            "module": notification.module,
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "action_url": notification.action_url or "",
            "metadata": metadata,
        }

        payload = {
            "to": self._get_token(device),
            "title": notification.title,
            "body": notification.message,
            "data": data,
            "sound": "default",
            "priority": self._map_priority(
                notification.priority
            ),
        }

        # --------------------------------------------------------------
        # Badge
        # --------------------------------------------------------------

        badge = self._get_badge(notification)

        if badge is not None:
            payload["badge"] = badge

        # --------------------------------------------------------------
        # Android notification channel
        # --------------------------------------------------------------

        channel_id = metadata.get(
            "android_channel_id"
        )

        if channel_id:
            payload["channelId"] = str(channel_id)

        # --------------------------------------------------------------
        # Notification category
        # --------------------------------------------------------------

        category_id = metadata.get(
            "category_id"
        )

        if category_id:
            payload["categoryId"] = str(category_id)

        # --------------------------------------------------------------
        # Optional TTL
        # --------------------------------------------------------------

        ttl = metadata.get("ttl")

        if ttl is not None:
            try:
                ttl = int(ttl)

                if ttl >= 0:
                    payload["ttl"] = ttl

            except (TypeError, ValueError):
                logger.warning(
                    "Invalid Expo TTL for notification %s: %r",
                    notification.pk,
                    ttl,
                )

        return payload

    # ------------------------------------------------------------------
    # Priority
    # ------------------------------------------------------------------

    @staticmethod
    def _map_priority(priority):
        """
        Convert Univa notification priority to Expo priority.
        """

        priority = str(
            priority or ""
        ).lower()

        if priority in {
            "urgent",
            "high",
        }:
            return "high"

        if priority == "low":
            return "low"

        return "default"

    # ------------------------------------------------------------------
    # Badge
    # ------------------------------------------------------------------

    @staticmethod
    def _get_badge(notification):
        """
        Return an optional badge value from notification metadata.
        """

        metadata = notification.metadata or {}

        badge = metadata.get("badge")

        if badge is None:
            return None

        try:
            badge = int(badge)
        except (TypeError, ValueError):
            return None

        return max(0, badge)

    # ------------------------------------------------------------------
    # HTTP delivery
    # ------------------------------------------------------------------

    def _send_payload(self, payload):
        """
        Send the payload to Expo's Push API.
        """

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }

        # --------------------------------------------------------------
        # Optional Expo access token
        # --------------------------------------------------------------

        if self.access_token:
            headers["Authorization"] = (
                f"Bearer {self.access_token}"
            )

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

        except requests.Timeout:
            logger.warning(
                "Expo push request timed out."
            )

            return {
                "success": False,
                "error": "Expo push request timed out.",
                "permanent": False,
            }

        except requests.RequestException as exc:
            logger.exception(
                "Expo push request failed."
            )

            return {
                "success": False,
                "error": str(exc),
                "permanent": False,
            }

        return self._parse_response(response)

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    def _parse_response(self, response):
        """
        Normalize an Expo HTTP response.
        """

        try:
            body = response.json()

        except ValueError:
            body = None

        # --------------------------------------------------------------
        # HTTP failure
        # --------------------------------------------------------------

        if not response.ok:
            error = self._extract_error(
                body,
                default=(
                    f"Expo returned HTTP "
                    f"{response.status_code}."
                ),
            )

            return {
                "success": False,
                "error": error,
                "permanent": False,
            }

        # --------------------------------------------------------------
        # Invalid response body
        # --------------------------------------------------------------

        if not isinstance(body, dict):
            return {
                "success": False,
                "error": (
                    "Expo returned an invalid response."
                ),
                "permanent": False,
            }

        # --------------------------------------------------------------
        # Extract push ticket
        # --------------------------------------------------------------

        ticket = self._extract_ticket(body)

        if ticket is None:
            error = self._extract_error(
                body,
                default=(
                    "Expo did not return a push ticket."
                ),
            )

            return {
                "success": False,
                "error": error,
                "permanent": False,
            }

        # --------------------------------------------------------------
        # Ticket status
        # --------------------------------------------------------------

        ticket_status = str(
            ticket.get("status", "")
        ).lower()

        if ticket_status == "ok":
            return {
                "success": True,
                "message": (
                    "Expo accepted the notification."
                ),
                "ticket_id": ticket.get("id"),
                "permanent": False,
                "ticket": ticket,
            }

        # --------------------------------------------------------------
        # Ticket error
        # --------------------------------------------------------------

        details = ticket.get(
            "details"
        )

        if not isinstance(details, dict):
            details = {}

        error_code = details.get(
            "error"
        )

        error_message = (
            ticket.get("message")
            or error_code
            or "Expo rejected the notification."
        )

        return {
            "success": False,
            "error": error_message,
            "permanent": (
                error_code
                in self.DEVICE_PERMANENT_ERRORS
            ),
            "error_code": error_code,
            "ticket": ticket,
        }

    # ------------------------------------------------------------------
    # Ticket extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_ticket(body):
        """
        Extract the first Expo push ticket.

        Expo may return:

            {
                "data": {
                    "status": "ok",
                    "id": "..."
                }
            }

        or:

            {
                "data": [
                    {
                        "status": "ok",
                        "id": "..."
                    }
                ]
            }
        """

        data = body.get("data")

        if isinstance(data, dict):
            return data

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return item

        return None

    # ------------------------------------------------------------------
    # Error extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_error(
        body,
        default="Expo notification failed.",
    ):
        """
        Extract a useful error message from an Expo response.
        """

        if not isinstance(body, dict):
            return default

        # --------------------------------------------------------------
        # errors: [...]
        # --------------------------------------------------------------

        errors = body.get("errors")

        if isinstance(errors, list) and errors:
            first_error = errors[0]

            if isinstance(first_error, dict):
                return (
                    first_error.get("message")
                    or first_error.get("code")
                    or default
                )

            return str(first_error)

        # --------------------------------------------------------------
        # error: {...}
        # --------------------------------------------------------------

        error = body.get("error")

        if isinstance(error, dict):
            return (
                error.get("message")
                or error.get("code")
                or default
            )

        if error:
            return str(error)

        # --------------------------------------------------------------
        # message
        # --------------------------------------------------------------

        message = body.get("message")

        if message:
            return str(message)

        return default

