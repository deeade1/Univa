# payment/canonical/tests/test_paystack_adapter.py

"""
Paystack adapter tests. HTTP is mocked with `responses` — no network.
"""

from __future__ import annotations

import requests
from decimal import Decimal
from uuid import uuid4

import pytest
import responses
from django.db.models.signals import post_save

from ecommerce.signals.refund import (
    sync_refund_from_payment_execution,
)
from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.providers.paystack.adapter import (
    PaystackAdapter,
)
from payment.canonical.services.providers.paystack.client import (
    PaystackClient,
)


BASE_URL = "https://api.paystack.co"


# =====================================================================
# SIGNAL SUPPRESSION
# =====================================================================
#
# These tests focus on the adapter's HTTP behavior. The refund signal
# resolves `Payment.source_id` back to an OrderGrantedRefund — a
# concern covered by `test_order_refund_flow.py`. Here we disable it
# so fixtures can use minimal dummy data.

@pytest.fixture(autouse=True)
def _disable_refund_signal():
    post_save.disconnect(
        sync_refund_from_payment_execution,
        sender="payment_canonical.PaymentExecution",
    )
    yield
    post_save.connect(
        sync_refund_from_payment_execution,
        sender="payment_canonical.PaymentExecution",
    )


# =====================================================================
# SETTINGS
# =====================================================================


@pytest.fixture(autouse=True)
def _paystack_settings(settings):
    settings.PAYSTACK_SECRET_KEY = "sk_test_secret"
    settings.PAYSTACK_BASE_URL = BASE_URL
    settings.PAYSTACK_TIMEOUT_SECONDS = 5
    settings.PAYSTACK_WEBHOOK_SECRET = "sk_test_secret"


# =====================================================================
# OBJECTS
# =====================================================================


@pytest.fixture
def adapter():
    return PaystackAdapter(client=PaystackClient())


@pytest.fixture
def receive_execution(db):
    """A canonical PaymentExecution for a RECEIVE (checkout) payment."""
    payment = Payment.objects.create(
        reference=f"PAY-{uuid4().hex[:12]}",
        direction=Payment.Direction.RECEIVE,
        purpose=Payment.Purpose.CHECKOUT,
        source_type="order",
        source_id="order-1",
        amount=Decimal("2500.00"),
        currency="NGN",
        idempotency_key=f"idem-{uuid4().hex[:12]}",
        metadata={"user_email": "test@example.com"},
    )
    return PaymentExecution.objects.create(
        reference=f"PEXEC-{uuid4().hex[:12]}",
        payment=payment,
        attempt_number=1,
        idempotency_key=f"exec-idem-{uuid4().hex[:12]}",
        route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        provider="paystack",
    )


@pytest.fixture
def refund_execution(db, receive_execution):
    """
    A DISBURSE PaymentExecution whose purpose is REFUND.

    Uses lightweight dummy data — the refund signal is disabled for
    these tests, so source_id does not need to resolve to a real
    OrderGrantedRefund row.
    """
    original_payment = receive_execution.payment

    # Complete the original execution so it has a provider reference.
    receive_execution.status = PaymentExecution.Status.COMPLETED
    receive_execution.provider_reference = "PSK-ORIGINAL-REF"
    receive_execution.save(
        update_fields=["status", "provider_reference"]
    )

    refund_payment = Payment.objects.create(
        reference=f"PAY-{uuid4().hex[:12]}",
        direction=Payment.Direction.DISBURSE,
        purpose=Payment.Purpose.REFUND,
        source_type="refund",
        source_id="1",                       # dummy numeric source_id
        source_reference="Refund for Order #1",
        amount=Decimal("2500.00"),
        currency="NGN",
        idempotency_key=f"refund-idem-{uuid4().hex[:12]}",
        metadata={
            "original_payment_id": str(original_payment.pk),
        },
    )

    return PaymentExecution.objects.create(
        reference=f"PEXEC-{uuid4().hex[:12]}",
        payment=refund_payment,
        attempt_number=1,
        idempotency_key=f"refund-exec-idem-{uuid4().hex[:12]}",
        route_type=PaymentExecution.RouteType.UNIVA_INTERNAL,
        provider="paystack",
    )


# =====================================================================
# INITIATE — RECEIVE
# =====================================================================


