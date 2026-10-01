"""
GraphQL Department queries.

GraphQL is responsible for the API boundary.
Department queryset retrieval is delegated to Staff selectors.
"""

from __future__ import annotations

import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay import from_global_id

from graphq.staff.filters.department import DepartmentFilter
from graphq.staff.types.department import DepartmentNode
from staff.models.department import Department
from staff.selectors.departments import (
    get_department,
    list_active_departments,
    list_departments,
)


class DepartmentQuery(graphene.ObjectType):
    """
    Department query fields.
    """

    department = graphene.Field(
        DepartmentNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the department.",
        ),
    )

    departments = DjangoFilterConnectionField(
        DepartmentNode,
        filterset_class=DepartmentFilter,
        description="Relay connection of staff departments.",
    )

    active_departments = DjangoFilterConnectionField(
        DepartmentNode,
        filterset_class=DepartmentFilter,
        description="Relay connection of active staff departments.",
    )

    @staticmethod
    def resolve_department(root, info, id):
        node_type, department_id = from_global_id(id)

        if node_type != DepartmentNode._meta.name:
            return None

        try:
            department = Department.objects.get(pk=department_id)
        except (Department.DoesNotExist, ValueError, TypeError):
            return None

        return get_department(
            department_id=department.pk,
        )

    @staticmethod
    def resolve_departments(root, info, **kwargs):
        return list_departments()

    @staticmethod
    def resolve_active_departments(root, info, **kwargs):
        return list_active_departments()


__all__ = [
    "DepartmentQuery",
]