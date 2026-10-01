# apps/backend/banking/services/compliance_service.py

"""
Compliance service.

Two money-movement paths:

    Card issuance fee   customer_account -> FEE
    ATM withdrawal      customer_account -> SETTLEMENT
    ATM deposit         SETTLEMENT -> customer_account

Every path posts through:

    banking.models.accounting.AccountingManager.create_double_entry

Card activation, blocking, and unblocking are status-only operations
and do not move money.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.compliance import (
    ATMCard,
    ATMTransaction,
    CardIssuance,
)
from banking.models.core import Account
from banking.models.payments import Transaction


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


# ============================================================================
# CARD SERVICE
# ============================================================================

class CardService:
    """Issuance and lifecycle of ATM cards."""

    CARD_TYPES = {
        'VISA': {
            'bin': '4',
            'length': 16,
            'issuer': 'Visa International',
        },
        'MASTERCARD': {
            'bin': '5',
            'length': 16,
            'issuer': 'MasterCard Worldwide',
        },
        'VERVE': {
            'bin': '5061',
            'length': 16,
            'issuer': 'Interswitch',
        },
    }

    CARD_ISSUANCE_FEE = Decimal("1500.00")

    # ------------------------------------------------------------------
    # REQUEST
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def request_card(
        *,
        user,
        account: Account,
        card_type: str = 'VISA',
        delivery_address: str = "",
        requested_by=None,
    ) -> dict:
        """
        Request a new ATM card.

        Posts the issuance fee:

            customer_account -> FEE  (CARD_ISSUANCE_FEE)

        Returns a dict with 'card', 'issuance', 'transaction', 'journal'.
        """
        if card_type not in CardService.CARD_TYPES:
            raise ValidationError(f"Invalid card type: {card_type}.")

        if user is None or user.pk is None:
            raise ValidationError("User is required.")

        if account is None or account.pk is None:
            raise ValidationError("Account is required.")

        if account.user_id != user.pk:
            raise ValidationError(
                "Account does not belong to this user."
            )

        if account.is_system_account:
            raise ValidationError(
                "Account cannot be a system account."
            )

        if account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Account is not active.")

        if not CardService._is_eligible_for_card(user, account):
            raise ValidationError(
                "User is not eligible for card issuance."
            )

        existing = ATMCard.objects.filter(
            user=user,
            account=account,
            card_type=card_type,
            status=ATMCard.ACTIVE,
        ).first()

        if existing:
            raise ValidationError(
                f"Active {card_type} card already exists for this account."
            )

        # --------------------------------------------------------------
        # Generate card details
        # --------------------------------------------------------------
        details = CardService._generate_card_details(card_type)

        card = ATMCard.objects.create(
            user=user,
            account=account,
            card_number=details['card_number'],
            card_type=card_type,
            cvv_hash=details['cvv_hash'],
            pin_hash=details['pin_hash'],
            expiry_date=details['expiry_date'],
            status=ATMCard.INACTIVE,
            daily_withdrawal_limit=Decimal('50000.00'),
            daily_pos_limit=Decimal('200000.00'),
            created_by=requested_by or user,
        )

        # --------------------------------------------------------------
        # Issuance fee journal: customer -> FEE
        # --------------------------------------------------------------
        fee = CardService.CARD_ISSUANCE_FEE

        if account.get_balance() < fee:
            raise ValidationError(
                "Insufficient funds to pay card issuance fee."
            )

        fee_account = AccountingManager.get_fee_account()

        fee_txn = Transaction.objects.create(
            account=account,
            amount=fee,
            type=Transaction.FEE,
            narration=f"{card_type} card issuance fee",
            fee=fee,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=fee_txn,
            debit_account=account,
            credit_account=fee_account,
            amount=fee,
            description=f"{card_type} card issuance fee",
            journal_type=AccountingJournal.FEE,
            created_by=requested_by or user,
        )

        fee_txn.journal = journal
        fee_txn.status = Transaction.SUCCESS
        fee_txn.balance_after = account.get_balance()
        fee_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Business record
        # --------------------------------------------------------------
        issuance = CardIssuance.objects.create(
            card=card,
            request_type='NEW',
            delivery_address=(
                delivery_address
                or getattr(user, "address", "")
                or ""
            ),
            status='PROCESSING',
            estimated_delivery=(
                timezone.now() + timedelta(days=7)
            ).date(),
            tracking_number=(
                f"CARD{timezone.now().strftime('%Y%m%d')}"
                f"{uuid.uuid4().hex[:6].upper()}"
            ),
            fee=fee,
            fee_paid=True,
            journal=journal,
            requested_by=requested_by or user,
        )

        logger.info(
            "Card issuance requested: card=%s user=%s fee=%s journal=%s",
            card.pk,
            user.pk,
            fee,
            journal.pk,
        )

        return {
            "success": True,
            "card": card,
            "issuance": issuance,
            "transaction": fee_txn,
            "journal": journal,
            "message": "Card request submitted successfully.",
        }

    # ------------------------------------------------------------------
    # ACTIVATE
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def activate_card(
        *,
        card_id,
        activation_code: str,
        activated_by=None,
    ) -> dict:
        try:
            card = ATMCard.objects.get(
                id=card_id, status=ATMCard.INACTIVE
            )
        except ATMCard.DoesNotExist:
            raise ValidationError(
                "Card not found or already activated."
            )

        if not CardService._verify_activation_code(card, activation_code):
            raise ValidationError("Invalid activation code.")

        card.status = ATMCard.ACTIVE
        card.activated_by = activated_by
        card.save()

        issuance = CardIssuance.objects.filter(card=card).first()
        if issuance:
            issuance.status = 'DELIVERED'
            issuance.activated_at = timezone.now()
            issuance.save()

        return {
            "success": True,
            "message": "Card activated successfully.",
            "card": card,
        }

    # ------------------------------------------------------------------
    # BLOCK / UNBLOCK
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def block_card(*, card_id, reason: str = "", blocked_by=None) -> dict:
        try:
            card = ATMCard.objects.get(id=card_id)
        except ATMCard.DoesNotExist:
            raise ValidationError("Card not found.")

        if card.status == ATMCard.BLOCKED:
            raise ValidationError("Card is already blocked.")

        card.status = ATMCard.BLOCKED
        card.blocked_by = blocked_by
        card.save()

        return {
            "success": True,
            "message": "Card blocked successfully.",
            "card": card,
        }

    @staticmethod
    @db_transaction.atomic
    def unblock_card(*, card_id, unblocked_by=None) -> dict:
        try:
            card = ATMCard.objects.get(id=card_id)
        except ATMCard.DoesNotExist:
            raise ValidationError("Card not found.")

        if card.status != ATMCard.BLOCKED:
            raise ValidationError("Card is not blocked.")

        card.status = ATMCard.ACTIVE
        card.save()

        return {
            "success": True,
            "message": "Card unblocked successfully.",
            "card": card,
        }

    # ------------------------------------------------------------------
    # ELIGIBILITY
    # ------------------------------------------------------------------

    @staticmethod
    def _is_eligible_for_card(user, account: Account) -> bool:
        if account.status != Account.STATUS_ACTIVE:
            return False

        if account.is_system_account:
            return False

        available_balance = AccountingManager.get_account_balance(account)

        if available_balance < Decimal("1000.00"):
            return False

        if not hasattr(user, "bvn_verification"):
            return False

        if user.bvn_verification.verification_status != "VERIFIED":
            return False

        account_age = timezone.now() - account.created_at
        if account_age.days < 30:
            return False

        from banking.models.security import FraudAlert

        recent_fraud = FraudAlert.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=90),
            status="OPEN",
        ).exists()

        return not recent_fraud

    # ------------------------------------------------------------------
    # CARD DETAILS
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_card_details(card_type: str) -> dict:
        def luhn_check_digit(card_without_check: str) -> str:
            def digits_of(n):
                return [int(d) for d in str(n)]

            digits = digits_of(card_without_check + "0")
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return str((10 - checksum % 10) % 10)

        bin_number = CardService.CARD_TYPES[card_type]['bin']
        card_length = CardService.CARD_TYPES[card_type]['length']

        middle_length = card_length - len(bin_number) - 1
        middle = ''.join(
            str(random.randint(0, 9)) for _ in range(middle_length)
        )
        card_without_check = bin_number + middle
        card_number = card_without_check + luhn_check_digit(
            card_without_check
        )

        cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
        pin = ''.join(str(random.randint(0, 9)) for _ in range(4))

        expiry_date = (timezone.now() + timedelta(days=3 * 365)).date()

        return {
            'card_number': card_number,
            'cvv': cvv,
            'cvv_hash': make_password(cvv),
            'pin': pin,
            'pin_hash': make_password(pin),
            'expiry_date': expiry_date,
        }

    @staticmethod
    def _verify_activation_code(card: ATMCard, code: str) -> bool:
        return bool(code) and len(code) == 6 and code.isdigit()


# ============================================================================
# ATM SERVICE
# ============================================================================

class ATMService:
    """Post and manage ATM transactions."""

    @staticmethod
    @db_transaction.atomic
    def process_withdrawal(
        *,
        account: Account,
        amount,
        card: ATMCard | None = None,
        user=None,
        terminal_id: str = "",
        location: str = "",
        processed_by=None,
    ) -> ATMTransaction:
        """
        Record an ATM withdrawal.

        Posts: customer_account -> SETTLEMENT
        """
        amount = ATMService._validate_amount(amount)
        ATMService._validate_account(account, user=user)

        if card is not None and card.status != ATMCard.ACTIVE:
            raise ValidationError("Card is not active.")

        if card is not None and card.account_id != account.pk:
            raise ValidationError(
                "Card does not belong to this account."
            )

        if account.get_balance() < amount:
            raise ValidationError("Insufficient funds in account.")

        reference = (
            f"ATM-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        settlement_account = AccountingManager.get_settlement_account()

        txn = Transaction.objects.create(
            account=account,
            amount=amount,
            type=Transaction.WITHDRAWAL,
            narration=f"ATM withdrawal {reference}",
            recipient_name="ATM",
            recipient_account_number=terminal_id,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=account,
            credit_account=settlement_account,
            amount=amount,
            description=f"ATM withdrawal {reference}",
            journal_type=AccountingJournal.WITHDRAWAL,
            created_by=processed_by or user,
        )

        txn.journal = journal
        txn.status = Transaction.SUCCESS
        txn.balance_after = account.get_balance()
        txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        atm_txn = ATMTransaction.objects.create(
            card=card,
            account=account,
            user=user,
            transaction_type=ATMTransaction.WITHDRAWAL,
            amount=amount,
            reference=reference,
            terminal_id=terminal_id,
            location=location,
            status=ATMTransaction.COMPLETED,
            journal=journal,
            processed_by=processed_by or user,
        )

        logger.info(
            "ATM withdrawal %s: account=%s amount=%s journal=%s",
            reference,
            account.pk,
            amount,
            journal.pk,
        )

        return atm_txn

    @staticmethod
    @db_transaction.atomic
    def process_deposit(
        *,
        account: Account,
        amount,
        card: ATMCard | None = None,
        user=None,
        terminal_id: str = "",
        location: str = "",
        processed_by=None,
    ) -> ATMTransaction:
        """
        Record an ATM deposit.

        Posts: SETTLEMENT -> customer_account
        """
        amount = ATMService._validate_amount(amount)
        ATMService._validate_account(account, user=user)

        if card is not None and card.status != ATMCard.ACTIVE:
            raise ValidationError("Card is not active.")

        if card is not None and card.account_id != account.pk:
            raise ValidationError(
                "Card does not belong to this account."
            )

        reference = (
            f"ATM-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        settlement_account = AccountingManager.get_settlement_account()

        txn = Transaction.objects.create(
            account=settlement_account,
            amount=amount,
            type=Transaction.DEPOSIT,
            narration=f"ATM deposit {reference}",
            recipient_name=(
                account.user.get_full_name() or account.user.email
                if account.user
                else ""
            ),
            recipient_account_number=account.nuban_number,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=settlement_account,
            credit_account=account,
            amount=amount,
            description=f"ATM deposit {reference}",
            journal_type=AccountingJournal.DEPOSIT,
            created_by=processed_by or user,
        )

        txn.journal = journal
        txn.status = Transaction.SUCCESS
        txn.balance_after = settlement_account.get_balance()
        txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        atm_txn = ATMTransaction.objects.create(
            card=card,
            account=account,
            user=user,
            transaction_type=ATMTransaction.DEPOSIT,
            amount=amount,
            reference=reference,
            terminal_id=terminal_id,
            location=location,
            status=ATMTransaction.COMPLETED,
            journal=journal,
            processed_by=processed_by or user,
        )

        logger.info(
            "ATM deposit %s: account=%s amount=%s journal=%s",
            reference,
            account.pk,
            amount,
            journal.pk,
        )

        return atm_txn

    @staticmethod
    @db_transaction.atomic
    def record_non_monetary(
        *,
        account: Account,
        transaction_type: str,
        card: ATMCard | None = None,
        user=None,
        terminal_id: str = "",
        location: str = "",
        processed_by=None,
    ) -> ATMTransaction:
        """
        Record a non-monetary ATM transaction (balance inquiry, PIN change).
        No ledger movement.
        """
        valid_non_monetary = {
            ATMTransaction.BALANCE_INQUIRY,
            ATMTransaction.PIN_CHANGE,
        }
        if transaction_type not in valid_non_monetary:
            raise ValidationError(
                "Only balance_inquiry and pin_change are non-monetary."
            )

        ATMService._validate_account(account, user=user)

        reference = (
            f"ATM-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        return ATMTransaction.objects.create(
            card=card,
            account=account,
            user=user,
            transaction_type=transaction_type,
            amount=None,
            reference=reference,
            terminal_id=terminal_id,
            location=location,
            status=ATMTransaction.COMPLETED,
            processed_by=processed_by or user,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        if amount is None:
            raise ValidationError("Amount is required.")
        try:
            value = Decimal(str(amount))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid amount.") from exc
        if not value.is_finite():
            raise ValidationError("Amount must be finite.")
        if value <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")
        return value.quantize(MONEY_QUANTUM)

    @staticmethod
    def _validate_account(account: Account, *, user=None) -> None:
        if account is None or account.pk is None:
            raise ValidationError("Account is required.")
        if account.is_system_account:
            raise ValidationError(
                "Account cannot be a system account."
            )
        if account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Account is not active.")
        if user is not None and account.user_id != user.pk:
            raise ValidationError(
                "Account does not belong to this user."
            )