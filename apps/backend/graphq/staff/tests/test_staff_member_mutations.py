"""
Tests for Staff GraphQL mutations.

GraphQL architectural boundary
-------------------------------

These tests verify that the Staff GraphQL mutations:

    - enforce the Accounts admin authorization boundary
    - resolve Relay IDs correctly
    - invoke Staff domain services
    - return StaffMember payloads
    - preserve Staff employment rules at the service boundary
    - do not assign or modify Accounts roles

Notification event emission is mocked here because the Staff domain
service and event adapter have their own dedicated integration tests.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from graphql_relay import to_global_id

from accounts.models.role import Role, UserRole

from backend.schema import schema as graphene_schema

from graphq.accounts.types.user import UserNode
from graphq.staff.mutations.staff_member import (
    ChangeStaffEmploymentStatus,
    CreateStaffMember,
)
from graphq.staff.types.department import DepartmentNode
from graphq.staff.types.position import PositionNode
from graphq.staff.types.staff_member import StaffMemberNode

from staff.models.department import Department
from staff.models.position import Position
from staff.models.staff_member import StaffMember


User = get_user_model()


class StaffMutationTestCase(TestCase):
    """
    Shared fixtures for Staff GraphQL mutation tests.

    The mutation methods are invoked directly rather than through
    GraphQL execution. Therefore the test must provide the minimum
    Graphene ResolveInfo contract required by the mutations:

        info.context.user
        info.schema

    The Accounts authorization boundary reads info.context.user.

    Relay's Node.get_node_from_global_id() reads info.schema in order
    to resolve the GraphQL type represented by the Relay global ID.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="staff-admin@example.com",
            password="test-password",
            first_name="Staff",
            last_name="Admin",
        )

        self.user = User.objects.create_user(
            email="staff-user@example.com",
            password="test-password",
            first_name="Staff",
            last_name="User",
        )

        self.manager_user = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
            first_name="Staff",
            last_name="Manager",
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

        self.manager_position = Position.objects.create(
            title="Operations Manager",
            code="OPS-MANAGER",
            department=self.department,
            is_management=True,
        )

        self.manager = StaffMember.objects.create(
            user=self.manager_user,
            employee_number="EMP-MANAGER",
            department=self.department,
            position=self.manager_position,
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
            date_joined=date(2026, 1, 1),
        )

        self.admin_info = self.make_info(self.admin)
        self.user_info = self.make_info(self.user)
        self.anonymous_info = self.make_info(
            SimpleNamespace(is_authenticated=False)
        )

    @staticmethod
    def make_info(user):
        """
        Build the minimum Graphene ResolveInfo-compatible object required
        by the Staff mutations.

        Accounts authorization reads:

            info.context.user

        Relay Node.get_node_from_global_id() reads:

            info.schema.get_type(...)
        
        Therefore info.schema must be the underlying GraphQL-core
        GraphQLSchema, not the outer Graphene Schema wrapper.
        """
        return SimpleNamespace(
            context=SimpleNamespace(
                user=user,
            ),
            schema=graphene_schema.graphql_schema,
        )

    @staticmethod
    def global_id(node_type, pk):
        """
        Create a Relay global ID using the GraphQL node type name.
        """
        return to_global_id(node_type, pk)


