# payment/canonical/tests/test_paystack_webhook.py

"""
Paystack webhook view tests.

The view:
    - verifies the HMAC-SHA512 signature
    - resolves the PaymentExecution
    - delegates to WebhookIngestionService

These tests exercise all three layers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from uuid import uuid4

import pytest
from django.test import Client

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
)


WEBHOOK_PATH = "/webhooks/paystack/"
SECRET = "sk_test_webhook_secret"


# =====================================================================
# FIXTURES
# =====================================================================


@pytest.fixture(autouse=True)
def _paystack_settings(settings):
    settings.PAYSTACK_SECRET_KEY = SECRET
    settings.PAYSTACK_WEBHOOK_SECRET = SECRET
    settings.PAYSTACK_BASE_URL = "https://api.paystack.co"


@pytest.fixture
def execution(db):
    """A RECEIVE PaymentExecution awaiting provider confirmation."""
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
        provider_reference="PSK-TEST-1",
    )


# =====================================================================
# HELPERS
# =====================================================================


def _sign(body: bytes) -> str:
    return hmac.new(
        key=SECRET.encode(),
        msg=body,
        digestmod=hashlib.sha512,
    ).hexdigest()


def _post(client: Client, body: dict, *, sign: bool = True):
    raw = json.dumps(body).encode("utf-8")
    headers = {"HTTP_X_PAYSTACK_SIGNATURE": _sign(raw)} if sign else {}
    return client.post(
        WEBHOOK_PATH,
        data=raw,
        content_type="application/json",
        **headers,
    )


def _charge_success_body(
    *,
    reference: str = "PSK-TEST-1",
    amount_kobo: int = 250000,
    currency: str = "NGN",
    provider_event_id: str = "evt-001",
) -> dict:
    return {
        "event": "charge.success",
        "data": {
            "id": provider_event_id,
            "reference": reference,
            "status": "success",
            "amount": amount_kobo,
            "currency": currency,
            "paid_at": "2026-10-09T12:00:00Z",
        },
    }


# =====================================================================
# SIGNATURE VERIFICATION
# =====================================================================


class TestSignature:

    def test_rejects_request_without_signature(self, execution):
        client = Client()
        response = _post(
            client,
            _charge_success_body(),
            sign=False,
        )
        assert response.status_code == 401

    def test_rejects_request_with_wrong_signature(self, execution):
        client = Client()
        body = _charge_success_body()
        raw = json.dumps(body).encode("utf-8")
        response = client.post(
            WEBHOOK_PATH,
            data=raw,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="deadbeef",
        )
        assert response.status_code == 401

    def test_accepts_valid_signature(self, execution):
        client = Client()
        response = _post(client, _charge_success_body())
        assert response.status_code == 200


# =====================================================================
# MALFORMED BODY
# =====================================================================


class TestMalformedBody:

    def test_rejects_invalid_json(self, execution):
        client = Client()
        raw = b"not json"
        response = client.post(
            WEBHOOK_PATH,
            data=raw,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(raw),
        )
        assert response.status_code == 400


# =====================================================================
# EXECUTION RESOLUTION
# =====================================================================


class TestExecutionResolution:

    def test_unresolvable_reference_returns_200(self, execution):
        """
        Paystack retries on non-2xx. For events we cannot resolve,
        we acknowledge with 200 to avoid infinite retries.
        """
        client = Client()
        body = _charge_success_body(reference="PSK-UNKNOWN")
        response = _post(client, body)
        assert response.status_code == 200

        # No new event should be created.
        assert (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .count()
            == 0
        )

    def test_resolves_by_provider_reference(self, execution):
        client = Client()
        body = _charge_success_body(reference="PSK-TEST-1")
        response = _post(client, body)
        assert response.status_code == 200

        # Event recorded against the resolved execution.
        assert (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .count()
            == 1
        )


# =====================================================================
# INGESTION
# =====================================================================


class TestIngestion:

    def test_charge_success_creates_event(self, execution):
        client = Client()
        body = _charge_success_body(reference="PSK-TEST-1")
        response = _post(client, body)
        assert response.status_code == 200

        events = (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
        )
        assert events.count() == 1

        event = events.first()
        assert event.source == PaymentExecutionEvent.Source.WEBHOOK
        assert (
            event.event_type
            == PaymentExecutionEvent.EventType.PROVIDER_COMPLETED
        )
        assert event.provider_event_id == "evt-001"
        assert event.provider_reference == "PSK-TEST-1"

    def test_charge_failed_creates_failed_event(self, execution):
        client = Client()
        body = _charge_success_body(reference="PSK-TEST-1")
        body["event"] = "charge.failed"
        body["data"]["status"] = "failed"

        response = _post(client, body)
        assert response.status_code == 200

        event = (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .first()
        )
        assert event is not None
        assert (
            event.event_type
            == PaymentExecutionEvent.EventType.PROVIDER_FAILED
        )

    def test_duplicate_webhook_is_idempotent(self, execution):
        """
        Two identical webhooks → one event. The service rejects the
        second as a duplicate (same provider_event_id and same data).
        """
        client = Client()
        body = _charge_success_body(reference="PSK-TEST-1")

        first = _post(client, body)
        second = _post(client, body)

        assert first.status_code == 200
        assert second.status_code == 200

        assert (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .count()
            == 1
        )

    def test_amount_mismatch_does_not_create_event(self, execution):
        """
        The Payment is 2500.00 NGN. A webhook claiming a different
        amount fails validation and produces no event.
        """
        client = Client()
        body = _charge_success_body(
            reference="PSK-TEST-1",
            amount_kobo=5000,       # 50.00 NGN
        )
        response = _post(client, body)
        assert response.status_code == 200

        assert (
            PaymentExecutionEvent.objects
            .filter(execution=execution)
            .count()
            == 0
        )

