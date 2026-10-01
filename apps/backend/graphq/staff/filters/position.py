"""
GraphQL filters for Staff Position objects.

This module is responsible only for filtering Position querysets.
Position business rules and mutations belong to the staff domain.
"""

import django_filters
from django.db.models import Q

from staff.models.department import Department
from staff.models.position import Position


class PositionFilter(django_filters.FilterSet):
    """
    Filters for Staff Position objects.
    """

    title = django_filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
    )

    code = django_filters.CharFilter(
        field_name="code",
        lookup_expr="iexact",
    )

    department = django_filters.ModelChoiceFilter(
        field_name="department",
        queryset=Department.objects.all(),
    )

    is_management = django_filters.BooleanFilter(
        field_name="is_management",
    )

    is_active = django_filters.BooleanFilter(
        field_name="is_active",
    )

    search = django_filters.CharFilter(
        method="filter_search",
        label="Search by position title or code.",
    )

    class Meta:
        model = Position
        fields = [
            "title",
            "code",
            "department",
            "is_management",
            "is_active",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(code__icontains=value)
        )


__all__ = [
    "PositionFilter",
]