"""
Univa Wallet Gateway Webhooks.

This module handles webhook callbacks for Univa wallet payments.
"""

import json
import logging

from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def univa_webhook(request):
    """
    Handle webhook callbacks for Univa wallet payments.

    This webhook receives confirmation from the Banking app
    when a wallet transaction is completed.
    """
    try:
        # Get webhook payload
        payload = json.loads(request.body)

        logger.info("Received Univa webhook: %s", payload)

        # Extract data
        transaction_reference = payload.get("reference")
        status = payload.get("status")
        amount = Decimal(str(payload.get("amount", 0)))
        user_id = payload.get("user_id")

        if not transaction_reference:
            logger.error("Missing transaction reference in webhook")
            return JsonResponse(
                {"success": False, "error": "Missing transaction reference"},
                status=400,
            )

        # Update Payment model
        try:
            from payment.models import Transaction

            transaction = Transaction.objects.get(reference=transaction_reference)
            
            if status == "completed":
                transaction.status = "COMPLETED"
            elif status == "failed":
                transaction.status = "FAILED"
            else:
                transaction.status = status.upper()
            
            transaction.save()
            
            # Record transaction event
            from payment.models import TransactionEvent
            
            TransactionEvent.objects.create(
                transaction=transaction,
                event_type="WEBHOOK_RECEIVED",
                data=payload,
            )

        except Transaction.DoesNotExist:
            logger.warning("Transaction not found for reference: %s", transaction_reference)

        return JsonResponse(
            {
                "success": True,
                "message": "Webhook processed successfully",
            },
            status=200,
        )

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON payload: %s", exc)
        return JsonResponse(
            {"success": False, "error": "Invalid JSON payload"},
            status=400,
        )

    except Exception as exc:
        logger.exception("Error processing Univa webhook: %s", exc)
        return JsonResponse(
            {"success": False, "error": str(exc)},
            status=500,
        )


__all__ = [
    "univa_webhook",
]