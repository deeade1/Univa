"""
Canonical Payment GraphQL mutations.

GraphQL is an adapter only.

Every mutation delegates to a canonical payment service.

This module MUST NOT:

    - implement payment business rules
    - call Payment.objects.create()
    - execute providers directly
    - perform reconciliation directly
"""

import graphene
from graphene import relay
from graphql import GraphQLError

from django.core.exceptions import ValidationError

from payment.canonical.services.execution import PaymentExecutionService
from payment.canonical.services.execution_orchestrator import (
    ExecutionOrchestrator,
)
from payment.canonical.services.reconciliation_coordinator import (
    ReconciliationCoordinator,
)
from payment.canonical.services.service import PaymentService
from univa_jwt.decorators import login_required

from graphq.accounts.types.user import UserNode

from .types import (
    PaymentExecutionNode,
    PaymentInstrumentNode,
    PaymentNode,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _graphql_error(exc, default_code="invalid_input"):
    """
    Translate a domain exception into a structured GraphQLError.

    Keeps the human-readable message but adds a stable machine code
    so clients can branch on the error type instead of parsing text.
    """
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            payload = exc.message_dict
        elif hasattr(exc, "messages"):
            payload = exc.messages
        else:
            payload = str(exc)

        return GraphQLError(
            "Validation failed.",
            extensions={
                "code": default_code,
                "errors": payload,
            },
        )

    return GraphQLError(str(exc))


def _resolve_user(info, global_id):
    """
    Resolve an optional Relay User global ID.
    """
    if not global_id:
        return None

    try:
        user = relay.Node.get_node_from_global_id(
            info,
            global_id,
            only_type=UserNode,
        )
    except Exception as exc:
        raise GraphQLError(
            "Invalid user ID.",
            extensions={"code": "invalid_user_id"},
        ) from exc

    if user is None:
        raise GraphQLError(
            "User not found.",
            extensions={"code": "user_not_found"},
        )

    return user


# ---------------------------------------------------------------------
# CreatePayment
# ---------------------------------------------------------------------

class CreatePayment(relay.ClientIDMutation):
    """
    Create a canonical Payment.

    All creation rules are delegated to PaymentService.
    The service is idempotent on idempotency_key.
    """

    class Input:
        direction = graphene.String(required=True)
        purpose = graphene.String(required=True)

        source_type = graphene.String(required=True)
        source_id = graphene.String(required=True)
        source_reference = graphene.String(required=False)

        payer_id = graphene.ID(required=False)
        beneficiary_id = graphene.ID(required=False)

        amount = graphene.Decimal(required=True)
        currency = graphene.String(required=True)
        idempotency_key = graphene.String(required=True)

        metadata = graphene.types.generic.GenericScalar(required=False)

    payment = graphene.Field(PaymentNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        payer = _resolve_user(info, input.get("payer_id"))
        beneficiary = _resolve_user(info, input.get("beneficiary_id"))

        try:
            payment = PaymentService.create_payment(
                direction=input["direction"],
                purpose=input["purpose"],
                source_type=input["source_type"],
                source_id=input["source_id"],
                source_reference=input.get("source_reference", ""),
                payer=payer,
                beneficiary=beneficiary,
                amount=input["amount"],
                currency=input["currency"],
                idempotency_key=input["idempotency_key"],
                metadata=input.get("metadata"),
            )
        except ValidationError as exc:
            raise _graphql_error(exc) from exc

        return cls(payment=payment)


# ---------------------------------------------------------------------
# CreatePaymentExecution
# ---------------------------------------------------------------------

class CreatePaymentExecution(relay.ClientIDMutation):
    """
    Create a canonical PaymentExecution.

    The execution is created in CREATED state. It is not executed
    until ExecutePaymentExecution is called or the orchestrator
    picks it up out-of-band.
    """

    class Input:
        payment_id = graphene.ID(required=True)
        route_type = graphene.String(required=True)
        provider = graphene.String(required=True)
        payment_instrument_id = graphene.ID(required=False)
        idempotency_key = graphene.String(required=True)
        metadata = graphene.types.generic.GenericScalar(required=False)

    payment_execution = graphene.Field(PaymentExecutionNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        payment = relay.Node.get_node_from_global_id(
            info,
            input["payment_id"],
            only_type=PaymentNode,
        )
        if payment is None:
            raise GraphQLError(
                "Payment not found.",
                extensions={"code": "payment_not_found"},
            )

        instrument = None
        instrument_gid = input.get("payment_instrument_id")

        if instrument_gid:
            instrument = relay.Node.get_node_from_global_id(
                info,
                instrument_gid,
                only_type=PaymentInstrumentNode,
            )
            if instrument is None:
                raise GraphQLError(
                    "Payment instrument not found.",
                    extensions={"code": "instrument_not_found"},
                )

        try:
            execution = PaymentExecutionService.create_execution(
                payment=payment,
                route_type=input["route_type"],
                provider=input["provider"],
                idempotency_key=input["idempotency_key"],
                instrument=instrument,
                metadata=input.get("metadata"),
            )
        except ValidationError as exc:
            raise _graphql_error(exc) from exc

        return cls(payment_execution=execution)


# ---------------------------------------------------------------------
# ExecutePaymentExecution
# ---------------------------------------------------------------------

class ExecutePaymentExecution(relay.ClientIDMutation):
    """
    Execute a PaymentExecution through its registered provider.

    Delegates to ExecutionOrchestrator. The orchestrator owns the
    lifecycle transitions, event recording, provider invocation,
    Payment synchronization, and reconciliation enqueue.

    The mutation itself only validates access.
    """

    class Input:
        payment_execution_id = graphene.ID(required=True)

    payment_execution = graphene.Field(PaymentExecutionNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        execution = relay.Node.get_node_from_global_id(
            info,
            input["payment_execution_id"],
            only_type=PaymentExecutionNode,
        )
        if execution is None:
            raise GraphQLError(
                "Payment execution not found.",
                extensions={"code": "execution_not_found"},
            )

        try:
            execution = ExecutionOrchestrator.execute(execution)
        except ValidationError as exc:
            raise _graphql_error(exc) from exc

        return cls(payment_execution=execution)


# ---------------------------------------------------------------------
# ReconcilePaymentExecution
# ---------------------------------------------------------------------

class ReconcilePaymentExecution(relay.ClientIDMutation):
    """
    Trigger reconciliation for a PaymentExecution.

    Delegates to ReconciliationCoordinator. The coordinator decides
    eligibility and, when eligible, invokes ReconciliationEntryPoint.

    The coordinator returns a ReconciliationCoordinationResult which
    is not GraphQL-serializable, so this mutation returns the
    (possibly updated) execution instead.
    """

    class Input:
        payment_execution_id = graphene.ID(required=True)

    payment_execution = graphene.Field(PaymentExecutionNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        execution = relay.Node.get_node_from_global_id(
            info,
            input["payment_execution_id"],
            only_type=PaymentExecutionNode,
        )
        if execution is None:
            raise GraphQLError(
                "Payment execution not found.",
                extensions={"code": "execution_not_found"},
            )

        try:
            ReconciliationCoordinator.reconcile(execution=execution)
        except ValidationError as exc:
            raise _graphql_error(exc) from exc

        # The coordinator returns a frozen dataclass and may have
        # transitioned the execution. Refetch so we return fresh state.
        execution.refresh_from_db()

        return cls(payment_execution=execution)


# ---------------------------------------------------------------------
# Mutation root
# ---------------------------------------------------------------------

class PaymentMutations(graphene.ObjectType):
    """
    Canonical Payment mutations.
    """

    create_payment = CreatePayment.Field()
    create_payment_execution = CreatePaymentExecution.Field()
    execute_payment_execution = ExecutePaymentExecution.Field()
    reconcile_payment_execution = ReconcilePaymentExecution.Field()


__all__ = [
    "CreatePayment",
    "CreatePaymentExecution",
    "ExecutePaymentExecution",
    "ReconcilePaymentExecution",
    "PaymentMutations",
]