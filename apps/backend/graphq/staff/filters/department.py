"""
GraphQL filters for Staff Department objects.

This module is responsible only for filtering Department querysets.
Department business rules and mutations belong to the staff domain.
"""

import django_filters
from django.db.models import Q

from staff.models.department import Department


class DepartmentFilter(django_filters.FilterSet):
    """
    Filters for Staff Department objects.
    """

    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )

    code = django_filters.CharFilter(
        field_name="code",
        lookup_expr="iexact",
    )

    is_active = django_filters.BooleanFilter(
        field_name="is_active",
    )

    parent = django_filters.ModelChoiceFilter(
        field_name="parent",
        queryset=Department.objects.all(),
    )

    search = django_filters.CharFilter(
        method="filter_search",
        label="Search by department name or code.",
    )

    class Meta:
        model = Department
        fields = [
            "name",
            "code",
            "is_active",
            "parent",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(code__icontains=value)
        )


__all__ = ["DepartmentFilter"]