# apps/backend/banking/services/notification_service.py

"""
Banking notification helpers.

This module is a thin namespace over the canonical notification emitter.

It does NOT:
    - create notification records directly
    - choose delivery channels
    - resolve recipients
    - know about Celery
    - know about push providers

It only translates banking domain concepts into canonical notification
event emissions.

Canonical events live in:

    notifications.events.constants

Canonical presentation lives in:

    notifications.events.registry

Canonical emission lives in:

    notifications.events.emitter.emit_notification_event

Robustness
----------

Every emitter is wrapped in `_safe_emit`, which catches any exception
raised by the canonical emitter (including Celery/Redis connection
failures) and logs it instead of propagating. Notification delivery is
a side effect of a business operation; a broker outage must never roll
back a completed money movement or a committed ledger journal.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from notifications.events import constants as events
from notifications.events.emitter import emit_notification_event


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- helpers

def _money(value) -> str:
    """Format a Decimal for payload transmission."""
    return str(Decimal(value).quantize(Decimal("0.01")))


def _safe_emit(event_fn, **kwargs) -> None:
    """
    Fire a notification without letting delivery failures propagate.

    The canonical emitter persists a NotificationEvent and then
    attempts to queue it via Celery. If Celery/Redis is unavailable,
    the queue call raises. That must never fail the caller's business
    operation — the money has already moved and been posted to the
    ledger.
    """
    try:
        event_fn(**kwargs)
    except Exception:
        logger.exception(
            "Notification emission failed for %s", event_fn.__name__,
        )


# ---------------------------------------------------------------- transfer

def emit_transfer_initiated(*, sender, money_transfer) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_TRANSFER_INITIATED,
        module="banking",
        actor=sender,
        object_type="MoneyTransfer",
        object_id=money_transfer.pk,
        payload={
            "recipient_id": sender.pk,
            "amount": _money(money_transfer.amount),
            "reference": money_transfer.reference,
        },
    )


def emit_transfer_succeeded(*, sender, money_transfer) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_TRANSFER_SUCCESSFUL,
        module="banking",
        actor=sender,
        object_type="MoneyTransfer",
        object_id=money_transfer.pk,
        payload={
            "recipient_id": sender.pk,
            "amount": _money(money_transfer.amount),
            "reference": money_transfer.reference,
        },
    )


def emit_transfer_received(*, recipient, money_transfer) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_TRANSFER_RECEIVED,
        module="banking",
        actor=money_transfer.sender,
        object_type="MoneyTransfer",
        object_id=money_transfer.pk,
        payload={
            "recipient_id": recipient.pk,
            "amount": _money(money_transfer.amount),
            "reference": money_transfer.reference,
            "sender_id": money_transfer.sender_id,
        },
    )


def emit_transfer_failed(*, sender, money_transfer, reason: str) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_TRANSFER_FAILED,
        module="banking",
        actor=sender,
        object_type="MoneyTransfer",
        object_id=money_transfer.pk if money_transfer else "",
        payload={
            "recipient_id": sender.pk,
            "amount": _money(money_transfer.amount) if money_transfer else "0.00",
            "reason": reason,
        },
    )


def emit_external_transfer_failed(*, sender, transaction, reason: str) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_EXTERNAL_TRANSFER_FAILED,
        module="banking",
        actor=sender,
        object_type="Transaction",
        object_id=transaction.pk if transaction else "",
        payload={
            "recipient_id": sender.pk,
            "amount": _money(transaction.amount) if transaction else "0.00",
            "reason": reason,
        },
    )


# ---------------------------------------------------------------- wallet

def emit_wallet_credited(*, wallet, amount, reference: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.WALLET_CREDITED,
        module="banking",
        actor=wallet.user,
        object_type="Wallet",
        object_id=wallet.pk,
        payload={
            "recipient_id": wallet.user_id,
            "amount": _money(amount),
            "wallet_reference": wallet.wallet_reference,
            "reference": reference,
        },
    )


def emit_wallet_debited(*, wallet, amount, reference: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.WALLET_DEBITED,
        module="banking",
        actor=wallet.user,
        object_type="Wallet",
        object_id=wallet.pk,
        payload={
            "recipient_id": wallet.user_id,
            "amount": _money(amount),
            "wallet_reference": wallet.wallet_reference,
            "reference": reference,
        },
    )


# ---------------------------------------------------------------- investments

def emit_investment_purchased(*, user, investment) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_INVESTMENT_PURCHASED,
        module="banking",
        actor=user,
        object_type="Investment",
        object_id=investment.pk,
        payload={
            "recipient_id": user.pk,
            "investment_reference": investment.investment_reference,
            "amount": _money(investment.amount),
            "product_name": investment.product.name,
        },
    )


def emit_investment_matured(*, user, investment) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_INVESTMENT_MATURED,
        module="banking",
        actor=user,
        object_type="Investment",
        object_id=investment.pk,
        payload={
            "recipient_id": user.pk,
            "investment_reference": investment.investment_reference,
            "amount": _money(investment.amount),
            "return": _money(investment.expected_return),
        },
    )


def emit_investment_withdrawn(*, user, investment) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_INVESTMENT_WITHDRAWN,
        module="banking",
        actor=user,
        object_type="Investment",
        object_id=investment.pk,
        payload={
            "recipient_id": user.pk,
            "investment_reference": investment.investment_reference,
            "amount": _money(investment.amount),
            "early": investment.early_withdrawal,
        },
    )


def emit_investment_cancelled(*, user, investment) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_INVESTMENT_CANCELLED,
        module="banking",
        actor=user,
        object_type="Investment",
        object_id=investment.pk,
        payload={
            "recipient_id": user.pk,
            "investment_reference": investment.investment_reference,
        },
    )


def emit_investment_earnings_paid(*, user, investment, earnings) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_INVESTMENT_EARNINGS_PAID,
        module="banking",
        actor=user,
        object_type="Investment",
        object_id=investment.pk,
        payload={
            "recipient_id": user.pk,
            "investment_reference": investment.investment_reference,
            "amount": _money(earnings.amount),
            "earning_type": earnings.earning_type,
        },
    )


# ---------------------------------------------------------------- savings

def emit_savings_goal_created(*, user, goal) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_SAVINGS_GOAL_CREATED,
        module="banking",
        actor=user,
        object_type="SavingsGoal",
        object_id=goal.pk,
        payload={
            "recipient_id": user.pk,
            "goal_id": goal.goal_id,
            "name": goal.name,
            "target_amount": _money(goal.target_amount),
        },
    )


def emit_savings_deposit(*, user, goal, savings_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_SAVINGS_DEPOSIT,
        module="banking",
        actor=user,
        object_type="SavingsGoal",
        object_id=goal.pk,
        payload={
            "recipient_id": user.pk,
            "goal_id": goal.goal_id,
            "name": goal.name,
            "amount": _money(savings_transaction.amount),
            "current_amount": _money(goal.current_amount),
            "target_amount": _money(goal.target_amount),
        },
    )


def emit_savings_withdrawal(*, user, goal, savings_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_SAVINGS_WITHDRAWAL,
        module="banking",
        actor=user,
        object_type="SavingsGoal",
        object_id=goal.pk,
        payload={
            "recipient_id": user.pk,
            "goal_id": goal.goal_id,
            "name": goal.name,
            "amount": _money(savings_transaction.amount),
            "current_amount": _money(goal.current_amount),
        },
    )


def emit_savings_goal_completed(*, user, goal) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_SAVINGS_GOAL_COMPLETED,
        module="banking",
        actor=user,
        object_type="SavingsGoal",
        object_id=goal.pk,
        payload={
            "recipient_id": user.pk,
            "goal_id": goal.goal_id,
            "name": goal.name,
            "target_amount": _money(goal.target_amount),
            "completed_at": (
                goal.completed_at.isoformat() if goal.completed_at else None
            ),
        },
    )


def emit_savings_interest_paid(*, user, goal, savings_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_SAVINGS_INTEREST_PAID,
        module="banking",
        actor=user,
        object_type="SavingsGoal",
        object_id=goal.pk,
        payload={
            "recipient_id": user.pk,
            "goal_id": goal.goal_id,
            "name": goal.name,
            "amount": _money(savings_transaction.amount),
            "current_amount": _money(goal.current_amount),
        },
    )


# ---------------------------------------------------------------- bill payments

def emit_bill_payment_successful(*, user, payment) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BILL_PAYMENT_SUCCESSFUL,
        module="banking",
        actor=user,
        object_type="BillPayment",
        object_id=payment.pk,
        payload={
            "recipient_id": user.pk,
            "amount": _money(payment.amount),
            "fee": _money(payment.fee),
            "total_amount": _money(payment.total_amount),
            "reference": payment.reference,
            "provider": payment.provider,
        },
    )


def emit_bill_payment_failed(*, user, payment, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BILL_PAYMENT_FAILED,
        module="banking",
        actor=user,
        object_type="BillPayment",
        object_id=payment.pk if payment else "",
        payload={
            "recipient_id": user.pk,
            "amount": _money(payment.amount) if payment else "0.00",
            "reason": reason,
        },
    )


def emit_airtime_purchase_successful(*, user, purchase) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.AIRTIME_PURCHASE_SUCCESSFUL,
        module="banking",
        actor=user,
        object_type="AirtimePurchase",
        object_id=purchase.pk,
        payload={
            "recipient_id": user.pk,
            "amount": _money(purchase.amount),
            "fee": _money(purchase.fee),
            "total_amount": _money(purchase.total_amount),
            "phone_number": purchase.phone_number,
            "operator": purchase.operator,
            "reference": purchase.reference,
        },
    )


def emit_airtime_purchase_failed(*, user, purchase, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.AIRTIME_PURCHASE_FAILED,
        module="banking",
        actor=user,
        object_type="AirtimePurchase",
        object_id=purchase.pk if purchase else "",
        payload={
            "recipient_id": user.pk,
            "amount": _money(purchase.amount) if purchase else "0.00",
            "reason": reason,
        },
    )


def emit_data_bundle_purchase_successful(*, user, purchase) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.DATA_BUNDLE_PURCHASE_SUCCESSFUL,
        module="banking",
        actor=user,
        object_type="DataBundlePurchase",
        object_id=purchase.pk,
        payload={
            "recipient_id": user.pk,
            "price": _money(purchase.price),
            "phone_number": purchase.phone_number,
            "operator": purchase.operator,
            "bundle_name": purchase.bundle_name,
        },
    )


def emit_data_bundle_purchase_failed(*, user, purchase, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.DATA_BUNDLE_PURCHASE_FAILED,
        module="banking",
        actor=user,
        object_type="DataBundlePurchase",
        object_id=purchase.pk if purchase else "",
        payload={
            "recipient_id": user.pk,
            "price": _money(purchase.price) if purchase else "0.00",
            "reason": reason,
        },
    )


# ---------------------------------------------------------------- QR payments

def emit_qr_payment_successful(*, user, qr_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_QR_PAYMENT_SUCCESSFUL,
        module="banking",
        actor=user,
        object_type="QRTransaction",
        object_id=qr_transaction.pk,
        payload={
            "recipient_id": user.pk,
            "amount": _money(qr_transaction.amount),
            "reference": qr_transaction.reference,
            "payee_id": qr_transaction.payee_id,
            "payee_account_id": qr_transaction.payee_account_id,
        },
    )


def emit_qr_payment_failed(*, user, qr_transaction, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_QR_PAYMENT_FAILED,
        module="banking",
        actor=user,
        object_type="QRTransaction",
        object_id=qr_transaction.pk if qr_transaction else "",
        payload={
            "recipient_id": user.pk,
            "amount": (
                _money(qr_transaction.amount) if qr_transaction else "0.00"
            ),
            "reason": reason,
        },
    )


# ---------------------------------------------------------------- merchants

def emit_merchant_created(*, user, merchant) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_CREATED,
        module="banking",
        actor=user,
        object_type="Merchant",
        object_id=merchant.pk,
        payload={
            "recipient_id": user.pk,
            "merchant_id": merchant.merchant_id,
            "business_name": merchant.business_name,
        },
    )


def emit_merchant_verified(*, user, merchant) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_VERIFIED,
        module="banking",
        actor=user,
        object_type="Merchant",
        object_id=merchant.pk,
        payload={
            "recipient_id": user.pk,
            "merchant_id": merchant.merchant_id,
            "business_name": merchant.business_name,
        },
    )


def emit_merchant_rejected(*, user, merchant, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_REJECTED,
        module="banking",
        actor=user,
        object_type="Merchant",
        object_id=merchant.pk,
        payload={
            "recipient_id": user.pk,
            "merchant_id": merchant.merchant_id,
            "business_name": merchant.business_name,
            "reason": reason,
        },
    )


def emit_merchant_suspended(*, user, merchant, reason: str = "") -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_SUSPENDED,
        module="banking",
        actor=user,
        object_type="Merchant",
        object_id=merchant.pk,
        payload={
            "recipient_id": user.pk,
            "merchant_id": merchant.merchant_id,
            "business_name": merchant.business_name,
            "reason": reason,
        },
    )


def emit_merchant_sale(*, merchant_user, customer, merchant_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_SALE,
        module="banking",
        actor=customer,
        object_type="MerchantTransaction",
        object_id=merchant_transaction.pk,
        payload={
            "recipient_id": merchant_user.pk,
            "amount": _money(merchant_transaction.amount),
            "fee": _money(merchant_transaction.fee),
            "net_amount": _money(merchant_transaction.net_amount),
            "reference": merchant_transaction.reference,
            "customer_id": customer.pk,
        },
    )


def emit_merchant_refund(*, merchant_user, merchant_transaction) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_REFUND,
        module="banking",
        actor=merchant_user,
        object_type="MerchantTransaction",
        object_id=merchant_transaction.pk,
        payload={
            "recipient_id": merchant_user.pk,
            "amount": _money(merchant_transaction.amount),
            "reference": merchant_transaction.reference,
        },
    )


def emit_merchant_settlement(*, user, merchant, count: int, total_amount) -> None:
    _safe_emit(
        emit_notification_event,
        event_type=events.BANK_MERCHANT_SETTLEMENT,
        module="banking",
        actor=user,
        object_type="Merchant",
        object_id=merchant.pk,
        payload={
            "recipient_id": user.pk,
            "merchant_id": merchant.merchant_id,
            "count": count,
            "total_amount": _money(total_amount),
        },
    )