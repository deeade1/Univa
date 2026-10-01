from django.test import SimpleTestCase

from payment.canonical.models import PaymentExecution
from payment.canonical.services.providers import (
    ProviderAdapter,
    ProviderResult,
)


class FakeProviderAdapter(ProviderAdapter):
    """
    Test-only provider implementation.

    This adapter intentionally performs no external I/O and does not
    mutate PaymentExecution.
    """

    @property
    def provider_name(self):
        return "fake_provider"

    def initiate(self, execution):
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-INIT-001",
            metadata={
                "source": "test",
            },
        )

    def get_status(self, execution):
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="FAKE-STATUS-001",
            metadata={
                "source": "test",
            },
        )


class CancellableFakeProviderAdapter(FakeProviderAdapter):
    def cancel(self, execution):
        return ProviderResult(
            status=PaymentExecution.Status.CANCELLED,
            provider_reference="FAKE-CANCEL-001",
        )


class ProviderResultTests(SimpleTestCase):
    def test_provider_result_stores_normalized_values(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="PROV-123",
            failure_code=None,
            failure_reason=None,
            reconciliation_required=False,
            metadata={
                "provider_status": "successful",
            },
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertEqual(
            result.provider_reference,
            "PROV-123",
        )
        self.assertIsNone(result.failure_code)
        self.assertIsNone(result.failure_reason)
        self.assertFalse(result.reconciliation_required)
        self.assertEqual(
            result.metadata,
            {"provider_status": "successful"},
        )

    def test_provider_result_supports_failed_result(self):
        result = ProviderResult(
            status=PaymentExecution.Status.FAILED,
            provider_reference="PROV-FAILED-001",
            failure_code="DECLINED",
            failure_reason="Provider declined the transaction.",
            reconciliation_required=False,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            result.provider_reference,
            "PROV-FAILED-001",
        )
        self.assertEqual(
            result.failure_code,
            "DECLINED",
        )
        self.assertEqual(
            result.failure_reason,
            "Provider declined the transaction.",
        )
        self.assertFalse(result.reconciliation_required)

    def test_provider_result_supports_pending_reconciliation_result(self):
        result = ProviderResult(
            status=PaymentExecution.Status.PENDING,
            provider_reference="PROV-PENDING-001",
            reconciliation_required=True,
        )

        self.assertEqual(
            result.status,
            PaymentExecution.Status.PENDING,
        )
        self.assertEqual(
            result.provider_reference,
            "PROV-PENDING-001",
        )
        self.assertTrue(result.reconciliation_required)

    def test_provider_result_is_immutable(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference="PROV-123",
        )

        with self.assertRaises(AttributeError):
            result.status = PaymentExecution.Status.FAILED

    def test_provider_result_metadata_defaults_to_none(self):
        result = ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
        )

        self.assertIsNone(result.metadata)


class ProviderAdapterContractTests(SimpleTestCase):
    def test_fake_adapter_exposes_provider_name(self):
        adapter = FakeProviderAdapter()

        self.assertEqual(
            adapter.provider_name,
            "fake_provider",
        )

    def test_fake_adapter_implements_initiate(self):
        adapter = FakeProviderAdapter()

        result = adapter.initiate(execution=object())

        self.assertIsInstance(result, ProviderResult)
        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertEqual(
            result.provider_reference,
            "FAKE-INIT-001",
        )

    def test_fake_adapter_implements_get_status(self):
        adapter = FakeProviderAdapter()

        result = adapter.get_status(execution=object())

        self.assertIsInstance(result, ProviderResult)
        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )
        self.assertEqual(
            result.provider_reference,
            "FAKE-STATUS-001",
        )

    def test_provider_adapter_cannot_be_instantiated_directly(self):
        with self.assertRaises(TypeError):
            ProviderAdapter()

    def test_provider_name_is_required(self):
        class MissingProviderNameAdapter(ProviderAdapter):
            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

            def get_status(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

        with self.assertRaises(TypeError):
            MissingProviderNameAdapter()

    def test_initiate_is_required(self):
        class MissingInitiateAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return "missing_initiate"

            def get_status(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

        with self.assertRaises(TypeError):
            MissingInitiateAdapter()

    def test_get_status_is_required(self):
        class MissingGetStatusAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return "missing_get_status"

            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.COMPLETED,
                )

        with self.assertRaises(TypeError):
            MissingGetStatusAdapter()

    def test_cancel_is_optional(self):
        adapter = FakeProviderAdapter()

        with self.assertRaises(NotImplementedError):
            adapter.cancel(execution=object())

    def test_adapter_can_implement_cancel(self):
        adapter = CancellableFakeProviderAdapter()

        result = adapter.cancel(execution=object())

        self.assertIsInstance(result, ProviderResult)
        self.assertEqual(
            result.status,
            PaymentExecution.Status.CANCELLED,
        )
        self.assertEqual(
            result.provider_reference,
            "FAKE-CANCEL-001",
        )

    def test_adapter_returns_normalized_status_not_provider_specific_status(self):
        adapter = FakeProviderAdapter()

        result = adapter.initiate(execution=object())

        self.assertIn(
            result.status,
            {
                PaymentExecution.Status.CREATED,
                PaymentExecution.Status.PROCESSING,
                PaymentExecution.Status.PENDING,
                PaymentExecution.Status.COMPLETED,
                PaymentExecution.Status.FAILED,
                PaymentExecution.Status.CANCELLED,
            },
        )

    def test_adapter_does_not_mutate_execution(self):
        class ExecutionProbe:
            status = PaymentExecution.Status.CREATED

        execution = ExecutionProbe()

        adapter = FakeProviderAdapter()

        result = adapter.initiate(execution)

        self.assertEqual(
            execution.status,
            PaymentExecution.Status.CREATED,
        )
        self.assertEqual(
            result.status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_pending_result_can_require_reconciliation(self):
        class PendingFakeAdapter(FakeProviderAdapter):
            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.PENDING,
                    provider_reference="FAKE-PENDING-001",
                    reconciliation_required=True,
                )

        adapter = PendingFakeAdapter()

        result = adapter.initiate(execution=object())

        self.assertEqual(
            result.status,
            PaymentExecution.Status.PENDING,
        )
        self.assertTrue(result.reconciliation_required)

    def test_failed_result_contains_failure_information(self):
        class FailedFakeAdapter(FakeProviderAdapter):
            def initiate(self, execution):
                return ProviderResult(
                    status=PaymentExecution.Status.FAILED,
                    provider_reference="FAKE-FAILED-001",
                    failure_code="DECLINED",
                    failure_reason="Payment declined.",
                )

        adapter = FailedFakeAdapter()

        result = adapter.initiate(execution=object())

        self.assertEqual(
            result.status,
            PaymentExecution.Status.FAILED,
        )
        self.assertEqual(
            result.failure_code,
            "DECLINED",
        )
        self.assertEqual(
            result.failure_reason,
            "Payment declined.",
        )