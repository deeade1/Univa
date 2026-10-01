"""
GraphQL Position queries.

GraphQL is responsible for the API boundary.
Position queryset retrieval is delegated to Staff selectors.
"""

from __future__ import annotations

import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay import from_global_id

from graphq.staff.filters.position import PositionFilter
from graphq.staff.types.position import PositionNode
from staff.models.position import Position
from staff.selectors.positions import (
    get_position,
    list_active_positions,
    list_positions,
)


class PositionQuery(graphene.ObjectType):
    """
    Position query fields.
    """

    position = graphene.Field(
        PositionNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the position.",
        ),
    )

    positions = DjangoFilterConnectionField(
        PositionNode,
        filterset_class=PositionFilter,
        description="Relay connection of staff positions.",
    )

    active_positions = DjangoFilterConnectionField(
        PositionNode,
        filterset_class=PositionFilter,
        description="Relay connection of active staff positions.",
    )

    @staticmethod
    def resolve_position(root, info, id):
        node_type, position_id = from_global_id(id)

        if node_type != PositionNode._meta.name:
            return None

        try:
            position = Position.objects.get(pk=position_id)
        except (Position.DoesNotExist, ValueError, TypeError):
            return None

        return get_position(
            position_id=position.pk,
        )

    @staticmethod
    def resolve_positions(root, info, **kwargs):
        return list_positions()

    @staticmethod
    def resolve_active_positions(root, info, **kwargs):
        return list_active_positions()


__all__ = [
    "PositionQuery",
]