"""
GraphQL Department type.

Staff GraphQL boundary
----------------------

This module exposes the canonical staff.Department model through
Graphene Relay.

Responsibilities:
    - GraphQL representation of Department
    - Relay Node implementation
    - Department relationships

Non-responsibilities:
    - department creation/update
    - authorization
    - filtering
    - business rules
    - staff lifecycle operations
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from staff.models.department import Department


class DepartmentNode(DjangoObjectType):
    """
    Relay GraphQL node for the Staff Department model.
    """

    class Meta:
        model = Department

        interfaces = (Node,)

        fields = (
            "id",
            "name",
            "code",
            "description",
            "parent",
            "is_active",
            "created_at",
            "updated_at",
        )

    parent = graphene.Field(
        lambda: DepartmentNode,
        description="Parent department, when applicable.",
    )


__all__ = [
    "DepartmentNode",
]