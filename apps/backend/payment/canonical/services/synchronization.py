from django.core.exceptions import ValidationError
from django.db import transaction

from payment.canonical.models import Payment, PaymentExecution
from payment.canonical.services.lifecycle import PaymentLifecycle


class PaymentExecutionSynchronization:
    """
    Synchronizes the overall Payment lifecycle from a PaymentExecution.

    PaymentExecution is the authority for an individual execution attempt.

    Payment remains the authority for the overall payment operation.

    This service does not:
        - create PaymentExecution records
        - create retries
        - call providers
        - perform reconciliation
        - mutate Payment directly
        - mutate PaymentExecution directly
        - create execution events
    """

    @classmethod
    def _validate_execution(cls, execution):
        if execution is None:
            raise ValidationError(
                {"execution": "Payment execution is required."}
            )

        if not isinstance(execution, PaymentExecution):
            raise ValidationError(
                {
                    "execution": (
                        "A valid PaymentExecution instance is required."
                    )
                }
            )

    @classmethod
    def _get_payment(cls, execution):
        payment = execution.payment

        if payment is None:
            raise ValidationError(
                {"payment": "Payment execution must belong to a payment."}
            )

        if not isinstance(payment, Payment):
            raise ValidationError(
                {"payment": "Payment execution has an invalid payment."}
            )

        return payment

    @classmethod
    @transaction.atomic
    def synchronize(cls, execution):
        """
        Synchronize Payment from the current PaymentExecution state.

        Rules:

            CREATED
                → no Payment change

            PROCESSING
                → Payment PENDING → PROCESSING
                → Payment PROCESSING → no-op

            PENDING
                → no Payment change

            COMPLETED
                → Payment PROCESSING → COMPLETED

            FAILED
                → no Payment change

            CANCELLED
                → no Payment change

        Individual execution failure/cancellation does not
        automatically terminalize the overall Payment.
        """

        cls._validate_execution(execution)

        execution = (
            PaymentExecution.objects
            .select_related("payment")
            .select_for_update()
            .get(pk=execution.pk)
        )

        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=execution.payment_id)
        )

        status = execution.status

        if status == PaymentExecution.Status.CREATED:
            return payment

        if status == PaymentExecution.Status.PROCESSING:
            if payment.status == Payment.Status.PENDING:
                return PaymentLifecycle.mark_processing(payment)

            if payment.status == Payment.Status.PROCESSING:
                return payment

            raise ValidationError(
                {
                    "payment": (
                        "Cannot synchronize a processing execution "
                        f"to a {payment.status} payment."
                    )
                }
            )

        if status == PaymentExecution.Status.PENDING:
            return payment

        if status == PaymentExecution.Status.COMPLETED:
            if payment.status == Payment.Status.PROCESSING:
                return PaymentLifecycle.mark_completed(payment)

            if payment.status == Payment.Status.COMPLETED:
                return payment

            raise ValidationError(
                {
                    "payment": (
                        "Cannot synchronize a completed execution "
                        f"to a {payment.status} payment."
                    )
                }
            )

        if status == PaymentExecution.Status.FAILED:
            return payment

        if status == PaymentExecution.Status.CANCELLED:
            return payment

        raise ValidationError(
            {
                "status": (
                    "Unsupported PaymentExecution status: "
                    f"{status}."
                )
            }
        )