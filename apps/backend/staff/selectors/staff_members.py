from accounts.models import User
from staff.models import Department, StaffMember


def get_staff_member(*, staff_member_id):
    return StaffMember.objects.get(pk=staff_member_id)


def get_staff_member_by_user(*, user):
    if not isinstance(user, User):
        raise TypeError("user must be an accounts.User instance.")

    return StaffMember.objects.get(user=user)


def get_staff_member_by_employee_number(*, employee_number):
    return StaffMember.objects.get(employee_number=employee_number)


def list_staff_members():
    return StaffMember.objects.all()


def list_active_staff_members():
    return StaffMember.objects.filter(
        employment_status=StaffMember.EmploymentStatus.ACTIVE
    )


def list_staff_members_by_department(*, department):
    if not isinstance(department, Department):
        raise TypeError("department must be a Department instance.")

    return StaffMember.objects.filter(department=department)


def list_staff_members_by_manager(*, manager):
    if not isinstance(manager, StaffMember):
        raise TypeError("manager must be a StaffMember instance.")

    return StaffMember.objects.filter(manager=manager)