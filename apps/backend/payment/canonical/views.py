# payment/canonical/views.py

"""
Inbound webhook views.

HTTP boundary for provider webhooks. Verifies signatures, parses the
body into a canonical WebhookPayload, resolves the target
PaymentExecution, and delegates to WebhookIngestionService.

This view does NOT:
    - mutate PaymentExecution status directly
    - call the provider
    - perform reconciliation
    - retry anything

It translates HTTP → canonical ingestion. Everything else is a
service-layer concern.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from payment.canonical.models import PaymentExecution
from payment.canonical.services.webhook import (
    WebhookIngestionService,
    WebhookPayload,
)


logger = logging.getLogger(__name__)


PAYSTACK_WEBHOOK_HEADER = "HTTP_X_PAYSTACK_SIGNATURE"


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Endpoint: POST /webhooks/paystack/

    Paystack signs every webhook with HMAC-SHA512 over the raw body,
    keyed by the secret key. Reject unsigned requests before touching
    the ingestion service.
    """
    signature = request.META.get(PAYSTACK_WEBHOOK_HEADER, "")

    if not _signature_is_valid(request.body, signature):
        logger.warning("Paystack webhook rejected: invalid signature.")
        return HttpResponse(status=401)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Paystack webhook rejected: malformed JSON.")
        return HttpResponseBadRequest("Malformed JSON.")

    event_type = body.get("event", "")
    data = body.get("data") or {}

    execution = _resolve_execution(data)

    if execution is None:
        # Acknowledge with 200 so Paystack doesn't retry forever.
        # Either the reference isn't ours, or the execution doesn't
        # exist. Log and move on.
        logger.warning(
            "Paystack webhook event=%s could not resolve execution.",
            event_type,
        )
        return HttpResponse(status=200)

    try:
        payload = _build_payload(event_type, data, execution)
    except ValidationError as exc:
        logger.warning(
            "Paystack webhook event=%s failed to build payload: %s",
            event_type,
            exc,
        )
        # Return 200 — this is a domain-level rejection, not a
        # transport failure. Retrying would hit the same validation.
        return HttpResponse(status=200)

    try:
        WebhookIngestionService.ingest(
            execution=execution,
            payload=payload,
        )
    except ValidationError as exc:
        logger.warning(
            "Paystack webhook event=%s ingestion failed: %s",
            event_type,
            exc,
        )
        return HttpResponse(status=200)

    return HttpResponse(status=200)


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


def _signature_is_valid(body: bytes, signature: str) -> bool:
    """
    HMAC-SHA512 over the raw request body, keyed with the webhook
    secret. Constant-time comparison.
    """
    if not signature:
        return False

    secret = (
        getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "")
        or getattr(settings, "PAYSTACK_SECRET_KEY", "")
    )
    if not secret:
        logger.error(
            "Paystack webhook secret is not configured; "
            "rejecting all webhooks."
        )
        return False

    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def _resolve_execution(data: dict) -> PaymentExecution | None:
    """
    Locate the PaymentExecution referenced by a Paystack webhook.

    Paystack puts the original transaction reference in
    data.reference for charge events, or data.transfer_code /
    data.reference for transfer events.
    """
    reference = (
        data.get("reference")
        or data.get("transfer_code")
        or ""
    )
    if not reference:
        return None

    execution = (
        PaymentExecution.objects
        .filter(provider_reference=reference)
        .order_by("-created_at")
        .first()
    )
    if execution is not None:
        return execution

    # Fall back: the reference may match the canonical execution
    # reference directly (when we sent execution.reference to Paystack).
    return (
        PaymentExecution.objects
        .filter(reference=reference)
        .order_by("-created_at")
        .first()
    )


def _build_payload(
    event_type: str,
    data: dict,
    execution: PaymentExecution,
) -> WebhookPayload:
    """
    Translate a Paystack webhook body into a canonical WebhookPayload.

    Raises ValidationError if required fields are missing or malformed.
    """
    status = _map_status(event_type, data)
    amount = _parse_amount(data)
    currency = str(data.get("currency") or "").upper()
    provider_reference = (
        data.get("reference")
        or data.get("transfer_code")
        or execution.provider_reference
        or ""
    )
    provider_event_id = str(
        data.get("id")
        or data.get("transfer_code")
        or data.get("reference")
        or ""
    )

    occurred_at_raw = data.get("paid_at") or data.get("updated_at")
    occurred_at = None
    if occurred_at_raw:
        try:
            occurred_at = datetime.fromisoformat(
                occurred_at_raw.replace("Z", "+00:00")
            )
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(
                    tzinfo=dt_timezone.utc
                )
        except (TypeError, ValueError):
            occurred_at = None

    return WebhookPayload(
        provider="paystack",
        provider_event_id=provider_event_id,
        provider_reference=provider_reference,
        status=status,
        amount=amount,
        currency=currency,
        occurred_at=occurred_at or timezone.now(),
        payload={"event": event_type, "data": data},
    )


def _map_status(event_type: str, data: dict) -> str:
    """
    Map Paystack event + data.status → canonical execution status.

    Canonical statuses accepted by WebhookIngestionService:
        PROCESSING, PENDING, COMPLETED, FAILED, CANCELLED
    """
    raw_status = str(data.get("status") or "").lower()

    if event_type == "charge.success" or raw_status == "success":
        return PaymentExecution.Status.COMPLETED
    if raw_status == "failed":
        return PaymentExecution.Status.FAILED
    if raw_status in {"abandoned", "reversed"}:
        return PaymentExecution.Status.CANCELLED
    if raw_status in {"ongoing", "pending"}:
        return PaymentExecution.Status.PENDING
    if raw_status in {"queued", "processing"}:
        return PaymentExecution.Status.PROCESSING

    # Conservative default: treat unknown as PENDING so the webhook
    # doesn't erroneously complete an execution.
    return PaymentExecution.Status.PENDING


def _parse_amount(data: dict) -> Decimal:
    raw = data.get("amount")
    if raw is None:
        raise ValidationError("Webhook payload missing amount.")
    try:
        # Paystack reports in minor units (kobo). Convert to major.
        return (Decimal(str(raw)) / Decimal("100")).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"Webhook amount is not a valid number: {raw!r}."
        ) from exc