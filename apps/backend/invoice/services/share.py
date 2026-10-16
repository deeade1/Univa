# apps/backend/invoice/services/share.py

"""
Share creation and revocation services.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from invoice.enums import InvoiceEventType, InvoiceShareChannel
from invoice.models import Invoice, InvoiceEvent, InvoiceShare


DEFAULT_TTL_DAYS = 30
ALLOWED_TTL_DAYS = {7, 30, 365}


@transaction.atomic
def create_share(
    *,
    invoice_id,
    created_by,
    ttl_days: int = DEFAULT_TTL_DAYS,
    label: str = "",
    recipient_email: str = "",
    recipient_phone: str = "",
    channel: str = InvoiceShareChannel.LINK_COPY,
    include_line_items: bool = True,
) -> InvoiceShare:
    """
    Create a share link for an invoice.

    Returns the persisted InvoiceShare.

    Raises ValidationError if the caller is not authorized
    (typically: the caller must be the invoice recipient, or an
    issuer-side user with explicit permission).
    """
    if ttl_days not in ALLOWED_TTL_DAYS:
        raise ValidationError(
            {
                "ttl_days": (
                    f"Share lifetime must be one of "
                    f"{sorted(ALLOWED_TTL_DAYS)} days."
                )
            }
        )

    invoice = Invoice.objects.get(pk=invoice_id)

    # Authorization: the caller must be the invoice recipient's
    # user account, or (in future iterations) an issuer-side
    # user. For now, only the recipient's user can share.
    recipient_user_id = invoice.recipient.user_id
    caller_id = getattr(created_by, "pk", None)

    if recipient_user_id is None or recipient_user_id != caller_id:
        raise ValidationError(
            {
                "created_by": (
                    "Only the invoice recipient can share this "
                    "invoice."
                )
            }
        )

    share = InvoiceShare.objects.create(
        invoice=invoice,
        created_by=created_by,
        label=label,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        channel=channel,
        include_line_items=include_line_items,
        expires_at=timezone.now() + timedelta(days=ttl_days),
    )

    InvoiceEvent.objects.create(
        invoice=invoice,
        type=InvoiceEventType.SHARE_CREATED,
        actor=created_by,
        parameters={
            "share_id": str(share.pk),
            "ttl_days": ttl_days,
        },
    )

    return share


@transaction.atomic
def revoke_share(*, share_id, by, reason: str = "") -> InvoiceShare:
    """
    Revoke a share. Idempotent.
    """
    share = InvoiceShare.objects.select_for_update().get(pk=share_id)

    if share.created_by_id != getattr(by, "pk", None):
        raise ValidationError(
            {"by": "Only the share creator can revoke this share."}
        )

    share.revoke(by=by, reason=reason)
    return share


def resolve_share(token: str):
    """
    Look up an active share by token.

    Returns the InvoiceShare if it is active (not revoked, not
    expired). Returns None otherwise.
    """
    share = (
        InvoiceShare.objects
        .select_related(
            "invoice",
            "invoice__issuer",
            "invoice__recipient",
        )
        .filter(token=token)
        .first()
    )

    if share is None or not share.is_active:
        return None

    return share