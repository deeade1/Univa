# apps/backend/ecommerce/signals/invoice.py

"""
Generate an Invoice when an order is placed.

The invoice app does not import ecommerce. Ecommerce imports
invoice services and translates the Order into the canonical
LineItemSpec / SourceSpec shape.

The adapter import is deferred to the handler body so that
importing `ecommerce.signals` does not pull in the invoice
service layer during app loading (which would create a circular
import).
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from ecommerce.models.enums import OrderEvents
from ecommerce.models.order import OrderEvent


logger = logging.getLogger(__name__)


@receiver(
    post_save,
    sender=OrderEvent,
    dispatch_uid="ecommerce.generate_invoice_on_order_placed",
)
def generate_invoice_on_order_placed(sender, instance, created, **kwargs):
    """
    Generate an Invoice when an order is placed.

    Non-blocking: if invoice generation fails, the order is not
    rolled back. An operator can retry from the admin.
    """
    if not created:
        return

    if instance.type != OrderEvents.PLACED:
        return

    # Deferred import: the invoice service layer imports invoice
    # models, which are not available at `ecommerce.signals`
    # import time (Django app registry is still initializing).
    from ecommerce.services.invoice import generate_invoice_from_order

    try:
        generate_invoice_from_order(instance.order)
    except Exception:
        logger.exception(
            "Failed to generate invoice for order %s",
            instance.order_id,
        )