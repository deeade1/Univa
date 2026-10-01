"""
GraphQL StaffMember queries.

GraphQL is responsible for the API boundary.
StaffMember queryset retrieval is delegated to Staff selectors.

Identity remains owned by Accounts.
Employment information remains owned by Staff.
"""

from __future__ import annotations

import graphene
from django.contrib.auth import get_user_model
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay import from_global_id

from graphq.accounts.types.user import UserNode
from graphq.staff.filters.staff_member import StaffMemberFilter
from graphq.staff.types.staff_member import StaffMemberNode
from staff.models.staff_member import StaffMember
from staff.selectors.staff_members import (
    get_staff_member,
    get_staff_member_by_employee_number,
    get_staff_member_by_user,
    list_active_staff_members,
    list_staff_members,
)


User = get_user_model()


class StaffMemberQuery(graphene.ObjectType):
    """
    StaffMember query fields.
    """

    staff_member = graphene.Field(
        StaffMemberNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the staff member.",
        ),
    )

    staff_member_by_employee_number = graphene.Field(
        StaffMemberNode,
        employee_number=graphene.String(
            required=True,
            description="Unique staff employee number.",
        ),
    )

    staff_member_by_user = graphene.Field(
        StaffMemberNode,
        user_id=graphene.ID(
            required=True,
            description="Global Relay ID of the associated Accounts user.",
        ),
    )

    staff_members = DjangoFilterConnectionField(
        StaffMemberNode,
        filterset_class=StaffMemberFilter,
        description="Relay connection of staff members.",
    )

    active_staff_members = DjangoFilterConnectionField(
        StaffMemberNode,
        filterset_class=StaffMemberFilter,
        description="Relay connection of active staff members.",
    )

    @staticmethod
    def resolve_staff_member(root, info, id):
        node_type, staff_member_id = from_global_id(id)

        if node_type != StaffMemberNode._meta.name:
            return None

        try:
            staff_member = StaffMember.objects.get(
                pk=staff_member_id,
            )
        except (
            StaffMember.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return None

        return get_staff_member(
            staff_member_id=staff_member.pk,
        )

    @staticmethod
    def resolve_staff_member_by_employee_number(
        root,
        info,
        employee_number,
    ):
        return get_staff_member_by_employee_number(
            employee_number=employee_number,
        )

    @staticmethod
    def resolve_staff_member_by_user(
        root,
        info,
        user_id,
    ):
        node_type, user_pk = from_global_id(user_id)

        if node_type != UserNode._meta.name:
            return None

        try:
            user = User.objects.get(pk=user_pk)
        except (
            User.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return None

        return get_staff_member_by_user(
            user=user,
        )

    @staticmethod
    def resolve_staff_members(root, info, **kwargs):
        return list_staff_members()

    @staticmethod
    def resolve_active_staff_members(root, info, **kwargs):
        return list_active_staff_members()


__all__ = [
    "StaffMemberQuery",
]