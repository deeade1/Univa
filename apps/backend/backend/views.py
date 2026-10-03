# apps/backend/backend/views.py

"""
Receipt / invoice PDF views.

Previously these views used the Gotomarket Purchase model. That model
was removed in the refactor — purchases are now Orders, and receipts
render from `invoice.Invoice` directly.

Invoice PDF rendering is intentionally decoupled from the Order/
Purchase model: any invoice (gotomarket, catalog, or manual) can be
rendered by ID.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from invoice.models import Invoice


@login_required
def purchase_pdf_view(request, purchase_id=None, invoice_id=None):
    """
    Generate and return a PDF receipt for an invoice.

    DEPRECATED name — kept for URL compatibility. Purchase-based
    receipts are no longer supported; every purchase now produces an
    Invoice.
    """
    if not invoice_id:
        return HttpResponse(
            "Missing invoice_id. Purchase-based receipts are no longer "
            "supported; use the invoice endpoint.",
            status=400,
        )

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        customer=request.user,
    )

    pdf_bytes = generate_invoice_pdf(invoice)

    if not pdf_bytes:
        return HttpResponse(
            "PDF generation failed. Install weasyprint or check server logs.",
            status=500,
        )

    filename = f"invoice_{invoice.number or invoice.invoice_number}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(pdf_bytes)
    return response


def generate_invoice_pdf(invoice: Invoice) -> bytes | None:
    """
    Generate PDF bytes from an invoice.

    Returns None if weasyprint is not installed.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        return None

    seller_name = getattr(settings, "MARKET_NAME", "Univa Market")
    seller_addr = getattr(settings, "MARKET_ADDRESS", "")
    seller_phone = getattr(settings, "MARKET_PHONE", "")

    html_content = build_invoice_html(
        invoice,
        seller_name,
        seller_addr,
        seller_phone,
    )

    return HTML(string=html_content, base_url="").write_pdf()


def build_invoice_html(
    invoice: Invoice,
    seller_name: str,
    seller_addr: str,
    seller_phone: str,
) -> str:
    """
    Build HTML content for an invoice PDF.
    """
    naira = "\u20a6"  # ₦

    rows = "".join(
        f"""
        <tr>
          <td style="padding:8px">{line.description}</td>
          <td style="text-align:center">{line.quantity}</td>
          <td style="text-align:right">{naira}{line.unit_price:.2f}</td>
          <td style="text-align:right">{naira}{line.total:.2f}</td>
        </tr>
        """
        for line in invoice.line_items.all()
    )

    notes_block = (
        f"<div style='margin: 20px 0;'><strong>Notes:</strong><br/>"
        f"{invoice.notes}</div>"
        if invoice.notes
        else ""
    )

    terms_block = (
        f"<div style='margin: 20px 0;'>"
        f"<strong>Terms & Conditions:</strong><br/>"
        f"{invoice.terms_and_conditions}</div>"
        if getattr(invoice, "terms_and_conditions", "")
        else ""
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{
    font-family: Arial, sans-serif;
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    color: #111;
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #333;
    padding-bottom: 20px;
    margin-bottom: 20px;
  }}
  .header h1 {{ margin: 0; color: #333; }}
  .header p {{ margin: 5px 0; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th {{
    background-color: #f5f5f5;
    padding: 10px;
    text-align: left;
    border-bottom: 2px solid #333;
  }}
  td {{ padding: 8px; border-bottom: 1px solid #eee; }}
  .total-row td {{ border-top: 2px solid #333; font-weight: bold; }}
  .footer {{
    margin-top: 30px;
    text-align: center;
    border-top: 2px solid #333;
    padding-top: 20px;
    color: #666;
  }}
  .status-badge {{
    display: inline-block;
    padding: 3px 12px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 14px;
  }}
  .status-PAID {{ background-color: #4CAF50; color: white; }}
  .status-SENT {{ background-color: #2196F3; color: white; }}
  .status-DRAFT {{ background-color: #9E9E9E; color: white; }}
  .status-CANCELLED {{ background-color: #f44336; color: white; }}
  .status-REFUNDED {{ background-color: #9C27B0; color: white; }}
  .status-OVERDUE {{ background-color: #FF9800; color: white; }}
  .status-VOID {{ background-color: #607D8B; color: white; }}
</style>
</head>
<body>
  <div class="header">
    <h1>{seller_name}</h1>
    <p>{seller_addr}</p>
    <p>Tel: {seller_phone}</p>
  </div>

  <div style="margin: 20px 0;">
    <div><strong>Invoice:</strong> {invoice.number or invoice.invoice_number}</div>
    <div><strong>Date:</strong> {invoice.issue_date.strftime('%Y-%m-%d')}</div>
    <div><strong>Status:</strong>
      <span class="status-badge status-{invoice.status}">
        {invoice.get_status_display()}
      </span>
    </div>
    <div><strong>Due Date:</strong> {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'}</div>
    <div><strong>Customer:</strong> {invoice.customer.email if invoice.customer else invoice.billing_email}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="text-align:left">Item</th>
        <th style="text-align:center">Qty</th>
        <th style="text-align:right">Price</th>
        <th style="text-align:right">Total</th>
      </tr>
    </thead>
    <tbody>
      {rows}
      <tr class="total-row">
        <td colspan="3" style="text-align:right">Subtotal</td>
        <td style="text-align:right">{naira}{invoice.subtotal:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Tax</td>
        <td style="text-align:right">{naira}{invoice.tax_amount:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Discount</td>
        <td style="text-align:right">-{naira}{invoice.discount_amount:.2f}</td>
      </tr>
      <tr class="total-row">
        <td colspan="3" style="text-align:right">Grand Total</td>
        <td style="text-align:right">{naira}{invoice.total_amount:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Amount Paid</td>
        <td style="text-align:right">{naira}{invoice.amount_paid:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Balance Due</td>
        <td style="text-align:right">{naira}{invoice.balance_due:.2f}</td>
      </tr>
    </tbody>
  </table>

  {notes_block}
  {terms_block}

  <div class="footer">
    <p>Thank you for your business!</p>
    <p style="font-size: 12px;">This is a computer-generated receipt. No signature required.</p>
  </div>
</body>
</html>"""