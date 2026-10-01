# apps/backend/banking/services/payment_gateway_service.py

"""
Payment gateway and USSD service.

Three concerns:

    GatewayRouter
        Selects the best PaymentGateway for a given operation.

    PaymentGatewayService
        HTTP dispatch to a gateway provider.

    USSDService
        Nigerian USSD banking state machine. Reads balances through
        AccountingManager (the canonical balance source) and delegates
        money movement to services that post through the ledger.

No money is posted directly by this module. USSD transfers call
PaymentService, which is the module that actually moves funds.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict

import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from banking.models.accounting import AccountingManager
from banking.models.payment_gateways import (
    PaymentGateway,
    USSDOperation,
    USSDSession,
)
from banking.models.payments import Transaction
from banking.models.security import BankingSecurity
from django.conf import settings


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


# ============================================================================
# GATEWAY ROUTER
# ============================================================================

class GatewayRouter:
    """Selects the best PaymentGateway for a given transaction."""

    @staticmethod
    def get_best_gateway(
        transaction_type: str,
        amount,
        bank_code: str | None = None,
    ) -> PaymentGateway | None:
        from django.db.models import Q

        gateways = PaymentGateway.objects.filter(
            is_active=True,
            supports_transfer=True,
        )

        if transaction_type == 'CARD':
            gateways = gateways.filter(supports_card=True)
        elif transaction_type == 'USSD':
            gateways = gateways.filter(supports_ussd=True)

        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError):
            amount = Decimal("0.00")

        scored = []
        for gateway in gateways:
            score = 0.0

            score += gateway.success_rate * 0.4
            score += gateway.uptime_percentage * 0.3

            response_score = max(0.0, 100.0 - gateway.average_response_time)
            score += response_score * 0.2

            if amount <= gateway.daily_transaction_limit:
                score += 10.0

            scored.append((gateway, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None


# ============================================================================
# PAYMENT GATEWAY SERVICE
# ============================================================================

class PaymentGatewayService:
    """HTTP dispatch to a configured PaymentGateway."""

    def __init__(self, gateway: PaymentGateway | None = None):
        self.gateway = gateway or self._get_default_gateway()
        self.session = requests.Session()

    @staticmethod
    def _get_default_gateway() -> PaymentGateway | None:
        return PaymentGateway.objects.filter(
            is_default=True, is_active=True
        ).first()

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------

    def transfer_funds(
        self,
        from_account,
        to_account,
        bank_code,
        amount,
        narration,
    ) -> dict:
        best = GatewayRouter.get_best_gateway(
            "BANK_TRANSFER", amount, bank_code
        )
        if not best:
            raise ValidationError("No suitable gateway available.")

        if best.provider == 'FLUTTERWAVE':
            return self._transfer_via_flutterwave(
                best, from_account, to_account,
                bank_code, amount, narration,
            )
        if best.provider == 'REMITA':
            return self._transfer_via_remita(
                best, from_account, to_account,
                bank_code, amount, narration,
            )
        if best.provider == 'INTERSWITCH':
            return self._transfer_via_interswitch(
                best, from_account, to_account,
                bank_code, amount, narration,
            )
        raise ValidationError(f"Unsupported provider: {best.provider}.")

    def _transfer_via_flutterwave(
        self, gateway, from_account, to_account,
        bank_code, amount, narration,
    ) -> dict:
        url = f"{gateway.base_url}/transfers"
        headers = {
            "Authorization": f"Bearer {gateway.secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "account_bank": bank_code,
            "account_number": to_account,
            "amount": str(amount),
            "narration": narration[:100],
            "currency": "NGN",
            "reference": (
                f"TF-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "callback_url": (
                f"{getattr(settings, 'BASE_URL', '')}"
                f"/api/webhooks/flutterwave/transfer"
            ),
            "debit_currency": "NGN",
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "success": True,
                "reference": data["data"]["reference"],
                "provider_reference": data["data"]["id"],
                "provider": "FLUTTERWAVE",
            }
        raise ValidationError(
            data.get("message", "Flutterwave transfer failed.")
        )

    def _transfer_via_remita(
        self, gateway, from_account, to_account,
        bank_code, amount, narration,
    ) -> dict:
        url = f"{gateway.base_url}/api/sps/core/bankTransfer/v2"
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        signature_string = (
            f"{gateway.public_key}{request_id}{timestamp}"
        )
        signature = hashlib.sha512(
            signature_string.encode()
        ).hexdigest()

        headers = {
            "PUBLICKEY": gateway.public_key,
            "REQUEST_ID": request_id,
            "REQUEST_TS": timestamp,
            "API_DETAILS_HASH": signature,
            "Content-Type": "application/json",
        }
        payload = {
            "accountNumber": to_account,
            "accountBank": bank_code,
            "amount": str(amount),
            "currency": "NGN",
            "narration": narration,
            "reference": (
                f"REM-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "senderName": "Univa Payments",
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return {
            "success": True,
            "reference": payload["reference"],
            "provider_reference": data.get("transactionRef"),
            "provider": "REMITA",
        }

    def _transfer_via_interswitch(
        self, gateway, from_account, to_account,
        bank_code, amount, narration,
    ) -> dict:
        url = (
            f"{gateway.base_url}"
            f"/api/v2/quickteller/payments/transfers"
        )
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        nonce = hashlib.sha256(
            str(timezone.now().timestamp()).encode()
        ).hexdigest()[:20]
        signature_string = f"{gateway.public_key}{nonce}{timestamp}"
        signature = hashlib.sha256(
            signature_string.encode()
        ).hexdigest()

        headers = {
            "Authorization": f"InterswitchAuth {gateway.public_key}",
            "Timestamp": timestamp,
            "Nonce": nonce,
            "Signature": signature,
            "SignatureMethod": "SHA256",
            "Content-Type": "application/json",
        }
        payload = {
            "mac": str(uuid.uuid4()),
            "merchantId": gateway.public_key,
            "payments": [{
                "amount": str(int(Decimal(amount) * 100)),
                "customerId": from_account,
                "paymentCode": "402",
                "customerEmail": "notifications@univa.com",
                "customerName": "Univa Customer",
                "transactionRef": (
                    f"ISW-"
                    f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
                ),
                "narration": narration,
            }],
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()

        return {
            "success": True,
            "reference": payload["payments"][0]["transactionRef"],
            "provider": "INTERSWITCH",
        }

    # ------------------------------------------------------------------
    # USSD charge initiation (Flutterwave)
    # ------------------------------------------------------------------

    def initiate_ussd_payment(
        self, amount, phone_number, provider_code,
    ) -> dict:
        gateway = PaymentGateway.objects.filter(
            provider='FLUTTERWAVE',
            is_active=True,
        ).first()
        if not gateway:
            raise ValidationError("USSD gateway not available.")

        url = f"{gateway.base_url}/charges?type=ussd"
        headers = {
            "Authorization": f"Bearer {gateway.secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "tx_ref": (
                f"USSD-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "amount": str(amount),
            "currency": "NGN",
            "payment_options": "ussd",
            "redirect_url": (
                f"{getattr(settings, 'BASE_URL', '')}"
                f"/api/payments/callback"
            ),
            "customer": {
                "email": f"{phone_number}@ussd.univa.com",
                "phonenumber": phone_number,
                "name": "USSD Customer",
            },
            "customizations": {
                "title": "Univa USSD Payment",
                "description": "Payment via USSD",
            },
            "meta": {"provider": provider_code},
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "success": True,
                "reference": data["data"]["tx_ref"],
                "ussd_code": data["data"]["meta"]["ussd_code"],
                "provider": "FLUTTERWAVE",
            }
        raise ValidationError(
            data.get("message", "USSD payment initiation failed.")
        )


# ============================================================================
# USSD SERVICE
# ============================================================================

class USSDService:
    """USSD banking state machine for Nigerian codes (*737#, *894#, ...)."""

    USSD_PROVIDERS = {
        'GTB': r'^\*737.*#$',
        'FIDELITY': r'^\*770.*#$',
        'ACCESS': r'^\*901.*#$',
        'UBA': r'^\*919.*#$',
        'FIRSTBANK': r'^\*894.*#$',
        'ZENITH': r'^\*966.*#$',
        'UNION': r'^\*826.*#$',
        'STERLING': r'^\*822.*#$',
    }

    def __init__(self):
        self.session_model = USSDSession

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def process_ussd_request(
        self,
        phone_number: str,
        ussd_code: str,
        session_id: str | None = None,
    ) -> Dict:
        ussd_code = ussd_code.strip()

        if not self._is_valid_ussd(ussd_code):
            return self._format_response("Invalid USSD code format")

        session = self._get_or_create_session(phone_number, session_id)

        if session.is_expired:
            return self._format_response(
                "Session expired. Please start again."
            )

        command = self._parse_ussd_command(ussd_code)

        handlers = {
            'main': self._handle_main_menu,
            'balance': self._handle_balance_check,
            'transfer': self._handle_transfer,
            'airtime': self._handle_airtime_purchase,
            'data': self._handle_data_purchase,
            'bill': self._handle_bill_payment,
        }
        handler = handlers.get(command['action'])
        if not handler:
            return self._format_response("Invalid option selected")

        return handler(session, command)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_main_menu(self, session, command) -> Dict:
        menu_text = (
            "Welcome to Univa Bank USSD Banking\n\n"
            "1. Check Balance\n"
            "2. Transfer Money\n"
            "3. Buy Airtime\n"
            "4. Buy Data\n"
            "5. Pay Bills\n"
            "6. Mini Statement\n"
            "7. Change PIN\n"
            "8. Help\n\n"
            "Reply with option number"
        )
        session.current_menu = 'main'
        session.save(update_fields=['current_menu', 'last_activity'])
        return self._format_response(menu_text, continue_session=True)

    def _handle_balance_check(self, session, command) -> Dict:
        try:
            user = session.user
            if not user:
                return self._format_response(
                    "Please login to your account first"
                )

            account = user.banking_account
            balance = AccountingManager.get_account_balance(account)

            response = (
                f"Account Balance\n"
                f"Available: N{balance:,.2f}\n"
                f"Account: {account.phone_number or account.nuban_number}\n\n"
                f"1. Back\n2. Main Menu\n3. End"
            )

            session.current_menu = 'balance_result'
            session.save(
                update_fields=['current_menu', 'last_activity']
            )
            return self._format_response(
                response, continue_session=True
            )

        except Exception as exc:
            logger.exception("USSD balance check failed")
            return self._format_response(
                "Error checking balance. Please try again."
            )

    def _handle_transfer(self, session, command) -> Dict:
        if 'step' not in session.session_data:
            session.session_data['step'] = 1
            session.current_menu = 'transfer_amount'
            session.save(
                update_fields=[
                    'session_data', 'current_menu', 'last_activity'
                ]
            )
            return self._format_response(
                "Enter amount to transfer:\n"
                "(Format: 1000 or 1000.50)\n\n"
                "0. Cancel",
                continue_session=True,
            )

        if session.session_data['step'] == 1:
            try:
                amount = Decimal(command.get('input', '0'))
            except (TypeError, ValueError):
                return self._format_response(
                    "Invalid amount format. Please try again."
                )

            if amount <= 0:
                return self._format_response(
                    "Invalid amount. Please enter a positive amount."
                )

            account = session.user.banking_account

            if amount > account.single_transaction_limit:
                return self._format_response(
                    "Amount exceeds single transaction limit."
                )

            today_total = (
                Transaction.objects
                .filter(
                    account=account,
                    status=Transaction.SUCCESS,
                    created_at__date=timezone.now().date(),
                )
                .aggregate(total=Sum('amount'))['total']
                or Decimal('0.00')
            )

            if today_total + amount > account.daily_limit:
                return self._format_response(
                    "Daily transfer limit exceeded."
                )

            session.session_data['amount'] = str(amount)
            session.session_data['step'] = 2
            session.current_menu = 'transfer_account'
            session.save(
                update_fields=[
                    'session_data', 'current_menu', 'last_activity'
                ]
            )
            return self._format_response(
                f"Transfer Amount: N{amount:,.2f}\n"
                "Enter recipient account number:\n\n"
                "0. Cancel\n00. Previous",
                continue_session=True,
            )

        if session.session_data['step'] == 2:
            account_number = command.get('input', '').strip()
            if not re.match(r'^\d{10}$', account_number):
                return self._format_response(
                    "Invalid account number. Must be 10 digits."
                )

            session.session_data['account_number'] = account_number
            session.session_data['step'] = 3
            session.current_menu = 'transfer_confirm'
            session.save(
                update_fields=[
                    'session_data', 'current_menu', 'last_activity'
                ]
            )
            return self._format_response(
                f"Transfer Details:\n"
                f"Amount: N{Decimal(session.session_data['amount']):,.2f}\n"
                f"To: {account_number}\n\n"
                "Enter PIN to confirm:\n\n"
                "0. Cancel\n00. Previous",
                continue_session=True,
            )

        if session.session_data['step'] == 3:
            pin = command.get('input', '')

            try:
                security = BankingSecurity.objects.get(user=session.user)
            except BankingSecurity.DoesNotExist:
                return self._format_response(
                    "Banking PIN not configured. Please visit a branch."
                )

            if not security.check_pin(pin):
                return self._format_response(
                    "Invalid PIN. Please try again."
                )

            amount = Decimal(session.session_data['amount'])
            account_number = session.session_data['account_number']

            # Clear session state AFTER reading
            session.session_data = {}
            session.current_menu = 'main'
            session.save(
                update_fields=[
                    'session_data', 'current_menu', 'last_activity'
                ]
            )

            # Delegate to PaymentService (which posts the ledger)
            try:
                from banking.services.payment_service import PaymentService

                payment_service = PaymentService()
                transfer_result = payment_service.transfer_funds_external(
                    sender=session.user,
                    sender_account=session.user.banking_account,
                    recipient_account_number=account_number,
                    recipient_bank_code='',
                    recipient_name='USSD Transfer',
                    amount=amount,
                    narration=f"USSD Transfer from {session.phone_number}",
                )
            except Exception as exc:
                logger.exception("USSD transfer failed")
                return self._format_response(
                    f"Transfer failed: {exc}"
                )

            response = (
                f"Transfer Successful!\n"
                f"Reference: {transfer_result.reference}\n"
                f"Amount: N{amount:,.2f}\n\n"
                "1. New Transfer\n2. Main Menu\n3. End"
            )
            return self._format_response(
                response, continue_session=True
            )

        return self._format_response("Invalid transfer step")

    def _handle_airtime_purchase(self, session, command) -> Dict:
        raise NotImplementedError(
            "USSD airtime flow not yet implemented."
        )

    def _handle_data_purchase(self, session, command) -> Dict:
        raise NotImplementedError(
            "USSD data flow not yet implemented."
        )

    def _handle_bill_payment(self, session, command) -> Dict:
        raise NotImplementedError(
            "USSD bill payment flow not yet implemented."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_response(
        self, text: str, continue_session: bool = False,
    ) -> Dict:
        return {
            'response': text,
            'continue_session': continue_session,
            'timestamp': timezone.now().isoformat(),
        }

    def _is_valid_ussd(self, ussd_code: str) -> bool:
        return bool(re.match(r'^\*\d{3,}(?:\*\d+)*#$', ussd_code))

    def _parse_ussd_command(self, ussd_code: str) -> Dict:
        cleaned = ussd_code.strip('*#')
        parts = cleaned.split('*')
        return {
            'action': parts[0] if parts else '',
            'parameters': parts[1:] if len(parts) > 1 else [],
            'input': parts[-1] if parts else '',
        }

    def _get_or_create_session(
        self, phone_number: str, session_id: str | None = None,
    ) -> USSDSession:
        if session_id:
            try:
                session = self.session_model.objects.get(
                    session_id=session_id,
                    phone_number=phone_number,
                    is_active=True,
                )
                session.last_activity = timezone.now()
                session.save(update_fields=['last_activity'])
                return session
            except self.session_model.DoesNotExist:
                pass

        session = self.session_model.objects.create(
            phone_number=phone_number,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        User = get_user_model()
        try:
            user = User.objects.get(phone_number=phone_number)
            session.user = user
            session.save(update_fields=['user'])
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        return session