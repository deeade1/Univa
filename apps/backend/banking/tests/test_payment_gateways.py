from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone

from banking.models import payment_gateways
from banking.models.payment_gateways import (
    GatewayRouter,
    PaymentGateway,
    PaymentGatewayService,
    USSDOperation,
    USSDService,
    USSDSession,
)


TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class PaymentGatewayModelTests(TestCase):
    def create_gateway(self, **overrides):
        defaults = {
            "name": "Flutterwave Test",
            "provider": "FLUTTERWAVE",
            "base_url": "https://api.flutterwave.com/v3",
        }
        defaults.update(overrides)
        return PaymentGateway.objects.create(**defaults)

    def test_create_gateway(self):
        gateway = self.create_gateway()

        self.assertIsNotNone(gateway.pk)
        self.assertEqual(gateway.name, "Flutterwave Test")
        self.assertEqual(gateway.provider, "FLUTTERWAVE")
        self.assertEqual(
            gateway.base_url,
            "https://api.flutterwave.com/v3",
        )

    def test_default_configuration(self):
        gateway = self.create_gateway()

        self.assertTrue(gateway.is_active)
        self.assertFalse(gateway.is_default)
        self.assertEqual(gateway.weight, 1)

    def test_default_capabilities(self):
        gateway = self.create_gateway()

        self.assertTrue(gateway.supports_transfer)
        self.assertTrue(gateway.supports_collection)
        self.assertFalse(gateway.supports_ussd)
        self.assertFalse(gateway.supports_card)
        self.assertTrue(gateway.supports_bank_account)

    def test_default_performance_metrics(self):
        gateway = self.create_gateway()

        self.assertEqual(gateway.success_rate, 0.0)
        self.assertEqual(gateway.average_response_time, 0.0)
        self.assertEqual(gateway.uptime_percentage, 100.0)

    def test_default_rate_limits(self):
        gateway = self.create_gateway()

        self.assertEqual(gateway.requests_per_minute, 60)
        self.assertEqual(
            gateway.daily_transaction_limit,
            Decimal("5000000.00"),
        )

    def test_default_config_is_empty_dict(self):
        gateway = self.create_gateway()

        self.assertEqual(gateway.config, {})

    def test_provider_choices(self):
        expected = {
            "FLUTTERWAVE",
            "PAYSTACK",
            "MONNIFY",
            "REMITA",
            "INTERSWITCH",
            "NIBSS",
        }

        actual = {
            value
            for value, _label in PaymentGateway.PROVIDER_CHOICES
        }

        self.assertEqual(actual, expected)

    def test_public_key_is_encrypted_at_rest(self):
        gateway = self.create_gateway()

        gateway.public_key = "public-test-key"
        gateway.save()

        gateway.refresh_from_db()

        self.assertNotEqual(
            gateway._public_key,
            b"public-test-key",
        )

        self.assertEqual(
            gateway.public_key,
            "public-test-key",
        )

    def test_secret_key_is_encrypted_at_rest(self):
        gateway = self.create_gateway()

        gateway.secret_key = "secret-test-key"
        gateway.save()

        gateway.refresh_from_db()

        self.assertNotEqual(
            gateway._secret_key,
            b"secret-test-key",
        )

        self.assertEqual(
            gateway.secret_key,
            "secret-test-key",
        )

    def test_public_key_returns_none_when_not_configured(self):
        gateway = self.create_gateway()

        self.assertIsNone(gateway.public_key)

    def test_secret_key_returns_none_when_not_configured(self):
        gateway = self.create_gateway()

        self.assertIsNone(gateway.secret_key)

    def test_public_key_and_secret_key_are_independently_encrypted(self):
        gateway = self.create_gateway()

        gateway.public_key = "public-key"
        gateway.secret_key = "secret-key"
        gateway.save()
        gateway.refresh_from_db()

        self.assertEqual(gateway.public_key, "public-key")
        self.assertEqual(gateway.secret_key, "secret-key")
        self.assertNotEqual(
            gateway._public_key,
            gateway._secret_key,
        )

    def test_encrypted_values_are_not_plaintext(self):
        gateway = self.create_gateway()

        gateway.public_key = "public-key"
        gateway.secret_key = "secret-key"
        gateway.save()
        gateway.refresh_from_db()

        self.assertNotIn(
            b"public-key",
            gateway._public_key,
        )

        self.assertNotIn(
            b"secret-key",
            gateway._secret_key,
        )

    def test_gateway_ordering_places_default_first(self):
        normal = self.create_gateway(
            name="Normal",
            weight=1,
            is_default=False,
        )

        default = self.create_gateway(
            name="Default",
            provider="PAYSTACK",
            base_url="https://api.paystack.co",
            weight=10,
            is_default=True,
        )

        gateways = list(
            PaymentGateway.objects.all()
        )

        self.assertEqual(gateways[0].pk, default.pk)
        self.assertEqual(gateways[1].pk, normal.pk)


