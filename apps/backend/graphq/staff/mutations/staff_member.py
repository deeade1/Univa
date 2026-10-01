"""
GraphQL StaffMember mutations.

GraphQL boundary
----------------

These mutations are adapters around the canonical Staff domain
services.

Business rules remain in:

    staff.services.staff_service

This module is responsible for:

    - authentication and authorization
    - Relay ID resolution
    - GraphQL input/output
    - invoking Staff domain services

Staff employment does not automatically modify Accounts roles.
"""

from __future__ import annotations

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from graphene import relay
from graphql_relay import from_global_id

from graphq.accounts.mutations.role import RoleMutationMixin
from graphq.accounts.types.user import UserNode
from graphq.staff.types.department import DepartmentNode
from graphq.staff.types.position import PositionNode
from graphq.staff.types.staff_member import StaffMemberNode

from staff.models.department import Department
from staff.models.position import Position
from staff.models.staff_member import StaffMember
from staff.services.staff_service import (
    change_employment_status,
    create_staff_member,
)


User = get_user_model()


def _resolve_relay_id(global_id, *, expected_type, field_name):
    """
    Decode a Relay global ID and validate its GraphQL node type.

    Returns the underlying primary-key value as a string.

    GraphQL remains responsible for the Relay representation while
    Django ORM remains responsible for loading the domain object.
    """
    try:
        node_type, object_id = from_global_id(global_id)
    except Exception as exc:
        raise ValidationError(
            {
                field_name: (
                    f"Invalid Relay ID for {expected_type}."
                )
            }
        ) from exc

    if not node_type or not object_id:
        raise ValidationError(
            {
                field_name: (
                    f"Invalid Relay ID for {expected_type}."
                )
            }
        )

    if node_type != expected_type:
        raise ValidationError(
            {
                field_name: (
                    f"Expected a {expected_type} Relay ID."
                )
            }
        )

    return object_id


class CreateStaffMember(relay.ClientIDMutation):
    """
    Create a StaffMember employment record for an existing
    Accounts user.

    Creating employment does not assign or modify Accounts roles.
    """

    class Input:
        user_id = graphene.ID(
            required=True,
            description="Global Relay ID of the Accounts user.",
        )
        employee_number = graphene.String(
            required=True,
            description="Unique staff employee number.",
        )
        department_id = graphene.ID(
            required=True,
            description="Global Relay ID of the staff department.",
        )
        position_id = graphene.ID(
            required=True,
            description="Global Relay ID of the staff position.",
        )
        manager_id = graphene.ID(
            required=False,
            description="Global Relay ID of the manager StaffMember.",
        )
        date_joined = graphene.Date(
            required=True,
            description="Date the staff member joined the organization.",
        )
        employment_status = graphene.String(
            required=False,
            default_value=StaffMember.EmploymentStatus.PENDING,
            description="Initial employment status.",
        )

    staff_member = graphene.Field(
        StaffMemberNode,
        description="The newly created staff member.",
    )

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        RoleMutationMixin.require_authenticated_user(info)
        RoleMutationMixin.require_admin(info)

        user_pk = _resolve_relay_id(
            input["user_id"],
            expected_type=UserNode._meta.name,
            field_name="user_id",
        )

        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist as exc:
            raise ValidationError(
                {
                    "user_id": (
                        "Accounts user not found."
                    )
                }
            ) from exc

        department_pk = _resolve_relay_id(
            input["department_id"],
            expected_type=DepartmentNode._meta.name,
            field_name="department_id",
        )

        try:
            department = Department.objects.get(
                pk=department_pk,
            )
        except Department.DoesNotExist as exc:
            raise ValidationError(
                {
                    "department_id": (
                        "Department not found."
                    )
                }
            ) from exc

        position_pk = _resolve_relay_id(
            input["position_id"],
            expected_type=PositionNode._meta.name,
            field_name="position_id",
        )

        try:
            position = Position.objects.get(
                pk=position_pk,
            )
        except Position.DoesNotExist as exc:
            raise ValidationError(
                {
                    "position_id": (
                        "Position not found."
                    )
                }
            ) from exc

        manager = None

        manager_id = input.get("manager_id")

        if manager_id is not None:
            manager_pk = _resolve_relay_id(
                manager_id,
                expected_type=StaffMemberNode._meta.name,
                field_name="manager_id",
            )

            try:
                manager = StaffMember.objects.get(
                    pk=manager_pk,
                )
            except StaffMember.DoesNotExist as exc:
                raise ValidationError(
                    {
                        "manager_id": (
                            "Manager StaffMember not found."
                        )
                    }
                ) from exc

        staff_member = create_staff_member(
            user=user,
            employee_number=input["employee_number"],
            department=department,
            position=position,
            date_joined=input["date_joined"],
            manager=manager,
            employment_status=input.get(
                "employment_status",
                StaffMember.EmploymentStatus.PENDING,
            ),
        )

        return cls(
            staff_member=staff_member,
        )


class ChangeStaffEmploymentStatus(relay.ClientIDMutation):
    """
    Change the employment status of an existing StaffMember.

    Employment transition rules are owned by the Staff domain service.
    """

    class Input:
        staff_member_id = graphene.ID(
            required=True,
            description="Global Relay ID of the StaffMember.",
        )
        employment_status = graphene.String(
            required=True,
            description="New employment status.",
        )
        date_left = graphene.Date(
            required=False,
            description=(
                "Employment end date. Required for RESIGNED "
                "and TERMINATED statuses."
            ),
        )

    staff_member = graphene.Field(
        StaffMemberNode,
        description="The updated staff member.",
    )

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        RoleMutationMixin.require_authenticated_user(info)
        RoleMutationMixin.require_admin(info)

        staff_member_pk = _resolve_relay_id(
            input["staff_member_id"],
            expected_type=StaffMemberNode._meta.name,
            field_name="staff_member_id",
        )

        try:
            staff_member = StaffMember.objects.get(
                pk=staff_member_pk,
            )
        except StaffMember.DoesNotExist as exc:
            raise ValidationError(
                {
                    "staff_member_id": (
                        "StaffMember not found."
                    )
                }
            ) from exc

        staff_member = change_employment_status(
            staff_member=staff_member,
            new_status=input["employment_status"],
            date_left=input.get("date_left"),
        )

        return cls(
            staff_member=staff_member,
        )


__all__ = [
    "CreateStaffMember",
    "ChangeStaffEmploymentStatus",
]
