# apps/backend/invoice/enums.py

"""
Enumerations for the invoice app.

Every status and type on every invoice model is expressed here so
that string literals never leak into business code.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class InvoiceStatus(models.TextChoices):
    """Lifecycle status of a canonical Invoice."""

    DRAFT = "draft", _("Draft")
    ISSUED = "issued", _("Issued")
    SENT = "sent", _("Sent")
    PAID = "paid", _("Paid")
    PARTIALLY_PAID = "partially_paid", _("Partially Paid")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED = "refunded", _("Refunded")
    VOID = "void", _("Void")


class InvoicePaymentType(models.TextChoices):
    """
    Where an InvoicePayment came from.

    Invoice does not know how payments are collected — the payment
    system does. This enumeration just records the source so the
    invoice can be reconciled.
    """

    PAYMENT_EXECUTION = "payment_execution", _("Payment Execution")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    CASH = "cash", _("Cash")
    MANUAL_ADJUSTMENT = "manual_adjustment", _("Manual Adjustment")
    REVERSAL = "reversal", _("Reversal")
    OTHER = "other", _("Other")


class InvoiceShareChannel(models.TextChoices):
    """
    How a share link was delivered.

    Advisory only. The token itself is channel-agnostic; this
    records the delivery method for the user's own audit.
    """

    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
    WHATSAPP = "whatsapp", _("WhatsApp")
    LINK_COPY = "link_copy", _("Link copied")
    DOWNLOAD = "download", _("Downloaded as PDF")
    IN_APP = "in_app", _("In-app forward")
    API = "api", _("API")


class InvoiceEventType(models.TextChoices):
    """
    Append-only audit events. Mirrors OrderEvent and
    PaymentExecutionEvent.
    """

    CREATED = "created", _("Created")
    ISSUED = "issued", _("Issued")
    SENT = "sent", _("Sent")
    PAYMENT_APPLIED = "payment_applied", _("Payment applied")
    PAID = "paid", _("Paid")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")
    VOIDED = "voided", _("Voided")
    REFUNDED = "refunded", _("Refunded")
    RENDERED = "rendered", _("Rendered to PDF")
    SHARE_CREATED = "share_created", _("Share created")
    SHARE_REVOKED = "share_revoked", _("Share revoked")