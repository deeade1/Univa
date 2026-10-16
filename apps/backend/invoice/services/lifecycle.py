# apps/backend/invoice/services/lifecycle.py

"""
Invoice lifecycle transitions.

All status changes go through this module. Every transition
locks the invoice row, validates the source and target states,
writes an InvoiceEvent, and returns the updated invoice.

State graph:

    DRAFT ──▶ ISSUED ──▶ SENT ──▶ PAID
                          │
                          ├──▶ PARTIALLY_PAID ──▶ PAID
                          │
                          └──▶ OVERDUE ──▶ PAID

    Any non-terminal state ──▶ CANCELLED
    Any non-PAID, non-CANCELLED state ──▶ VOID
    PAID ──▶ REFUNDED
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from invoice.enums import InvoiceEventType, InvoiceStatus
from invoice.models import Invoice, InvoiceEvent


_TERMINAL = {InvoiceStatus.CANCELLED, InvoiceStatus.VOID, InvoiceStatus.REFUNDED}


def _lock_invoice(invoice_id):
    return Invoice.objects.select_for_update().get(pk=invoice_id)


def _emit(invoice, event_type, *, actor=None, parameters=None):
    return InvoiceEvent.objects.create(
        invoice=invoice,
        type=event_type,
        actor=actor,
        parameters=parameters or {},
    )


@transaction.atomic
def mark_issued(invoice, *, actor=None):
    locked = _lock_invoice(invoice.pk)

    if locked.status != InvoiceStatus.DRAFT:
        raise ValidationError(
            {
                "status": (
                    f"Cannot issue an invoice with status "
                    f"{locked.status}."
                )
            }
        )

    locked.status = InvoiceStatus.ISSUED
    locked.save(update_fields=["status", "updated_at"])

    _emit(locked, InvoiceEventType.ISSUED, actor=actor)

    invoice.status = locked.status
    return locked


@transaction.atomic
def mark_sent(invoice, *, actor=None):
    locked = _lock_invoice(invoice.pk)

    if locked.status not in {InvoiceStatus.ISSUED, InvoiceStatus.SENT}:
        raise ValidationError(
            {
                "status": (
                    f"Cannot mark as sent an invoice with status "
                    f"{locked.status}."
                )
            }
        )

    locked.status = InvoiceStatus.SENT
    locked.save(update_fields=["status", "updated_at"])

    _emit(locked, InvoiceEventType.SENT, actor=actor)

    invoice.status = locked.status
    return locked


@transaction.atomic
def mark_overdue(invoice, *, actor=None):
    locked = _lock_invoice(invoice.pk)

    if locked.status not in {
        InvoiceStatus.SENT,
        InvoiceStatus.PARTIALLY_PAID,
    }:
        raise ValidationError(
            {
                "status": (
                    f"Cannot mark overdue an invoice with status "
                    f"{locked.status}."
                )
            }
        )

    if not locked.due_date or timezone.now().date() <= locked.due_date:
        return locked  # Not yet overdue.

    locked.status = InvoiceStatus.OVERDUE
    locked.save(update_fields=["status", "updated_at"])

    _emit(locked, InvoiceEventType.OVERDUE, actor=actor)

    invoice.status = locked.status
    return locked


@transaction.atomic
def cancel(invoice, *, reason="", actor=None):
    locked = _lock_invoice(invoice.pk)

    if locked.status in _TERMINAL or locked.status == InvoiceStatus.PAID:
        raise ValidationError(
            {
                "status": (
                    f"Cannot cancel an invoice with status "
                    f"{locked.status}."
                )
            }
        )

    locked.status = InvoiceStatus.CANCELLED
    locked.save(update_fields=["status", "updated_at"])

    _emit(
        locked,
        InvoiceEventType.CANCELLED,
        actor=actor,
        parameters={"reason": reason},
    )

    invoice.status = locked.status
    return locked


@transaction.atomic
def void(invoice, *, reason="", actor=None):
    locked = _lock_invoice(invoice.pk)

    if locked.status in {InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID}:
        raise ValidationError(
            {
                "status": (
                    f"Cannot void an invoice with status "
                    f"{locked.status}."
                )
            }
        )

    locked.status = InvoiceStatus.VOID
    locked.save(update_fields=["status", "updated_at"])

    _emit(
        locked,
        InvoiceEventType.VOIDED,
        actor=actor,
        parameters={"reason": reason},
    )

    invoice.status = locked.status
    return locked


@transaction.atomic
def refresh_paid_state(invoice, *, actor=None):
    """
    Recompute status based on payments.

    Called by the payment service after a payment is applied.
    Handles the transition from SENT/PARTIALLY_PAID/OVERDUE to
    PAID when balance reaches zero.
    """
    locked = _lock_invoice(invoice.pk)

    if locked.status in _TERMINAL:
        return locked

    if locked.balance_due > 0 and locked.amount_paid > 0:
        target = InvoiceStatus.PARTIALLY_PAID
    elif locked.balance_due == 0 and locked.amount_paid > 0:
        target = InvoiceStatus.PAID
    else:
        return locked

    if target != locked.status:
        locked.status = target
        locked.save(update_fields=["status", "updated_at"])

        _emit(
            locked,
            InvoiceEventType.PAID
            if target == InvoiceStatus.PAID
            else InvoiceEventType.PAYMENT_APPLIED,
            actor=actor,
        )

        invoice.status = locked.status

    return locked