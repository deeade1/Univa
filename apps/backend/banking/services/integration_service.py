# apps/backend/banking/services/integration_service.py

"""
Integration service.

Handles HTTP communication with configured payment-processor and bank
integrations. Every request is persisted as an APITransactionLog row.

Two layers:

    IntegrationClient
        Generic HTTP client for a BankAPIIntegration. One instance per
        integration. Owns the requests.Session and the logging.

    BankAPIIntegrationService
        Orchestration on top of IntegrationClient: name enquiry,
        transfers, and connection tests. Chosen by the mutations layer.

Nothing here posts to the ledger. These are external API operations
only. If a transfer results in a money movement, the caller
(banking_orchestrator, etc.) is responsible for the ledger posting.
"""

from __future__ import annotations

import logging
import uuid

import requests
from django.core.exceptions import ValidationError
from django.utils import timezone

from banking.models.integrations import (
    BankAPIIntegration,
    APITransactionLog,
)

logger = logging.getLogger(__name__)


class IntegrationClient:
    """Generic HTTP client for a single BankAPIIntegration."""

    def __init__(self, integration: BankAPIIntegration):
        if integration is None or integration.pk is None:
            raise ValidationError("Integration is required.")
        if not integration.is_active:
            raise ValidationError(
                f"Integration {integration.name} is not active."
            )
        self.integration = integration
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Name enquiry
    # ------------------------------------------------------------------

    def name_enquiry(self, *, account_number: str, bank_code: str) -> dict:
        endpoint = f"{self.integration.base_url}/name_enquiry"
        payload = {
            "account_number": account_number,
            "bank_code": bank_code,
            "reference": f"ENQ-{uuid.uuid4().hex[:12].upper()}",
        }
        return self._request("POST", endpoint, payload)

    # ------------------------------------------------------------------
    # Transfer
    # ------------------------------------------------------------------

    def transfer_funds(
        self,
        *,
        from_account: str,
        to_account: str,
        amount,
        narration: str,
    ) -> dict:
        endpoint = f"{self.integration.base_url}/transfer"
        payload = {
            "source_account": from_account,
            "destination_account": to_account,
            "amount": str(amount),
            "narration": narration,
            "reference": (
                f"TF-{timezone.now().strftime('%Y%m%d')}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            ),
            "currency": "NGN",
        }
        return self._request("POST", endpoint, payload)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> dict:
        endpoint = f"{self.integration.base_url}/ping"
        try:
            return self._request("GET", endpoint, None)
        except Exception:
            endpoint = f"{self.integration.base_url}/health"
            return self._request("GET", endpoint, None)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _request(self, method: str, endpoint: str, data) -> dict:
        reference = (
            data.get("reference", str(uuid.uuid4()))
            if isinstance(data, dict)
            else str(uuid.uuid4())
        )

        api_log = APITransactionLog.objects.create(
            integration=self.integration,
            endpoint=endpoint,
            method=method,
            request_body=data or {},
            response_body={},
            http_status=0,
            started_at=timezone.now(),
            reference=reference,
        )

        headers = {
            "Authorization": f"Bearer {self.integration.api_key}",
            "Content-Type": "application/json",
        }
        if self.integration.provider == "PAYSTACK":
            headers["Authorization"] = (
                f"Bearer {self.integration.secret_key}"
            )

        try:
            response = self.session.request(
                method=method,
                url=endpoint,
                json=data,
                headers=headers,
                timeout=30,
            )
        except Exception as exc:
            api_log.completed_at = timezone.now()
            api_log.error_message = str(exc)
            api_log.http_status = 500
            api_log.is_successful = False
            api_log.response_body = {"error": str(exc)}
            api_log.save()

            self.integration.record_request(successful=False)
            raise

        api_log.completed_at = timezone.now()
        api_log.duration_ms = (
            api_log.completed_at - api_log.started_at
        ).total_seconds() * 1000
        api_log.http_status = response.status_code

        try:
            api_log.response_body = response.json()
        except ValueError:
            api_log.response_body = {"raw_response": response.text}

        api_log.is_successful = response.status_code in (200, 201)
        if not api_log.is_successful:
            api_log.error_message = response.text
        api_log.save()

        self.integration.record_request(
            successful=api_log.is_successful,
            duration_ms=api_log.duration_ms,
        )

        return {
            "success": api_log.is_successful,
            "data": api_log.response_body,
            "reference": api_log.reference,
            "external_reference": (
                api_log.response_body.get("reference")
                if isinstance(api_log.response_body, dict)
                else None
            ),
            "log": api_log,
        }


class BankAPIIntegrationService:
    """Orchestration over IntegrationClient."""

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    @staticmethod
    def get_integration(
        provider_name: str | None = None,
    ) -> BankAPIIntegration:
        """
        Return the requested integration, or the default active one.

        Raises ValidationError if none found.
        """
        if provider_name:
            integration = BankAPIIntegration.objects.filter(
                provider=provider_name,
                is_active=True,
            ).first()
            if integration is None:
                raise ValidationError(
                    f"No active integration for provider {provider_name}."
                )
            return integration

        integration = BankAPIIntegration.objects.filter(
            is_default=True,
            is_active=True,
        ).first()
        if integration is None:
            raise ValidationError(
                "No default active integration configured."
            )
        return integration

    @staticmethod
    def client_for(
        provider_name: str | None = None,
    ) -> IntegrationClient:
        return IntegrationClient(
            BankAPIIntegrationService.get_integration(provider_name)
        )

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    @staticmethod
    def name_enquiry(
        *,
        account_number: str,
        bank_code: str,
        provider_name: str | None = None,
    ) -> dict:
        client = BankAPIIntegrationService.client_for(provider_name)
        return client.name_enquiry(
            account_number=account_number,
            bank_code=bank_code,
        )

    @staticmethod
    def transfer_funds(
        *,
        from_account: str,
        to_account: str,
        amount,
        narration: str,
        provider_name: str | None = None,
    ) -> dict:
        client = BankAPIIntegrationService.client_for(provider_name)
        return client.transfer_funds(
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            narration=narration,
        )

    @staticmethod
    def test_connection(
        integration: BankAPIIntegration,
    ) -> tuple[bool, str]:
        """
        Fire a lightweight request and return (success, message).
        """
        if not integration.is_active:
            return False, "Integration is not active."

        try:
            client = IntegrationClient(integration)
            result = client.ping()
        except Exception as exc:
            return False, f"Connection test failed: {exc}"

        if result.get("success"):
            return True, "Integration test successful."
        return False, (
            f"Integration test failed. "
            f"HTTP {result.get('log').http_status}."
        )

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    @staticmethod
    def retry_log(
        *,
        api_log: APITransactionLog,
    ) -> dict:
        """
        Replay a failed APITransactionLog through its integration.
        """
        if api_log.is_successful:
            raise ValidationError(
                "Cannot retry a successful transaction."
            )
        if api_log.retry_count >= 3:
            raise ValidationError("Maximum retry attempts (3) reached.")

        integration = api_log.integration
        if not integration.is_active:
            raise ValidationError(
                f"Integration {integration.name} is not active."
            )

        client = IntegrationClient(integration)
        result = client._request(
            method=api_log.method,
            endpoint=api_log.endpoint,
            data=api_log.request_body,
        )

        api_log.retry_count += 1
        api_log.save(update_fields=["retry_count"])

        return result