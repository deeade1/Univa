# payment/canonical/services/providers/paystack/client.py

"""
Thin HTTP wrapper around the Paystack API.

Owns:
    - authentication headers
    - timeouts
    - error normalization

Does NOT own:
    - translation to ProviderResult
    - business decisions about retries
    - lifecycle transitions
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

import requests
from django.conf import settings

from payment.canonical.services.providers.paystack.exceptions import (
    PaystackConfigurationError,
    PaystackRequestError,
    PaystackResponseError,
)


logger = logging.getLogger(__name__)


class PaystackClient:
    """Synchronous HTTP client for the Paystack API."""

    def __init__(
        self,
        *,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self._secret_key = (
            secret_key
            if secret_key is not None
            else getattr(settings, "PAYSTACK_SECRET_KEY", "")
        )
        self._base_url = (
            base_url
            or getattr(
                settings,
                "PAYSTACK_BASE_URL",
                "https://api.paystack.co",
            )
        ).rstrip("/")
        self._timeout = (
            timeout
            if timeout is not None
            else getattr(settings, "PAYSTACK_TIMEOUT_SECONDS", 15)
        )

    def _headers(self) -> Mapping[str, str]:
        if not self._secret_key:
            raise PaystackConfigurationError(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        return {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def post(
        self,
        path: str,
        *,
        json: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return self._request("POST", path, json=json)

    def get(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        return self._request("GET", path, params=params)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        url = f"{self._base_url}{path}"

        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Paystack request failed: %s %s",
                method,
                url,
                exc_info=True,
            )
            raise PaystackRequestError(str(exc)) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise PaystackRequestError(
                f"Paystack returned non-JSON response "
                f"(status={response.status_code})."
            ) from exc

        if not isinstance(body, Mapping):
            raise PaystackRequestError(
                "Paystack response was not a JSON object."
            )

        if response.status_code >= 400:
            message = body.get("message") or f"HTTP {response.status_code}"
            raise PaystackResponseError(str(message))

        if body.get("status") is False:
            message = body.get("message") or "Paystack reported failure."
            raise PaystackResponseError(str(message))

        return body