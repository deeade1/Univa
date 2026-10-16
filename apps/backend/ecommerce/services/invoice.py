# apps/backend/ecommerce/services/invoice.py

"""
Ecommerce -> Invoice adapter.

This is the only place ecommerce and invoice meet. The invoice
app does not import ecommerce; ecommerce imports invoice
services and translates Order shape into the canonical
LineItemSpec / SourceSpec shape.

Called from the order-placed flow (typically via a signal
receiver on OrderEvent type=PLACED). Idempotent: if an invoice
already exists for the order, returns it unchanged.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from invoice.enums import InvoiceStatus
from invoice.models import Invoice, InvoiceParty
from invoice.services import (
    LineItemSpec,
    SourceSpec,
    generate_invoice,
)


logger = logging.getLogger(__name__)


# =====================================================================
# ISSUER RESOLUTION
# =====================================================================


# A minimal mapping from channel country to legal entity. In
# production this would come from a database table (or
# settings-driven registry) so that adding a jurisdiction
# doesn't require code changes. For now, name-based lookup on
# InvoiceParty keeps the adapter declarative.
DEFAULT_ISSUER_NAME = "Univa"


def _resolve_issuer_for_channel(channel) -> InvoiceParty:
    """
    Return the legal issuer for a channel's country.

    Falls back to a generic "Univa" party if no
    jurisdiction-specific issuer is configured. The fallback is
    idempotent: repeated calls return the same party row.
    """
    country_code = getattr(channel, "default_country", None)
    country_code = str(country_code) if country_code else ""

    issuer_name = DEFAULT_ISSUER_NAME
    if country_code:
        issuer_name = f"{DEFAULT_ISSUER_NAME} {country_code}"

    issuer, _ = InvoiceParty.objects.get_or_create(
        name=issuer_name,
        is_organization=True,
        defaults={"tax_id": ""},
    )
    return issuer


# =====================================================================
# RECIPIENT RESOLUTION
# =====================================================================


def _recipient_from_order(order) -> InvoiceParty:
    """
    Build or look up the InvoiceParty for an order's customer.

    Uses the user account when present. Falls back to a guest
    party keyed on the order email.
    """
    if order.user_id:
        party, _ = InvoiceParty.objects.get_or_create(
            user_id=order.user_id,
            defaults={
                "name": (
                    order.user.get_full_name()
                    or order.user.email
                ),
                "email": order.user.email,
            },
        )
        return party

    party, _ = InvoiceParty.objects.get_or_create(
        user=None,
        email=order.user_email,
        defaults={
            "name": order.user_email,
            "is_organization": False,
        },
    )
    return party


# =====================================================================
# LINE ITEM TRANSLATION
# =====================================================================


def _line_item_specs_for_order(order) -> list[LineItemSpec]:
    """
    Translate OrderLine rows into canonical LineItemSpec objects.

    Tax rate is derived from the gross/net split on each line,
    matching the ecommerce pricing convention. The rate is a
    percentage (7.5 = 7.5%).
    """
    specs: list[LineItemSpec] = []

    for line in order.lines.all():
        tax_amount = (
            line.total_price_gross_amount
            - line.total_price_net_amount
        )

        tax_rate = Decimal("0.00")
        if line.total_price_net_amount > 0:
            tax_rate = (
                tax_amount
                / line.total_price_net_amount
                * Decimal("100")
            ).quantize(Decimal("0.01"))

        specs.append(
            LineItemSpec(
                description=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price_gross_amount,
                discount_amount=Decimal("0.00"),
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                metadata={
                    "order_line_id": str(line.pk),
                    "variant_name": line.variant_name or "",
                    "quantity_unit": line.quantity_unit or "",
                },
            )
        )

    return specs


# =====================================================================
# PUBLIC ENTRY POINT
# =====================================================================


@transaction.atomic
def generate_invoice_from_order(order) -> Invoice:
    """
    Create an Invoice for an ecommerce Order.

    Idempotent: if an invoice already exists for this order, the
    existing invoice is returned unchanged.

    Raises ValueError if the order has no lines.
    """
    # Idempotency: check for an existing invoice sourced from
    # this order before doing any work.
    existing = Invoice.objects.for_source(
        source_type="order",
        source_id=str(order.pk),
    ).first()

    if existing is not None:
        return existing

    line_items = _line_item_specs_for_order(order)
    if not line_items:
        raise ValueError(
            f"Order {order.pk} has no lines; cannot generate invoice."
        )

    issuer = _resolve_issuer_for_channel(order.channel)
    recipient = _recipient_from_order(order)

    sources = [
        SourceSpec(
            source_type="order",
            source_id=str(order.pk),
            source_reference=getattr(order, "number", "") or str(order.pk),
        )
    ]

    invoice = generate_invoice(
        issuer=issuer,
        recipient=recipient,
        currency=order.currency,
        line_items=line_items,
        sources=sources,
        shipping_amount=order.shipping_price_net_amount,
        status=InvoiceStatus.DRAFT,
    )

    logger.info(
        "Generated invoice %s for order %s",
        invoice.number,
        order.pk,
    )

    return invoice