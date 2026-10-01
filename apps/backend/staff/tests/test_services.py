
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import User, Role, UserRole
from staff.models import Department, Position, StaffMember
from staff.services import create_staff_member, change_employment_status
from django.core.exceptions import ValidationError



class CreateStaffMemberServiceTests(TestCase):
    def setUp(self):
        self.User = get_user_model()


        self.user = self.User.objects.create_user(
            email="employee@example.com",
            password="test-password",
            first_name="John",
            last_name="Employee",
        )

        self.manager_user = self.User.objects.create_user(
            email="manager@example.com",
            password="test-password",
            first_name="Jane",
            last_name="Manager",
        )

        self.department = Department.objects.create(
            name="Human Resources",
            code="HR",
        )

        self.position = Position.objects.create(
            title="HR Officer",
            code="HR-OFFICER",
            department=self.department,
        )

        self.manager_position = Position.objects.create(
            title="HR Manager",
            code="HR-MANAGER",
            department=self.department,
            is_management=True,
        )

        self.manager = StaffMember.objects.create(
            user=self.manager_user,
            employee_number="EMP-0000",
            department=self.department,
            position=self.manager_position,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2025, 1, 1),
        )

    def test_creates_staff_member(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        self.assertIsInstance(staff_member, StaffMember)
        self.assertEqual(staff_member.user, self.user)
        self.assertEqual(staff_member.employee_number, "EMP-0001")
        self.assertEqual(staff_member.department, self.department)
        self.assertEqual(staff_member.position, self.position)
        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.PENDING,
        )

    def test_preserves_manager(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            manager=self.manager,
            date_joined=date(2026, 1, 15),
        )

        self.assertEqual(staff_member.manager, self.manager)
        self.assertIn(
            staff_member,
            self.manager.direct_reports.all(),
        )

    def test_accepts_explicit_employment_status(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

    def test_does_not_assign_accounts_roles(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        self.assertIsNotNone(staff_member.pk)
        self.assertFalse(
            UserRole.objects.filter(user=self.user).exists()
        )

    def test_does_not_modify_existing_accounts_roles(self):
        role = Role.objects.create(
            name="staff_test_role",
            app_name="admin",
        )

        assignment = UserRole.objects.create(
            user=self.user,
            role=role,
            is_active=True,
        )

        create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        assignment.refresh_from_db()

        self.assertTrue(assignment.is_active)
        self.assertEqual(
            UserRole.objects.filter(user=self.user).count(),
            1,
        )
    def test_new_staff_member_has_no_date_left(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        self.assertIsNone(staff_member.date_left)


    def test_new_staff_member_defaults_to_pending(self):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 15),
        )

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.PENDING,
        )
        self.assertIsNone(staff_member.date_left)


    def test_create_staff_member_rejects_resigned_status(self):
        with self.assertRaises(ValidationError):
            create_staff_member(
                user=self.user,
                employee_number="EMP-0001",
                department=self.department,
                position=self.position,
                date_joined=date(2026, 1, 15),
                employment_status=StaffMember.EmploymentStatus.RESIGNED,
            )


    def test_create_staff_member_rejects_terminated_status(self):
        with self.assertRaises(ValidationError):
            create_staff_member(
                user=self.user,
                employee_number="EMP-0001",
                department=self.department,
                position=self.position,
                date_joined=date(2026, 1, 15),
                employment_status=StaffMember.EmploymentStatus.TERMINATED,
            )


class ChangeEmploymentStatusServiceTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.user = User.objects.create_user(
            email="status@example.com",
            password="test-password",
            first_name="Status",
            last_name="Test",
        )

        self.department = Department.objects.create(
            name="Operations",
            code="OPS",
        )

        self.position = Position.objects.create(
            title="Operations Officer",
            code="OPS-OFFICER",
            department=self.department,
        )

    def create_staff(self, status):
        return StaffMember.objects.create(
            user=self.user,
            employee_number=f"EMP-{status}",
            department=self.department,
            position=self.position,
            employment_status=status,
            date_joined=date(2026, 1, 1),
        )

    def test_pending_can_become_active(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.PENDING
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

    def test_active_can_become_on_leave(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.ACTIVE
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.ON_LEAVE,
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.ON_LEAVE,
        )

    def test_on_leave_can_return_to_active(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.ON_LEAVE
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

    def test_suspended_can_return_to_active(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.SUSPENDED
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

  
    def test_active_can_be_resigned(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.ACTIVE
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.RESIGNED,
            date_left=date(2026, 8, 31),
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(
            result.date_left,
            date(2026, 8, 31),
        )


    def test_active_can_be_terminated(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.ACTIVE
        )

        result = change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.TERMINATED,
            date_left=date(2026, 9, 15),
        )

        self.assertEqual(
            result.employment_status,
            StaffMember.EmploymentStatus.TERMINATED,
        )
        self.assertEqual(
            result.date_left,
            date(2026, 9, 15),
        )


        def test_pending_cannot_be_suspended(self):
            staff_member = self.create_staff(
                StaffMember.EmploymentStatus.PENDING
            )

            with self.assertRaises(ValidationError):
                change_employment_status(
                    staff_member=staff_member,
                    new_status=StaffMember.EmploymentStatus.SUSPENDED,
                )

    def test_pending_cannot_be_resigned(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.PENDING
        )

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff_member,
                new_status=StaffMember.EmploymentStatus.RESIGNED,
            )

    def test_resigned_is_terminal(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.RESIGNED
        )

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff_member,
                new_status=StaffMember.EmploymentStatus.ACTIVE,
            )

    def test_terminated_is_terminal(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.TERMINATED
        )

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff_member,
                new_status=StaffMember.EmploymentStatus.ACTIVE,
            )

    def test_invalid_status_is_rejected(self):
        staff_member = self.create_staff(
            StaffMember.EmploymentStatus.ACTIVE
        )

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff_member,
                new_status="NOT_A_STATUS",
            )


class EmploymentStatusDateLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="staff-date@example.com",
            password="test-password",
        )

        self.department = Department.objects.create(
            name="Operations",
            code="OPS",
        )

        self.position = Position.objects.create(
            title="Operations Officer",
            code="OPS-OFFICER",
            department=self.department,
        )

        self.date_joined = date(2026, 1, 10)

    def create_staff(self, status=StaffMember.EmploymentStatus.ACTIVE):
        return StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-DATE-001",
            department=self.department,
            position=self.position,
            date_joined=self.date_joined,
            employment_status=status,
        )

    def test_active_to_resigned_requires_date_left(self):
        staff = self.create_staff()

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff,
                new_status=StaffMember.EmploymentStatus.RESIGNED,
            )

    def test_active_to_resigned_sets_explicit_date_left(self):
        staff = self.create_staff()
        date_left = date(2026, 8, 31)

        updated = change_employment_status(
            staff_member=staff,
            new_status=StaffMember.EmploymentStatus.RESIGNED,
            date_left=date_left,
        )

        self.assertEqual(
            updated.employment_status,
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(updated.date_left, date_left)

    def test_active_to_terminated_requires_date_left(self):
        staff = self.create_staff()

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff,
                new_status=StaffMember.EmploymentStatus.TERMINATED,
            )

    def test_active_to_terminated_sets_explicit_date_left(self):
        staff = self.create_staff()
        date_left = date(2026, 9, 15)

        updated = change_employment_status(
            staff_member=staff,
            new_status=StaffMember.EmploymentStatus.TERMINATED,
            date_left=date_left,
        )

        self.assertEqual(
            updated.employment_status,
            StaffMember.EmploymentStatus.TERMINATED,
        )
        self.assertEqual(updated.date_left, date_left)

    def test_terminal_date_left_cannot_precede_date_joined(self):
        staff = self.create_staff()
        date_left = self.date_joined - timedelta(days=1)

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff,
                new_status=StaffMember.EmploymentStatus.RESIGNED,
                date_left=date_left,
            )

    def test_on_leave_to_active_keeps_date_left_none(self):
        staff = self.create_staff(
            StaffMember.EmploymentStatus.ON_LEAVE,
        )

        updated = change_employment_status(
            staff_member=staff,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertIsNone(updated.date_left)

    def test_suspended_to_active_keeps_date_left_none(self):
        staff = self.create_staff(
            StaffMember.EmploymentStatus.SUSPENDED,
        )

        updated = change_employment_status(
            staff_member=staff,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertIsNone(updated.date_left)

    def test_resigned_cannot_return_to_active(self):
        staff = self.create_staff(
            StaffMember.EmploymentStatus.RESIGNED,
        )
        staff.date_left = date(2026, 8, 31)
        staff.save(update_fields=["date_left"])

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff,
                new_status=StaffMember.EmploymentStatus.ACTIVE,
            )

    def test_terminated_cannot_return_to_active(self):
        staff = self.create_staff(
            StaffMember.EmploymentStatus.TERMINATED,
        )
        staff.date_left = date(2026, 8, 31)
        staff.save(update_fields=["date_left"])

        with self.assertRaises(ValidationError):
            change_employment_status(
                staff_member=staff,
                new_status=StaffMember.EmploymentStatus.ACTIVE,
            )