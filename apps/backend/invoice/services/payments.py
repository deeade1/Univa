# apps/backend/invoice/services/payments.py

"""
Payment application service.

apply_payment is idempotent on idempotency_key. Retries with the
same key return the existing InvoicePayment row without
re-applying the amount.

The invoice's amount_paid and balance_due are recomputed from
the aggregate of its payments, not incremented in place. This
avoids drift under concurrency.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from invoice.enums import InvoicePaymentType
from invoice.models import Invoice, InvoicePayment
from invoice.services.lifecycle import refresh_paid_state


@transaction.atomic
def apply_payment(
    *,
    invoice_id,
    idempotency_key: str,
    payment_type: str,
    amount: Decimal,
    currency: str,
    payment_id: str = "",
    applied_by=None,
    metadata=None,
):
    """
    Apply a payment to an invoice.

    Returns (InvoicePayment, created: bool).

    Idempotent: a second call with the same idempotency_key
    returns the existing row and created=False.
    """
    if not idempotency_key:
        raise ValidationError(
            {"idempotency_key": "Idempotency key is required."}
        )

    existing = InvoicePayment.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if existing is not None:
        return existing, False

    amount = Decimal(str(amount))
    if amount == Decimal("0.00"):
        raise ValidationError(
            {"amount": "Payment amount must not be zero."}
        )

    # Lock the invoice row so concurrent applications serialize.
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

    if invoice.currency.upper() != currency.upper():
        raise ValidationError(
            {
                "currency": (
                    f"Payment currency {currency} does not match "
                    f"invoice currency {invoice.currency}."
                )
            }
        )

    payment = InvoicePayment.objects.create(
        invoice=invoice,
        idempotency_key=idempotency_key,
        payment_type=payment_type,
        payment_id=payment_id or "",
        amount=amount,
        currency=currency.upper(),
        applied_by=applied_by,
        metadata=metadata or {},
    )

    # Recompute the invoice header from the aggregate of payments.
    invoice.recalculate_totals()
    invoice.save(
        update_fields=[
            "amount_paid",
            "balance_due",
            "updated_at",
        ]
    )

    # Transition the status.
    refresh_paid_state(invoice, actor=applied_by)
    invoice.refresh_from_db()

    return payment, True


@transaction.atomic
def reverse_payment(
    *,
    invoice_id,
    idempotency_key: str,
    original_payment_id=None,
    amount: Decimal,
    reason: str = "",
    applied_by=None,
):
    """
    Reverse a payment by creating a negative-amount row.

    Idempotent on idempotency_key. The original InvoicePayment
    is never mutated.
    """
    return apply_payment(
        invoice_id=invoice_id,
        idempotency_key=idempotency_key,
        payment_type=InvoicePaymentType.REVERSAL,
        amount=-abs(Decimal(str(amount))),
        currency=Invoice.objects.get(pk=invoice_id).currency,
        payment_id=str(original_payment_id) if original_payment_id else "",
        applied_by=applied_by,
        metadata={"reason": reason},
    )