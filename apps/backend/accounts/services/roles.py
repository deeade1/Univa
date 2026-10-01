"""
Role provisioning and authorization-related account services.

This module owns operations involving Role and UserRole.

The models remain responsible for persistence and invariants.
"""

from django.db import transaction
from django.utils import timezone

from accounts.models import Role, UserRole


@transaction.atomic
def assign_default_roles(
    user,
    *,
    assigned_by=None,
):
    """
    Assign all roles configured for automatic assignment.

    This operation is idempotent.
    """

    roles = Role.get_default_roles()

    assignments = []

    for role in roles:
        assignment, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={
                "is_active": not role.requires_verification,
                "created_by": assigned_by,
            },
        )

        assignments.append(assignment)

    return assignments


@transaction.atomic
def assign_role(
    user,
    role,
    *,
    assigned_by=None,
    verified_by=None,
    activate=True,
    notes="",
    expires_at=None,
):
    """
    Explicitly assign a role to a user.
    """

    verified_at = (
        timezone.now()
        if verified_by is not None
        else None
    )

    assignment, created = UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={
            "is_active": (
                activate
                and (
                    not role.requires_verification
                    or verified_by is not None
                )
            ),
            "created_by": assigned_by,
            "verified_by": verified_by,
            "verified_at": verified_at,
            "notes": notes,
            "expires_at": expires_at,
        },
    )

    return assignment


@transaction.atomic
def revoke_role(
    user,
    role,
    *,
    revoked_by=None,
):
    """
    Revoke a user's role.
    """

    assignment = UserRole.objects.select_for_update().get(
        user=user,
        role=role,
    )

    assignment.revoke(
        by_user=revoked_by,
    )

    return assignment