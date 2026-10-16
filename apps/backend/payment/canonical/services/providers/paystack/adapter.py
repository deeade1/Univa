# payment/canonical/services/providers/paystack/adapter.py

"""
Paystack provider adapter.

Translates canonical PaymentExecution state into Paystack API calls
and Paystack responses into canonical ProviderResult.

The adapter is a thin translation layer. It does not make business
decisions — those live in the orchestrator.
"""

from __future__ import annotations

import logging
from typing import Optional

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.providers.adapter import ProviderAdapter
from payment.canonical.services.providers.paystack.client import (
    PaystackClient,
)
from payment.canonical.services.providers.paystack.exceptions import (
    PaystackConfigurationError,
    PaystackError,
    PaystackRequestError,
    PaystackResponseError,
)
from payment.canonical.services.providers.result import ProviderResult


logger = logging.getLogger(__name__)


# Paystack status → canonical PaymentExecution.Status
_STATUS_MAP = {
    "success": PaymentExecution.Status.COMPLETED,
    "failed": PaymentExecution.Status.FAILED,
    "abandoned": PaymentExecution.Status.CANCELLED,
    "ongoing": PaymentExecution.Status.PENDING,
    "pending": PaymentExecution.Status.PENDING,
    "processing": PaymentExecution.Status.PROCESSING,
    "queued": PaymentExecution.Status.PROCESSING,
    "reversed": PaymentExecution.Status.CANCELLED,
    "processed": PaymentExecution.Status.COMPLETED,
}


