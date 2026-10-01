from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from payment.canonical.services.providers import (
    ProviderAdapter,
    ProviderRegistry,
    ProviderResult,
)


class FakeProviderAdapter(ProviderAdapter):
    """Test-only provider adapter."""

    def __init__(self, name="fake_provider"):
        self._provider_name = name

    @property
    def provider_name(self):
        return self._provider_name

    def initiate(self, execution):
        return ProviderResult(
            status="completed",
            provider_reference="FAKE-INIT-001",
        )

    def get_status(self, execution):
        return ProviderResult(
            status="completed",
            provider_reference="FAKE-STATUS-001",
        )


class ProviderRegistryTests(SimpleTestCase):
    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_registers_valid_adapter(self):
        adapter = FakeProviderAdapter()

        result = ProviderRegistry.register(adapter)

        self.assertIs(result, adapter)
        self.assertTrue(
            ProviderRegistry.has("fake_provider")
        )

    def test_retrieves_registered_adapter(self):
        adapter = FakeProviderAdapter()

        ProviderRegistry.register(adapter)

        result = ProviderRegistry.get("fake_provider")

        self.assertIs(result, adapter)

    def test_provider_name_is_normalized_on_registration(self):
        adapter = FakeProviderAdapter(
            name="  FakeProvider  "
        )

        ProviderRegistry.register(adapter)

        self.assertTrue(
            ProviderRegistry.has("fakeprovider")
        )

        self.assertIs(
            ProviderRegistry.get("FAKEPROVIDER"),
            adapter,
        )

    def test_get_normalizes_provider_name(self):
        adapter = FakeProviderAdapter(
            name="fake_provider"
        )

        ProviderRegistry.register(adapter)

        self.assertIs(
            ProviderRegistry.get("  FAKE_PROVIDER  "),
            adapter,
        )

    def test_duplicate_provider_registration_is_rejected(self):
        first = FakeProviderAdapter(
            name="fake_provider"
        )
        second = FakeProviderAdapter(
            name="fake_provider"
        )

        ProviderRegistry.register(first)

        with self.assertRaises(ValidationError):
            ProviderRegistry.register(second)

        self.assertIs(
            ProviderRegistry.get("fake_provider"),
            first,
        )

    def test_invalid_adapter_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProviderRegistry.register(object())

    def test_none_adapter_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProviderRegistry.register(None)

    def test_adapter_with_missing_provider_name_is_rejected(self):
        class MissingProviderNameAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return ""

            def initiate(self, execution):
                return ProviderResult(
                    status="completed",
                )

            def get_status(self, execution):
                return ProviderResult(
                    status="completed",
                )

        adapter = MissingProviderNameAdapter()

        with self.assertRaises(ValidationError):
            ProviderRegistry.register(adapter)

    def test_adapter_with_non_string_provider_name_is_rejected(self):
        class InvalidProviderNameAdapter(ProviderAdapter):
            @property
            def provider_name(self):
                return None

            def initiate(self, execution):
                return ProviderResult(
                    status="completed",
                )

            def get_status(self, execution):
                return ProviderResult(
                    status="completed",
                )

        adapter = InvalidProviderNameAdapter()

        with self.assertRaises(ValidationError):
            ProviderRegistry.register(adapter)

    def test_get_unknown_provider_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProviderRegistry.get("unknown_provider")

    def test_get_missing_provider_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProviderRegistry.get("")

    def test_get_none_provider_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProviderRegistry.get(None)

    def test_has_returns_true_for_registered_provider(self):
        adapter = FakeProviderAdapter()

        ProviderRegistry.register(adapter)

        self.assertTrue(
            ProviderRegistry.has("fake_provider")
        )

    def test_has_returns_false_for_unknown_provider(self):
        self.assertFalse(
            ProviderRegistry.has("unknown_provider")
        )

    def test_has_returns_false_for_invalid_provider_name(self):
        self.assertFalse(
            ProviderRegistry.has("")
        )
        self.assertFalse(
            ProviderRegistry.has(None)
        )

    def test_clear_removes_registered_adapters(self):
        adapter = FakeProviderAdapter()

        ProviderRegistry.register(adapter)

        self.assertTrue(
            ProviderRegistry.has("fake_provider")
        )

        ProviderRegistry.clear()

        self.assertFalse(
            ProviderRegistry.has("fake_provider")
        )

    def test_registry_returns_exact_registered_adapter_instance(self):
        adapter = FakeProviderAdapter()

        ProviderRegistry.register(adapter)

        result = ProviderRegistry.get("fake_provider")

        self.assertIs(result, adapter)

    def test_registry_does_not_execute_adapter(self):
        class TrackingAdapter(FakeProviderAdapter):
            def __init__(self):
                super().__init__()
                self.initiate_called = False
                self.get_status_called = False

            def initiate(self, execution):
                self.initiate_called = True
                return super().initiate(execution)

            def get_status(self, execution):
                self.get_status_called = True
                return super().get_status(execution)

        adapter = TrackingAdapter()

        ProviderRegistry.register(adapter)
        ProviderRegistry.get("fake_provider")

        self.assertFalse(adapter.initiate_called)
        self.assertFalse(adapter.get_status_called)