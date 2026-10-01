"""
Commission audit integration for Univa.

This module adapts commission lifecycle events to the canonical
AuditLog service.

Commission code does not create AuditLog records directly.

Canonical flow:

    CommissionLifecycle
        ↓
    CommissionAuditService
        ↓
    audit.services.audit.record_audit()
        ↓
    AuditLog
"""

from typing import Any

from audit.constants import AuditAction
from audit.services.audit import record_audit

from ..models import Commission


class CommissionAuditService:
    """
    Application boundary between commissions and the canonical
    Univa audit infrastructure.
    """

    @staticmethod
    def record_transition(
        *,
        commission: Commission,
        action: str,
        actor=None,
        from_status: str | None = None,
        to_status: str | None = None,
        **extra_data: Any,
    ):
        """
        Record a commission lifecycle transition.

        Args:
            commission:
                The commission whose lifecycle changed.

            action:
                A valid commission AuditAction.

            actor:
                The user or system actor responsible for the change.

            from_status:
                Commission status before the transition.

            to_status:
                Commission status after the transition.

            extra_data:
                Additional contextual audit information.
        """

        data = {
            "object_type": "commission",
            "object_id": str(commission.id),
            "from_status": from_status,
            "to_status": to_status,
            "calculated_amount": str(
                commission.calculated_amount
            ),
            "currency": commission.currency,
            "source_type": commission.source_type,
            "source_id": commission.source_id,
            "plan_id": str(commission.plan_id),
        }

        data.update(extra_data)

        return record_audit(
            action=action,
            actor=actor,
            target_user=commission.beneficiary,
            data=data,
        )