class PaystackAdapter(ProviderAdapter):
    """Provider adapter backed by the Paystack API."""

    def __init__(self, client: Optional[PaystackClient] = None):
        self._client = client or PaystackClient()

    @property
    def provider_name(self) -> str:
        return "paystack"

    # ------------------------------------------------------------------
    # initiate
    # ------------------------------------------------------------------

    def initiate(self, execution: PaymentExecution) -> ProviderResult:
        """
        Trigger the provider-side operation for this execution.

        RECEIVE → POST /transaction/initialize
        DISBURSE (purpose != REFUND) → POST /transfer
        DISBURSE (purpose == REFUND) → POST /refund
        """
        payment = execution.payment
        if payment is None:
            return self._fail(
                "PaymentExecution has no Payment attached.",
                code="missing_payment",
            )

        try:
            if payment.direction == Payment.Direction.RECEIVE:
                return self._initiate_receive(execution, payment)
            if payment.direction == Payment.Direction.DISBURSE:
                if payment.purpose == Payment.Purpose.REFUND:
                    return self._initiate_refund(execution, payment)
                return self._initiate_disburse(execution, payment)
        except PaystackConfigurationError as exc:
            logger.error("Paystack not configured: %s", exc)
            return self._fail(str(exc), code="provider_not_configured")
        except PaystackRequestError as exc:
            logger.warning("Paystack network error: %s", exc)
            return ProviderResult(
                status=PaymentExecution.Status.PENDING,
                reconciliation_required=True,
                metadata={"error": str(exc)},
            )
        except PaystackResponseError as exc:
            logger.warning("Paystack rejected request: %s", exc)
            return self._fail(str(exc), code="provider_error")
        except PaystackError as exc:
            logger.exception("Unhandled Paystack error.")
            return self._fail(str(exc), code="provider_error")

        return self._fail(
            f"Unsupported payment direction: {payment.direction!r}",
            code="unsupported_direction",
        )

    def _initiate_receive(
        self,
        execution: PaymentExecution,
        payment: Payment,
    ) -> ProviderResult:
        """
        POST /transaction/initialize.

        Returns PENDING with the authorization URL. The customer
        must visit that URL to complete the charge. Paystack will
        notify via webhook when it settles.
        """
        body = {
            "email": self._email_for(payment),
            "amount": self._to_kobo(payment.amount),
            "currency": payment.currency,
            "reference": execution.reference,
            "metadata": {
                **(payment.metadata or {}),
                "payment_id": str(payment.pk),
                "execution_id": str(execution.pk),
            },
        }

        response = self._client.post(
            "/transaction/initialize",
            json=body,
        )

        data = response.get("data") or {}
        access_code = data.get("access_code")
        authorization_url = data.get("authorization_url")
        reference = data.get("reference") or execution.reference

        return ProviderResult(
            status=PaymentExecution.Status.PENDING,
            provider_reference=reference,
            reconciliation_required=True,
            metadata={
                "access_code": access_code,
                "authorization_url": authorization_url,
            },
        )

    def _initiate_disburse(
        self,
        execution: PaymentExecution,
        payment: Payment,
    ) -> ProviderResult:
        """
        POST /transfer.

        Requires a Paystack recipient code, resolved from the
        execution's instrument metadata.
        """
        recipient_code = self._resolve_recipient_code(execution)
        if not recipient_code:
            return self._fail(
                "Cannot disburse without a resolved recipient.",
                code="missing_recipient",
            )

        body = {
            "source": "balance",
            "amount": self._to_kobo(payment.amount),
            "currency": payment.currency,
            "recipient": recipient_code,
            "reference": execution.reference,
            "reason": payment.source_reference or "",
        }

        response = self._client.post("/transfer", json=body)
        data = response.get("data") or {}
        transfer_code = data.get("transfer_code")
        status = str(data.get("status") or "").lower()

        canonical_status = _STATUS_MAP.get(
            status, PaymentExecution.Status.PROCESSING
        )

        return ProviderResult(
            status=canonical_status,
            provider_reference=transfer_code or execution.reference,
            reconciliation_required=canonical_status
            in {
                PaymentExecution.Status.PENDING,
                PaymentExecution.Status.PROCESSING,
            },
            metadata={"transfer_code": transfer_code},
        )

    def _initiate_refund(
        self,
        execution: PaymentExecution,
        payment: Payment,
    ) -> ProviderResult:
        """
        POST /refund.

        Requires the original transaction reference, resolved from
        the original Payment's most recent COMPLETED execution.
        """
        original_payment_id = (payment.metadata or {}).get(
            "original_payment_id"
        )
        if not original_payment_id:
            return self._fail(
                "Cannot refund without original_payment_id in metadata.",
                code="missing_original_payment",
            )

        original_payment = Payment.objects.filter(
            pk=original_payment_id
        ).first()
        if original_payment is None:
            return self._fail(
                "Original payment for refund not found.",
                code="original_payment_not_found",
            )

        original_reference = self._resolve_provider_reference(
            original_payment
        )
        if not original_reference:
            return self._fail(
                "Original payment has no provider reference.",
                code="missing_provider_reference",
            )

        body = {
            "transaction": original_reference,
            "amount": self._to_kobo(payment.amount),
            "currency": payment.currency,
            "merchant_note": payment.source_reference or "",
        }

        response = self._client.post("/refund", json=body)
        data = response.get("data") or {}
        refund_reference = data.get("reference") or execution.reference
        status = str(data.get("status") or "").lower()

        canonical_status = _STATUS_MAP.get(
            status, PaymentExecution.Status.PROCESSING
        )

        return ProviderResult(
            status=canonical_status,
            provider_reference=refund_reference,
            reconciliation_required=canonical_status
            in {
                PaymentExecution.Status.PENDING,
                PaymentExecution.Status.PROCESSING,
            },
            metadata={"refund_reference": refund_reference},
        )

    # ------------------------------------------------------------------
    # get_status
    # ------------------------------------------------------------------

    def get_status(self, execution: PaymentExecution) -> ProviderResult:
        """GET the verify endpoint for this execution."""
        reference = execution.provider_reference or execution.reference
        payment = execution.payment
        direction = payment.direction if payment else None

        try:
            if direction == Payment.Direction.RECEIVE:
                response = self._client.get(
                    f"/transaction/verify/{reference}"
                )
            elif direction == Payment.Direction.DISBURSE:
                response = self._client.get(
                    f"/transfer/verify/{reference}"
                )
            else:
                return self._fail(
                    "Cannot verify without payment direction.",
                    code="unsupported_direction",
                )
        except PaystackConfigurationError as exc:
            return self._fail(str(exc), code="provider_not_configured")
        except PaystackRequestError as exc:
            return ProviderResult(
                status=PaymentExecution.Status.PENDING,
                reconciliation_required=True,
                metadata={"error": str(exc)},
            )
        except PaystackResponseError as exc:
            return self._fail(str(exc), code="provider_error")

        data = response.get("data") or {}
        status = str(data.get("status") or "").lower()
        canonical_status = _STATUS_MAP.get(
            status, PaymentExecution.Status.PENDING
        )

        return ProviderResult(
            status=canonical_status,
            provider_reference=(
                data.get("reference")
                or data.get("transfer_code")
                or reference
            ),
            reconciliation_required=canonical_status
            in {
                PaymentExecution.Status.PENDING,
                PaymentExecution.Status.PROCESSING,
            },
            metadata=data,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_kobo(amount) -> int:
        """Paystack works in minor units (kobo, cents)."""
        return int((amount * 100).to_integral_value())

    @staticmethod
    def _email_for(payment: Payment) -> str:
        metadata_email = (payment.metadata or {}).get("user_email")
        if metadata_email:
            return str(metadata_email)
        if payment.payer and payment.payer.email:
            return payment.payer.email
        return "no-reply@univa.example"

    @staticmethod
    def _resolve_recipient_code(
        execution: PaymentExecution,
    ) -> Optional[str]:
        instrument = execution.instrument
        if instrument is None:
            return None
        metadata = instrument.metadata or {}
        code = metadata.get("paystack_recipient_code")
        return str(code) if code else None

    @staticmethod
    def _resolve_provider_reference(payment: Payment) -> Optional[str]:
        completed = (
            payment.executions
            .filter(status=PaymentExecution.Status.COMPLETED)
            .order_by("-created_at")
            .first()
        )
        if completed is None:
            return None
        return completed.provider_reference or None

    @staticmethod
    def _fail(message: str, *, code: str) -> ProviderResult:
        return ProviderResult(
            status=PaymentExecution.Status.FAILED,
            failure_code=code,
            failure_reason=message,
            reconciliation_required=False,
            metadata={"error": message},
        )   
    
    def refund(
        self,
        execution: PaymentExecution,
    ) -> ProviderResult:
        """
        Refund a previously settled payment.

        Adapters that support refunds override this. The default
        implementation raises — callers must not assume refunds
        are universally supported.
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support refunds."
        )