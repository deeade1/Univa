# apps/backend/staff/admin.py

"""
Django Admin configuration for the Staff domain.

The admin layer is intentionally thin.

Business rules remain in:
    - staff.models
    - staff.services.staff_service

Admin is responsible only for:
    - model registration
    - list presentation
    - filtering
    - searching
    - ordering
    - relationship navigation
"""

from django.contrib import admin

from staff.models.department import Department
from staff.models.position import Position
from staff.models.staff_member import StaffMember


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "parent",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "is_active",
    )
    search_fields = (
        "name",
        "code",
        "description",
    )
    ordering = (
        "name",
    )
    list_select_related = (
        "parent",
    )


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "department",
        "is_management",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "is_management",
        "is_active",
        "department",
    )
    search_fields = (
        "title",
        "code",
        "description",
    )
    ordering = (
        "department__name",
        "title",
    )
    list_select_related = (
        "department",
    )


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number",
        "user",
        "department",
        "position",
        "manager",
        "employment_status",
        "date_joined",
        "date_left",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "employment_status",
        "department",
        "position",
    )
    search_fields = (
        "employee_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone_number",
    )
    ordering = (
        "employee_number",
    )
    list_select_related = (
        "user",
        "department",
        "position",
        "manager",
    )


__all__ = [
    "DepartmentAdmin",
    "PositionAdmin",
    "StaffMemberAdmin",
]