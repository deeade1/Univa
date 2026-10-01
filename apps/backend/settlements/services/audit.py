from audit.constants import AuditAction
from audit.services.audit import record_audit
from settlements.models import Settlement

SETTLEMENT_AUDIT_ACTIONS = {
Settlement.Status.ELIGIBLE: AuditAction.SETTLEMENT_ELIGIBLE,
Settlement.Status.PROCESSING: AuditAction.SETTLEMENT_PROCESSING,
Settlement.Status.SETTLED: AuditAction.SETTLEMENT_SETTLED,
Settlement.Status.FAILED: AuditAction.SETTLEMENT_FAILED,
Settlement.Status.CANCELLED: AuditAction.SETTLEMENT_CANCELLED,
Settlement.Status.REVERSED: AuditAction.SETTLEMENT_REVERSED,
}

class SettlementAuditService:
    """
    Audit adapter for Settlement lifecycle events.
    Settlement owns the lifecycle.
    Audit infrastructure owns AuditLog persistence.

    This service translates Settlement lifecycle transitions into
    canonical audit events through audit.services.audit.record_audit().
    """

    @classmethod
    def record_transition(
        cls,
        settlement,
        *,
        previous_status,
        new_status,
        actor=None,
    ):
        """
        Record a Settlement lifecycle transition.

        The transition must correspond to a known Settlement audit action.
        """

        if new_status not in SETTLEMENT_AUDIT_ACTIONS:
            raise ValueError(
                f"No audit action configured for settlement status "
                f"{new_status!r}."
            )

        action = SETTLEMENT_AUDIT_ACTIONS[new_status]

        data = {
            "settlement_id": str(settlement.id),
            "reference": settlement.reference,
            "previous_status": previous_status,
            "new_status": new_status,
            "amount": str(settlement.amount),
            "currency": settlement.currency,
            "source_type": settlement.source_type,
            "source_id": settlement.source_id,
        }

        if settlement.source_reference:
            data["source_reference"] = settlement.source_reference

        if new_status == Settlement.Status.FAILED:
            data["failure_code"] = settlement.failure_code
            data["failure_reason"] = settlement.failure_reason

        return record_audit(
            action=action,
            actor=actor,
            target_user=settlement.beneficiary,
            data=data,
        )
