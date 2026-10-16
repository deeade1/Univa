# graphq/ecommerce/schema/order.py

"""
Order GraphQL queries.
"""

from __future__ import annotations

import graphene
from django.db.models import Q
from graphene import Node

from ecommerce.models.order import Order
from graphq.core.fields import AccessControlledFilterConnectionField
from graphq.ecommerce.types.order import FulfillmentNode, OrderNode
from univa_jwt.decorators import staff_member_required


def _user_visible_orders(info):
    """
    Base queryset for the order connection field.

    Staff see all orders. Regular users see only their own.
    Unauthenticated requests see nothing.
    """
    user = getattr(info.context, "user", None)

    if user is None or not user.is_authenticated:
        return Order.objects.none()

    if getattr(user, "is_staff", False):
        return Order.objects.all()

    return Order.objects.filter(
        Q(user=user) | Q(user_email=user.email)
    )


class OrderQuery(graphene.ObjectType):
    """Order queries for the ecommerce schema."""

    order = Node.Field(OrderNode)

    all_orders = AccessControlledFilterConnectionField(
        OrderNode,
        get_base_queryset=_user_visible_orders,
    )

    fulfillment = Node.Field(FulfillmentNode)

    order_by_token = graphene.Field(
        OrderNode,
        token=graphene.String(required=True),
        description=(
            "Fetch an order by the checkout token it was created from. "
            "Used for guest access — possession of the token is the "
            "authorization."
        ),
    )

    order_by_number = graphene.Field(
        OrderNode,
        number=graphene.Int(required=True),
        description=(
            "Fetch an order by its human-readable number. Staff only."
        ),
    )

    @staticmethod
    def resolve_order_by_token(root, info, token):
        return Order.objects.get_by_checkout_token(token)

    @staticmethod
    @staff_member_required
    def resolve_order_by_number(root, info, number):
        return Order.objects.filter(number=number).first()


__all__ = ["OrderQuery"]