class CreateStaffMemberMutationTests(StaffMutationTestCase):
    """
    GraphQL contract tests for CreateStaffMember.
    """

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_admin_can_create_staff_member(
        self,
        emit_staff_member_created,
    ):
        result = CreateStaffMember.mutate_and_get_payload(
            None,
            self.admin_info,
            user_id=self.global_id(
                UserNode._meta.name,
                self.user.pk,
            ),
            employee_number="EMP-0001",
            department_id=self.global_id(
                DepartmentNode._meta.name,
                self.department.pk,
            ),
            position_id=self.global_id(
                PositionNode._meta.name,
                self.position.pk,
            ),
            date_joined=date(2026, 1, 15),
        )

        self.assertIsNotNone(result.staff_member)
        self.assertIsInstance(
            result.staff_member,
            StaffMember,
        )

        staff_member = result.staff_member

        self.assertEqual(
            staff_member.user_id,
            self.user.pk,
        )
        self.assertEqual(
            staff_member.employee_number,
            "EMP-0001",
        )
        self.assertEqual(
            staff_member.department_id,
            self.department.pk,
        )
        self.assertEqual(
            staff_member.position_id,
            self.position.pk,
        )
        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.PENDING,
        )
        self.assertIsNone(staff_member.manager_id)

        emit_staff_member_created.assert_called_once_with(
            staff_member=staff_member,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_admin_can_create_staff_member_with_manager(
        self,
        emit_staff_member_created,
    ):
        result = CreateStaffMember.mutate_and_get_payload(
            None,
            self.admin_info,
            user_id=self.global_id(
                UserNode._meta.name,
                self.user.pk,
            ),
            employee_number="EMP-0002",
            department_id=self.global_id(
                DepartmentNode._meta.name,
                self.department.pk,
            ),
            position_id=self.global_id(
                PositionNode._meta.name,
                self.position.pk,
            ),
            manager_id=self.global_id(
                StaffMemberNode._meta.name,
                self.manager.pk,
            ),
            date_joined=date(2026, 2, 1),
        )

        staff_member = result.staff_member

        self.assertEqual(
            staff_member.manager_id,
            self.manager.pk,
        )

        emit_staff_member_created.assert_called_once_with(
            staff_member=staff_member,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_admin_can_create_active_staff_member(
        self,
        emit_staff_member_created,
    ):
        result = CreateStaffMember.mutate_and_get_payload(
            None,
            self.admin_info,
            user_id=self.global_id(
                UserNode._meta.name,
                self.user.pk,
            ),
            employee_number="EMP-0003",
            department_id=self.global_id(
                DepartmentNode._meta.name,
                self.department.pk,
            ),
            position_id=self.global_id(
                PositionNode._meta.name,
                self.position.pk,
            ),
            date_joined=date(2026, 2, 1),
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        self.assertEqual(
            result.staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

        emit_staff_member_created.assert_called_once_with(
            staff_member=result.staff_member,
        )

    def test_non_admin_cannot_create_staff_member(self):
        with self.assertRaises(Exception):
            CreateStaffMember.mutate_and_get_payload(
                None,
                self.user_info,
                user_id=self.global_id(
                    UserNode._meta.name,
                    self.user.pk,
                ),
                employee_number="EMP-0004",
                department_id=self.global_id(
                    DepartmentNode._meta.name,
                    self.department.pk,
                ),
                position_id=self.global_id(
                    PositionNode._meta.name,
                    self.position.pk,
                ),
                date_joined=date(2026, 2, 1),
            )

        self.assertFalse(
            StaffMember.objects.filter(
                employee_number="EMP-0004",
            ).exists()
        )

    def test_unauthenticated_user_cannot_create_staff_member(self):
        with self.assertRaises(Exception):
            CreateStaffMember.mutate_and_get_payload(
                None,
                self.anonymous_info,
                user_id=self.global_id(
                    UserNode._meta.name,
                    self.user.pk,
                ),
                employee_number="EMP-0005",
                department_id=self.global_id(
                    DepartmentNode._meta.name,
                    self.department.pk,
                ),
                position_id=self.global_id(
                    PositionNode._meta.name,
                    self.position.pk,
                ),
                date_joined=date(2026, 2, 1),
            )

        self.assertFalse(
            StaffMember.objects.filter(
                employee_number="EMP-0005",
            ).exists()
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_invalid_department_id_is_rejected(
        self,
        emit_staff_member_created,
    ):
        with self.assertRaises(Exception):
            CreateStaffMember.mutate_and_get_payload(
                None,
                self.admin_info,
                user_id=self.global_id(
                    UserNode._meta.name,
                    self.user.pk,
                ),
                employee_number="EMP-0006",
                department_id=self.global_id(
                    DepartmentNode._meta.name,
                    999999,
                ),
                position_id=self.global_id(
                    PositionNode._meta.name,
                    self.position.pk,
                ),
                date_joined=date(2026, 2, 1),
            )

        emit_staff_member_created.assert_not_called()

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_invalid_position_id_is_rejected(
        self,
        emit_staff_member_created,
    ):
        with self.assertRaises(Exception):
            CreateStaffMember.mutate_and_get_payload(
                None,
                self.admin_info,
                user_id=self.global_id(
                    UserNode._meta.name,
                    self.user.pk,
                ),
                employee_number="EMP-0007",
                department_id=self.global_id(
                    DepartmentNode._meta.name,
                    self.department.pk,
                ),
                position_id=self.global_id(
                    PositionNode._meta.name,
                    999999,
                ),
                date_joined=date(2026, 2, 1),
            )

        emit_staff_member_created.assert_not_called()

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_invalid_manager_id_is_rejected(
        self,
        emit_staff_member_created,
    ):
        with self.assertRaises(Exception):
            CreateStaffMember.mutate_and_get_payload(
                None,
                self.admin_info,
                user_id=self.global_id(
                    UserNode._meta.name,
                    self.user.pk,
                ),
                employee_number="EMP-0008",
                department_id=self.global_id(
                    DepartmentNode._meta.name,
                    self.department.pk,
                ),
                position_id=self.global_id(
                    PositionNode._meta.name,
                    self.position.pk,
                ),
                manager_id=self.global_id(
                    StaffMemberNode._meta.name,
                    999999,
                ),
                date_joined=date(2026, 2, 1),
            )

        emit_staff_member_created.assert_not_called()

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_creation_does_not_assign_accounts_roles(
        self,
        emit_staff_member_created,
    ):
        result = CreateStaffMember.mutate_and_get_payload(
            None,
            self.admin_info,
            user_id=self.global_id(
                UserNode._meta.name,
                self.user.pk,
            ),
            employee_number="EMP-0009",
            department_id=self.global_id(
                DepartmentNode._meta.name,
                self.department.pk,
            ),
            position_id=self.global_id(
                PositionNode._meta.name,
                self.position.pk,
            ),
            date_joined=date(2026, 2, 1),
        )

        self.assertIsNotNone(result.staff_member)

        self.assertFalse(
            UserRole.objects.filter(
                user=self.user,
            ).exists()
        )

        emit_staff_member_created.assert_called_once_with(
            staff_member=result.staff_member,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_created"
    )
    def test_creation_does_not_modify_existing_accounts_roles(
        self,
        emit_staff_member_created,
    ):
        role = Role.objects.create(
            name="staff_graphql_test_role",
            app_name="admin",
        )

        assignment = UserRole.objects.create(
            user=self.user,
            role=role,
            is_active=True,
        )

        CreateStaffMember.mutate_and_get_payload(
            None,
            self.admin_info,
            user_id=self.global_id(
                UserNode._meta.name,
                self.user.pk,
            ),
            employee_number="EMP-0010",
            department_id=self.global_id(
                DepartmentNode._meta.name,
                self.department.pk,
            ),
            position_id=self.global_id(
                PositionNode._meta.name,
                self.position.pk,
            ),
            date_joined=date(2026, 2, 1),
        )

        assignment.refresh_from_db()

        self.assertTrue(assignment.is_active)

        self.assertEqual(
            UserRole.objects.filter(
                user=self.user,
            ).count(),
            1,
        )

        emit_staff_member_created.assert_called_once_with(
            staff_member=assignment.user.staff_member,
        )


class ChangeStaffEmploymentStatusMutationTests(
    StaffMutationTestCase,
):
    """
    GraphQL contract tests for ChangeStaffEmploymentStatus.
    """

    def create_staff_member(self, status):
        return StaffMember.objects.create(
            user=self.user,
            employee_number=f"EMP-{self.user.pk}-{status}",
            department=self.department,
            position=self.position,
            employment_status=status,
            date_joined=date(2026, 1, 15),
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_admin_can_change_pending_to_active(
        self,
        emit_status_changed,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.PENDING,
        )

        result = ChangeStaffEmploymentStatus.mutate_and_get_payload(
            None,
            self.admin_info,
            staff_member_id=self.global_id(
                StaffMemberNode._meta.name,
                staff_member.pk,
            ),
            employment_status=StaffMember.EmploymentStatus.ACTIVE,
        )

        staff_member.refresh_from_db()

        self.assertEqual(
            result.staff_member.pk,
            staff_member.pk,
        )
        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )
        self.assertIsNone(staff_member.date_left)

        emit_status_changed.assert_called_once_with(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.PENDING,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_admin_can_change_active_to_resigned(
        self,
        emit_status_changed,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.ACTIVE,
        )

        date_left = date(2026, 8, 31)

        result = ChangeStaffEmploymentStatus.mutate_and_get_payload(
            None,
            self.admin_info,
            staff_member_id=self.global_id(
                StaffMemberNode._meta.name,
                staff_member.pk,
            ),
            employment_status=StaffMember.EmploymentStatus.RESIGNED,
            date_left=date_left,
        )

        staff_member.refresh_from_db()

        self.assertEqual(
            result.staff_member.pk,
            staff_member.pk,
        )
        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(
            staff_member.date_left,
            date_left,
        )

        emit_status_changed.assert_called_once_with(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.ACTIVE,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_admin_can_change_active_to_terminated(
        self,
        emit_status_changed,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.ACTIVE,
        )

        date_left = date(2026, 9, 15)

        ChangeStaffEmploymentStatus.mutate_and_get_payload(
            None,
            self.admin_info,
            staff_member_id=self.global_id(
                StaffMemberNode._meta.name,
                staff_member.pk,
            ),
            employment_status=StaffMember.EmploymentStatus.TERMINATED,
            date_left=date_left,
        )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.TERMINATED,
        )
        self.assertEqual(
            staff_member.date_left,
            date_left,
        )

        emit_status_changed.assert_called_once_with(
            staff_member=staff_member,
            previous_status=StaffMember.EmploymentStatus.ACTIVE,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_terminal_status_requires_date_left(
        self,
        emit_status_changed,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.admin_info,
                staff_member_id=self.global_id(
                    StaffMemberNode._meta.name,
                    staff_member.pk,
                ),
                employment_status=StaffMember.EmploymentStatus.RESIGNED,
            )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )
        self.assertIsNone(staff_member.date_left)

        emit_status_changed.assert_not_called()

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_invalid_transition_is_rejected(
        self,
        emit_status_changed,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.RESIGNED,
        )

        staff_member.date_left = date(2026, 8, 31)
        staff_member.save(
            update_fields=["date_left"],
        )

        with self.assertRaises(ValidationError):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.admin_info,
                staff_member_id=self.global_id(
                    StaffMemberNode._meta.name,
                    staff_member.pk,
                ),
                employment_status=StaffMember.EmploymentStatus.ACTIVE,
            )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.RESIGNED,
        )
        self.assertEqual(
            staff_member.date_left,
            date(2026, 8, 31),
        )

        emit_status_changed.assert_not_called()

    def test_non_admin_cannot_change_employment_status(self):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.ACTIVE,
        )

        with self.assertRaises(Exception):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.user_info,
                staff_member_id=self.global_id(
                    StaffMemberNode._meta.name,
                    staff_member.pk,
                ),
                employment_status=StaffMember.EmploymentStatus.ON_LEAVE,
            )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

    def test_unauthenticated_user_cannot_change_employment_status(
        self,
    ):
        staff_member = self.create_staff_member(
            StaffMember.EmploymentStatus.ACTIVE,
        )

        with self.assertRaises(Exception):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.anonymous_info,
                staff_member_id=self.global_id(
                    StaffMemberNode._meta.name,
                    staff_member.pk,
                ),
                employment_status=StaffMember.EmploymentStatus.ON_LEAVE,
            )

        staff_member.refresh_from_db()

        self.assertEqual(
            staff_member.employment_status,
            StaffMember.EmploymentStatus.ACTIVE,
        )

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_invalid_staff_member_id_is_rejected(
        self,
        emit_status_changed,
    ):
        with self.assertRaises(Exception):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.admin_info,
                staff_member_id=self.global_id(
                    StaffMemberNode._meta.name,
                    999999,
                ),
                employment_status=StaffMember.EmploymentStatus.ACTIVE,
            )

        emit_status_changed.assert_not_called()

    @patch(
        "staff.services.staff_service.emit_staff_member_employment_status_changed"
    )
    def test_wrong_relay_type_is_rejected(
        self,
        emit_status_changed,
    ):
        with self.assertRaises(Exception):
            ChangeStaffEmploymentStatus.mutate_and_get_payload(
                None,
                self.admin_info,
                staff_member_id=self.global_id(
                    DepartmentNode._meta.name,
                    self.department.pk,
                ),
                employment_status=StaffMember.EmploymentStatus.ACTIVE,
            )

        emit_status_changed.assert_not_called()
