from datetime import date
from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from staff.models import Department, Position, StaffMember



class StaffEventContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="staff-events@example.com",
            password="test-password",
            first_name="Staff",
            last_name="Events",
        )

        self.department = Department.objects.create(
            name="Legal",
            code="LEGAL",
        )

        self.position = Position.objects.create(
            title="Legal Officer",
            code="LEGAL-OFFICER",
            department=self.department,
        )

    @patch("staff.events.staff_events.emit_notification_event")
    def test_staff_member_created_event_contract(
        self,
        emit_notification_event,
    ):
        
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
        )
        # This test intentionally represents the event contract that
        # staff.events.staff_events must provide.
        from staff.events.staff_events import emit_staff_member_created

        emit_staff_member_created(
            staff_member=staff_member,
        )

        emit_notification_event.assert_called_once()

        _, kwargs = emit_notification_event.call_args

        self.assertEqual(
            kwargs["event_type"],
            "STAFF.MEMBER_CREATED",
        )
        self.assertEqual(kwargs["module"], "staff")
        self.assertIsNone(kwargs["actor"])
        self.assertEqual(kwargs["object_type"], "StaffMember")
        self.assertEqual(kwargs["object_id"], staff_member.pk)

        self.assertEqual(
            kwargs["payload"],
            {
                "staff_member_id": staff_member.pk,
                "employee_number": staff_member.employee_number,
                "department_id": staff_member.department_id,
                "position_id": staff_member.position_id,
                "employment_status": (
                    staff_member.employment_status
                ),
                "recipient_id": staff_member.user_id,
            },
        )

    @patch("staff.events.staff_events.emit_notification_event")
    def test_staff_member_employment_status_changed_event_contract(
        self,
        emit_notification_event,
    ):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
        )

        previous_status = (
            StaffMember.EmploymentStatus.PENDING
        )

        staff_member.employment_status = (
            StaffMember.EmploymentStatus.ACTIVE
        )
        staff_member.save(
            update_fields=[
                "employment_status",
                "updated_at",
            ]
        )

        from staff.events.staff_events import (
            emit_staff_member_employment_status_changed,
        )

        emit_staff_member_employment_status_changed(
            staff_member=staff_member,
            previous_status=previous_status,
        )

        emit_notification_event.assert_called_once()

        _, kwargs = emit_notification_event.call_args

        self.assertEqual(
            kwargs["event_type"],
            "STAFF.MEMBER_EMPLOYMENT_STATUS_CHANGED",
        )
        self.assertEqual(kwargs["module"], "staff")
        self.assertIsNone(kwargs["actor"])
        self.assertEqual(kwargs["object_type"], "StaffMember")
        self.assertEqual(kwargs["object_id"], staff_member.pk)

        self.assertEqual(
            kwargs["payload"],
            {
                "staff_member_id": staff_member.pk,
                "employee_number": staff_member.employee_number,
                "previous_status": previous_status,
                "new_status": (
                    staff_member.employment_status
                ),
                "date_left": None,
                "recipient_id": staff_member.user_id,
            },
        )

    @patch("staff.events.staff_events.emit_notification_event")
    def test_staff_member_employment_status_changed_includes_date_left(
        self,
        emit_notification_event,
    ):
        staff_member = StaffMember.objects.create(
            user=self.user,
            employee_number="EMP-0001",
            department=self.department,
            position=self.position,
            date_joined=date(2026, 1, 1),
        )

        previous_status = (
            StaffMember.EmploymentStatus.PENDING
        )

        staff_member.employment_status = (
            StaffMember.EmploymentStatus.ACTIVE
        )
        staff_member.date_left = None
        staff_member.save(
            update_fields=[
                "employment_status",
                "date_left",
                "updated_at",
            ]
        )

        from staff.events.staff_events import (
            emit_staff_member_employment_status_changed,
        )

        staff_member.employment_status = (
            StaffMember.EmploymentStatus.RESIGNED
        )
        staff_member.date_left = date(2026, 9, 21)
        staff_member.save(
            update_fields=[
                "employment_status",
                "date_left",
                "updated_at",
            ]
        )

        emit_staff_member_employment_status_changed(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        emit_notification_event.assert_called_once()

        _, kwargs = emit_notification_event.call_args

        self.assertEqual(
            kwargs["payload"]["previous_status"],
            StaffMember.EmploymentStatus.ACTIVE,
        )
        self.assertEqual(
            kwargs["payload"]["new_status"],
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(
            kwargs["payload"]["date_left"],
            "2026-09-21",
        )