class GatewayRouterTests(TestCase):
    def create_gateway(self, **overrides):
        defaults = {
            "name": "Gateway",
            "provider": "FLUTTERWAVE",
            "base_url": "https://example.com",
            "is_active": True,
            "supports_transfer": True,
            "supports_card": False,
            "supports_ussd": False,
            "success_rate": 90.0,
            "uptime_percentage": 99.0,
            "average_response_time": 20.0,
            "daily_transaction_limit": Decimal("5000000.00"),
        }

        defaults.update(overrides)

        return PaymentGateway.objects.create(**defaults)

    def test_returns_none_when_no_active_transfer_gateway_exists(self):
        self.create_gateway(
            is_active=False,
        )

        result = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER",
            Decimal("10000.00"),
        )

        self.assertIsNone(result)

    def test_ignores_gateways_that_do_not_support_transfer(self):
        unsupported = self.create_gateway(
            name="Unsupported",
            supports_transfer=False,
        )

        supported = self.create_gateway(
            name="Supported",
            success_rate=90,
        )

        result = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER",
            Decimal("10000.00"),
        )

        self.assertEqual(result.pk, supported.pk)
        self.assertNotEqual(result.pk, unsupported.pk)

    def test_card_transaction_requires_card_capability(self):
        card_gateway = self.create_gateway(
            name="Card Gateway",
            supports_card=True,
        )

        non_card_gateway = self.create_gateway(
            name="Non Card Gateway",
            supports_card=False,
        )

        result = GatewayRouter.get_best_gateway(
            "CARD",
            Decimal("10000.00"),
        )

        self.assertEqual(result.pk, card_gateway.pk)
        self.assertNotEqual(result.pk, non_card_gateway.pk)

    def test_ussd_transaction_requires_ussd_capability(self):
        ussd_gateway = self.create_gateway(
            name="USSD Gateway",
            supports_ussd=True,
        )

        non_ussd_gateway = self.create_gateway(
            name="Non USSD Gateway",
            supports_ussd=False,
        )

        result = GatewayRouter.get_best_gateway(
            "USSD",
            Decimal("10000.00"),
        )

        self.assertEqual(result.pk, ussd_gateway.pk)
        self.assertNotEqual(result.pk, non_ussd_gateway.pk)

    def test_router_prefers_higher_scored_gateway(self):
        low = self.create_gateway(
            name="Low",
            success_rate=50.0,
            uptime_percentage=80.0,
            average_response_time=80.0,
        )

        high = self.create_gateway(
            name="High",
            success_rate=95.0,
            uptime_percentage=99.0,
            average_response_time=10.0,
        )

        result = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER",
            Decimal("10000.00"),
        )

        self.assertEqual(result.pk, high.pk)
        self.assertNotEqual(result.pk, low.pk)

    def test_gateway_with_amount_above_daily_limit_loses_capacity_score(self):
        within_limit = self.create_gateway(
            name="Within",
            success_rate=90.0,
            uptime_percentage=90.0,
            average_response_time=20.0,
            daily_transaction_limit=Decimal("100000.00"),
        )

        over_limit = self.create_gateway(
            name="Over",
            success_rate=90.0,
            uptime_percentage=90.0,
            average_response_time=20.0,
            daily_transaction_limit=Decimal("10000.00"),
        )

        result = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER",
            Decimal("50000.00"),
        )

        self.assertEqual(result.pk, within_limit.pk)
        self.assertNotEqual(result.pk, over_limit.pk)

    def test_router_returns_gateway_with_best_combined_score(self):
        gateway_a = self.create_gateway(
            name="Gateway A",
            success_rate=99.0,
            uptime_percentage=99.0,
            average_response_time=10.0,
        )

        gateway_b = self.create_gateway(
            name="Gateway B",
            success_rate=70.0,
            uptime_percentage=70.0,
            average_response_time=50.0,
        )

        result = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER",
            Decimal("10000.00"),
        )

        self.assertEqual(result.pk, gateway_a.pk)
        self.assertNotEqual(result.pk, gateway_b.pk)


