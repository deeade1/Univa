# apps/backend/invoice/services/render.py

"""
PDF rendering service.

Rendering is optional. If WeasyPrint is not installed, the
service raises a clear error rather than silently returning
None. Callers decide how to handle the failure.
"""

from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from invoice.enums import InvoiceEventType
from invoice.models import Invoice, InvoiceEvent


class RenderBackendUnavailable(RuntimeError):
    """Raised when no PDF backend is available."""


def render_invoice_pdf(invoice, *, actor=None) -> bytes:
    """
    Render the invoice to PDF bytes.

    Raises RenderBackendUnavailable if WeasyPrint is missing.
    """
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RenderBackendUnavailable(
            "WeasyPrint is not installed. Install it or disable "
            "PDF rendering."
        ) from exc

    html = render_to_string(
        "invoice/invoice.html",
        {
            "invoice": invoice,
            "issuer": invoice.issuer,
            "recipient": invoice.recipient,
            "line_items": invoice.line_items.all(),
            "sources": invoice.sources.all(),
            "is_share_view": False,
        },
    )

    return HTML(string=html, base_url="").write_pdf()


@transaction.atomic
def render_and_attach(invoice, *, actor=None) -> Invoice:
    """
    Render the invoice to PDF and attach it to invoice_file.
    """
    pdf_bytes = render_invoice_pdf(invoice, actor=actor)

    filename = f"{invoice.number}.pdf"
    invoice.rendered_file.save(
        filename,
        ContentFile(pdf_bytes),
        save=False,
    )
    invoice.rendered_at = timezone.now()
    invoice.save(
        update_fields=["rendered_file", "rendered_at", "updated_at"]
    )

    InvoiceEvent.objects.create(
        invoice=invoice,
        type=InvoiceEventType.RENDERED,
        actor=actor,
        parameters={"bytes": len(pdf_bytes)},
    )

    return invoice