from django.core.exceptions import ValidationError
from django.test import TestCase
from datetime import date
from django.contrib.auth import get_user_model
from staff.models import Department, Position, StaffMember

class DepartmentModelTests(TestCase):
    def test_department_creation(self):
        department = Department.objects.create(
        name="Human Resources",
        code="HR",
        description="People operations and employee services.",
        )
        self.assertEqual(department.name, "Human Resources")
        self.assertEqual(department.code, "HR")
        self.assertTrue(department.is_active)
        self.assertIsNone(department.parent)

    def test_department_can_have_parent(self):
        parent = Department.objects.create(
            name="Operations",
            code="OPS",
        )
        child = Department.objects.create(
            name="Transport Operations",
            code="OPS-TRANSPORT",
            parent=parent,
        )

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.child_departments.all())

    def test_department_cannot_be_its_own_parent(self):
        department = Department.objects.create(
            name="Finance",
            code="FIN",
        )

        department.parent = department

        with self.assertRaises(ValidationError):
            department.full_clean()


class PositionModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
        name="Finance",
        code="FIN",
        )


    def test_position_creation(self):
        position = Position.objects.create(
            title="Finance Manager",
            code="FIN-MGR",
            department=self.department,
            is_management=True,
        )

        self.assertEqual(position.title, "Finance Manager")
        self.assertEqual(position.code, "FIN-MGR")
        self.assertEqual(position.department, self.department)
        self.assertTrue(position.is_management)
        self.assertTrue(position.is_active)

    def test_position_belongs_to_department(self):
        position = Position.objects.create(
            title="Accountant",
            code="FIN-ACC",
            department=self.department,
        )

        self.assertIn(position, self.department.positions.all())

    def test_position_department_is_protected(self):
        Position.objects.create(
            title="Accountant",
            code="FIN-ACC",
            department=self.department,
        )

        with self.assertRaises(Exception):
            self.department.delete()


class StaffMemberModelTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email="staff@example.com",
            password="test-password",
            first_name="John",
            last_name="Doe",
        )

        self.manager_user = self.User.objects.create_user(
            email="manager@example.com",
            password="test-password",
            first_name="Jane",
            last_name="Manager",
        )

        self.department = Department.objects.create(
            name="Finance",
            code="FIN",
        )

        self.position = Position.objects.create(
            title="Accountant",
            code="FIN-ACC",
            department=self.department,
        )

        self.manager_position = Position.objects.create(
            title="Finance Manager",
            code="FIN-MGR",
            department=self.department,
            is_management=True,
        )

    def test_staff_member_creation(self):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        self.assertEqual(staff_member.user, self.user)
        self.assertEqual(staff_member.department, self.department)
        self.assertEqual(staff_member.position, self.position)
        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.PENDING,
        )
        self.assertIsNone(staff_member.manager)
        self.assertIsNone(staff_member.date_left)

    def test_staff_member_can_have_manager(self):
        manager = StaffMember.objects.create(
            user=self.manager_user,
            employee_number="EMP-0000",
            department=self.department,
            position=self.manager_position,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2025, 1, 1),
        )

        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            manager=manager,
            date_joined=date(2026, 1, 15),
        )

        self.assertEqual(staff_member.manager, manager)
        self.assertIn(staff_member, manager.direct_reports.all())

    def test_staff_member_cannot_be_own_manager(self):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        staff_member.manager = staff_member

        with self.assertRaises(ValidationError):
            staff_member.full_clean()

    def test_date_left_cannot_precede_date_joined(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
            date_left=date(2026, 1, 14),
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()

    def test_user_can_have_only_one_staff_member(self):
        StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        with self.assertRaises(Exception):
            StaffMember.objects.create(
                user=self.user,
                employee_number="EMP-0002",
                department=self.department,
                position=self.position,
                date_joined=date(2026, 2, 1),
            )

    def test_user_is_protected_from_staff_member_deletion(self):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        with self.assertRaises(Exception):
            self.user.delete()

        self.assertTrue(
            StaffMember.objects.filter(pk=staff_member.pk).exists()
        )
    
    def test_active_cannot_have_date_left(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-001",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2026, 1, 10),
            date_left=date(2026, 8, 31),
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()


    def test_pending_cannot_have_date_left(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-002",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.PENDING,
            date_joined=date(2026, 1, 10),
            date_left=date(2026, 8, 31),
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()


    def test_resigned_requires_date_left(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-003",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.RESIGNED,
            date_joined=date(2026, 1, 10),
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()


    def test_terminated_requires_date_left(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-004",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.TERMINATED,
            date_joined=date(2026, 1, 10),
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()


    def test_resigned_with_valid_date_left_passes_validation(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-005",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.RESIGNED,
            date_joined=date(2026, 1, 10),
            date_left=date(2026, 8, 31),
        )

        staff_member.full_clean()


    def test_terminated_with_valid_date_left_passes_validation(self):
        staff_member = StaffMember(
            user=self.user,
            employee_number="EMP-DATE-006",
            department=self.department,
            position=self.position,
            employment_status=StaffMember.EmploymentStatus.TERMINATED,
            date_joined=date(2026, 1, 10),
            date_left=date(2026, 9, 15),
        )

        staff_member.full_clean()
