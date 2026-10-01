"""
GraphQL filters for StaffMember objects.

This module is responsible only for filtering StaffMember querysets.

Identity fields remain owned by Accounts.User and are exposed here
only through StaffMember.user relationship filters.
"""

import django_filters

from staff.models.department import Department
from staff.models.position import Position
from staff.models.staff_member import StaffMember


class StaffMemberFilter(django_filters.FilterSet):
    """
    Filters for StaffMember objects.
    """

    employee_number = django_filters.CharFilter(
        field_name="employee_number",
        lookup_expr="icontains",
    )

    department = django_filters.ModelChoiceFilter(
        field_name="department",
        queryset=Department.objects.all(),
    )

    position = django_filters.ModelChoiceFilter(
        field_name="position",
        queryset=Position.objects.all(),
    )

    manager = django_filters.ModelChoiceFilter(
        field_name="manager",
        queryset=StaffMember.objects.all(),
    )

    employment_status = django_filters.ChoiceFilter(
        field_name="employment_status",
        choices=StaffMember.EmploymentStatus.choices,
    )

    date_joined = django_filters.DateFilter(
        field_name="date_joined",
    )

    date_joined_after = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="gte",
    )

    date_joined_before = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="lte",
    )

    date_left = django_filters.DateFilter(
        field_name="date_left",
    )

    date_left_after = django_filters.DateFilter(
        field_name="date_left",
        lookup_expr="gte",
    )

    date_left_before = django_filters.DateFilter(
        field_name="date_left",
        lookup_expr="lte",
    )

    user_email = django_filters.CharFilter(
        field_name="user__email",
        lookup_expr="icontains",
    )

    user_phone_number = django_filters.CharFilter(
        field_name="user__phone_number",
        lookup_expr="icontains",
    )

    user_first_name = django_filters.CharFilter(
        field_name="user__first_name",
        lookup_expr="icontains",
    )

    user_last_name = django_filters.CharFilter(
        field_name="user__last_name",
        lookup_expr="icontains",
    )

    class Meta:
        model = StaffMember
        fields = [
            "employee_number",
            "department",
            "position",
            "manager",
            "employment_status",
            "date_joined",
            "date_joined_after",
            "date_joined_before",
            "date_left",
            "date_left_after",
            "date_left_before",
            "user_email",
            "user_phone_number",
            "user_first_name",
            "user_last_name",
        ]


__all__ = ["StaffMemberFilter"]