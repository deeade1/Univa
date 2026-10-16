"""
Canonical GraphQL types for the Payment domain.

Architectural boundary
----------------------

These types expose canonical payment models.

They MUST NOT:

    - implement payment business rules
    - create payments
    - execute providers
    - perform reconciliation
    - access Banking services
"""

from django.db.models import Q
from graphene import relay
from graphene_django import DjangoObjectType

from graphq.core.types.scalars import JSONScalar
from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
    PaymentInstrument,
)

from .filters import (
    PaymentExecutionEventFilter,
    PaymentExecutionFilter,
    PaymentFilter,
    PaymentInstrumentFilter,
)


# ---------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------

class PaymentNode(DjangoObjectType):
    """
    Relay GraphQL representation of the canonical Payment.
    """

    metadata = JSONScalar()

    class Meta:
        model = Payment
        interfaces = (relay.Node,)

        fields = (
            "id",
            "reference",
            "direction",
            "purpose",
            "source_type",
            "source_id",
            "source_reference",
            "payer",
            "beneficiary",
            "amount",
            "currency",
            "status",
            "idempotency_key",
            "processing_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "reversed_at",
            # "metadata" declared explicitly above
            "created_at",
            "updated_at",
        )
        filterset_class = PaymentFilter

    @classmethod
    def get_queryset(cls, queryset, info):
        user = getattr(info.context, "user", None)

        if user is None or not user.is_authenticated:
            return queryset.none()

        return queryset.filter(
            Q(payer=user) | Q(beneficiary=user)
        )


# ---------------------------------------------------------------------
# PaymentExecution
# ---------------------------------------------------------------------

class PaymentExecutionNode(DjangoObjectType):
    """
    Relay GraphQL representation of a canonical PaymentExecution.

    Access is inherited from the owning Payment: a user may only
    access an execution when they are the payer or beneficiary of
    that Payment.
    """

    metadata = JSONScalar()

    class Meta:
        model = PaymentExecution
        interfaces = (relay.Node,)

        fields = (
            "id",
            "reference",
            "payment",
            "attempt_number",
            "idempotency_key",
            "route_type",
            "provider",
            "provider_reference",
            "instrument",
            "status",
            "reconciliation_state",
            "failure_code",
            "failure_reason",
            "banking_transaction_reference",
            "processing_at",
            "pending_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "reconciled_at",
            # "metadata" declared explicitly above
            "created_at",
            "updated_at",
        )
        filterset_class = PaymentExecutionFilter

    @classmethod
    def get_queryset(cls, queryset, info):
        user = getattr(info.context, "user", None)

        if user is None or not user.is_authenticated:
            return queryset.none()

        return queryset.filter(
            Q(payment__payer=user) | Q(payment__beneficiary=user)
        )


# ---------------------------------------------------------------------
# PaymentExecutionEvent
# ---------------------------------------------------------------------

class PaymentExecutionEventNode(DjangoObjectType):
    """
    Relay GraphQL representation of a PaymentExecutionEvent.

    Events are append-only history. This node is read-only.
    Access is inherited from the owning Payment via the execution.
    """

    payload = JSONScalar()

    class Meta:
        model = PaymentExecutionEvent
        interfaces = (relay.Node,)

        fields = (
            "id",
            "execution",
            "event_type",
            "source",
            "provider_event_id",
            "provider_reference",
            # "payload" declared explicitly above
            "occurred_at",
            "received_at",
            "created_at",
        )
        filterset_class = PaymentExecutionEventFilter

    @classmethod
    def get_queryset(cls, queryset, info):
        user = getattr(info.context, "user", None)

        if user is None or not user.is_authenticated:
            return queryset.none()

        return queryset.filter(
            Q(execution__payment__payer=user)
            | Q(execution__payment__beneficiary=user)
        )


# ---------------------------------------------------------------------
# PaymentInstrument
# ---------------------------------------------------------------------

class PaymentInstrumentNode(DjangoObjectType):
    """
    Relay GraphQL representation of a canonical PaymentInstrument.

    Instruments are owned by a user. Access is restricted to the owner.
    """

    metadata = JSONScalar()

    class Meta:
        model = PaymentInstrument
        interfaces = (relay.Node,)

        fields = (
            "id",
            "reference",
            "owner",
            "instrument_type",
            "institution",
            "can_fund",
            "can_receive",
            "display_reference",
            "verification_status",
            "verification_reference",
            "verified_at",
            "status",
            "activated_at",
            "deactivated_at",
            "blocked_at",
            "expired_at",
            # "metadata" declared explicitly above
            "created_at",
            "updated_at",
        )
        filterset_class = PaymentInstrumentFilter

    @classmethod
    def get_queryset(cls, queryset, info):
        user = getattr(info.context, "user", None)

        if user is None or not user.is_authenticated:
            return queryset.none()

        return queryset.filter(owner=user)