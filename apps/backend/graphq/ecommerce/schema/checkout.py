# graphq/ecommerce/schema/checkout.py

"""
Checkout GraphQL queries.
"""

import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField

from ecommerce.services.checkout import get_checkout_by_token
from graphq.ecommerce.types.checkout import (
    CheckoutLineNode,
    CheckoutNode,
)


class CheckoutQuery(graphene.ObjectType):
    """Checkout queries for the ecommerce schema."""

    checkout = Node.Field(CheckoutNode)
    all_checkouts = DjangoFilterConnectionField(CheckoutNode)

    checkout_line = Node.Field(CheckoutLineNode)
    all_checkout_lines = DjangoFilterConnectionField(CheckoutLineNode)

    checkout_by_token = graphene.Field(
        CheckoutNode,
        token=graphene.UUID(required=True),
        description=(
            "Fetch a checkout by token. Used for guest access — "
            "possession of the token is the authorization."
        ),
    )

    @staticmethod
    def resolve_checkout_by_token(root, info, token):
        return get_checkout_by_token(str(token))


__all__ = ["CheckoutQuery"]