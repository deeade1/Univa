from django.core.exceptions import ValidationError
from django.test import TestCase
from decimal import Decimal
from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.execution_router import ExecutionRouter
from payment.canonical.services.providers import (
    ProviderAdapter,
    ProviderRegistry,
    ProviderResult,
)


class FakeProviderAdapter(ProviderAdapter):
    """Test-only provider adapter."""

    @property
    def provider_name(self):
        return "fake_provider"

    def initiate(self, execution):
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-INIT-001",
        )

    def get_status(self, execution):
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-STATUS-001",
        )


class ExecutionRouterTests(TestCase):
    def setUp(self):
        ProviderRegistry.clear()

        self.user = self.create_user()

        self.payment = Payment.objects.create(
            reference="PAY-ROUTER-001",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="CHECKOUT-001",
            payer=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="PAY-ROUTER-IDEMPOTENCY-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="PEXEC-ROUTER-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="PEXEC-ROUTER-IDEMPOTENCY-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="fake_provider",
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
        )

        self.adapter = FakeProviderAdapter()

        ProviderRegistry.register(self.adapter)

    def tearDown(self):
        ProviderRegistry.clear()

    def create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email="router@example.com",
            password="test-password",
        )

    def test_resolves_registered_provider_adapter(self):
        adapter = ExecutionRouter.resolve(self.execution)

        self.assertIs(adapter, self.adapter)

    def test_resolved_adapter_is_provider_adapter(self):
        adapter = ExecutionRouter.resolve(self.execution)

        self.assertIsInstance(adapter, ProviderAdapter)

    def test_router_uses_execution_provider(self):
        self.assertEqual(
            self.execution.provider,
            "fake_provider",
        )

        adapter = ExecutionRouter.resolve(self.execution)

        self.assertEqual(
            adapter.provider_name,
            "fake_provider",
        )

    def test_provider_name_lookup_is_case_insensitive(self):
        self.execution.provider = "FAKE_PROVIDER"
        self.execution.save(update_fields=["provider"])

        adapter = ExecutionRouter.resolve(self.execution)

        self.assertIs(adapter, self.adapter)

    def test_provider_name_lookup_ignores_surrounding_whitespace(self):
        self.execution.provider = "  fake_provider  "
        self.execution.save(update_fields=["provider"])

        adapter = ExecutionRouter.resolve(self.execution)

        self.assertIs(adapter, self.adapter)

    def test_missing_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ExecutionRouter.resolve(None)

    def test_invalid_execution_is_rejected(self):
        with self.assertRaises(ValidationError):
            ExecutionRouter.resolve(object())

    def test_execution_without_provider_is_rejected(self):
        self.execution.provider = ""
        self.execution.save(update_fields=["provider"])

        with self.assertRaises(ValidationError):
            ExecutionRouter.resolve(self.execution)

    def test_unknown_provider_is_rejected(self):
        self.execution.provider = "unknown_provider"
        self.execution.save(update_fields=["provider"])

        with self.assertRaises(ValidationError):
            ExecutionRouter.resolve(self.execution)

    def test_router_does_not_initiate_execution(self):
        class TrackingAdapter(FakeProviderAdapter):
            def __init__(self):
                self.initiate_called = False
                self.get_status_called = False

            def initiate(self, execution):
                self.initiate_called = True
                return super().initiate(execution)

            def get_status(self, execution):
                self.get_status_called = True
                return super().get_status(execution)

        ProviderRegistry.clear()

        adapter = TrackingAdapter()
        ProviderRegistry.register(adapter)

        self.execution.provider = "fake_provider"
        self.execution.save(update_fields=["provider"])

        result = ExecutionRouter.resolve(self.execution)

        self.assertIs(result, adapter)
        self.assertFalse(adapter.initiate_called)
        self.assertFalse(adapter.get_status_called)

    def test_router_does_not_mutate_execution(self):
        original_status = self.execution.status
        original_provider = self.execution.provider
        original_route_type = self.execution.route_type
        original_attempt_number = self.execution.attempt_number

        ExecutionRouter.resolve(self.execution)

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.status,
            original_status,
        )
        self.assertEqual(
            self.execution.provider,
            original_provider,
        )
        self.assertEqual(
            self.execution.route_type,
            original_route_type,
        )
        self.assertEqual(
            self.execution.attempt_number,
            original_attempt_number,
        )

    def test_router_does_not_mutate_payment(self):
        original_status = self.payment.status
        original_amount = self.payment.amount
        original_currency = self.payment.currency

        ExecutionRouter.resolve(self.execution)

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            original_status,
        )
        self.assertEqual(
            self.payment.amount,
            original_amount,
        )
        self.assertEqual(
            self.payment.currency,
            original_currency,
        )

    def test_router_returns_exact_registered_adapter_instance(self):
        result = ExecutionRouter.resolve(self.execution)

        registered = ProviderRegistry.get("fake_provider")

        self.assertIs(result, registered)
        self.assertIs(result, self.adapter)

    def test_router_does_not_select_a_different_provider(self):
        class AnotherFakeProviderAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return "another_provider"

            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

            def get_status(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

        another_adapter = AnotherFakeProviderAdapter()
        ProviderRegistry.register(another_adapter)

        self.execution.provider = "fake_provider"
        self.execution.save(update_fields=["provider"])

        result = ExecutionRouter.resolve(self.execution)

        self.assertIs(result, self.adapter)
        self.assertIsNot(result, another_adapter)

    def test_router_resolves_different_registered_provider(self):
        class AnotherFakeProviderAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return "another_provider"

            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

            def get_status(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

        another_adapter = AnotherFakeProviderAdapter()
        ProviderRegistry.register(another_adapter)

        self.execution.provider = "another_provider"
        self.execution.save(update_fields=["provider"])

        result = ExecutionRouter.resolve(self.execution)

        self.assertIs(result, another_adapter)
        self.assertIsNot(result, self.adapter)