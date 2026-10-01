"""
GraphQL StaffMember type.

Staff GraphQL boundary
----------------------

This module exposes the canonical staff.StaffMember model through
Graphene Relay.

StaffMember owns employment information.

The centralized Accounts User model remains the owner of identity,
authentication, authorization, and account information.

Therefore StaffMemberNode references UserNode instead of duplicating
User fields.
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from staff.models.staff_member import StaffMember

from graphq.accounts.types.user import UserNode
from graphq.staff.types.department import DepartmentNode
from graphq.staff.types.position import PositionNode


class StaffMemberNode(DjangoObjectType):
    """
    Relay GraphQL node for the StaffMember model.

    Employment information belongs to Staff.

    Identity and account information belongs to Accounts/UserNode.
    """

    user = graphene.Field(
        UserNode,
        description="Accounts user associated with this staff member.",
    )

    department = graphene.Field(
        DepartmentNode,
        description="Department in which the staff member works.",
    )

    position = graphene.Field(
        PositionNode,
        description="Position held by the staff member.",
    )

    manager = graphene.Field(
        lambda: StaffMemberNode,
        description="Staff member's manager, when applicable.",
    )

    class Meta:
        model = StaffMember

        interfaces = (Node,)

        fields = (
            "id",
            "user",
            "employee_number",
            "department",
            "position",
            "manager",
            "employment_status",
            "date_joined",
            "date_left",
            "created_at",
            "updated_at",
        )


__all__ = [
    "StaffMemberNode",
]