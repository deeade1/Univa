from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from settlements.models import Settlement
from settlements.services.audit import SettlementAuditService

class SettlementLifecycle:
    TRANSITIONS = {
    Settlement.Status.PENDING: {
    Settlement.Status.ELIGIBLE,
    Settlement.Status.CANCELLED,
    },
    Settlement.Status.ELIGIBLE: {
    Settlement.Status.PROCESSING,
    Settlement.Status.CANCELLED,
    },
    Settlement.Status.PROCESSING: {
    Settlement.Status.SETTLED,
    Settlement.Status.FAILED,
    },
    Settlement.Status.FAILED: {
    Settlement.Status.PROCESSING,
    Settlement.Status.CANCELLED,
    },
    Settlement.Status.SETTLED: {
    Settlement.Status.REVERSED,
    },
    Settlement.Status.CANCELLED: set(),
    Settlement.Status.REVERSED: set(),
    }


    @classmethod
    def _get_locked_settlement(cls, settlement):
        return (
            Settlement.objects
            .select_for_update()
            .get(pk=settlement.pk)
        )

    @classmethod
    def _validate_transition(cls, settlement, target_status):
        allowed = cls.TRANSITIONS.get(
            settlement.status,
            set(),
        )

        if target_status not in allowed:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot transition settlement from "
                        f"{settlement.status} to "
                        f"{target_status}."
                    )
                }
            )

    @classmethod
    def _save_transition(
        cls,
        settlement,
        target_status,
        *,
        timestamp_field,
        actor=None,
    ):
        previous_status = settlement.status

        cls._validate_transition(
            settlement,
            target_status,
        )

        now = timezone.now()

        settlement.status = target_status
        setattr(settlement, timestamp_field, now)

        settlement.full_clean()
        settlement.save()

        SettlementAuditService.record_transition(
            settlement,
            previous_status=previous_status,
            new_status=target_status,
            actor=actor,
        )

        return settlement

    @classmethod
    @transaction.atomic
    def mark_eligible(cls, settlement, *, actor=None):
        settlement = cls._get_locked_settlement(settlement)

        return cls._save_transition(
            settlement,
            Settlement.Status.ELIGIBLE,
            timestamp_field="eligible_at",
            actor=actor,
        )

    @classmethod
    @transaction.atomic
    def mark_processing(cls, settlement, *, actor=None):
        settlement = cls._get_locked_settlement(settlement)

        previous_status = settlement.status

        cls._validate_transition(
            settlement,
            Settlement.Status.PROCESSING,
        )

        now = timezone.now()

        if settlement.status == Settlement.Status.FAILED:
            settlement.failure_code = ""
            settlement.failure_reason = ""
            settlement.failed_at = None

        settlement.status = Settlement.Status.PROCESSING
        settlement.processing_at = now

        settlement.full_clean()
        settlement.save()

        SettlementAuditService.record_transition(
            settlement,
            previous_status=previous_status,
            new_status=Settlement.Status.PROCESSING,
            actor=actor,
        )

        return settlement

    @classmethod
    @transaction.atomic
    def mark_settled(cls, settlement, *, actor=None):
        settlement = cls._get_locked_settlement(settlement)

        return cls._save_transition(
            settlement,
            Settlement.Status.SETTLED,
            timestamp_field="settled_at",
            actor=actor,
        )

    @classmethod
    @transaction.atomic
    def mark_failed(
        cls,
        settlement,
        *,
        failure_reason,
        failure_code="",
        actor=None,
    ):
        if not failure_reason:
            raise ValidationError(
                {
                    "failure_reason": (
                        "Failure reason is required."
                    )
                }
            )

        settlement = cls._get_locked_settlement(settlement)

        previous_status = settlement.status

        cls._validate_transition(
            settlement,
            Settlement.Status.FAILED,
        )

        settlement.status = Settlement.Status.FAILED
        settlement.failed_at = timezone.now()
        settlement.failure_code = failure_code or ""
        settlement.failure_reason = failure_reason

        settlement.full_clean()
        settlement.save()

        SettlementAuditService.record_transition(
            settlement,
            previous_status=previous_status,
            new_status=Settlement.Status.FAILED,
            actor=actor,
        )

        return settlement

    @classmethod
    @transaction.atomic
    def cancel(cls, settlement, *, actor=None):
        settlement = cls._get_locked_settlement(settlement)

        previous_status = settlement.status

        cls._validate_transition(
            settlement,
            Settlement.Status.CANCELLED,
        )

        settlement.status = Settlement.Status.CANCELLED
        settlement.cancelled_at = timezone.now()

        if settlement.failure_code or settlement.failure_reason:
            settlement.failure_code = ""
            settlement.failure_reason = ""
            settlement.failed_at = None

        settlement.full_clean()
        settlement.save()

        SettlementAuditService.record_transition(
            settlement,
            previous_status=previous_status,
            new_status=Settlement.Status.CANCELLED,
            actor=actor,
        )

        return settlement

    @classmethod
    @transaction.atomic
    def reverse(cls, settlement, *, actor=None):
        settlement = cls._get_locked_settlement(settlement)

        return cls._save_transition(
            settlement,
            Settlement.Status.REVERSED,
            timestamp_field="reversed_at",
            actor=actor,
        )
