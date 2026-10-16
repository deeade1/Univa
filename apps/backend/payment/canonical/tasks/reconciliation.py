"""
Asynchronous reconciliation task for canonical PaymentExecution.

Architectural responsibility
----------------------------

This task is intentionally a thin asynchronous adapter.

It is responsible only for:

    - receiving a PaymentExecution identifier
    - loading the persisted PaymentExecution
    - delegating to ReconciliationDispatcher
    - returning the delegated result

It does NOT:

    - implement reconciliation rules
    - select Banking vs generic reconciliation
    - collect evidence
    - resolve Banking transactions
    - call providers
    - process webhooks
    - perform lifecycle transitions
    - mutate PaymentExecution directly
    - mutate Payment directly
    - implement retry policy
"""
from celery import shared_task

from payment.canonical.models import PaymentExecution
from payment.canonical.services.reconciliation_entry import (
    ReconciliationEntryPoint,
)
from payment.canonical.services.reconciliation_trigger import (
    ReconciliationTriggerPolicy,
)


@shared_task
def reconcile_payment_execution_task(execution_id):
    execution = PaymentExecution.objects.get(
        pk=execution_id,
    )

    if not ReconciliationTriggerPolicy.is_eligible(
        execution=execution,
    ):
        return None

    return ReconciliationEntryPoint.reconcile(
        execution=execution,
    )