# apps/backend/invoice/services/__init__.py

"""
Invoice service layer.

Public API:

    from invoice.services import (
        generate_invoice,
        apply_payment,
        create_share,
    )

Everything else is internal.
"""

from .generation import (
    LineItemSpec,
    SourceSpec,
    generate_invoice,
)
from .lifecycle import (
    cancel,
    mark_issued,
    mark_overdue,
    mark_sent,
    refresh_paid_state,
    void,
)
from .numbering import allocate_invoice_number
from .payments import (
    apply_payment,
    reverse_payment,
)
from .render import (
    RenderBackendUnavailable,
    render_and_attach,
    render_invoice_pdf,
)
from .share import (
    create_share,
    resolve_share,
    revoke_share,
)



__all__ = [
    "LineItemSpec",
    "SourceSpec",
    "generate_invoice",
    "allocate_invoice_number",
    "mark_issued",
    "mark_sent",
    "mark_overdue",
    "cancel",
    "void",
    "refresh_paid_state",
    "apply_payment",
    "reverse_payment",
    "render_invoice_pdf",
    "render_and_attach",
    "RenderBackendUnavailable",
    "create_share",
    "revoke_share",
    "resolve_share",
]