"""
Staff member domain services.

This module owns operations involving StaffMember.

Staff employment is separate from Accounts authorization.
Creating or changing employment status does not automatically
modify Accounts roles.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from staff.events import (
    emit_staff_member_created,
    emit_staff_member_employment_status_changed,
)
from staff.models import StaffMember


EMPLOYMENT_STATUS_TRANSITIONS = {
    StaffMember.EmploymentStatus.PENDING: {
        StaffMember.EmploymentStatus.ACTIVE,
    },
    StaffMember.EmploymentStatus.ACTIVE: {
        StaffMember.EmploymentStatus.ON_LEAVE,
        StaffMember.EmploymentStatus.SUSPENDED,
        StaffMember.EmploymentStatus.RESIGNED,
        StaffMember.EmploymentStatus.TERMINATED,
    },
    StaffMember.EmploymentStatus.ON_LEAVE: {
        StaffMember.EmploymentStatus.ACTIVE,
        StaffMember.EmploymentStatus.SUSPENDED,
        StaffMember.EmploymentStatus.RESIGNED,
        StaffMember.EmploymentStatus.TERMINATED,
    },
    StaffMember.EmploymentStatus.SUSPENDED: {
        StaffMember.EmploymentStatus.ACTIVE,
        StaffMember.EmploymentStatus.RESIGNED,
        StaffMember.EmploymentStatus.TERMINATED,
    },
    StaffMember.EmploymentStatus.RESIGNED: set(),
    StaffMember.EmploymentStatus.TERMINATED: set(),
}


@transaction.atomic
def create_staff_member(
    *,
    user,
    employee_number,
    department,
    position,
    date_joined,
    manager=None,
    employment_status=StaffMember.EmploymentStatus.PENDING,
):
    """
    Create a StaffMember for an existing accounts.User.

    New staff members cannot be created directly in a terminal
    employment state. Terminal states must be reached through
    change_employment_status(), which requires date_left.

    Authorization is intentionally not modified here.
    """

    terminal_statuses = {
        StaffMember.EmploymentStatus.RESIGNED,
        StaffMember.EmploymentStatus.TERMINATED,
    }

    if employment_status in terminal_statuses:
        raise ValidationError(
            {
                "employment_status": (
                    "Staff members cannot be created directly in a "
                    "terminal employment status."
                )
            }
        )

    staff_member = StaffMember.objects.create(
        user=user,
        employee_number=employee_number,
        department=department,
        position=position,
        manager=manager,
        employment_status=employment_status,
        date_joined=date_joined,
    )

    emit_staff_member_created(
        staff_member=staff_member,
    )

    return staff_member


@transaction.atomic
def change_employment_status(
    *,
    staff_member,
    new_status,
    date_left=None,
):
    """
    Change a StaffMember's employment status.

    Terminal employment statuses require an explicit date_left.
    Non-terminal statuses must not have a date_left.
    """

    staff_member = (
        StaffMember.objects
        .select_for_update()
        .get(pk=staff_member.pk)
    )

    previous_status = staff_member.employment_status

    if new_status not in dict(StaffMember.EmploymentStatus.choices):
        raise ValidationError(
            {"employment_status": "Invalid employment status."}
        )

    if new_status not in EMPLOYMENT_STATUS_TRANSITIONS[previous_status]:
        raise ValidationError(
            {
                "employment_status": (
                    f"Cannot change employment status from "
                    f"{previous_status} to {new_status}."
                )
            }
        )

    terminal_statuses = {
        StaffMember.EmploymentStatus.RESIGNED,
        StaffMember.EmploymentStatus.TERMINATED,
    }

    if new_status in terminal_statuses:
        if date_left is None:
            raise ValidationError(
                {
                    "date_left": (
                        "date_left is required when employment status "
                        "is RESIGNED or TERMINATED."
                    )
                }
            )

        if date_left < staff_member.date_joined:
            raise ValidationError(
                {
                    "date_left": (
                        "Date left cannot be before date joined."
                    )
                }
            )

    elif date_left is not None:
        raise ValidationError(
            {
                "date_left": (
                    "date_left must be empty for non-terminal "
                    "employment statuses."
                )
            }
        )

    staff_member.employment_status = new_status
    staff_member.date_left = date_left

    staff_member.save(
        update_fields=[
            "employment_status",
            "date_left",
            "updated_at",
        ]
    )

    emit_staff_member_employment_status_changed(
        staff_member=staff_member,
        previous_status=previous_status,
    )

    return staff_member