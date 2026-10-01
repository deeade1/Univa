# apps/backend/banking/services/account_service.py

"""
Account service.

Orchestrates customer account creation. Every account is created
with:

    - a NUBAN derived from the customer's phone number
    - a BankingSecurity row (single source of truth for banking PINs)
    - optionally, a virtual account provisioned via the bank API layer

Account creation is atomic. If virtual account provisioning fails,
the whole operation rolls back — the customer either has a fully
working account or none at all.

NUBAN format
------------

Nigerian fintech convention (OPay, Moniepoint, PalmPay):

    phone_number = "08033334444"
    nuban_number = "8033334444"

The phone number without the leading zero IS the account number.
No bank code prefix, no check digit — the phone is the identifier.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.core import Account, Bank
from banking.models.security import BankingSecurity


logger = logging.getLogger(__name__)

User = get_user_model()


class AccountService:

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def create_account(
        *,
        user,
        bank: Bank | None = None,
        account_name: str | None = None,
        daily_limit=None,
        single_transaction_limit=None,
        created_by=None,
        provision_virtual_account: bool = False,
    ) -> Account:
        """
        Create a banking account for `user`.

        The account's NUBAN is the user's phone number with the leading
        zero stripped. `user.phone_number` is required and must be
        unique across the Account table.

        If `provision_virtual_account` is True, the account is also
        registered with the chosen bank's virtual-account provider
        (Paystack or Monnify). A provisioning failure rolls the whole
        operation back.
        """
        if user is None or user.pk is None:
            raise ValidationError("User is required.")

        if Account.objects.filter(user=user).exists():
            raise ValidationError(
                "This user already has a banking account."
            )

        # --------------------------------------------------------------
        # Phone number (required, becomes the account number)
        # --------------------------------------------------------------
        phone = AccountService._normalize_phone(
            getattr(user, "phone_number", None)
        )
        if not phone:
            raise ValidationError(
                "User must have a phone number to open an account."
            )

        if Account.objects.filter(phone_number=phone).exists():
            raise ValidationError(
                "An account already exists with this phone number."
            )

        nuban = AccountService._phone_to_nuban(phone)
        if not nuban:
            raise ValidationError(
                "Unable to derive a NUBAN from this phone number."
            )

        if Account.objects.filter(nuban_number=nuban).exists():
            raise ValidationError(
                "An account already exists with this account number."
            )

        # --------------------------------------------------------------
        # Bank
        # --------------------------------------------------------------
        if bank is None:
            bank = Bank.objects.filter(
                is_active=True, is_partner_bank=True
            ).order_by("-health_score", "current_daily_usage").first()
            if bank is None:
                raise ValidationError(
                    "No active partner bank available."
                )

        if not bank.is_active:
            raise ValidationError(f"Bank {bank.name} is not active.")

        # --------------------------------------------------------------
        # Account name
        # --------------------------------------------------------------
        if not account_name:
            full_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            )
            account_name = full_name or getattr(user, "email", "")

        if not account_name:
            raise ValidationError(
                "Unable to determine an account name for this user."
            )

        # --------------------------------------------------------------
        # Limits
        # --------------------------------------------------------------
        daily_limit = Decimal(
            str(daily_limit if daily_limit is not None else "50000.00")
        ).quantize(Decimal("0.01"))
        single_limit = Decimal(
            str(
                single_transaction_limit
                if single_transaction_limit is not None
                else "50000.00"
            )
        ).quantize(Decimal("0.01"))

        if daily_limit < Decimal("0.00"):
            raise ValidationError("Daily limit cannot be negative.")

        if single_limit < Decimal("0.00"):
            raise ValidationError(
                "Single transaction limit cannot be negative."
            )

        if single_limit > daily_limit:
            raise ValidationError(
                "Single transaction limit cannot exceed daily limit."
            )

        # --------------------------------------------------------------
        # Create the Account
        # --------------------------------------------------------------
        account = Account.objects.create(
            user=user,
            bank=bank,
            phone_number=phone,
            nuban_number=nuban,
            account_name=account_name,
            daily_limit=daily_limit,
            single_transaction_limit=single_limit,
            status=Account.STATUS_ACTIVE,
            is_system_account=False,
        )

        # --------------------------------------------------------------
        # BankingSecurity — single source of truth for PINs
        # --------------------------------------------------------------
        BankingSecurity.objects.get_or_create(user=user)

        # --------------------------------------------------------------
        # Virtual account provisioning (optional)
        # --------------------------------------------------------------
        if provision_virtual_account:
            from banking.services.bank_manager import BankAPIManager

            try:
                result = BankAPIManager.create_virtual_account(user)
            except Exception as exc:
                # Roll back the whole operation. Account creation and
                # virtual-account provisioning are one logical step.
                logger.exception(
                    "Virtual account provisioning failed for user %s",
                    user.pk,
                )
                raise ValidationError(
                    f"Virtual account provisioning failed: {exc}"
                ) from exc

            if result:
                account.provider_reference = result.get(
                    "reference", ""
                )
                account.save(update_fields=[
                    "provider_reference", "updated_at"
                ])

        logger.info(
            "Account created: user=%s bank=%s nuban=%s "
            "created_by=%s",
            user.pk,
            bank.pk,
            nuban,
            getattr(created_by, "pk", None),
        )

        return account

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_phone(phone) -> str:
        """
        Return digits-only phone string with leading country code
        stripped to the local 11-digit form (0XXXXXXXXXX).

        Accepts None, strings, and phonenumber_field PhoneNumber
        instances (whose __str__ is verbose).
        """
        if phone is None:
            return ""

        # phonenumber_field exposes national_number and country_code
        national = getattr(phone, "national_number", None)
        if national:
            digits = str(national)
        else:
            digits = re.sub(r"\D", "", str(phone))

        if not digits:
            return ""

        # Normalize to 0XXXXXXXXXX (11 digits)
        if len(digits) == 13 and digits.startswith("234"):
            digits = "0" + digits[3:]
        elif len(digits) == 10 and not digits.startswith("0"):
            digits = "0" + digits

        if not re.fullmatch(r"0\d{10}", digits):
            raise ValidationError(
                "Phone number must be a valid Nigerian number "
                "(e.g. 08033334444)."
            )

        return digits

    @staticmethod
    def _phone_to_nuban(phone: str) -> str:
        """
        Convert a normalized Nigerian phone number to a 10-digit NUBAN.

            08033334444  ->  8033334444
        """
        if not phone or not phone.startswith("0") or len(phone) != 11:
            return ""
        return phone[1:]  # strip leading zero