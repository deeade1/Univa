import logging
import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

from banking.models.core import Bank
from banking.models.integrations import APITransactionLog

logger = logging.getLogger(__name__)


class BankAPIManager:
    """
    OPay-style Virtual Account Manager

    - Internal wallet abstraction
    - Paystack → Monnify failover
    - Provider details NEVER exposed to user
    """

    PROVIDER_PRIORITY = ["PAYSTACK", "MONNIFY"]

    # ---------------------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------------------

    @staticmethod
    def create_virtual_account(user):
        last_error = None

        for _ in range(3):  # hard cap
            bank = BankAPIManager._select_partner_bank()
            if not bank:
                break

            try:
                provider = bank.virtual_account_provider

                if provider == "PAYSTACK":
                    result = BankAPIManager._create_paystack_account(user, bank)
                elif provider == "MONNIFY":
                    result = BankAPIManager._create_monnify_account(user, bank)
                else:
                    raise ValueError("Unsupported provider")

                bank.increment_virtual_account_usage()
                bank.record_success()

                return {
                    "account_number": result["account_number"],
                    "account_name": result["account_name"],
                    "bank_name": "Univa Wallet",
                    "bank_code": "UNIVA",
                    "reference": result["provider_reference"],
                }

            except Exception as e:
                bank.record_failure()
                last_error = e
                continue

        raise ValueError(f"Virtual account creation failed: {last_error}")

    # ---------------------------------------------------------------------
    # PROVIDER IMPLEMENTATIONS
    # ---------------------------------------------------------------------

    @staticmethod
    def _create_paystack_account(user, bank):
        url = "https://api.paystack.co/dedicated_account"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "customer": {
                "email": user.user.email,
                "first_name": user.user.first_name,
                "last_name": user.user.last_name,
                "phone": user.user.phone_number,
            },
            "preferred_bank": bank.code.lower(),
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("status"):
            raise ValueError(data.get("message"))

        acc = data["data"]

        return {
            "account_number": acc["account_number"],
            "account_name": f"{user.user.first_name} {user.user.last_name}",
            "provider_reference": acc["customer"]["customer_code"],
            "provider": "PAYSTACK",
        }

    @staticmethod
    def _create_monnify_account(user, bank):
        # Auth
        auth = requests.post(
            f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login",
            auth=(settings.MONNIFY_API_KEY, settings.MONNIFY_SECRET_KEY),
            timeout=30,
        )
        auth.raise_for_status()
        token = auth.json()["responseBody"]["accessToken"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        reference = f"UNIVA-{user.id}-{int(timezone.now().timestamp())}"

        payload = {
            "accountReference": reference,
            "accountName": f"{user.user.first_name} {user.user.last_name}",
            "currencyCode": "NGN",
            "contractCode": settings.MONNIFY_CONTRACT_CODE,
            "customerEmail": user.user.email,
            "customerName": f"{user.user.first_name} {user.user.last_name}",
            "preferredBanks": [bank.code],
        }

        response = requests.post(
            f"{settings.MONNIFY_BASE_URL}/api/v2/bank-transfer/reserved-accounts",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("requestSuccessful"):
            raise ValueError(data.get("responseMessage"))

        acc = data["responseBody"]["accounts"][0]

        return {
            "account_number": acc["accountNumber"],
            "account_name": payload["accountName"],
            "provider_reference": reference,
            "provider": "MONNIFY",
        }

    # ---------------------------------------------------------------------
    # TRANSFERS (UNCHANGED)
    # ---------------------------------------------------------------------
    
    @staticmethod
    def transfer_funds(from_account, to_account, to_bank_code, amount, narration):
        provider = settings.DEFAULT_TRANSFER_PROVIDER or "paystack"

        provider_map = {
            "paystack": BankAPIManager._transfer_via_paystack,
            "monnify": BankAPIManager._transfer_via_monnify,
        }

        if provider not in provider_map:
            raise ValueError(f"Unsupported transfer provider: {provider}")

        try:
            return provider_map[provider](
                from_account, to_account, to_bank_code, amount, narration
            )
        except Exception:
            fallback = "monnify" if provider == "paystack" else "paystack"
            return provider_map[fallback](
                from_account, to_account, to_bank_code, amount, narration
            )

    @staticmethod
    def _transfer_via_paystack(from_account, to_account, to_bank_code, amount, narration):
        url = "https://api.paystack.co/transfer"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "source": "balance",
            "amount": int(Decimal(amount) * 100),
            "recipient": to_account,
            "reason": narration,
            "reference": f"TF-{int(timezone.now().timestamp())}",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        return {
            "success": data.get("status"),
            "reference": data["data"]["reference"],
        }
        
    @staticmethod
    def _transfer_via_monnify(from_account, to_account, to_bank_code, amount, narration):
        """
        Initiate a bank transfer via Monnify.

        Two-step flow: authenticate, then POST the disbursement.
        """
        # --------------------------------------------------------------
        # 1. Authenticate
        # --------------------------------------------------------------
        auth = requests.post(
            f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login",
            auth=(
                settings.MONNIFY_API_KEY,
                settings.MONNIFY_SECRET_KEY,
            ),
            timeout=30,
        )
        auth.raise_for_status()
        token = auth.json()["responseBody"]["accessToken"]

        # --------------------------------------------------------------
        # 2. Disbursement
        # --------------------------------------------------------------
        reference = (
            f"UNIVA-TF-{int(timezone.now().timestamp())}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        payload = {
            "amount": float(Decimal(amount)),
            "reference": reference,
            "narration": narration,
            "destinationBankCode": to_bank_code,
            "destinationAccountNumber": to_account,
            "currency": "NGN",
            "sourceAccountNumber": from_account,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{settings.MONNIFY_BASE_URL}/api/v2/disbursements/single",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("requestSuccessful"):
            raise ValueError(
                data.get("responseMessage", "Monnify transfer failed.")
            )

        return {
            "success": True,
            "reference": reference,
            "provider_reference": data.get("responseBody", {}).get(
                "reference", reference
            ),
        }

    # ---------------------------------------------------------------------
    # LOGGING
    # ---------------------------------------------------------------------

    @staticmethod
    def _log_api_call(endpoint, request, response, reference, is_successful=True):
        APITransactionLog.objects.create(
            integration=None,
            endpoint=endpoint,
            method="POST",
            request_body=request,
            response_body=response,
            http_status=200 if is_successful else 500,
            reference=reference,
            external_reference=response.get("provider_reference"),
            started_at=timezone.now(),
            completed_at=timezone.now(),
            is_successful=is_successful,
            duration_ms=0,
        )


    @staticmethod
    def _select_partner_bank():
        banks = Bank.objects.filter(
            is_active=True,
            is_partner_bank=True,
        ).order_by(
            "-health_score",
            "current_daily_usage"
        )

        for bank in banks:
            if bank.is_available_for_virtual_accounts:
                return bank

        return None
