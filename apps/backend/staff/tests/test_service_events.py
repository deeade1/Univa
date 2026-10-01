from datetime import date
from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from staff.models import Department, Position, StaffMember
from staff.services import (
    change_employment_status,
    create_staff_member,
)


class StaffServiceEventIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="service-events@example.com",
            password="test-password",
            first_name="Service",
            last_name="Events",
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

    @patch("staff.services.staff_service.emit_staff_member_created")
    def test_create_staff_member_emits_created_event(
        self,
        emit_staff_member_created,
    ):
        staff_member = create_staff_member(
            user=self.user,
            employee_number="EMP-1001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
        )

        emit_staff_member_created.assert_called_once_with(
            staff_member=staff_member,
        )

    @patch(
        "staff.services.staff_service."
        "emit_staff_member_employment_status_changed"
    )
    def test_change_employment_status_emits_status_changed_event(
        self,
        emit_staff_member_employment_status_changed,
    ):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-1002",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
            employment_status=StaffMember.EmploymentStatus.PENDING,
        )

        change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        emit_staff_member_employment_status_changed.assert_called_once_with(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.PENDING,
        )

    @patch(
        "staff.services.staff_service."
        "emit_staff_member_employment_status_changed"
    )
    def test_terminal_status_change_emits_date_left_on_staff_member(
        self,
        emit_staff_member_employment_status_changed,
    ):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-1003",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        date_left = date(2026, 9, 21)

        change_employment_status(
            staff_member=staff_member,
            new_status=StaffMember.EmploymentStatus.RESIGNED,
            date_left=date_left,
        )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(
            staff_member.date_left,
            date_left,
        )

        emit_staff_member_employment_status_changed.assert_called_once_with(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.ACTIVE,
        )