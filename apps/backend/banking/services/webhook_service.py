# apps/backend/banking/services/webhook_service.py
import hashlib
import hmac
import json
import logging
from threading import Thread
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db import transaction

import requests
from ..models.compliance import Webhook, WebhookDelivery
from ..models.core import Account
from ..models.integrations import APITransactionLog

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        self.timeout = getattr(settings, 'WEBHOOK_TIMEOUT', 10)

    # ---------------- Webhook Delivery ----------------
    def send_webhook(self, event_type, payload, recipient_url=None):
        """Send webhook asynchronously"""
        webhooks = Webhook.objects.filter(event_type=event_type, is_active=True)
        if recipient_url:
            webhooks = webhooks.filter(url=recipient_url)

        for webhook in webhooks:
            thread = Thread(target=self._deliver_webhook_sync, args=(webhook.id, payload))
            thread.daemon = True
            thread.start()

    def _deliver_webhook_sync(self, webhook_id, payload, attempt=1, max_attempts=3):
        """Synchronous webhook delivery with retries"""
        try:
            webhook = Webhook.objects.get(id=webhook_id)
            signature = self._generate_signature(webhook.secret, payload)
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'User-Agent': 'BankingAPI/1.0.0',
                'X-Event-Type': webhook.event_type,
            }

            response = requests.post(webhook.url, json=payload, headers=headers, timeout=self.timeout)

            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                payload=payload,
                response_code=response.status_code,
                response_body=response.text,
                attempts=attempt,
                delivered=200 <= response.status_code < 300
            )

            if not delivery.delivered and response.status_code >= 500 and attempt < max_attempts:
                import time; time.sleep(60 * attempt)
                self._deliver_webhook_sync(webhook_id, payload, attempt + 1, max_attempts)
                return

            webhook.last_triggered = timezone.now()
            webhook.save(update_fields=['last_triggered'])
            logger.info(f"Webhook delivered: {webhook.url} - {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook delivery failed: {str(e)}")
            WebhookDelivery.objects.create(
                webhook_id=webhook_id,
                payload=payload,
                response_code=None,
                response_body=str(e),
                attempts=attempt,
                delivered=False
            )
            if attempt < max_attempts:
                import time; time.sleep(60 * attempt)
                self._deliver_webhook_sync(webhook_id, payload, attempt + 1, max_attempts)

    def _generate_signature(self, secret, payload):
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hmac.new(secret.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

    def verify_incoming_webhook(self, request, expected_secret):
        signature = request.headers.get('X-Webhook-Signature')
        if not signature:
            return False
        payload = getattr(request, 'data', json.loads(request.body))
        expected_signature = self._generate_signature(expected_secret, payload)
        return hmac.compare_digest(signature, expected_signature)

    # ---------------- Reconciliation ----------------
    @transaction.atomic
    def reconcile_incoming_payment(self, provider, payload):
        """
        Reconcile incoming payment for OPay-style internal wallets.
        Returns a dict with keys: status, account_id, amount, reason
        """
        try:
            # Extract reference and amount depending on provider
            if provider.lower() == "paystack":
                ref = payload.get("data", {}).get("reference")
                amount = Decimal(payload.get("data", {}).get("amount", 0)) / 100  # kobo → NGN
            elif provider.lower() == "monnify":
                ref = payload.get("paymentReference")
                amount = Decimal(payload.get("amountPaid", 0))
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            if not ref or amount <= 0:
                return {"status": "failed", "reason": "Invalid payload"}

            # Check for duplicate transaction
            if APITransactionLog.objects.filter(reference=ref).exists():
                return {"status": "skipped"}

            # Map to internal account (OPay-style)
            # Example: payload.customer.email
            customer_email = payload.get("data", {}).get("customer", {}).get("email") or payload.get("customerEmail")
            account = Account.objects.select_for_update().filter(user__user__email=customer_email).first()
            if not account:
                return {"status": "failed", "reason": "Account not found"}

           

            # Log transaction
            APITransactionLog.objects.create(
                integration=None,
                endpoint=f"{provider}/webhook",
                method="POST",
                request_body=payload,
                response_body={"credited_amount": float(amount)},
                http_status=200,
                reference=ref,
                external_reference=ref,
                started_at=timezone.now(),
                completed_at=timezone.now(),
                is_successful=True,
                duration_ms=0
            )

            # Trigger outgoing webhooks if any
            self.send_webhook(event_type="payment_credited", payload={
                "account_id": account.id,
                "amount": float(amount),
                "provider": provider,
                "reference": ref
            })

            return {"status": "success", "account_id": account.id, "amount": float(amount)}

        except Exception as e:
            logger.error(f"Reconciliation error: {str(e)}")
            return {"status": "failed", "reason": str(e)}
