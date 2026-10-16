from __future__ import annotations

from typing import Any

from audit.constants import AuditAction
from audit.services.audit import record_audit


class InvestorAuditService:
    """
    Investor-domain adapter for the canonical audit service.

    This service does not create AuditLog records directly.

    All persistence is delegated to:

        audit.services.audit.record_audit()
    """

    @staticmethod
    def _record(
        *,
        action: str,
        actor=None,
        target_user=None,
        data: dict[str, Any] | None = None,
    ):
        return record_audit(
            action=action,
            actor=actor,
            target_user=target_user,
            data=data,
        )

    # ------------------------------------------------------------------
    # Investor
    # ------------------------------------------------------------------

    @classmethod
    def created(
        cls,
        investor,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTOR_CREATED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @classmethod
    def updated(
        cls,
        investor,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTOR_UPDATED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @classmethod
    def activated(
        cls,
        investor,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTOR_ACTIVATED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @classmethod
    def suspended(
        cls,
        investor,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTOR_SUSPENDED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    @classmethod
    def closed(
        cls,
        investor,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTOR_CLOSED,
            actor=actor,
            target_user=investor.user,
            data={
                "investor_id": str(investor.pk),
                "reference": investor.reference,
            },
        )

    # ------------------------------------------------------------------
    # Investment Opportunity
    # ------------------------------------------------------------------

    @classmethod
    def opportunity_created(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_CREATED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @classmethod
    def opportunity_updated(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_UPDATED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @classmethod
    def opportunity_opened(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_OPENED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @classmethod
    def opportunity_paused(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_PAUSED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @classmethod
    def opportunity_closed(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_CLOSED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    @classmethod
    def opportunity_cancelled(
        cls,
        opportunity,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_OPPORTUNITY_CANCELLED,
            actor=actor,
            data={
                "opportunity_id": str(opportunity.pk),
                "reference": opportunity.reference,
            },
        )

    # ------------------------------------------------------------------
    # Investment Plan
    # ------------------------------------------------------------------

    @classmethod
    def plan_created(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_CREATED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @classmethod
    def plan_updated(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_UPDATED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @classmethod
    def plan_activated(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_ACTIVATED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @classmethod
    def plan_paused(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_PAUSED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @classmethod
    def plan_closed(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_CLOSED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    @classmethod
    def plan_cancelled(
        cls,
        plan,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_PLAN_CANCELLED,
            actor=actor,
            data={
                "plan_id": str(plan.pk),
                "reference": plan.reference,
                "opportunity_id": str(plan.opportunity_id),
            },
        )

    # ------------------------------------------------------------------
    # Investment Commitment
    # ------------------------------------------------------------------

    @classmethod
    def commitment_created(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_CREATED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
                "opportunity_id": str(commitment.opportunity_id),
                "plan_id": str(commitment.plan_id),
            },
        )

    @classmethod
    def commitment_updated(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_UPDATED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    @classmethod
    def commitment_confirmed(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_CONFIRMED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    @classmethod
    def commitment_funded(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_FUNDED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    @classmethod
    def commitment_cancelled(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_CANCELLED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    @classmethod
    def commitment_expired(
        cls,
        commitment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_COMMITMENT_EXPIRED,
            actor=actor,
            target_user=commitment.investor,
            data={
                "commitment_id": str(commitment.pk),
                "reference": commitment.reference,
            },
        )

    # ------------------------------------------------------------------
    # Investment
    # ------------------------------------------------------------------

    @classmethod
    def investment_created(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_CREATED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
                "opportunity_id": str(investment.opportunity_id),
                "plan_id": str(investment.plan_id),
                "commitment_id": str(investment.commitment_id),
            },
        )

    @classmethod
    def investment_updated(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_UPDATED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    @classmethod
    def investment_activated(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_ACTIVATED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    @classmethod
    def investment_matured(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_MATURED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    @classmethod
    def investment_closed(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_CLOSED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    @classmethod
    def investment_cancelled(
        cls,
        investment,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_CANCELLED,
            actor=actor,
            target_user=investment.investor,
            data={
                "investment_id": str(investment.pk),
                "reference": investment.reference,
            },
        )

    # ------------------------------------------------------------------
    # Investment Return
    # ------------------------------------------------------------------

    @classmethod
    def return_created(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_CREATED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
                "investment_id": str(
                    investment_return.investment_id
                ),
            },
        )

    @classmethod
    def return_updated(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_UPDATED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_calculated(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_CALCULATED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_approved(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_APPROVED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_payable(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_PAYABLE,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_paid(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_PAID,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_cancelled(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_CANCELLED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )

    @classmethod
    def return_reversed(
        cls,
        investment_return,
        *,
        actor=None,
    ):
        return cls._record(
            action=AuditAction.INVESTMENT_RETURN_REVERSED,
            actor=actor,
            target_user=investment_return.investment.investor,
            data={
                "investment_return_id": str(investment_return.pk),
                "reference": investment_return.reference,
            },
        )