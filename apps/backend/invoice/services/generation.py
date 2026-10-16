# apps/backend/invoice/services/generation.py

"""
Invoice generation services.

An invoice is created here from a source description. The
generation service does not know about ecommerce, transport, or
any other domain — it receives a canonical description and
persists it.

Domain-specific adapters (e.g. generate_invoice_from_order in
ecommerce) call these functions.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from invoice.enums import InvoiceEventType, InvoiceStatus
from invoice.models import (
    Invoice,
    InvoiceEvent,
    InvoiceLineItem,
    InvoiceParty,
    InvoiceSource,
)
from invoice.services.numbering import allocate_invoice_number


@dataclass
class LineItemSpec:
    """
    Domain-agnostic line item specification.
    """
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal = Decimal("0.00")
    tax_rate: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    metadata: dict = field(default_factory=dict)


@dataclass
class SourceSpec:
    """
    Domain-agnostic source attachment specification.
    """
    source_type: str
    source_id: str
    source_reference: str = ""


@transaction.atomic
def generate_invoice(
    *,
    issuer: InvoiceParty,
    recipient: InvoiceParty,
    currency: str,
    line_items: list[LineItemSpec],
    sources: Optional[list[SourceSpec]] = None,
    shipping_amount: Decimal = Decimal("0.00"),
    discount_amount: Decimal = Decimal("0.00"),
    issue_date=None,
    due_date=None,
    payment_terms: str = "",
    notes: str = "",
    status: str = InvoiceStatus.DRAFT,
    created_by_user=None,
):
    """
    Create a canonical Invoice from a specification.

    Returns the persisted Invoice. Line items and sources are
    created in the same transaction.

    The caller is responsible for choosing the issuer and
    recipient. The ecommerce adapter will typically look up the
    issuer for a channel and build/lookup the recipient party
    from the order's user.
    """
    if not line_items:
        raise ValidationError(
            {"line_items": "At least one line item is required."}
        )

    if len(currency) != 3:
        raise ValidationError(
            {"currency": "Currency must be exactly three characters."}
        )

    number = allocate_invoice_number()

    # Build kwargs, only including optional values when the caller
    # provided them. This lets the model defaults apply when a
    # value is not given, rather than overriding them with None.
    create_kwargs = {
        "number": number,
        "issuer": issuer,
        "recipient": recipient,
        "currency": currency.upper(),
        "shipping_amount": shipping_amount,
        "discount_amount": discount_amount,
        "payment_terms": payment_terms,
        "notes": notes,
        "status": status,
    }
    if issue_date is not None:
        create_kwargs["issue_date"] = issue_date
    if due_date is not None:
        create_kwargs["due_date"] = due_date

    invoice = Invoice.objects.create(**create_kwargs)

    for spec in line_items:
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=spec.description,
            quantity=spec.quantity,
            unit_price=spec.unit_price,
            discount_amount=spec.discount_amount,
            tax_rate=spec.tax_rate,
            tax_amount=spec.tax_amount,
            currency=currency.upper(),
            metadata=spec.metadata,
        )

    for source in sources or []:
        InvoiceSource.objects.create(
            invoice=invoice,
            source_type=source.source_type,
            source_id=str(source.source_id),
            source_reference=source.source_reference,
        )

    invoice.recalculate_totals()
    invoice.save(
        update_fields=[
            "subtotal_amount",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "balance_due",
            "updated_at",
        ]
    )

    InvoiceEvent.objects.create(
        invoice=invoice,
        type=InvoiceEventType.CREATED,
        actor=created_by_user,
    )

    return invoice