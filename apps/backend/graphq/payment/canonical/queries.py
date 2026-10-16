"""
Canonical Payment GraphQL queries.

Queries are responsible only for GraphQL resolution and
access boundaries.

They do not implement payment business rules.
"""

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .types import (
    PaymentExecutionEventNode,
    PaymentExecutionNode,
    PaymentInstrumentNode,
    PaymentNode,
)


class PaymentQueries(graphene.ObjectType):
    """
    Top-level Query fields for the canonical Payment surface.
    """

    # --- Single-node lookups (Relay global ID) ------------------------
    payment = relay.Node.Field(PaymentNode)
    payment_execution = relay.Node.Field(PaymentExecutionNode)
    payment_execution_event = relay.Node.Field(PaymentExecutionEventNode)
    payment_instrument = relay.Node.Field(PaymentInstrumentNode)

    # --- Filterable connections ---------------------------------------
    all_payments = DjangoFilterConnectionField(PaymentNode)
    all_payment_executions = DjangoFilterConnectionField(
        PaymentExecutionNode
    )
    all_payment_execution_events = DjangoFilterConnectionField(
        PaymentExecutionEventNode
    )
    all_payment_instruments = DjangoFilterConnectionField(
        PaymentInstrumentNode
    )


__all__ = ["PaymentQueries"]