class TestInitiateReceive:

    @responses.activate
    def test_returns_pending_with_authorization_url(
        self, adapter, receive_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/transaction/initialize",
            json={
                "status": True,
                "data": {
                    "access_code": "ac_123",
                    "authorization_url": (
                        "https://checkout.paystack.com/xyz"
                    ),
                    "reference": receive_execution.reference,
                },
            },
            status=200,
        )

        result = adapter.initiate(receive_execution)

        assert result.status == PaymentExecution.Status.PENDING
        assert result.reconciliation_required is True
        assert result.provider_reference == receive_execution.reference
        assert result.metadata["access_code"] == "ac_123"
        assert (
            result.metadata["authorization_url"]
            == "https://checkout.paystack.com/xyz"
        )

    @responses.activate
    def test_sends_amount_in_kobo(
        self, adapter, receive_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/transaction/initialize",
            json={
                "status": True,
                "data": {"reference": "PSK-1"},
            },
            status=200,
        )

        adapter.initiate(receive_execution)

        body = responses.calls[0].request.body
        assert b'"amount": 250000' in body

    @responses.activate
    def test_sends_authorization_header(
        self, adapter, receive_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/transaction/initialize",
            json={
                "status": True,
                "data": {"reference": "PSK-1"},
            },
            status=200,
        )

        adapter.initiate(receive_execution)

        headers = responses.calls[0].request.headers
        assert headers["Authorization"] == "Bearer sk_test_secret"

    @responses.activate
    def test_network_error_returns_pending_reconciliation(
        self, adapter, receive_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/transaction/initialize",
            body=requests.ConnectionError("Connection refused"),
        )

        result = adapter.initiate(receive_execution)

        assert result.status == PaymentExecution.Status.PENDING
        assert result.reconciliation_required is True
        assert "Connection refused" in result.metadata["error"]

    @responses.activate
    def test_4xx_returns_failed(
        self, adapter, receive_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/transaction/initialize",
            json={
                "status": False,
                "message": "Invalid key",
            },
            status=401,
        )

        result = adapter.initiate(receive_execution)

        assert result.status == PaymentExecution.Status.FAILED
        assert result.failure_code == "provider_error"
        assert "Invalid key" in result.failure_reason


# =====================================================================
# INITIATE — REFUND
# =====================================================================


class TestInitiateRefund:

    @responses.activate
    def test_refund_calls_refund_endpoint_with_original_reference(
        self, adapter, refund_execution,
    ):
        responses.add(
            responses.POST,
            f"{BASE_URL}/refund",
            json={
                "status": True,
                "data": {
                    "reference": "PSK-REFUND-1",
                    "status": "processed",
                },
            },
            status=200,
        )

        result = adapter.initiate(refund_execution)

        body = responses.calls[0].request.body
        assert b'"transaction": "PSK-ORIGINAL-REF"' in body
        assert b'"amount": 250000' in body
        assert result.provider_reference == "PSK-REFUND-1"

    @responses.activate
    def test_refund_without_original_reference_fails_cleanly(
        self, adapter, refund_execution,
    ):
        # Wipe the original_payment_id from the refund Payment's
        # metadata so the adapter cannot resolve it.
        refund_execution.payment.metadata = {}
        refund_execution.payment.save(
            update_fields=["metadata", "updated_at"]
        )

        result = adapter.initiate(refund_execution)

        assert result.status == PaymentExecution.Status.FAILED
        assert result.failure_code == "missing_original_payment"


# =====================================================================
# GET STATUS
# =====================================================================


class TestGetStatus:

    @responses.activate
    def test_receive_verify_endpoint(
        self, adapter, receive_execution,
    ):
        receive_execution.provider_reference = "PSK-RCV-1"
        receive_execution.save(update_fields=["provider_reference"])

        responses.add(
            responses.GET,
            f"{BASE_URL}/transaction/verify/PSK-RCV-1",
            json={
                "status": True,
                "data": {
                    "status": "success",
                    "reference": "PSK-RCV-1",
                },
            },
            status=200,
        )

        result = adapter.get_status(receive_execution)

        assert result.status == PaymentExecution.Status.COMPLETED

    @responses.activate
    def test_disburse_verify_endpoint(
        self, adapter, refund_execution,
    ):
        refund_execution.provider_reference = "PSK-TRF-1"
        refund_execution.save(update_fields=["provider_reference"])

        responses.add(
            responses.GET,
            f"{BASE_URL}/transfer/verify/PSK-TRF-1",
            json={
                "status": True,
                "data": {
                    "status": "success",
                    "transfer_code": "PSK-TRF-1",
                },
            },
            status=200,
        )

        result = adapter.get_status(refund_execution)

        assert result.status == PaymentExecution.Status.COMPLETED


# =====================================================================
# CONFIGURATION
# =====================================================================


class TestConfiguration:

    def test_missing_secret_key_returns_failed(
        self, adapter, receive_execution, settings,
    ):
        settings.PAYSTACK_SECRET_KEY = ""
        adapter._client._secret_key = ""

        result = adapter.initiate(receive_execution)

        assert result.status == PaymentExecution.Status.FAILED
        assert result.failure_code == "provider_not_configured"