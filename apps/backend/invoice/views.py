# apps/backend/invoice/views.py

"""
Public views for shared invoices.

The only unauthenticated view in the invoice app. It is reached
by an opaque token, not by invoice pk.
"""

from django.http import HttpResponseGone
from django.shortcuts import render
from django.views import View

from invoice.services.share import resolve_share


class SharedInvoiceView(View):
    """
    Render a shared invoice for a token holder.

    The view is bounded: it shows the invoice header, line items
    (if the share allows), and the issuer and recipient names. It
    does not expose account details, other invoices, or the
    source domain.
    """

    def get(self, request, token):
        share = resolve_share(token)

        if share is None:
            return HttpResponseGone(
                "This link is not valid, has been revoked, or has expired.",
                content_type="text/plain",
            )

        share.record_view()

        invoice = share.invoice
        line_items = (
            invoice.line_items.all() if share.include_line_items else []
        )

        return render(
            request,
            "invoice/shared.html",
            {
                "invoice": invoice,
                "issuer": invoice.issuer,
                "recipient": invoice.recipient,
                "line_items": line_items,
                "include_line_items": share.include_line_items,
                "share": share,
                "is_share_view": True,
            },
        )