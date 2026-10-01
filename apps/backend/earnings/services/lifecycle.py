# apps/backend/earnings/services/lifecycle.py

"""
Canonical earning lifecycle management.

The lifecycle service is the single authority for Earning state
transitions.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from audit.constants import AuditAction

from ..models import Earning
from .audit import EarningAuditService


class EarningLifecycle:

    TRANSITIONS = {
        Earning.Status.PENDING: {
            Earning.Status.CALCULATED,
            Earning.Status.CANCELLED,
        },
        Earning.Status.CALCULATED: {
            Earning.Status.CONFIRMED,
            Earning.Status.CANCELLED,
            Earning.Status.REVERSED,
        },
        Earning.Status.CONFIRMED: {
            Earning.Status.PAYABLE,
            Earning.Status.REVERSED,
        },
        Earning.Status.PAYABLE: {
            Earning.Status.SETTLED,
            Earning.Status.REVERSED,
        },
        Earning.Status.SETTLED: {
            Earning.Status.REVERSED,
        },
        Earning.Status.CANCELLED: set(),
        Earning.Status.REVERSED: set(),
    }

    AUDIT_ACTIONS = {
        Earning.Status.CALCULATED:
            AuditAction.EARNING_CALCULATED,

        Earning.Status.CONFIRMED:
            AuditAction.EARNING_CONFIRMED,

        Earning.Status.PAYABLE:
            AuditAction.EARNING_PAYABLE,

        Earning.Status.SETTLED:
            AuditAction.EARNING_SETTLED,

        Earning.Status.CANCELLED:
            AuditAction.EARNING_CANCELLED,

        Earning.Status.REVERSED:
            AuditAction.EARNING_REVERSED,
    }

    @classmethod
    def can_transition(
        cls,
        *,
        current_status: str,
        target_status: str,
    ) -> bool:
        return target_status in cls.TRANSITIONS.get(
            current_status,
            set(),
        )

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        *,
        earning: Earning,
        target_status: str,
        actor=None,
    ) -> Earning:

        current_status = earning.status

        if current_status == target_status:
            raise ValidationError(
                _(
                    "Earning is already in the %(status)s state."
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
                    "Invalid earning transition: "
                    "%(current)s → %(target)s."
                )
                % {
                    "current": current_status,
                    "target": target_status,
                }
            )

        cls._validate_transition_requirements(
            earning=earning,
            target_status=target_status,
        )

        now = timezone.now()

        earning.status = target_status

        update_fields = [
            "status",
            "updated_at",
        ]

        if target_status == Earning.Status.CALCULATED:
            earning.calculated_at = now
            update_fields.append("calculated_at")

        elif target_status == Earning.Status.CONFIRMED:
            earning.confirmed_at = now
            update_fields.append("confirmed_at")

        elif target_status == Earning.Status.PAYABLE:
            earning.payable_at = now
            update_fields.append("payable_at")

        elif target_status == Earning.Status.SETTLED:
            earning.settled_at = now
            update_fields.append("settled_at")

        elif target_status == Earning.Status.REVERSED:
            earning.reversed_at = now
            update_fields.append("reversed_at")

        earning.full_clean()

        earning.save(
            update_fields=update_fields,
        )

        audit_action = cls.AUDIT_ACTIONS.get(
            target_status
        )

        if audit_action is not None:
            EarningAuditService.record_transition(
                earning=earning,
                action=audit_action,
                actor=actor,
                from_status=current_status,
                to_status=target_status,
            )

        return earning

    @classmethod
    def _validate_transition_requirements(
        cls,
        *,
        earning: Earning,
        target_status: str,
    ) -> None:

        if target_status == Earning.Status.CALCULATED:
            if earning.amount is None:
                raise ValidationError(
                    _(
                        "An earning must have an amount "
                        "before entering the calculated state."
                    )
                )

        if target_status == Earning.Status.CONFIRMED:
            if earning.amount <= 0:
                raise ValidationError(
                    _(
                        "Only positive earnings can be confirmed."
                    )
                )

        if target_status == Earning.Status.SETTLED:
            if earning.status != Earning.Status.PAYABLE:
                raise ValidationError(
                    _(
                        "Only payable earnings can be settled."
                    )
                )