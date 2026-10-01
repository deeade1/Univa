# apps/backend/accounts/models/role.py

"""
Role and UserRole domain models.

ARCHITECTURE
------------

Role
    └── Defines application-level roles and their policy.

UserRole
    └── Represents a user's assignment to a Role and owns the
        assignment lifecycle.

IMPORTANT
---------

Role.requires_verification means:

    "This role requires an application-specific verification process
     before the assignment can become active."

It does NOT mean that every user must complete face verification
during registration.

Face verification / FaceEncoding belongs to specific application
workflows such as:

    - real-estate agent verification
    - banking/KYC workflows
    - other identity-sensitive operations

It is therefore intentionally NOT part of:

    - User registration
    - UserProfile creation
    - Role creation
    - generic UserRole assignment
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# =============================================================================
# ROLE
# =============================================================================


class Role(models.Model):
    """
    Application-level role definition.

    A Role describes what a role means within an application.

    A Role does not represent a specific user's assignment.

    User-specific assignment state belongs to UserRole.
    """

    APP_CHOICES = [
        ("admin", "Site Admin"),
        ("transport", "Transport Service"),
        ("ecommerce", "E-Commerce"),
        ("realestate", "Real Estate"),
        ("social", "Social Media"),
        ("banking", "Banking/Fintech"),
        ("blog", "Blog Platform"),
        ("chat", "Chat/Messaging"),
    ]

    name = models.CharField(
        max_length=50,
    )

    app_name = models.CharField(
        max_length=30,
        choices=APP_CHOICES,
    )

    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="application_roles",
    )

    description = models.TextField(
        blank=True,
    )

    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Marks this role as a default role for its application."
        ),
    )

    requires_verification = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Whether this role requires an application-specific "
            "verification process before activation."
        ),
    )

    auto_assign = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "When True, Accounts may automatically assign this role "
            "to a user during a defined onboarding flow. It does NOT "
            "mean 'every user in the app gets this role.' Capability "
            "roles (driver, agent, vendor, banker) must never be "
            "auto-assigned."
        ),
    )

    class Meta:
        ordering = [
            "app_name",
            "name",
        ]

        verbose_name = "Application Role"
        verbose_name_plural = "Application Roles"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "name",
                    "app_name",
                ],
                name="accounts_role_name_app_unique",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "app_name",
                    "is_default",
                ],
                name="accounts_role_app_default_idx",
            ),
            models.Index(
                fields=[
                    "app_name",
                    "auto_assign",
                ],
                name="accounts_role_app_auto_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_app_name_display()} - {self.name}"
        )

    # =========================================================================
    # ROLE QUERIES
    # =========================================================================

    @classmethod
    def get_default_roles(cls):
        """
        Return roles configured for automatic assignment.

        Only roles explicitly marked auto_assign=True are returned.
        """

        return cls.objects.filter(
            auto_assign=True,
        )

    @classmethod
    def get_app_roles(
        cls,
        app_name: str,
    ):
        """
        Return all roles belonging to an application.
        """

        return cls.objects.filter(
            app_name=app_name,
        )

    @classmethod
    def get_auto_assign_roles(
        cls,
        app_name: str | None = None,
    ):
        """
        Return roles configured for automatic assignment.

        Optionally restrict the result to one application.
        """

        queryset = cls.objects.filter(
            auto_assign=True,
        )

        if app_name:
            queryset = queryset.filter(
                app_name=app_name,
            )

        return queryset


# =============================================================================
# USER ROLE QUERYSET / MANAGER
# =============================================================================


class UserRoleQuerySet(models.QuerySet):
    """
    Query API for UserRole.

    Query/business-selection logic belongs here rather than in GraphQL
    mutations or resolvers.

    "Effective" means, consistently across this API:

        is_active=True
        revoked_at IS NULL
        expires_at IS NULL OR expires_at > now

    This is the single canonical definition of an effective role
    assignment. Every caller that asks "does this user have role X"
    must use one of these methods to stay consistent.
    """

    def get_user_roles(
        self,
        user,
        app_name: str | None = None,
    ):
        """
        Return currently effective role assignments for a user.

        If app_name is provided, restrict the result to that application.

        Expiration is filtered at the database level so that expired
        assignments are never returned as active.
        """

        now = timezone.now()

        queryset = (
            self.filter(
                user=user,
                is_active=True,
                revoked_at__isnull=True,
            )
            .filter(
                Q(expires_at__isnull=True)
                | Q(expires_at__gt=now)
            )
            .select_related("role")
        )

        if app_name:
            queryset = queryset.filter(
                role__app_name=app_name,
            )

        return queryset

    def get_active_roles(
        self,
        user,
        app_name: str | None = None,
    ):
        """
        Alias for get_user_roles().

        Retained for backwards compatibility with existing callers.
        Both methods now return the same result: currently effective
        role assignments (active, not revoked, not expired).
        """

        return self.get_user_roles(
            user=user,
            app_name=app_name,
        )

    def get_pending_verification_roles(
        self,
        user=None,
        app_name: str | None = None,
    ):
        """
        Return role assignments awaiting role-specific verification.

        This is NOT account verification and is NOT face verification.
        """

        queryset = (
            self.filter(
                is_active=False,
                revoked_at__isnull=True,
                role__requires_verification=True,
                verified_at__isnull=True,
            )
            .select_related(
                "user",
                "role",
            )
        )

        if user is not None:
            queryset = queryset.filter(
                user=user,
            )

        if app_name:
            queryset = queryset.filter(
                role__app_name=app_name,
            )

        return queryset


class UserRoleManager(models.Manager.from_queryset(UserRoleQuerySet)):
    """
    Manager for UserRole.

    Exposes the domain's role-assignment query API through
    UserRole.objects.
    """

    pass


# =============================================================================
# USER ROLE
# =============================================================================


class UserRole(models.Model):
    """
    Persistent assignment of an application Role to a User.

    This model owns the lifecycle of the assignment.

    It does NOT decide:

        - which roles should exist
        - which roles should automatically be assigned
        - how face verification works
        - how real-estate verification works
        - how banking KYC works

    Those responsibilities belong to their respective domains.

    Verification fields here represent verification of the ROLE
    ASSIGNMENT, not generic identity verification.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_roles",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_roles",
    )

    notes = models.TextField(
        blank=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revoked_roles",
    )

    objects = UserRoleManager()

    class Meta:
        ordering = [
            "-created_at",
        ]

        verbose_name = "User Application Role"
        verbose_name_plural = "User Application Roles"

        constraints = [
            # One assignment per user/role combination.
            models.UniqueConstraint(
                fields=[
                    "user",
                    "role",
                ],
                name="accounts_userrole_user_role_unique",
            ),

            # An assignment cannot be simultaneously revoked and active.
            models.CheckConstraint(
                condition=Q(
                    is_active=False,
                )
                | Q(
                    revoked_at__isnull=True,
                ),
                name="accounts_userrole_active_not_revoked",
            ),

            # A revoked assignment must have a revocation timestamp.
            models.CheckConstraint(
                condition=Q(
                    revoked_at__isnull=True,
                )
                | Q(
                    is_active=False,
                ),
                name="accounts_userrole_revoked_inactive",
            ),

            # Verification timestamps must be logically paired.
            models.CheckConstraint(
                condition=(
                    Q(verified_at__isnull=True)
                    & Q(verified_by__isnull=True)
                )
                | (
                    Q(verified_at__isnull=False)
                    & Q(verified_by__isnull=False)
                ),
                name="accounts_userrole_verification_pair",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_active",
                ],
                name="acc_role_user_active_idx",
            ),
            models.Index(
                fields=[
                    "role",
                    "is_active",
                ],
                name="accounts_role_role_act_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "role",
                    "is_active",
                ],
                name="accounts_userrole_lookup_idx",
            ),
        ]

    # =========================================================================
    # QUERYSET DELEGATES
    # =========================================================================
    #
    # The canonical implementations live on UserRoleQuerySet. These
    # classmethods exist so that both call styles work:
    #
    #     UserRole.get_user_roles(user)
    #     UserRole.objects.get_user_roles(user)
    #
    # Both return the same queryset. There is exactly one definition
    # of "effective" and it lives in the queryset.

    @classmethod
    def get_user_roles(
        cls,
        user,
        app_name=None,
    ):
        """
        Return currently effective role assignments for a user.

        Delegates to UserRoleQuerySet.get_user_roles().
        """

        return cls.objects.get_user_roles(
            user=user,
            app_name=app_name,
        )

    @classmethod
    def get_active_roles(
        cls,
        user,
        app_name=None,
    ):
        """
        Alias for get_user_roles().

        Delegates to UserRoleQuerySet.get_active_roles().
        """

        return cls.objects.get_active_roles(
            user=user,
            app_name=app_name,
        )

    @classmethod
    def get_pending_verification_roles(
        cls,
        user=None,
        app_name=None,
    ):
        """
        Return role assignments awaiting role-specific verification.

        Delegates to UserRoleQuerySet.get_pending_verification_roles().
        """

        return cls.objects.get_pending_verification_roles(
            user=user,
            app_name=app_name,
        )

    def __str__(self) -> str:
        user_identifier = (
            getattr(self.user, "email", None)
            or getattr(self.user, "phone_number", None)
            or str(self.user.pk)
        )

        return (
            f"{user_identifier} - {self.role}"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def clean(self):
        """
        Validate the role assignment.

        IMPORTANT:

        We intentionally do NOT use a database constraint such as:

            role__requires_verification

        Django does not permit relational joins inside database
        CheckConstraint expressions.

        The Role relationship is therefore validated here in Python.

        NOTE: Django's ORM does not call clean() automatically on
        save(). Callers that write UserRole rows outside of
        UserRole.activate() must either call full_clean() explicitly
        or route through a mutation layer that enforces the same
        invariants (see RoleMutationMixin.build_user_role_defaults).
        """

        super().clean()

        if self.role_id:
            role = self.role

            # A role requiring verification cannot be active without
            # a completed role verification.
            if (
                role.requires_verification
                and self.is_active
                and not self.verified_at
            ):
                raise ValidationError(
                    {
                        "is_active": (
                            "This role requires verification "
                            "before activation."
                        ),
                    }
                )

            if (
                role.requires_verification
                and self.is_active
                and not self.verified_by_id
            ):
                raise ValidationError(
                    {
                        "verified_by": (
                            "A verified_by user is required "
                            "when this role is activated."
                        ),
                    }
                )

        # A revoked assignment cannot remain active.
        if self.revoked_at and self.is_active:
            raise ValidationError(
                {
                    "is_active": (
                        "A revoked role assignment cannot be active."
                    ),
                }
            )

        # Verification fields must be paired.
        if bool(self.verified_at) != bool(self.verified_by_id):
            raise ValidationError(
                {
                    "verified_at": (
                        "verified_at and verified_by must "
                        "be provided together."
                    ),
                }
            )

    # =========================================================================
    # STATE PROPERTIES
    # =========================================================================

    @property
    def is_expired(self) -> bool:
        """
        Return whether this assignment has expired.
        """

        return bool(
            self.expires_at
            and self.expires_at <= timezone.now()
        )

    @property
    def is_revoked(self) -> bool:
        """
        Return whether this assignment has been revoked.
        """

        return self.revoked_at is not None

    @property
    def is_verified(self) -> bool:
        """
        Return whether this role assignment has been verified.
        """

        return bool(
            self.verified_at
            and self.verified_by_id
        )

    @property
    def effective_active(self) -> bool:
        """
        Return whether the role is currently usable.

        This is more authoritative than is_active alone because an
        assignment can be active but expired.
        """

        if not self.is_active:
            return False

        if self.is_revoked:
            return False

        if self.is_expired:
            return False

        return True

    # =========================================================================
    # LIFECYCLE METHODS
    # =========================================================================

    def activate(
        self,
        verified_by=None,
    ):
        """
        Activate the role assignment.

        For roles requiring verification, verified_by is mandatory.

        This method intentionally does not perform face verification.

        If an application requires face verification, that application
        must complete its own verification workflow first and then call
        the appropriate role-verification service/mutation.
        """

        role = self.role

        if role.requires_verification and verified_by is None:
            raise ValidationError(
                (
                    f"Role '{role.name}' requires verification "
                    "before activation."
                )
            )

        self.is_active = True

        if verified_by is not None:
            self.verified_by = verified_by
            self.verified_at = timezone.now()

        self.revoked_at = None
        self.revoked_by = None

        self.full_clean(
            exclude=None,
        )

        self.save(
            update_fields=[
                "is_active",
                "verified_by",
                "verified_at",
                "revoked_at",
                "revoked_by",
            ]
        )

    def deactivate(self):
        """
        Temporarily deactivate the role assignment.

        Deactivation does not erase verification history.
        """

        if not self.is_active:
            return

        self.is_active = False

        self.save(
            update_fields=[
                "is_active",
            ]
        )

    def revoke(
        self,
        by_user=None,
    ):
        """
        Permanently record revocation of this assignment.

        Revocation makes the assignment inactive and records who
        performed the revocation.
        """

        now = timezone.now()

        self.is_active = False
        self.revoked_at = now
        self.revoked_by = by_user

        self.save(
            update_fields=[
                "is_active",
                "revoked_at",
                "revoked_by",
            ]
        )

    def clear_verification(self):
        """
        Clear verification state.

        This is useful when an application-specific verification
        process has been invalidated and the role must return to a
        pending state.
        """

        self.verified_at = None
        self.verified_by = None

        if self.role.requires_verification:
            self.is_active = False

        self.save(
            update_fields=[
                "verified_at",
                "verified_by",
                "is_active",
            ]
        )