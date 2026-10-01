from django.core.exceptions import ValidationError
from django.db import transaction

from payment.canonical.models import Payment


class PaymentLifecycle:
    """
    Canonical lifecycle transitions for Payment.

    PaymentLifecycle owns Payment state transitions only.

    It does not:
        - execute providers
        - create PaymentExecution records
        - perform reconciliation
        - move Banking money
        - calculate entitlements
        - manage Settlement eligibility
    """

    TRANSITIONS = {
        Payment.Status.PENDING: {
            Payment.Status.PROCESSING,
            Payment.Status.CANCELLED,
        },
        Payment.Status.PROCESSING: {
            Payment.Status.COMPLETED,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        },
        Payment.Status.FAILED: {
            Payment.Status.PROCESSING,
        },
        Payment.Status.COMPLETED: {
            Payment.Status.REVERSED,
        },
        Payment.Status.CANCELLED: set(),
        Payment.Status.REVERSED: set(),
    }

    @classmethod
    def _validate_transition(cls, current_status, new_status):
        allowed = cls.TRANSITIONS.get(current_status, set())

        if new_status not in allowed:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot transition Payment from "
                        f"{current_status} to {new_status}."
                    )
                }
            )

    @classmethod
    def _save_transition(
        cls,
        payment,
        *,
        new_status,
        timestamp_field=None,
    ):
        previous_status = payment.status

        cls._validate_transition(
            previous_status,
            new_status,
        )

        payment.status = new_status

        if timestamp_field:
            from django.utils import timezone

            setattr(
                payment,
                timestamp_field,
                timezone.now(),
            )

        payment.full_clean()
        payment.save()

        return payment

    @classmethod
    @transaction.atomic
    def mark_processing(cls, payment):
        """
        PENDING → PROCESSING
        FAILED  → PROCESSING

        A retry creates a new PaymentExecution.
        PaymentLifecycle only changes the Payment state.
        """
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        return cls._save_transition(
            payment,
            new_status=Payment.Status.PROCESSING,
            timestamp_field="processing_at",
        )

    @classmethod
    @transaction.atomic
    def mark_completed(cls, payment):
        """
        PROCESSING → COMPLETED
        """
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        return cls._save_transition(
            payment,
            new_status=Payment.Status.COMPLETED,
            timestamp_field="completed_at",
        )

    @classmethod
    @transaction.atomic
    def mark_failed(cls, payment):
        """
        PROCESSING → FAILED.

        Execution-specific failure information belongs to
        PaymentExecution, not Payment.
        """
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        return cls._save_transition(
            payment,
            new_status=Payment.Status.FAILED,
            timestamp_field="failed_at",
        )

    @classmethod
    @transaction.atomic
    def cancel(cls, payment):
        """
        PENDING → CANCELLED
        PROCESSING → CANCELLED

        PROCESSING → CANCELLED is only valid when the
        execution layer has established that cancellation
        is safe.
        """
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        return cls._save_transition(
            payment,
            new_status=Payment.Status.CANCELLED,
            timestamp_field="cancelled_at",
        )

    @classmethod
    @transaction.atomic
    def reverse(cls, payment):
        """
        COMPLETED → REVERSED.

        Reversal is a Payment lifecycle operation.
        It does not itself move Banking money or execute
        a provider refund.
        """
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        return cls._save_transition(
            payment,
            new_status=Payment.Status.REVERSED,
            timestamp_field="reversed_at",
        )