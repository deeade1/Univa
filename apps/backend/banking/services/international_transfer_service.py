# apps/backend/banking/services/international_transfer_service.py

"""
International transfer service.

Orchestrates cross-border remittance from a customer Naira account
to a remittance provider for FX conversion and payout.

Accounting model (Nigerian IMTO convention)
-------------------------------------------

    principal:  customer_account -> SETTLEMENT   (source_amount)
    fee:        customer_account -> FEE          (platform_fee)

The customer's Naira lands in the designated Univa Settlement account
where it waits for FX conversion and payout by the remittance provider.
This mirrors the CBN requirement that IMTO flows pass through a
declared settlement account rather than a generic suspense account.

`provider_fee` is deducted from the target side (the recipient
receives `target_amount` minus provider fee), so it does not produce
a Naira journal at this stage. FX conversion and payout are handled
out of band against the settlement account.

All ledger posting goes through:

    banking.models.accounting.AccountingManager.create_double_entry
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.core import Account
from banking.models.payments import Transaction
from banking.models.scheduled import InternationalTransfer


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class InternationalTransferService:
    """Service layer for international transfer initiation."""

    # ------------------------------------------------------------------
    # INITIATE
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def initiate_transfer(
        *,
        sender,
        source_account: Account,
        provider,
        transfer_type: str,
        source_amount,
        source_currency: str,
        target_currency: str,
        exchange_rate,
        payout_method: str,
        recipient_name: str,
        recipient_phone: str,
        recipient_email: str = "",
        recipient_country: str = "",
        recipient_bank: str = "",
        recipient_account: str = "",
        purpose_of_remittance: str = "",
        source_of_funds: str = "",
        provider_fee=None,
        platform_fee=None,
    ) -> InternationalTransfer:
        """
        Initiate an international transfer.

        Posts:

            principal: customer_account -> SETTLEMENT  (source_amount)
            fee:       customer_account -> FEE         (platform_fee)

        Returns the persisted InternationalTransfer with both journals
        linked.
        """
        # --------------------------------------------------------------
        # Validate sender / source account
        # --------------------------------------------------------------
        if sender is None or sender.pk is None:
            raise ValidationError("Sender is required.")

        if source_account is None or source_account.pk is None:
            raise ValidationError("Source account is required.")

        if source_account.user_id != sender.pk:
            raise ValidationError(
                "Source account does not belong to this sender."
            )

        if source_account.is_system_account:
            raise ValidationError(
                "Source account cannot be a system account."
            )

        if source_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Source account is not active.")

        # --------------------------------------------------------------
        # Validate transfer type / payout method
        # --------------------------------------------------------------
        valid_transfer_types = {
            choice[0] for choice in InternationalTransfer.TRANSFER_TYPES
        }
        if transfer_type not in valid_transfer_types:
            raise ValidationError(
                f"Invalid transfer type: {transfer_type}."
            )

        valid_payouts = {
            choice[0] for choice in InternationalTransfer.PAYOUT_METHODS
        }
        if payout_method not in valid_payouts:
            raise ValidationError(
                f"Invalid payout method: {payout_method}."
            )

        # --------------------------------------------------------------
        # Validate provider
        # --------------------------------------------------------------
        if provider is None or provider.pk is None:
            raise ValidationError("Remittance provider is required.")

        if not provider.is_active:
            raise ValidationError("Remittance provider is not active.")

        # --------------------------------------------------------------
        # Validate amounts
        # --------------------------------------------------------------
        source_amount = InternationalTransferService._validate_amount(
            source_amount
        )

        if source_amount < provider.min_amount:
            raise ValidationError(
                f"Source amount is below the provider minimum of "
                f"{provider.min_amount}."
            )

        if source_amount > provider.max_amount:
            raise ValidationError(
                f"Source amount exceeds the provider maximum of "
                f"{provider.max_amount}."
            )

        try:
            exchange_rate = Decimal(str(exchange_rate))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid exchange rate.") from exc

        if not exchange_rate.is_finite() or exchange_rate <= Decimal("0"):
            raise ValidationError(
                "Exchange rate must be greater than zero."
            )

        provider_fee = InternationalTransferService._validate_amount(
            provider_fee if provider_fee is not None else Decimal("0.00"),
            allow_zero=True,
        )

        platform_fee = InternationalTransferService._validate_amount(
            platform_fee if platform_fee is not None else Decimal("0.00"),
            allow_zero=True,
        )

        # target_amount is what the recipient receives.
        # provider_fee is deducted on the target side.
        gross_target = (source_amount * exchange_rate).quantize(
            MONEY_QUANTUM
        )
        target_amount = (gross_target - provider_fee).quantize(
            MONEY_QUANTUM
        )

        if target_amount <= Decimal("0.00"):
            raise ValidationError(
                "Provider fee exceeds the target amount."
            )

        total_debit = (source_amount + platform_fee).quantize(
            MONEY_QUANTUM
        )

        if source_account.get_balance() < total_debit:
            raise ValidationError(
                "Insufficient funds in source account."
            )

        # --------------------------------------------------------------
        # Resolve system accounts
        # --------------------------------------------------------------
        settlement_account = AccountingManager.get_settlement_account()
        fee_account = AccountingManager.get_fee_account()

        # --------------------------------------------------------------
        # Principal journal: customer -> SETTLEMENT
        # --------------------------------------------------------------
        principal_txn = Transaction.objects.create(
            account=source_account,
            amount=source_amount,
            type=Transaction.TRANSFER,
            narration=(
                f"International transfer to {recipient_name} "
                f"({provider.name})"
            ),
            recipient_name=recipient_name,
            recipient_account_number=recipient_account,
            status=Transaction.PENDING,
        )

        principal_journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=source_account,
            credit_account=settlement_account,
            amount=source_amount,
            description=(
                f"International transfer: {provider.name} -> "
                f"{recipient_name}"
            ),
            journal_type=AccountingJournal.TRANSFER,
            created_by=sender,
        )

        principal_txn.journal = principal_journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = source_account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Fee journal: customer -> FEE (only if platform_fee > 0)
        # --------------------------------------------------------------
        fee_journal = None
        if platform_fee > Decimal("0.00"):
            fee_txn = Transaction.objects.create(
                account=source_account,
                amount=platform_fee,
                type=Transaction.FEE,
                narration=(
                    f"International transfer fee ({provider.name})"
                ),
                fee=platform_fee,
                status=Transaction.PENDING,
            )

            fee_journal = AccountingManager.create_double_entry(
                transaction=fee_txn,
                debit_account=source_account,
                credit_account=fee_account,
                amount=platform_fee,
                description=(
                    f"International transfer fee: {provider.name}"
                ),
                journal_type=AccountingJournal.FEE,
                created_by=sender,
            )

            fee_txn.journal = fee_journal
            fee_txn.status = Transaction.SUCCESS
            fee_txn.balance_after = source_account.get_balance()
            fee_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

        # --------------------------------------------------------------
        # Business record
        # --------------------------------------------------------------
        transfer = InternationalTransfer.objects.create(
            sender=sender,
            recipient=None,
            source_account=source_account,
            journal=principal_journal,
            fee_journal=fee_journal,
            transfer_type=transfer_type,
            provider=provider,
            source_amount=source_amount,
            source_currency=source_currency,
            target_amount=target_amount,
            target_currency=target_currency,
            exchange_rate=exchange_rate,
            provider_fee=provider_fee,
            platform_fee=platform_fee,
            payout_method=payout_method,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
            recipient_country=recipient_country,
            recipient_bank=recipient_bank,
            recipient_account=recipient_account,
            purpose_of_remittance=purpose_of_remittance,
            source_of_funds=source_of_funds,
            status=InternationalTransfer.STATUS_CHOICES[0][0],  # PENDING
            initiated_at=timezone.now(),
        )

        logger.info(
            "International transfer %s: sender=%s provider=%s "
            "source=%s %s target=%s %s principal_journal=%s "
            "fee_journal=%s",
            transfer.reference,
            sender.pk,
            provider.pk,
            source_amount,
            source_currency,
            target_amount,
            target_currency,
            principal_journal.pk,
            fee_journal.pk if fee_journal else None,
        )

        return transfer

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount, allow_zero: bool = False) -> Decimal:
        if amount is None:
            if allow_zero:
                return Decimal("0.00")
            raise ValidationError("Amount is required.")

        try:
            value = Decimal(str(amount))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid amount.") from exc

        if not value.is_finite():
            raise ValidationError("Amount must be finite.")

        if allow_zero:
            if value < Decimal("0.00"):
                raise ValidationError("Amount cannot be negative.")
        else:
            if value <= Decimal("0.00"):
                raise ValidationError(
                    "Amount must be greater than zero."
                )

        return value.quantize(MONEY_QUANTUM)