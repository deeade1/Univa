from datetime import date

from django.test import TestCase

from accounts.models import User
from staff.models import Department, Position, StaffMember
from staff.selectors import (
    get_department,
    get_position,
    get_staff_member,
    get_staff_member_by_employee_number,
    get_staff_member_by_user,
    list_active_departments,
    list_active_positions,
    list_active_staff_members,
    list_departments,
    list_positions,
    list_positions_by_department,
    list_staff_members,
    list_staff_members_by_department,
    list_staff_members_by_manager,
)


class DepartmentSelectorTests(TestCase):
    def setUp(self):
        self.active_department = Department.objects.create(
            name="Operations",
            code="OPS",
            is_active=True,
        )
        self.inactive_department = Department.objects.create(
            name="Legal",
            code="LEGAL",
            is_active=False,
        )

    def test_get_department_returns_department(self):
        result = get_department(
            department_id=self.active_department.pk,
        )

        self.assertEqual(result, self.active_department)

    def test_get_department_raises_when_missing(self):
        with self.assertRaises(Department.DoesNotExist):
            get_department(department_id=999999)

    def test_list_departments_returns_all_departments(self):
        result = list_departments()

        self.assertEqual(
            set(result),
            {
                self.active_department,
                self.inactive_department,
            },
        )

    def test_list_active_departments_returns_only_active(self):
        result = list(list_active_departments())

        self.assertEqual(result, [self.active_department])


class PositionSelectorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Operations",
            code="OPS",
        )
        self.other_department = Department.objects.create(
            name="Finance",
            code="FIN",
        )

        self.active_position = Position.objects.create(
            title="Operations Manager",
            code="OPS-MGR",
            department=self.department,
            is_active=True,
        )
        self.inactive_position = Position.objects.create(
            title="Former Operations Officer",
            code="OPS-OFF",
            department=self.department,
            is_active=False,
        )
        self.other_position = Position.objects.create(
            title="Finance Officer",
            code="FIN-OFF",
            department=self.other_department,
            is_active=True,
        )

    def test_get_position_returns_position(self):
        result = get_position(
            position_id=self.active_position.pk,
        )

        self.assertEqual(result, self.active_position)

    def test_get_position_raises_when_missing(self):
        with self.assertRaises(Position.DoesNotExist):
            get_position(position_id=999999)

    def test_list_positions_returns_all_positions(self):
        result = list(list_positions())

        self.assertEqual(
            set(result),
            {
                self.active_position,
                self.inactive_position,
                self.other_position,
            },
        )

    def test_list_active_positions_returns_only_active_positions(self):
        result = list(list_active_positions())

        self.assertEqual(
            set(result),
            {
                self.active_position,
                self.other_position,
            },
        )

    def test_list_positions_by_department_returns_matching_positions(self):
        result = list(
            list_positions_by_department(
                department=self.department,
            )
        )

        self.assertEqual(
            set(result),
            {
                self.active_position,
                self.inactive_position,
            },
        )

    def test_list_positions_by_department_requires_department_instance(self):
        with self.assertRaises(TypeError):
            list_positions_by_department(
                department=self.department.pk,
            )


class StaffMemberSelectorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Operations",
            code="OPS",
        )
        self.other_department = Department.objects.create(
            name="Finance",
            code="FIN",
        )

        self.position = Position.objects.create(
            title="Operations Officer",
            code="OPS-OFF",
            department=self.department,
        )
        self.other_position = Position.objects.create(
            title="Finance Officer",
            code="FIN-OFF",
            department=self.other_department,
        )

        self.user = User.objects.create_user(
            email="staff1@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            email="staff2@example.com",
            password="test-password",
        )
        self.third_user = User.objects.create_user(
            email="staff3@example.com",
            password="test-password",
        )

        self.manager = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-001",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2026, 1, 10),
        )

        self.staff_member = StaffMember.objects.create(
            user=self.other_user,
            employee_number="EMP-002",
            department=self.department,
            position=self.position,
            manager=self.manager,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2026, 2, 10),
        )

        self.inactive_staff_member = StaffMember.objects.create(
            user=self.third_user,
            employee_number="EMP-003",
            department=self.other_department,
            position=self.other_position,
            employment_status=StaffMember.EmploymentStatus.ON_LEAVE,
            date_joined=date(2026, 3, 10),
        )

    def test_get_staff_member_returns_staff_member(self):
        result = get_staff_member(
            staff_member_id=self.staff_member.pk,
        )

        self.assertEqual(result, self.staff_member)

    def test_get_staff_member_raises_when_missing(self):
        with self.assertRaises(StaffMember.DoesNotExist):
            get_staff_member(staff_member_id=999999)

    def test_get_staff_member_by_user_returns_matching_staff_member(self):
        result = get_staff_member_by_user(
            user=self.staff_member.user,
        )

        self.assertEqual(result, self.staff_member)

    def test_get_staff_member_by_user_requires_user_instance(self):
        with self.assertRaises(TypeError):
            get_staff_member_by_user(user=self.staff_member.user.pk)

    def test_get_staff_member_by_employee_number_returns_matching_staff_member(
        self,
    ):
        result = get_staff_member_by_employee_number(
            employee_number="EMP-002",
        )

        self.assertEqual(result, self.staff_member)

    def test_list_staff_members_returns_all_staff_members(self):
        result = list(list_staff_members())

        self.assertEqual(
            set(result),
            {
                self.manager,
                self.staff_member,
                self.inactive_staff_member,
            },
        )

    def test_list_active_staff_members_returns_only_active_staff(self):
        result = list(list_active_staff_members())

        self.assertEqual(
            set(result),
            {
                self.manager,
                self.staff_member,
            },
        )

    def test_list_staff_members_by_department_returns_matching_staff(
        self,
    ):
        result = list(
            list_staff_members_by_department(
                department=self.department,
            )
        )

        self.assertEqual(
            set(result),
            {
                self.manager,
                self.staff_member,
            },
        )

    def test_list_staff_members_by_department_requires_department_instance(
        self,
    ):
        with self.assertRaises(TypeError):
            list_staff_members_by_department(
                department=self.department.pk,
            )

    def test_list_staff_members_by_manager_returns_direct_reports(self):
        result = list(
            list_staff_members_by_manager(
                manager=self.manager,
            )
        )

        self.assertEqual(result, [self.staff_member])

    def test_list_staff_members_by_manager_requires_staff_member_instance(
        self,
    ):
        with self.assertRaises(TypeError):
            list_staff_members_by_manager(
                manager=self.manager.pk,
            )