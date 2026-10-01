# apps/backend/banking/services/card_service.py

"""
Virtual and physical card service.

Money movement
--------------

    authorization:  account -> SUSPENSE  (hold amount)
    settlement:     SUSPENSE -> SETTLEMENT  (settled amount)
    reversal:       SUSPENSE -> account  (released hold)
    physical card:  account -> FEE  (card_fee + shipping_fee)

Every path posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This service operates against the customer's Account, which is the
ledger-integrated funding source. Wallet is a metadata pointer only.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from decimal import Decimal

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.cards import (
    CardBrand,
    CardTransaction,
    PhysicalCard,
    VirtualCard,
)
from banking.models.core import Account
from banking.models.payments import Transaction


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class CardService:
    """Issuance, authorization, and settlement of bank cards."""

    # ------------------------------------------------------------------
    # CIPHER
    # ------------------------------------------------------------------

    @staticmethod
    def _cipher() -> Fernet:
        return Fernet(settings.CARD_ENCRYPTION_KEY.encode())

    @classmethod
    def encrypt_field(cls, value: str) -> str:
        return cls._cipher().encrypt(value.encode()).decode()

    @classmethod
    def decrypt_field(cls, value: str) -> str:
        return cls._cipher().decrypt(value.encode()).decode()

    # ------------------------------------------------------------------
    # CARD NUMBER / CVV / EXPIRY GENERATION
    # ------------------------------------------------------------------

    CARD_BINS = {
        'VISA': '4',
        'MASTERCARD': '5',
        'VERVE': '5060',
    }

    @classmethod
    def generate_card_number(cls, card_type: str) -> str:
        prefix = cls.CARD_BINS.get(card_type.upper(), '4')

        middle = ''.join(
            str(secrets.randbelow(10))
            for _ in range(15 - len(prefix))
        )
        without_check = prefix + middle

        check = cls._luhn_check_digit(without_check)
        return without_check + str(check)

    @staticmethod
    def _luhn_check_digit(number: str) -> int:
        digits = [int(d) for d in number]
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 0:
                doubled = digit * 2
                total += doubled if doubled < 10 else doubled - 9
            else:
                total += digit
        return (10 - (total % 10)) % 10

    @staticmethod
    def generate_cvv() -> str:
        return f"{secrets.randbelow(1000):03d}"

    @staticmethod
    def generate_expiry() -> tuple[int, int]:
        now = timezone.now()
        year = now.year + 5
        return now.month, year

    # ------------------------------------------------------------------
    # ISSUE VIRTUAL CARD
    # ------------------------------------------------------------------

    @classmethod
    @db_transaction.atomic
    def issue_virtual_card(
        cls,
        *,
        user,
        account: Account,
        card_type: str,
        card_holder_name: str | None = None,
        daily_limit=None,
        monthly_limit=None,
        per_transaction_limit=None,
    ) -> VirtualCard:
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

        card_brand = CardBrand.objects.filter(
            code=card_type.upper(),
            is_active=True,
        ).first()
        if not card_brand:
            raise ValidationError(
                f"No active card brand for type {card_type}."
            )

        daily_limit = Decimal(
            str(daily_limit if daily_limit is not None else "100000.00")
        ).quantize(MONEY_QUANTUM)
        monthly_limit = Decimal(
            str(monthly_limit if monthly_limit is not None else "1000000.00")
        ).quantize(MONEY_QUANTUM)
        per_txn_limit = Decimal(
            str(
                per_transaction_limit
                if per_transaction_limit is not None
                else "50000.00"
            )
        ).quantize(MONEY_QUANTUM)

        if daily_limit > monthly_limit:
            raise ValidationError(
                "Daily limit cannot exceed monthly limit."
            )
        if per_txn_limit > daily_limit:
            raise ValidationError(
                "Per-transaction limit cannot exceed daily limit."
            )

        # Wallet is created lazily as a metadata pointer.
        from banking.models.payments import Wallet

        wallet = Wallet.objects.filter(
            user=user, account=account
        ).first()
        if wallet is None:
            wallet = Wallet.objects.create(
                user=user,
                account=account,
            )

        card_number = cls.generate_card_number(card_type)
        cvv = cls.generate_cvv()
        expiry_month, expiry_year = cls.generate_expiry()
        expires_at = timezone.now() + timedelta(days=365 * 5)

        card = VirtualCard.objects.create(
            user=user,
            wallet=wallet,
            card_brand=card_brand,
            card_number=cls.encrypt_field(card_number),
            card_holder_name=(
                card_holder_name or user.get_full_name() or user.email
            ),
            expiry_month=expiry_month,
            expiry_year=expiry_year,
            cvv=cls.encrypt_field(cvv),
            card_type=card_type.upper(),
            last_four=card_number[-4:],
            bin=card_number[:6],
            daily_limit=daily_limit,
            monthly_limit=monthly_limit,
            per_transaction_limit=per_txn_limit,
            status='ACTIVE',
            is_active=True,
            activated_at=timezone.now(),
            expires_at=expires_at,
        )

        logger.info(
            "Virtual card issued: card=%s user=%s last_four=%s",
            card.pk,
            user.pk,
            card.last_four,
        )

        return card

    # ------------------------------------------------------------------
    # AUTHORIZE
    # ------------------------------------------------------------------

    @classmethod
    @db_transaction.atomic
    def authorize_transaction(
        cls,
        *,
        card: VirtualCard,
        account: Account,
        amount,
        merchant_name: str,
        merchant_category_code: str,
        merchant_country: str = "NG",
        acquirer_id: str = "LOCAL",
        currency: str = "NGN",
    ) -> CardTransaction:
        """
        Authorize a card transaction.

        Posts: account -> SUSPENSE  (hold amount)

        Funds are debited from the customer account and held in
        SUSPENSE until settle_transaction or reverse_authorization.
        """
        if card.status != 'ACTIVE' or card.is_frozen:
            raise ValidationError(
                f"Card is not active. Status: {card.status}."
            )

        if card.is_expired:
            raise ValidationError("Card has expired.")

        if account is None or account.pk is None:
            raise ValidationError("Account is required.")

        if account.user_id != card.user_id:
            raise ValidationError(
                "Account does not belong to the card holder."
            )

        if account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Account is not active.")

        if account.is_system_account:
            raise ValidationError(
                "Account cannot be a system account."
            )

        amount = Decimal(str(amount)).quantize(MONEY_QUANTUM)
        if amount <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")

        # Limits (properties)
        if amount > card.per_transaction_limit:
            raise ValidationError(
                "Amount exceeds per-transaction limit."
            )

        if card.daily_usage + amount > card.daily_limit:
            raise ValidationError("Amount exceeds daily limit.")

        if card.monthly_usage + amount > card.monthly_limit:
            raise ValidationError("Amount exceeds monthly limit.")

        if account.get_balance() < amount:
            raise ValidationError("Insufficient funds in account.")

        # --------------------------------------------------------------
        # Ledger: account -> SUSPENSE
        # --------------------------------------------------------------
        suspense = AccountingManager.get_suspense_account()

        auth_txn = Transaction.objects.create(
            account=account,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=f"Card authorization: {merchant_name}",
            recipient_name=merchant_name,
            recipient_account_number="",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=auth_txn,
            debit_account=account,
            credit_account=suspense,
            amount=amount,
            description=(
                f"Card authorization {card.last_four}: {merchant_name}"
            ),
            journal_type=AccountingJournal.TRANSFER,
            created_by=card.user,
        )

        auth_txn.journal = journal
        auth_txn.status = Transaction.SUCCESS
        auth_txn.balance_after = account.get_balance()
        auth_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        auth_code = f"AUTH-{secrets.token_hex(8).upper()}"

        card_transaction = CardTransaction.objects.create(
            card=card,
            transaction=auth_txn,
            user=card.user,
            transaction_type='AUTHORIZATION',
            amount=amount,
            currency=currency,
            merchant_name=merchant_name,
            merchant_category_code=merchant_category_code,
            merchant_country=merchant_country,
            auth_code=auth_code,
            auth_amount=amount,
            status='AUTHORIZED',
            acquirer_id=acquirer_id,
            authorized_at=timezone.now(),
            journal=journal,
        )

        card.last_used_at = timezone.now()
        card.save(update_fields=['last_used_at'])

        logger.info(
            "Card authorization %s: card=%s amount=%s journal=%s",
            auth_code,
            card.pk,
            amount,
            journal.pk,
        )

        return card_transaction

    # ------------------------------------------------------------------
    # SETTLE
    # ------------------------------------------------------------------

    @classmethod
    @db_transaction.atomic
    def settle_transaction(
        cls, *, auth_code: str
    ) -> CardTransaction:
        """
        Settle an authorized transaction.

        Posts: SUSPENSE -> SETTLEMENT  (settled amount)
        """
        try:
            card_transaction = CardTransaction.objects.get(
                auth_code=auth_code
            )
        except CardTransaction.DoesNotExist:
            raise ValidationError("Authorization not found.")

        if card_transaction.status != 'AUTHORIZED':
            raise ValidationError(
                f"Transaction is not authorized. "
                f"Status: {card_transaction.status}."
            )

        suspense = AccountingManager.get_suspense_account()
        settlement = AccountingManager.get_settlement_account()

        amount = card_transaction.amount

        settle_txn = Transaction.objects.create(
            account=suspense,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=(
                f"Card settlement: "
                f"{card_transaction.merchant_name}"
            ),
            recipient_name=card_transaction.merchant_name,
            recipient_account_number="",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=settle_txn,
            debit_account=suspense,
            credit_account=settlement,
            amount=amount,
            description=(
                f"Card settlement {auth_code}: "
                f"{card_transaction.merchant_name}"
            ),
            journal_type=AccountingJournal.SETTLEMENT,
            created_by=card_transaction.user,
        )

        settle_txn.journal = journal
        settle_txn.status = Transaction.SUCCESS
        settle_txn.balance_after = suspense.get_balance()
        settle_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        card_transaction.status = 'SETTLED'
        card_transaction.settled_at = timezone.now()
        card_transaction.journal = journal
        card_transaction.save(update_fields=[
            'status', 'settled_at', 'journal',
        ])

        logger.info(
            "Card settlement %s: amount=%s journal=%s",
            auth_code,
            amount,
            journal.pk,
        )

        return card_transaction

    # ------------------------------------------------------------------
    # REVERSE
    # ------------------------------------------------------------------

    @classmethod
    @db_transaction.atomic
    def reverse_authorization(
        cls,
        *,
        auth_code: str,
        reason: str = "",
        account: Account | None = None,
    ) -> CardTransaction:
        """
        Reverse an authorization and release the hold.

        Posts: SUSPENSE -> account  (released hold amount)

        If `account` is None, the card holder's primary account is used.
        """
        try:
            card_transaction = CardTransaction.objects.get(
                auth_code=auth_code
            )
        except CardTransaction.DoesNotExist:
            raise ValidationError("Authorization not found.")

        if card_transaction.status != 'AUTHORIZED':
            raise ValidationError(
                f"Transaction is not authorized. "
                f"Status: {card_transaction.status}."
            )

        if account is None:
            account = Account.objects.filter(
                user=card_transaction.user,
                is_system_account=False,
                status=Account.STATUS_ACTIVE,
            ).first()

        if account is None:
            raise ValidationError(
                "No destination account for reversal."
            )

        suspense = AccountingManager.get_suspense_account()
        amount = card_transaction.amount

        reverse_txn = Transaction.objects.create(
            account=suspense,
            amount=amount,
            type=Transaction.TRANSFER,
            narration=(
                f"Card authorization reversal: "
                f"{card_transaction.merchant_name}"
            ),
            recipient_name=(
                account.user.get_full_name() or account.user.email
                if account.user
                else ""
            ),
            recipient_account_number=account.nuban_number,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=reverse_txn,
            debit_account=suspense,
            credit_account=account,
            amount=amount,
            description=(
                f"Card auth reversal {auth_code}: "
                f"{card_transaction.merchant_name}"
            ),
            journal_type=AccountingJournal.REVERSAL,
            created_by=card_transaction.user,
        )

        reverse_txn.journal = journal
        reverse_txn.status = Transaction.SUCCESS
        reverse_txn.balance_after = suspense.get_balance()
        reverse_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        card_transaction.status = 'REVERSED'
        card_transaction.status_reason = reason
        card_transaction.journal = journal
        card_transaction.save(update_fields=[
            'status', 'status_reason', 'journal',
        ])

        logger.info(
            "Card authorization reversed %s: amount=%s journal=%s",
            auth_code,
            amount,
            journal.pk,
        )

        return card_transaction

    # ------------------------------------------------------------------
    # PHYSICAL CARD
    # ------------------------------------------------------------------

    @classmethod
    @db_transaction.atomic
    def request_physical_card(
        cls,
        *,
        user,
        virtual_card: VirtualCard,
        account: Account,
        delivery_address: str,
        delivery_city: str,
        delivery_state: str,
        delivery_phone: str,
        shipping_method: str,
        card_fee,
        shipping_fee=None,
        delivery_country: str = "NG",
    ) -> PhysicalCard:
        """
        Request a physical card.

        Posts: account -> FEE  (card_fee + shipping_fee)
        """
        if virtual_card.user_id != user.pk:
            raise ValidationError(
                "Virtual card does not belong to this user."
            )

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

        if PhysicalCard.objects.filter(
            virtual_card=virtual_card
        ).exclude(delivery_status="CANCELLED").exists():
            raise ValidationError(
                "A physical card has already been requested for this "
                "virtual card."
            )

        card_fee = Decimal(str(card_fee)).quantize(MONEY_QUANTUM)
        shipping_fee = Decimal(
            str(shipping_fee if shipping_fee is not None else "0.00")
        ).quantize(MONEY_QUANTUM)

        if card_fee <= Decimal("0.00"):
            raise ValidationError(
                "Card fee must be greater than zero."
            )
        if shipping_fee < Decimal("0.00"):
            raise ValidationError(
                "Shipping fee cannot be negative."
            )

        total_fee = card_fee + shipping_fee

        if account.get_balance() < total_fee:
            raise ValidationError(
                "Insufficient funds to pay the card fee."
            )

        fee_account = AccountingManager.get_fee_account()

        fee_txn = Transaction.objects.create(
            account=account,
            amount=total_fee,
            type=Transaction.FEE,
            narration="Physical card issuance fee",
            fee=total_fee,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=fee_txn,
            debit_account=account,
            credit_account=fee_account,
            amount=total_fee,
            description=(
                f"Physical card fee for ****{virtual_card.last_four}"
            ),
            journal_type=AccountingJournal.FEE,
            created_by=user,
        )

        fee_txn.journal = journal
        fee_txn.status = Transaction.SUCCESS
        fee_txn.balance_after = account.get_balance()
        fee_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        physical_card = PhysicalCard.objects.create(
            user=user,
            virtual_card=virtual_card,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_state=delivery_state,
            delivery_country=delivery_country,
            delivery_phone=delivery_phone,
            shipping_method=shipping_method,
            card_fee=card_fee,
            shipping_fee=shipping_fee,
            delivery_status="PENDING",
            journal=journal,
        )

        logger.info(
            "Physical card requested: card=%s user=%s total_fee=%s "
            "journal=%s",
            virtual_card.pk,
            user.pk,
            total_fee,
            journal.pk,
        )

        return physical_card