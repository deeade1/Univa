# apps/backend/invoice/services/numbering.py

"""
Atomic invoice-number allocation.

Every invoice number is drawn from a per-month sequence, locked
with select_for_update, so that concurrent invoice creation
cannot produce duplicates or gaps.
"""

from django.db import transaction
from django.utils import timezone

from invoice.models import InvoiceNumberSequence


def allocate_invoice_number(*, prefix="INV", when=None):
    """
    Allocate the next invoice number for the given period.

    Returns a string of the form INV-YYYYMM-NNNN.

    Concurrency: two callers in the same second receive different
    numbers. The sequence row is locked for the duration of the
    transaction.
    """
    when = when or timezone.now()

    with transaction.atomic():
        sequence, _ = (
            InvoiceNumberSequence.objects
            .select_for_update()
            .get_or_create(
                prefix=prefix,
                year=when.year,
                month=when.month,
                defaults={"next_value": 1},
            )
        )

        value = sequence.next_value
        sequence.next_value = value + 1
        sequence.save(update_fields=["next_value"])

    return f"{prefix}-{when.year}{when.month:02d}-{value:04d}"