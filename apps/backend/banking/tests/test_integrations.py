"""
Unit tests for apps/backend/banking/models/integrations.py

Covers:
    - BankAPIIntegration
    - APITransactionLog
    - BankAPIManager

The tests verify model defaults, encryption behavior, provider selection,
API request logging, response handling, and error handling.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

from banking.models.integrations import (
    APITransactionLog,
    BankAPIIntegration,
    BankAPIManager,
)


TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class BankAPIIntegrationTests(TestCase):
    def make_integration(self, **kwargs):
        defaults = {
            "name": "Test Paystack",
            "provider": "PAYSTACK",
            "base_url": "https://api.paystack.test",
        }
        defaults.update(kwargs)
        return BankAPIIntegration.objects.create(**defaults)

    def test_create_integration(self):
        integration = self.make_integration()

        self.assertEqual(integration.name, "Test Paystack")
        self.assertEqual(integration.provider, "PAYSTACK")
        self.assertEqual(integration.base_url, "https://api.paystack.test")

    def test_defaults(self):
        integration = self.make_integration()

        self.assertTrue(integration.is_active)
        self.assertFalse(integration.is_default)
        self.assertEqual(integration.weight, 1)

        self.assertEqual(
            integration.max_amount_per_transaction,
            Decimal("500000.00"),
        )
        self.assertEqual(
            integration.daily_amount_limit,
            Decimal("5000000.00"),
        )

        self.assertEqual(integration.supported_banks, [])
        self.assertEqual(integration.success_rate, 0.0)
        self.assertEqual(integration.average_response_time, 0.0)
        self.assertEqual(integration.total_requests, 0)
        self.assertEqual(integration.failed_requests, 0)

    def test_string_representation(self):
        integration = self.make_integration(
            name="Flutterwave Gateway",
            provider="FLUTTERWAVE",
        )

        self.assertEqual(
            str(integration),
            "Flutterwave Gateway (FLUTTERWAVE)",
        )

    def test_api_key_is_encrypted_at_rest(self):
        integration = self.make_integration()

        integration.api_key = "test-api-key"
        integration.save()

        integration.refresh_from_db()

        self.assertIsNotNone(integration._api_key)
        self.assertNotEqual(
            integration._api_key,
            b"test-api-key",
        )
        self.assertEqual(
            integration.api_key,
            "test-api-key",
        )

    def test_secret_key_is_encrypted_at_rest(self):
        integration = self.make_integration()

        integration.secret_key = "test-secret-key"
        integration.save()

        integration.refresh_from_db()

        self.assertIsNotNone(integration._secret_key)
        self.assertNotEqual(
            integration._secret_key,
            b"test-secret-key",
        )
        self.assertEqual(
            integration.secret_key,
            "test-secret-key",
        )

    def test_api_key_returns_none_when_not_configured(self):
        integration = self.make_integration()

        self.assertIsNone(integration.api_key)

    def test_secret_key_returns_none_when_not_configured(self):
        integration = self.make_integration()

        self.assertIsNone(integration.secret_key)

    def test_supported_banks_json_field(self):
        integration = self.make_integration(
            supported_banks=["058", "044", "033"],
        )

        self.assertEqual(
            integration.supported_banks,
            ["058", "044", "033"],
        )

    def test_ordering_by_created_desc(self):
        first = self.make_integration(
            name="First",
        )

        second = self.make_integration(
            name="Second",
            provider="MONNIFY",
            base_url="https://api.monnify.test",
        )

        integrations = list(BankAPIIntegration.objects.all())

        self.assertEqual(integrations[0], second)
        self.assertEqual(integrations[1], first)


class APITransactionLogTests(TestCase):
    def make_integration(self, **kwargs):
        defaults = {
            "name": "Test Integration",
            "provider": "PAYSTACK",
            "base_url": "https://api.paystack.test",
        }
        defaults.update(kwargs)
        return BankAPIIntegration.objects.create(**defaults)

    def make_log(self, integration=None, **kwargs):
        integration = integration or self.make_integration()

        defaults = {
            "integration": integration,
            "endpoint": "https://api.paystack.test/transfer",
            "method": "POST",
            "request_body": {
                "amount": "1000.00",
                "reference": "TEST-REF-001",
            },
            "response_body": {
                "status": True,
            },
            "http_status": 200,
            "reference": "TEST-REF-001",
            "started_at": timezone.now(),
        }

        defaults.update(kwargs)

        return APITransactionLog.objects.create(**defaults)

    def test_create_log(self):
        integration = self.make_integration()

        log = self.make_log(integration=integration)

        self.assertEqual(log.integration, integration)
        self.assertEqual(log.method, "POST")
        self.assertEqual(log.http_status, 200)
        self.assertEqual(log.reference, "TEST-REF-001")

    def test_defaults(self):
        log = self.make_log()

        self.assertEqual(log.request_headers, {})
        self.assertEqual(log.response_headers, {})
        self.assertEqual(log.duration_ms, 0.0)
        self.assertFalse(log.is_successful)
        self.assertEqual(log.error_message, "")
        self.assertEqual(log.retry_count, 0)

    def test_external_reference_is_optional(self):
        log = self.make_log()

        self.assertIsNone(log.external_reference)

    def test_string_representation(self):
        log = self.make_log(
            reference="REF-123",
            http_status=201,
        )

        self.assertEqual(
            str(log),
            "API Log REF-123 - 201",
        )

    def test_ordering_by_created_desc(self):
        integration = self.make_integration()

        first = self.make_log(
            integration=integration,
            reference="REF-001",
        )

        second = self.make_log(
            integration=integration,
            reference="REF-002",
        )

        logs = list(APITransactionLog.objects.all())

        self.assertEqual(logs[0], second)
        self.assertEqual(logs[1], first)

    def test_related_logs(self):
        integration = self.make_integration()

        self.make_log(
            integration=integration,
            reference="REF-001",
        )
        self.make_log(
            integration=integration,
            reference="REF-002",
        )

        self.assertEqual(
            integration.api_logs.count(),
            2,
        )

    def test_integration_cascade_deletes_logs(self):
        integration = self.make_integration()

        log = self.make_log(
            integration=integration,
        )

        log_id = log.pk

        integration.delete()

        self.assertFalse(
            APITransactionLog.objects.filter(pk=log_id).exists()
        )


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class BankAPIManagerTests(TestCase):
    def make_integration(self, **kwargs):
        defaults = {
            "name": "Test Paystack",
            "provider": "PAYSTACK",
            "base_url": "https://api.paystack.test",
        }
        defaults.update(kwargs)
        integration = BankAPIIntegration.objects.create(**defaults)

        integration.api_key = "test-api-key"
        integration.secret_key = "test-secret-key"
        integration.save()

        return integration

    def test_explicit_provider_selects_active_provider(self):
        integration = self.make_integration(
            provider="PAYSTACK",
            is_active=True,
        )

        manager = BankAPIManager(provider_name="PAYSTACK")

        self.assertEqual(
            manager.provider,
            integration,
        )

    def test_explicit_provider_does_not_select_inactive_provider(self):
        self.make_integration(
            provider="PAYSTACK",
            is_active=False,
        )

        manager = BankAPIManager(provider_name="PAYSTACK")

        self.assertIsNone(manager.provider)

    def test_default_provider_selection(self):
        self.make_integration(
            provider="PAYSTACK",
            is_default=True,
            is_active=True,
        )

        manager = BankAPIManager()

        self.assertEqual(
            manager.provider.provider,
            "PAYSTACK",
        )

    @patch("banking.models.integrations.requests.Session.request")
    def test_name_enquiry(self, mock_request):
        integration = self.make_integration(
            provider="NIBSS",
            base_url="https://nibss.test",
        )

        response = Mock()
        response.status_code = 200
        response.text = '{"status": true}'
        response.json.return_value = {
            "status": True,
            "account_name": "Jane Doe",
        }

        mock_request.return_value = response

        manager = BankAPIManager(provider_name="NIBSS")

        result = manager.name_enquiry(
            account_number="0123456789",
            bank_code="058",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["data"]["account_name"],
            "Jane Doe",
        )

        self.assertEqual(
            result["log"].http_status,
            200,
        )

        self.assertTrue(
            result["log"].is_successful,
        )

        mock_request.assert_called_once()

        call_kwargs = mock_request.call_args.kwargs

        self.assertEqual(
            call_kwargs["method"],
            "POST",
        )
        self.assertEqual(
            call_kwargs["url"],
            "https://nibss.test/name_enquiry",
        )
        self.assertEqual(
            call_kwargs["json"]["account_number"],
            "0123456789",
        )
        self.assertEqual(
            call_kwargs["json"]["bank_code"],
            "058",
        )

    @patch("banking.models.integrations.requests.Session.request")
    def test_transfer_funds(self, mock_request):
        integration = self.make_integration(
            provider="BANK",
            base_url="https://bank.test",
        )

        response = Mock()
        response.status_code = 201
        response.text = '{"reference": "BANK-REF-001"}'
        response.json.return_value = {
            "success": True,
            "reference": "BANK-REF-001",
        }

        mock_request.return_value = response

        manager = BankAPIManager(provider_name="BANK")

        result = manager.transfer_funds(
            from_account="1000000001",
            to_account="2000000002",
            amount=Decimal("5000.00"),
            narration="Test transfer",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["data"]["reference"],
            "BANK-REF-001",
        )
        self.assertEqual(
            result["log"].http_status,
            201,
        )

        mock_request.assert_called_once()

        call_kwargs = mock_request.call_args.kwargs

        self.assertEqual(
            call_kwargs["method"],
            "POST",
        )
        self.assertEqual(
            call_kwargs["url"],
            "https://bank.test/transfer",
        )

        self.assertEqual(
            call_kwargs["json"]["source_account"],
            "1000000001",
        )
        self.assertEqual(
            call_kwargs["json"]["destination_account"],
            "2000000002",
        )
        self.assertEqual(
            call_kwargs["json"]["amount"],
            "5000.00",
        )
        self.assertEqual(
            call_kwargs["json"]["narration"],
            "Test transfer",
        )
        self.assertEqual(
            call_kwargs["json"]["currency"],
            "NGN",
        )

    @patch("banking.models.integrations.requests.Session.request")
    def test_successful_request_uses_api_key_authorization(self, mock_request):
        self.make_integration(
            provider="BANK",
        )

        response = Mock()
        response.status_code = 200
        response.text = '{"status": true}'
        response.json.return_value = {
            "status": True,
        }

        mock_request.return_value = response

        manager = BankAPIManager(provider_name="BANK")

        manager.name_enquiry(
            account_number="0123456789",
            bank_code="058",
        )

        headers = mock_request.call_args.kwargs["headers"]

        self.assertEqual(
            headers["Authorization"],
            "Bearer test-api-key",
        )
        self.assertEqual(
            headers["Content-Type"],
            "application/json",
        )

    @patch("banking.models.integrations.requests.Session.request")
    def test_paystack_uses_secret_key_authorization(self, mock_request):
        self.make_integration(
            provider="PAYSTACK",
        )

        response = Mock()
        response.status_code = 200
        response.text = '{"status": true}'
        response.json.return_value = {
            "status": True,
        }

        mock_request.return_value = response

        manager = BankAPIManager(provider_name="PAYSTACK")

        manager.name_enquiry(
            account_number="0123456789",
            bank_code="058",
        )

        headers = mock_request.call_args.kwargs["headers"]

        self.assertEqual(
            headers["Authorization"],
            "Bearer test-secret-key",
        )

    @patch("banking.models.integrations.requests.Session.request")
    def test_failed_request_is_logged(self, mock_request):
        self.make_integration(
            provider="BANK",
        )

        response = Mock()
        response.status_code = 400
        response.text = "Bad request"
        response.json.return_value = {
            "error": "Invalid account",
        }

        mock_request.return_value = response

        manager = BankAPIManager(provider_name="BANK")

        result = manager.name_enquiry(
            account_number="0000000000",
            bank_code="999",
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["data"],
            {"error": "Invalid account"},
        )

        log = result["log"]

        self.assertFalse(log.is_successful)
        self.assertEqual(log.http_status, 400)
        self.assertEqual(log.error_message, "Bad request")

    @patch("banking.models.integrations.requests.Session.request")
    def test_request_exception_is_logged(self, mock_request):
        self.make_integration(
            provider="BANK",
        )

        mock_request.side_effect = requests.RequestException(
            "Connection failed"
        )

        manager = BankAPIManager(provider_name="BANK")

        result = manager.name_enquiry(
            account_number="0123456789",
            bank_code="058",
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["error"],
            "Connection failed",
        )

        log = APITransactionLog.objects.get(
            reference=result["reference"],
        )

        self.assertFalse(log.is_successful)
        self.assertEqual(log.http_status, 500)
        self.assertEqual(
            log.error_message,
            "Connection failed",
        )

    def test_manager_creates_requests_session(self):
        self.make_integration(
            provider="BANK",
        )

        manager = BankAPIManager(provider_name="BANK")

        self.assertIsInstance(
            manager.session,
            requests.Session,
        )