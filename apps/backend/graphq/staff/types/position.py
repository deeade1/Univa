"""
GraphQL Position type.

Staff GraphQL boundary
----------------------

This module exposes the canonical staff.Position model through
Graphene Relay.

Responsibilities:
    - GraphQL representation of Position
    - Relay Node implementation
    - Position relationships

Non-responsibilities:
    - position creation/update
    - authorization
    - filtering
    - business rules
    - staff lifecycle operations
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from staff.models.position import Position

from graphq.staff.types.department import DepartmentNode


class PositionNode(DjangoObjectType):
    """
    Relay GraphQL node for the Staff Position model.
    """

    department = graphene.Field(
        DepartmentNode,
        description="Department to which this position belongs.",
    )

    class Meta:
        model = Position

        interfaces = (Node,)

        fields = (
            "id",
            "title",
            "code",
            "department",
            "description",
            "is_management",
            "is_active",
            "created_at",
            "updated_at",
        )


__all__ = [
    "PositionNode",
]