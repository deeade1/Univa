# apps/backend/accounts/tests/test_role.py

"""
Tests for the Role model.

Role is the application-level definition.

Role owns:

    - application namespace
    - role name
    - permissions
    - default status
    - verification policy
    - auto-assignment policy

Role does NOT own:

    - a user's assignment
    - face verification
    - account registration
    - authentication tokens
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase

from accounts.models.role import Role


User = get_user_model()


class RoleModelTests(TestCase):
    """Tests for application roles."""

    def test_create_role(self):
        """A role can be created for a valid application."""

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
        )

        self.assertEqual(
            role.name,
            "customer",
        )

        self.assertEqual(
            role.app_name,
            "ecommerce",
        )

    def test_role_string_representation(self):
        role = Role.objects.create(
            name="agent",
            app_name="realestate",
        )

        self.assertIn(
            "agent",
            str(role),
        )

        self.assertIn(
            "Real Estate",
            str(role),
        )

    def test_role_name_and_app_must_be_unique(self):
        """
        The same role name may exist in different applications,
        but not twice within the same application.
        """

        Role.objects.create(
            name="admin",
            app_name="realestate",
        )

        with self.assertRaises(
            IntegrityError,
        ):
            Role.objects.create(
                name="admin",
                app_name="realestate",
            )

    def test_same_role_name_can_exist_in_different_apps(self):
        """Role uniqueness is scoped to the application."""

        first = Role.objects.create(
            name="admin",
            app_name="realestate",
        )

        second = Role.objects.create(
            name="admin",
            app_name="transport",
        )

        self.assertNotEqual(
            first.pk,
            second.pk,
        )

    def test_requires_verification_defaults_to_false(self):
        """Ordinary roles do not require verification."""

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
        )

        self.assertFalse(
            role.requires_verification,
        )

    def test_requires_verification_can_be_enabled(self):
        """Verification policy belongs to Role."""

        role = Role.objects.create(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        self.assertTrue(
            role.requires_verification,
        )

    def test_auto_assign_defaults_to_false(self):
        """Roles are not automatically assigned unless configured."""

        role = Role.objects.create(
            name="agent",
            app_name="realestate",
        )

        self.assertFalse(
            role.auto_assign,
        )

    def test_get_default_roles_returns_auto_assign_roles(self):
        """get_default_roles() returns roles marked auto_assign."""

        default_role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
            auto_assign=True,
        )

        Role.objects.create(
            name="vendor",
            app_name="ecommerce",
            auto_assign=False,
        )

        roles = Role.get_default_roles()

        self.assertIn(
            default_role,
            roles,
        )

        self.assertEqual(
            roles.count(),
            1,
        )

    def test_get_app_roles_filters_by_application(self):
        """get_app_roles() scopes roles to one application."""

        realestate_role = Role.objects.create(
            name="agent",
            app_name="realestate",
        )

        Role.objects.create(
            name="driver",
            app_name="transport",
        )

        roles = Role.get_app_roles(
            "realestate",
        )

        self.assertIn(
            realestate_role,
            roles,
        )

        self.assertEqual(
            roles.count(),
            1,
        )

    def test_get_auto_assign_roles_can_filter_application(self):
        """Auto-assignment roles can be scoped to an app."""

        expected = Role.objects.create(
            name="customer",
            app_name="ecommerce",
            auto_assign=True,
        )

        Role.objects.create(
            name="customer",
            app_name="social",
            auto_assign=True,
        )

        roles = Role.get_auto_assign_roles(
            app_name="ecommerce",
        )

        self.assertEqual(
            roles.count(),
            1,
        )

        self.assertEqual(
            roles.first(),
            expected,
        )

    def test_role_permissions_can_be_assigned(self):
        """Role permissions use Django's permission system."""

        permission = Permission.objects.first()

        if permission is None:
            self.skipTest(
                "No Django Permission records are available."
            )

        role = Role.objects.create(
            name="staff",
            app_name="admin",
        )

        role.permissions.add(
            permission,
        )

        self.assertIn(
            permission,
            role.permissions.all(),
        )

    def test_all_configured_application_names_are_valid_choices(self):
        """Role exposes the expected Univa application namespaces."""

        configured_apps = {
            value
            for value, _label in Role.APP_CHOICES
        }

        expected_apps = {
            "admin",
            "transport",
            "ecommerce",
            "realestate",
            "social",
            "banking",
            "blog",
            "chat",
        }

        self.assertEqual(
            configured_apps,
            expected_apps,
        )