# ecommerce/tasks/payment.py

"""
Async Celery task for executing an order's payment.

Thin wrapper: the task loads the PaymentExecution and delegates to
ExecutionOrchestrator. No business logic lives here.
"""

from __future__ import annotations

import logging

from celery import shared_task


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="payment",)
def execute_order_payment_task(self, execution_id: str):
    """
    Run ExecutionOrchestrator.execute() for a PaymentExecution.

    Idempotent: if the execution has already moved past CREATED,
    the orchestrator's state-machine guards prevent duplicate work.
    """
    from payment.canonical.models import PaymentExecution
    from payment.canonical.services.execution_orchestrator import (
        ExecutionOrchestrator,
    )

    try:
        execution = PaymentExecution.objects.get(pk=execution_id)
    except PaymentExecution.DoesNotExist:
        logger.warning(
            "PaymentExecution %s not found; task aborted.",
            execution_id,
        )
        return

    try:
        ExecutionOrchestrator.execute(execution)
    except Exception as exc:
        logger.exception(
            "PaymentExecution %s failed during orchestration.",
            execution_id,
        )
        raise self.retry(exc=exc)