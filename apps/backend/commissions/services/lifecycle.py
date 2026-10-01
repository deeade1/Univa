"""
Commission lifecycle management for Univa.

This module defines the canonical state-transition rules for
Commission records.

Lifecycle transitions are intentionally centralized here so that
callers cannot independently move a commission between arbitrary
states.

This module does not:

    - calculate commissions
    - create commission records
    - perform settlements
    - perform payments
    - write audit records directly
    - emit notifications

Audit integration is delegated to CommissionAuditService.

Those concerns belong to their respective application/domain layers.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from audit.constants import AuditAction

from ..models import Commission
from .audit import CommissionAuditService


class CommissionLifecycle:
    """
    Canonical commission state-transition service.
    """

    TRANSITIONS = {
        Commission.Status.PENDING: {
            Commission.Status.CALCULATED,
            Commission.Status.CANCELLED,
        },
        Commission.Status.CALCULATED: {
            Commission.Status.APPROVED,
            Commission.Status.CANCELLED,
            Commission.Status.REVERSED,
        },
        Commission.Status.APPROVED: {
            Commission.Status.PAYABLE,
            Commission.Status.CANCELLED,
            Commission.Status.REVERSED,
        },
        Commission.Status.PAYABLE: {
            Commission.Status.SETTLED,
            Commission.Status.CANCELLED,
            Commission.Status.REVERSED,
        },
        Commission.Status.SETTLED: {
            Commission.Status.REVERSED,
        },
        Commission.Status.CANCELLED: set(),
        Commission.Status.REVERSED: set(),
    }

    """
    Lifecycle state → canonical audit action.

    The lifecycle service owns the state transition.
    CommissionAuditService owns adaptation of that transition
    into the canonical audit subsystem.
    """

    AUDIT_ACTIONS = {
        Commission.Status.CALCULATED: AuditAction.COMMISSION_CALCULATED,
        Commission.Status.APPROVED: AuditAction.COMMISSION_APPROVED,
        Commission.Status.PAYABLE: AuditAction.COMMISSION_PAYABLE,
        Commission.Status.SETTLED: AuditAction.COMMISSION_SETTLED,
        Commission.Status.CANCELLED: AuditAction.COMMISSION_CANCELLED,
        Commission.Status.REVERSED: AuditAction.COMMISSION_REVERSED,
    }

    @classmethod
    def can_transition(
        cls,
        *,
        current_status: str,
        target_status: str,
    ) -> bool:
        """
        Return whether a commission may move from the current
        state to the requested target state.
        """

        allowed_states = cls.TRANSITIONS.get(
            current_status,
            set(),
        )

        return target_status in allowed_states

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        *,
        commission: Commission,
        target_status: str,
        actor=None,
    ) -> Commission:
        """
        Transition a commission to a valid lifecycle state.

        The transition matrix is the single source of truth for
        commission lifecycle movement.

        Successful lifecycle transitions are recorded through the
        canonical CommissionAuditService.
        """

        current_status = commission.status

        if current_status == target_status:
            raise ValidationError(
                _(
                    "Commission is already in the %(status)s state."
                )
                % {
                    "status": target_status,
                }
            )

        if not cls.can_transition(
            current_status=current_status,
            target_status=target_status,
        ):
            raise ValidationError(
                _(
                    "Invalid commission transition: "
                    "%(current)s → %(target)s."
                )
                % {
                    "current": current_status,
                    "target": target_status,
                }
            )

        cls._validate_transition_requirements(
            commission=commission,
            target_status=target_status,
        )

        now = timezone.now()

        commission.status = target_status

        update_fields = [
            "status",
            "updated_at",
        ]

        if target_status == Commission.Status.CALCULATED:
            commission.calculated_at = now
            update_fields.append("calculated_at")

        elif target_status == Commission.Status.APPROVED:
            commission.approved_at = now
            update_fields.append("approved_at")

        elif target_status == Commission.Status.PAYABLE:
            commission.payable_at = now
            update_fields.append("payable_at")

        elif target_status == Commission.Status.SETTLED:
            commission.settled_at = now
            update_fields.append("settled_at")

        elif target_status == Commission.Status.REVERSED:
            commission.reversed_at = now
            update_fields.append("reversed_at")

        commission.full_clean()

        commission.save(
            update_fields=update_fields,
        )

        audit_action = cls.AUDIT_ACTIONS.get(target_status)

        if audit_action is not None:
            CommissionAuditService.record_transition(
                commission=commission,
                action=audit_action,
                actor=actor,
                from_status=current_status,
                to_status=target_status,
            )

        return commission

    @classmethod
    def _validate_transition_requirements(
        cls,
        *,
        commission: Commission,
        target_status: str,
    ) -> None:
        """
        Validate requirements associated with a lifecycle transition.
        """

        if target_status == Commission.Status.CALCULATED:
            if commission.calculated_amount is None:
                raise ValidationError(
                    _(
                        "A commission must have a calculated amount "
                        "before entering the calculated state."
                    )
                )

            if commission.calculated_at is None:
                # The transition method supplies this timestamp.
                return

        if target_status == Commission.Status.SETTLED:
            if commission.status != Commission.Status.PAYABLE:
                raise ValidationError(
                    _(
                        "Only payable commissions can be settled."
                    )
                )

        if target_status == Commission.Status.REVERSED:
            if commission.status == Commission.Status.CANCELLED:
                raise ValidationError(
                    _(
                        "A cancelled commission cannot be reversed."
                    )
                )