@override_settings(
    ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    BASE_URL="https://univa.test",
)
class PaymentGatewayServiceTests(TestCase):
    def create_gateway(self, **overrides):
        defaults = {
            "name": "Flutterwave",
            "provider": "FLUTTERWAVE",
            "base_url": "https://api.flutterwave.com/v3",
            "is_active": True,
            "is_default": True,
            "supports_transfer": True,
            "secret_key": "flutter-secret",
            "public_key": "flutter-public",
        }

        defaults.update(overrides)

        gateway = PaymentGateway.objects.create(
            **{
                key: value
                for key, value in defaults.items()
                if key not in {"secret_key", "public_key"}
            }
        )

        if "secret_key" in overrides:
            gateway.secret_key = overrides.pop("secret_key")

        if "public_key" in overrides:
            gateway.public_key = overrides.pop("public_key")

        if overrides:
            for key, value in overrides.items():
                setattr(gateway, key, value)

        gateway.save()

        return gateway

    def test_service_uses_explicit_gateway(self):
        gateway = self.create_gateway(
            is_default=False,
        )

        service = PaymentGatewayService(
            gateway=gateway,
        )

        self.assertEqual(
            service.gateway.pk,
            gateway.pk,
        )

    def test_service_uses_active_default_gateway(self):
        gateway = self.create_gateway()

        service = PaymentGatewayService()

        self.assertEqual(
            service.gateway.pk,
            gateway.pk,
        )

    def test_service_has_requests_session(self):
        service = PaymentGatewayService(
            gateway=self.create_gateway(),
        )

        self.assertIsNotNone(service.session)

    @patch(
        "banking.models.payment_gateways.GatewayRouter.get_best_gateway"
    )
    def test_transfer_funds_raises_when_no_gateway_is_available(
        self,
        mock_get_best_gateway,
    ):
        mock_get_best_gateway.return_value = None

        service = PaymentGatewayService(
            gateway=self.create_gateway(),
        )

        with self.assertRaisesMessage(
            ValueError,
            "No suitable gateway available",
        ):
            service.transfer_funds(
                "SOURCE",
                "1234567890",
                "999",
                Decimal("1000.00"),
                "Test transfer",
            )

    @patch(
        "banking.models.payment_gateways.GatewayRouter.get_best_gateway"
    )
    def test_transfer_funds_rejects_unsupported_provider(
        self,
        mock_get_best_gateway,
    ):
        gateway = self.create_gateway(
            provider="PAYSTACK",
        )

        mock_get_best_gateway.return_value = gateway

        service = PaymentGatewayService(
            gateway=gateway,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Unsupported provider: PAYSTACK",
        ):
            service.transfer_funds(
                "SOURCE",
                "1234567890",
                "999",
                Decimal("1000.00"),
                "Test transfer",
            )

    @patch(
        "banking.models.payment_gateways.GatewayRouter.get_best_gateway"
    )
    @patch.object(
        PaymentGatewayService,
        "_transfer_via_flutterwave",
    )
    def test_transfer_funds_routes_flutterwave(
        self,
        mock_transfer,
        mock_get_best_gateway,
    ):
        gateway = self.create_gateway(
            provider="FLUTTERWAVE",
        )

        mock_get_best_gateway.return_value = gateway
        mock_transfer.return_value = {
            "success": True,
            "provider": "FLUTTERWAVE",
        }

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service.transfer_funds(
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertEqual(
            result["provider"],
            "FLUTTERWAVE",
        )

        mock_transfer.assert_called_once_with(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

    @patch(
        "banking.models.payment_gateways.GatewayRouter.get_best_gateway"
    )
    @patch.object(
        PaymentGatewayService,
        "_transfer_via_remita",
    )
    def test_transfer_funds_routes_remita(
        self,
        mock_transfer,
        mock_get_best_gateway,
    ):
        gateway = self.create_gateway(
            provider="REMITA",
        )

        mock_get_best_gateway.return_value = gateway
        mock_transfer.return_value = {
            "success": True,
            "provider": "REMITA",
        }

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service.transfer_funds(
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertEqual(
            result["provider"],
            "REMITA",
        )

        mock_transfer.assert_called_once_with(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

    @patch(
        "banking.models.payment_gateways.GatewayRouter.get_best_gateway"
    )
    @patch.object(
        PaymentGatewayService,
        "_transfer_via_interswitch",
    )
    def test_transfer_funds_routes_interswitch(
        self,
        mock_transfer,
        mock_get_best_gateway,
    ):
        gateway = self.create_gateway(
            provider="INTERSWITCH",
        )

        mock_get_best_gateway.return_value = gateway
        mock_transfer.return_value = {
            "success": True,
            "provider": "INTERSWITCH",
        }

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service.transfer_funds(
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertEqual(
            result["provider"],
            "INTERSWITCH",
        )

        mock_transfer.assert_called_once_with(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

    @patch("requests.Session.post")
    def test_flutterwave_transfer_success(
        self,
        mock_post,
    ):
        gateway = self.create_gateway(
            provider="FLUTTERWAVE",
            secret_key="flutter-secret",
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "success",
            "data": {
                "reference": "FLW-001",
                "id": "12345",
            },
        }

        mock_post.return_value = response

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service._transfer_via_flutterwave(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["reference"],
            "FLW-001",
        )
        self.assertEqual(
            result["provider_reference"],
            "12345",
        )
        self.assertEqual(
            result["provider"],
            "FLUTTERWAVE",
        )

        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args.kwargs

        self.assertEqual(
            call_kwargs["headers"]["Authorization"],
            "Bearer flutter-secret",
        )
        self.assertEqual(
            call_kwargs["json"]["account_bank"],
            "999",
        )
        self.assertEqual(
            call_kwargs["json"]["account_number"],
            "1234567890",
        )
        self.assertEqual(
            call_kwargs["json"]["amount"],
            "1000.00",
        )
        self.assertEqual(
            call_kwargs["json"]["currency"],
            "NGN",
        )

    @patch("requests.Session.post")
    def test_flutterwave_transfer_failure_raises(
        self,
        mock_post,
    ):
        gateway = self.create_gateway(
            provider="FLUTTERWAVE",
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "failed",
            "message": "Transfer failed",
        }

        mock_post.return_value = response

        service = PaymentGatewayService(
            gateway=gateway,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Transfer failed",
        ):
            service._transfer_via_flutterwave(
                gateway,
                "SOURCE",
                "1234567890",
                "999",
                Decimal("1000.00"),
                "Test transfer",
            )

    @patch("requests.Session.post")
    def test_remita_transfer_success(
        self,
        mock_post,
    ):
        gateway = self.create_gateway(
            provider="REMITA",
            public_key="remita-public",
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "transactionRef": "REM-PROVIDER-001",
        }

        mock_post.return_value = response

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service._transfer_via_remita(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["provider"],
            "REMITA",
        )
        self.assertEqual(
            result["provider_reference"],
            "REM-PROVIDER-001",
        )

        call_kwargs = mock_post.call_args.kwargs

        self.assertEqual(
            call_kwargs["headers"]["PUBLICKEY"],
            "remita-public",
        )
        self.assertEqual(
            call_kwargs["json"]["accountNumber"],
            "1234567890",
        )
        self.assertEqual(
            call_kwargs["json"]["accountBank"],
            "999",
        )
        self.assertEqual(
            call_kwargs["json"]["currency"],
            "NGN",
        )

    @patch("requests.Session.post")
    def test_interswitch_transfer_success(
        self,
        mock_post,
    ):
        gateway = self.create_gateway(
            provider="INTERSWITCH",
            public_key="interswitch-public",
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "success",
        }

        mock_post.return_value = response

        service = PaymentGatewayService(
            gateway=gateway,
        )

        result = service._transfer_via_interswitch(
            gateway,
            "SOURCE",
            "1234567890",
            "999",
            Decimal("1000.00"),
            "Test transfer",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["provider"],
            "INTERSWITCH",
        )

        call_kwargs = mock_post.call_args.kwargs
        payload = call_kwargs["json"]

        self.assertEqual(
            payload["merchantId"],
            "interswitch-public",
        )
        self.assertEqual(
            payload["payments"][0]["amount"],
            "100000",
        )
        self.assertEqual(
            payload["payments"][0]["customerId"],
            "SOURCE",
        )


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class USSDSessionTests(TestCase):
    def test_session_id_is_generated(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertTrue(session.session_id)
        self.assertTrue(
            session.session_id.startswith("USSD-")
        )

    def test_default_session_state(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertEqual(session.current_menu, "main")
        self.assertEqual(session.previous_menu, "")
        self.assertEqual(session.session_data, {})
        self.assertEqual(session.transaction_data, {})
        self.assertTrue(session.is_active)

    def test_session_expiry_is_generated_when_missing(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
        )

        self.assertIsNotNone(session.expires_at)

        self.assertGreater(
            session.expires_at,
            timezone.now(),
        )

    def test_new_session_is_not_expired(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertFalse(session.is_expired())

    def test_old_session_is_expired(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(session.is_expired())

    def test_session_can_store_json_data(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
            session_data={
                "step": 2,
                "amount": "5000.00",
            },
            transaction_data={
                "account_number": "1234567890",
            },
        )

        session.refresh_from_db()

        self.assertEqual(
            session.session_data["step"],
            2,
        )

        self.assertEqual(
            session.transaction_data["account_number"],
            "1234567890",
        )

    def test_session_id_is_unique(self):
        first = USSDSession.objects.create(
            phone_number="08030000001",
        )

        with self.assertRaises(IntegrityError):
            USSDSession.objects.create(
                session_id=first.session_id,
                phone_number="08030000002",
            )

    def test_default_str_representation(self):
        session = USSDSession.objects.create(
            phone_number="08030000001",
        )

        self.assertEqual(
            str(session),
            f"USSDSession object ({session.pk})",
        )


class USSDOperationTests(TestCase):
    def create_session(self):
        return USSDSession.objects.create(
            phone_number="08030000001",
        )

    def test_create_operation(self):
        session = self.create_session()

        operation = USSDOperation.objects.create(
            session=session,
            operation_type="BALANCE_CHECK",
            ussd_code="*737#",
            input_text="1",
            response_text="Balance: ₦100,000.00",
        )

        self.assertIsNotNone(operation.pk)
        self.assertEqual(
            operation.session,
            session,
        )
        self.assertEqual(
            operation.operation_type,
            "BALANCE_CHECK",
        )

    def test_operation_defaults_to_successful(self):
        session = self.create_session()

        operation = USSDOperation.objects.create(
            session=session,
            operation_type="TRANSFER",
            ussd_code="*737*2#",
            input_text="2",
            response_text="Transfer successful",
        )

        self.assertTrue(operation.is_successful)
        self.assertEqual(
            operation.error_message,
            "",
        )
        self.assertEqual(
            operation.transaction_ref,
            "",
        )

    def test_operation_error_fields(self):
        session = self.create_session()

        operation = USSDOperation.objects.create(
            session=session,
            operation_type="TRANSFER",
            ussd_code="*737*2#",
            input_text="2",
            response_text="Transfer failed",
            is_successful=False,
            error_message="Insufficient funds",
            transaction_ref="TX-001",
        )

        self.assertFalse(operation.is_successful)
        self.assertEqual(
            operation.error_message,
            "Insufficient funds",
        )
        self.assertEqual(
            operation.transaction_ref,
            "TX-001",
        )

    def test_operation_ordering(self):
        session = self.create_session()

        first = USSDOperation.objects.create(
            session=session,
            operation_type="BALANCE_CHECK",
            ussd_code="*737#",
            input_text="1",
            response_text="Balance",
        )

        second = USSDOperation.objects.create(
            session=session,
            operation_type="TRANSFER",
            ussd_code="*737*2#",
            input_text="2",
            response_text="Transfer",
        )

        operations = list(
            USSDOperation.objects.all()
        )

        self.assertEqual(
            operations[0].pk,
            second.pk,
        )
        self.assertEqual(
            operations[1].pk,
            first.pk,
        )

    def test_operation_str_representation(self):
        session = self.create_session()

        operation = USSDOperation.objects.create(
            session=session,
            operation_type="BALANCE_CHECK",
            ussd_code="*737#",
            input_text="1",
            response_text="Balance",
        )

        value = str(operation)

        self.assertIn(
            "BALANCE_CHECK",
            value,
        )
        self.assertIn(
            "08030000001",
            value,
        )

    def test_session_deletion_cascades_to_operations(self):
        session = self.create_session()

        operation = USSDOperation.objects.create(
            session=session,
            operation_type="BALANCE_CHECK",
            ussd_code="*737#",
            input_text="1",
            response_text="Balance",
        )

        operation_id = operation.pk

        session.delete()

        self.assertFalse(
            USSDOperation.objects.filter(
                pk=operation_id
            ).exists()
        )





class USSDServiceTests(TestCase):
    def test_valid_ussd_code(self):
        service = USSDService()

        self.assertTrue(
            service._is_valid_ussd("*737#")
        )
        self.assertTrue(
            service._is_valid_ussd("*737*1000*1234567890#")
        )
        self.assertTrue(
            service._is_valid_ussd("*894*2#")
        )

    def test_invalid_ussd_code(self):
        service = USSDService()

        self.assertFalse(
            service._is_valid_ussd("737")
        )
        self.assertFalse(
            service._is_valid_ussd("*73#")
        )
        self.assertFalse(
            service._is_valid_ussd("*ABC#")
        )

    def test_parse_ussd_command(self):
        service = USSDService()

        result = service._parse_ussd_command(
            "*737*1000*1234567890#"
        )

        self.assertEqual(
            result["action"],
            "737",
        )
        self.assertEqual(
            result["parameters"],
            ["1000", "1234567890"],
        )
        self.assertEqual(
            result["input"],
            "1234567890",
        )

    def test_parse_simple_ussd_command(self):
        service = USSDService()

        result = service._parse_ussd_command(
            "*737#"
        )

        self.assertEqual(
            result["action"],
            "737",
        )
        self.assertEqual(
            result["parameters"],
            [],
        )
        self.assertEqual(
            result["input"],
            "737",
        )

    def test_format_response(self):
        service = USSDService()

        result = service._format_response(
            "Welcome to Univa",
            continue_session=True,
        )

        self.assertEqual(
            result["response"],
            "Welcome to Univa",
        )
        self.assertTrue(
            result["continue_session"],
        )
        self.assertIn(
            "timestamp",
            result,
        )

    def test_format_response_defaults_to_end_session(self):
        service = USSDService()

        result = service._format_response(
            "Goodbye",
        )

        self.assertEqual(
            result["response"],
            "Goodbye",
        )
        self.assertFalse(
            result["continue_session"],
        )

    def test_main_menu_response(self):
        service = USSDService()

        session = USSDSession.objects.create(
            phone_number="08030000001",
        )

        result = service._handle_main_menu(
            session,
            {"action": "main"},
        )

        self.assertIn(
            "Check Balance",
            result["response"],
        )
        self.assertIn(
            "Transfer Money",
            result["response"],
        )
        self.assertIn(
            "Buy Airtime",
            result["response"],
        )
        self.assertTrue(
            result["continue_session"],
        )

        session.refresh_from_db()

        self.assertEqual(
            session.current_menu,
            "main",
        )

    def test_process_invalid_ussd_request(self):
        service = USSDService()

        result = service.process_ussd_request(
            "08030000001",
            "invalid",
        )

        self.assertEqual(
            result["response"],
            "Invalid USSD code format",
        )
        self.assertFalse(
            result["continue_session"],
        )

    def test_get_or_create_session_creates_session(self):
        service = USSDService()

        session = service._get_or_create_session(
            "08030000001",
        )

        self.assertIsNotNone(session.pk)
        self.assertEqual(
            session.phone_number,
            "08030000001",
        )
        self.assertTrue(
            session.is_active,
        )

    def test_get_or_create_session_reuses_existing_session(self):
        service = USSDService()

        existing = USSDSession.objects.create(
            phone_number="08030000001",
            session_id="USSD-EXISTING",
        )

        result = service._get_or_create_session(
            "08030000001",
            "USSD-EXISTING",
        )

        self.assertEqual(
            result.pk,
            existing.pk,
        )
        self.assertEqual(
            USSDSession.objects.filter(
                phone_number="08030000001"
            ).count(),
            1,
        )

    def test_expired_session_returns_expired_response(self):
        service = USSDService()

        session = USSDSession.objects.create(
            phone_number="08030000001",
            session_id="USSD-EXPIRED",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = service.process_ussd_request(
            "08030000001",
            "*737#",
            session_id=session.session_id,
        )

        self.assertEqual(
            result["response"],
            "Session expired. Please start again.",
        )
        self.assertFalse(
            result["continue_session"],
        )