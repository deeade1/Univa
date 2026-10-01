from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from payment.canonical.models import PaymentExecution


class PaymentExecutionLifecycle:
    """
    Canonical lifecycle transitions for PaymentExecution.

    This lifecycle owns execution state only.

    It does not:
        - call providers
        - select providers
        - process webhooks
        - perform reconciliation
        - mutate Payment status
        - move Banking money
    """

    TRANSITIONS = {
        PaymentExecution.Status.CREATED: {
            PaymentExecution.Status.PROCESSING,
            PaymentExecution.Status.CANCELLED,
        },
        PaymentExecution.Status.PROCESSING: {
            PaymentExecution.Status.PENDING,
            PaymentExecution.Status.COMPLETED,
            PaymentExecution.Status.FAILED,
            PaymentExecution.Status.CANCELLED,
        },
        PaymentExecution.Status.PENDING: {
            PaymentExecution.Status.COMPLETED,
            PaymentExecution.Status.FAILED,
            PaymentExecution.Status.CANCELLED,
        },
        PaymentExecution.Status.FAILED: set(),
        PaymentExecution.Status.CANCELLED: set(),
        PaymentExecution.Status.COMPLETED: set(),
    }

    @classmethod
    def _validate_transition(
        cls,
        current_status,
        new_status,
    ):
        allowed = cls.TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot transition PaymentExecution "
                        f"from {current_status} to {new_status}."
                    )
                }
            )

    @classmethod
    def _save_transition(
        cls,
        execution,
        *,
        new_status,
        timestamp_field=None,
    ):
        previous_status = execution.status

        cls._validate_transition(
            previous_status,
            new_status,
        )

        execution.status = new_status

        if timestamp_field:
            setattr(
                execution,
                timestamp_field,
                timezone.now(),
            )

        execution.full_clean()
        execution.save()

        return execution

    @classmethod
    @transaction.atomic
    def mark_processing(cls, execution):
        """
        CREATED → PROCESSING
        """
        execution = (
            PaymentExecution.objects
            .select_for_update()
            .get(pk=execution.pk)
        )

        return cls._save_transition(
            execution,
            new_status=PaymentExecution.Status.PROCESSING,
            timestamp_field="processing_at",
        )

    @classmethod
    @transaction.atomic
    def mark_pending(
        cls,
        execution,
        *,
        reconciliation_required=False,
    ):
        """
        PROCESSING → PENDING

        A pending execution represents an outcome that has not
        yet reached a terminal financial state.

        If the outcome is uncertain, reconciliation must be
        required.
        """
        execution = (
            PaymentExecution.objects
            .select_for_update()
            .get(pk=execution.pk)
        )

        cls._validate_transition(
            execution.status,
            PaymentExecution.Status.PENDING,
        )

        if reconciliation_required:
            execution.reconciliation_state = (
                PaymentExecution.ReconciliationState.REQUIRED
            )
        else:
            execution.reconciliation_state = (
                PaymentExecution.ReconciliationState.PENDING
            )

        execution.status = PaymentExecution.Status.PENDING
        execution.pending_at = timezone.now()

        execution.full_clean()
        execution.save()

        return execution

    @classmethod
    @transaction.atomic
    def mark_completed(
        cls,
        execution,
    ):
        """
        PROCESSING/PENDING → COMPLETED.

        Completion means the execution has sufficient evidence
        that the financial operation succeeded.
        """
        execution = (
            PaymentExecution.objects
            .select_for_update()
            .get(pk=execution.pk)
        )

        cls._validate_transition(
            execution.status,
            PaymentExecution.Status.COMPLETED,
        )

        execution.status = PaymentExecution.Status.COMPLETED
        execution.completed_at = timezone.now()

        execution.full_clean()
        execution.save()

        return execution

    @classmethod
    @transaction.atomic
    def mark_failed(
        cls,
        execution,
        *,
        failure_code="",
        failure_reason="",
    ):
        """
        PROCESSING/PENDING → FAILED.

        Failure details belong to the execution because they
        describe the execution attempt.
        """
        if not failure_reason or not failure_reason.strip():
            raise ValidationError(
                {
                    "failure_reason": (
                        "Failure reason is required."
                    )
                }
            )

        execution = (
            PaymentExecution.objects
            .select_for_update()
            .get(pk=execution.pk)
        )

        cls._validate_transition(
            execution.status,
            PaymentExecution.Status.FAILED,
        )

        execution.status = PaymentExecution.Status.FAILED
        execution.failure_code = failure_code or ""
        execution.failure_reason = failure_reason
        execution.failed_at = timezone.now()

        execution.full_clean()
        execution.save()

        return execution

    @classmethod
    @transaction.atomic
    def cancel(cls, execution):
        """
        CREATED/PROCESSING/PENDING → CANCELLED.

        Whether cancellation is safe for an in-flight provider
        operation is established by the execution/integration
        layer. This method only performs the canonical state
        transition.
        """
        execution = (
            PaymentExecution.objects
            .select_for_update()
            .get(pk=execution.pk)
        )

        return cls._save_transition(
            execution,
            new_status=PaymentExecution.Status.CANCELLED,
            timestamp_field="cancelled_at",
        )