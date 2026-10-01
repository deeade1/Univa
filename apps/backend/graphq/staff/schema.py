"""
Staff GraphQL schema composition.

The Staff schema is a composition layer only.

Query behavior belongs to the individual Staff query modules.
Mutation behavior belongs to the individual Staff mutation modules.
Filtering belongs to the Staff filter modules.
Business logic belongs to the Staff domain services and selectors.
"""

import graphene

from graphq.staff.mutations.staff_member import (
    ChangeStaffEmploymentStatus,
    CreateStaffMember,
)
from graphq.staff.queries.department import DepartmentQuery
from graphq.staff.queries.position import PositionQuery
from graphq.staff.queries.staff_member import StaffMemberQuery


class StaffQuery(
    DepartmentQuery,
    PositionQuery,
    StaffMemberQuery,
    graphene.ObjectType,
):
    """
    Root GraphQL query composition for the Staff domain.
    """

    pass


class StaffMutation(graphene.ObjectType):
    """
    Root GraphQL mutation composition for the Staff domain.
    """

    create_staff_member = CreateStaffMember.Field()
    change_staff_employment_status = ChangeStaffEmploymentStatus.Field()


__all__ = [
    "StaffQuery",
    "StaffMutation",
]