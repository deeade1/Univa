"""
Univa Wallet Gateway API.

This module handles the integration between Payment app and Banking app.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from payment.gateways.univa.consts import *
from payment.gateways.univa.errors import *

User = get_user_model()
logger = logging.getLogger(__name__)


class UnivaWalletAPI:
    """
    Univa Wallet Gateway API.

    This is the bridge between the Payment app and Banking app.
    It handles:
    1. Wallet payments (debit)
    2. Wallet refunds (credit)
    3. Wallet balance checks
    4. Transaction validation
    """

    @staticmethod
    def get_wallet_balance(user) -> Dict[str, Any]:
        """
        Get user's wallet balance.

        Args:
            user: The user

        Returns:
            Dict with balance information
        """
        try:
            from banking.models.payments import Wallet

            wallet = Wallet.objects.get(user=user)

            return {
                "success": True,
                "balance": wallet.balance,
                "currency": "NGN",
                "wallet_reference": wallet.wallet_reference,
                "status": wallet.status,
                "is_active": wallet.is_active,
                "daily_limit": wallet.daily_transaction_limit,
                "daily_used": wallet.daily_transaction_amount,
            }

        except Wallet.DoesNotExist:
            return {
                "success": False,
                "error": ERROR_WALLET_NOT_FOUND,
                "message": "Wallet not found.",
            }

        except Exception as exc:
            logger.exception("Error getting wallet balance: %s", exc)
            return {
                "success": False,
                "error": "BALANCE_CHECK_FAILED",
                "message": str(exc),
            }

    @staticmethod
    def initiate_payment(
        user,
        amount: Decimal,
        currency: str = "NGN",
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initiate a wallet payment.

        Args:
            user: The user making the payment
            amount: Amount to pay
            currency: Currency (default: NGN)
            payment_reference: Payment reference from Payment app
            metadata: Additional metadata

        Returns:
            Dict with payment result
        """
        try:
            logger.info(
                "Initiating Univa wallet payment: user=%s amount=%s",
                user.pk,
                amount,
            )

            from banking.models.payments import Wallet

            # Validate amount
            if amount <= Decimal("0.00"):
                raise AmountInvalidError("Amount must be greater than zero.")

            # Get user's wallet
            try:
                wallet = Wallet.objects.get(user=user)
            except Wallet.DoesNotExist:
                raise WalletNotFoundError("Wallet not found for user.")

            # Validate wallet
            if not wallet.is_active:
                raise WalletInactiveError("Wallet is not active.")

            if wallet.balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient balance. Available: ₦{wallet.balance:,.2f}"
                )

            # Check daily limit
            try:
                wallet.can_transact(amount)
            except ValidationError as exc:
                raise DailyLimitExceededError(str(exc))

            # Process the payment
            result = UnivaWalletAPI._process_wallet_payment(
                user=user,
                wallet=wallet,
                amount=amount,
                currency=currency,
                payment_reference=payment_reference,
                metadata=metadata,
            )

            return result

        except WalletNotFoundError as exc:
            logger.error("Wallet not found for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_WALLET_NOT_FOUND,
                "message": "Wallet not found. Please create a wallet first.",
            }

        except InsufficientBalanceError as exc:
            logger.error("Insufficient balance for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_INSUFFICIENT_BALANCE,
                "message": str(exc),
            }

        except WalletInactiveError as exc:
            logger.error("Wallet inactive for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_WALLET_INACTIVE,
                "message": "Wallet is not active.",
            }

        except AmountInvalidError as exc:
            logger.error("Invalid amount for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_AMOUNT_INVALID,
                "message": str(exc),
            }

        except DailyLimitExceededError as exc:
            logger.error("Daily limit exceeded for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_DAILY_LIMIT_EXCEEDED,
                "message": str(exc),
            }

        except TransactionFailedError as exc:
            logger.error("Transaction failed for user %s: %s", user.pk, exc)
            return {
                "success": False,
                "error": ERROR_TRANSACTION_FAILED,
                "message": str(exc),
            }

        except Exception as exc:
            logger.exception("Unexpected error processing wallet payment: %s", exc)
            return {
                "success": False,
                "error": "UNEXPECTED_ERROR",
                "message": "An unexpected error occurred.",
            }

    @staticmethod
    def process_refund(
        user,
        amount: Decimal,
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a refund to user's wallet.

        Args:
            user: The user receiving the refund
            amount: Amount to refund
            payment_reference: Original payment reference
            metadata: Additional metadata

        Returns:
            Dict with refund result
        """
        try:
            logger.info(
                "Processing Univa wallet refund: user=%s amount=%s",
                user.pk,
                amount,
            )

            from banking.models.payments import Wallet

            if amount <= Decimal("0.00"):
                raise AmountInvalidError("Refund amount must be greater than zero.")

            try:
                wallet = Wallet.objects.get(user=user)
            except Wallet.DoesNotExist:
                raise WalletNotFoundError("Wallet not found for user.")

            if not wallet.is_active:
                raise WalletInactiveError("Wallet is not active.")

            # Process refund
            result = UnivaWalletAPI._process_wallet_refund(
                user=user,
                wallet=wallet,
                amount=amount,
                payment_reference=payment_reference,
                metadata=metadata,
            )

            return result

        except Exception as exc:
            logger.exception("Unexpected error processing wallet refund: %s", exc)
            return {
                "success": False,
                "error": "REFUND_FAILED",
                "message": str(exc),
            }

    @staticmethod
    @db_transaction.atomic
    def _process_wallet_payment(
        user,
        wallet,
        amount: Decimal,
        currency: str = "NGN",
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process wallet payment (debit).
        This is the bridge between Payment and Banking.
        """
        try:
            # 1. Create banking transaction record
            from banking.models.payments import Transaction as BankingTransaction
            from banking.models.core import Account

            # Get user's banking account
            account = Account.objects.get(user=user)

            # Create banking transaction
            banking_transaction = BankingTransaction.objects.create(
                account=account,
                amount=amount,
                type=BankingTransaction.WITHDRAWAL,
                narration=f"Payment: {payment_reference or 'Unknown'}",
                status=BankingTransaction.PENDING,
                balance_after=wallet.balance - amount,
            )

            # 2. Debit wallet
            wallet.debit(amount)

            # 3. Update banking transaction
            banking_transaction.status = BankingTransaction.SUCCESS
            banking_transaction.save()

            # 4. Create audit log
            try:
                from banking.models.security import AuditLog

                AuditLog.objects.create(
                    user=user,
                    action="TRANSACTION",
                    resource_type="Wallet",
                    resource_id=str(wallet.pk),
                    description=f"Wallet payment: ₦{amount:,.2f} - {payment_reference}",
                    metadata={
                        "amount": str(amount),
                        "currency": currency,
                        "payment_reference": payment_reference,
                        "balance_after": str(wallet.balance),
                        "metadata": metadata or {},
                    },
                )
            except ImportError:
                logger.warning("AuditLog model not available, skipping audit")

            # 5. Emit notification event
            try:
                from notifications.events.emitter import emit_and_queue_notification_event

                emit_and_queue_notification_event(
                    event_type="WALLET_DEBITED",
                    module="payment",
                    actor=user,
                    object_type="Wallet",
                    object_id=wallet.pk,
                    payload={
                        "amount": str(amount),
                        "currency": currency,
                        "payment_reference": payment_reference,
                        "balance_after": str(wallet.balance),
                        "description": metadata.get("description", "Wallet payment") if metadata else "Wallet payment",
                    },
                )
            except Exception as exc:
                logger.warning("Failed to emit notification: %s", exc)

            logger.info(
                "Wallet payment successful: user=%s amount=%s reference=%s",
                user.pk,
                amount,
                payment_reference,
            )

            return {
                "success": True,
                "reference": banking_transaction.reference,
                "amount": amount,
                "currency": currency,
                "balance_after": wallet.balance,
                "message": "Payment processed successfully.",
            }

        except Exception as exc:
            logger.exception("Failed to process wallet payment: %s", exc)
            raise TransactionFailedError(f"Payment processing failed: {exc}")

    @staticmethod
    @db_transaction.atomic
    def _process_wallet_refund(
        user,
        wallet,
        amount: Decimal,
        payment_reference: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process wallet refund (credit).
        """
        try:
            # 1. Create banking transaction
            from banking.models.payments import Transaction as BankingTransaction
            from banking.models.core import Account

            account = Account.objects.get(user=user)

            banking_transaction = BankingTransaction.objects.create(
                account=account,
                amount=amount,
                type=BankingTransaction.DEPOSIT,
                narration=f"Refund: {payment_reference or 'Unknown'}",
                status=BankingTransaction.PENDING,
                balance_after=wallet.balance + amount,
            )

            # 2. Credit wallet
            wallet.credit(amount)

            # 3. Update banking transaction
            banking_transaction.status = BankingTransaction.SUCCESS
            banking_transaction.save()

            # 4. Create audit log
            try:
                from banking.models.security import AuditLog

                AuditLog.objects.create(
                    user=user,
                    action="TRANSACTION",
                    resource_type="Wallet",
                    resource_id=str(wallet.pk),
                    description=f"Wallet refund: ₦{amount:,.2f} - {payment_reference}",
                    metadata={
                        "amount": str(amount),
                        "payment_reference": payment_reference,
                        "balance_after": str(wallet.balance),
                        "metadata": metadata or {},
                    },
                )
            except ImportError:
                logger.warning("AuditLog model not available, skipping audit")

            # 5. Emit notification event
            try:
                from notifications.events.emitter import emit_and_queue_notification_event

                emit_and_queue_notification_event(
                    event_type="WALLET_CREDITED",
                    module="payment",
                    actor=user,
                    object_type="Wallet",
                    object_id=wallet.pk,
                    payload={
                        "amount": str(amount),
                        "payment_reference": payment_reference,
                        "balance_after": str(wallet.balance),
                        "description": metadata.get("description", "Wallet refund") if metadata else "Wallet refund",
                    },
                )
            except Exception as exc:
                logger.warning("Failed to emit notification: %s", exc)

            logger.info(
                "Wallet refund successful: user=%s amount=%s reference=%s",
                user.pk,
                amount,
                payment_reference,
            )

            return {
                "success": True,
                "reference": banking_transaction.reference,
                "amount": amount,
                "balance_after": wallet.balance,
                "message": "Refund processed successfully.",
            }

        except Exception as exc:
            logger.exception("Failed to process wallet refund: %s", exc)
            raise TransactionFailedError(f"Refund processing failed: {exc}")


__all__ = [
    "UnivaWalletAPI",
]