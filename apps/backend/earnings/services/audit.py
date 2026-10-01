# apps/backend/earnings/services/audit.py

"""
Earning audit integration.

Earnings does not create AuditLog records directly.

Canonical flow:

    EarningLifecycle
        ↓
    EarningAuditService
        ↓
    audit.services.audit.record_audit()
        ↓
    AuditLog
"""

from typing import Any

from audit.services.audit import record_audit

from ..models import Earning


class EarningAuditService:

    @staticmethod
    def record_transition(
        *,
        earning: Earning,
        action: str,
        actor=None,
        from_status: str | None = None,
        to_status: str | None = None,
        **extra_data: Any,
    ):
        data = {
            "object_type": "earning",
            "object_id": str(earning.id),
            "from_status": from_status,
            "to_status": to_status,
            "amount": str(earning.amount),
            "currency": earning.currency,
            "earning_type": earning.earning_type.code,
            "source_type": earning.source_type,
            "source_id": earning.source_id,
            "source_reference": earning.source_reference,
        }

        data.update(extra_data)

        return record_audit(
            action=action,
            actor=actor,
            target_user=earning.beneficiary,
            data=data,
        )