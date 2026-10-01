"""
Centralized Univa User model.
"""

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from core.models.metadata import (
    ModelWithExternalReference,
    ModelWithMetadata,
)

from accounts.managers import UserManager
from accounts.validators.phone import PossiblePhoneNumberField


class User(
    ModelWithMetadata,
    AbstractUser,
    ModelWithExternalReference,
):
    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
    )

    phone_number = PossiblePhoneNumberField(
        blank=True,
        null=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------

    email_verified = models.BooleanField(
        default=False,
        db_index=True,
    )

    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    username = None

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ("email",)
        indexes = [
            models.Index(
                fields=["email"],
                name="user_email_idx",
            ),
            GinIndex(
                fields=[
                    "first_name",
                    "last_name",
                ],
                name="user_name_search_gin",
                opclasses=[
                    "gin_trgm_ops",
                    "gin_trgm_ops",
                ],
            ),
        ]

    def __str__(self):
        return self.email or str(self.phone_number)

    # ------------------------------------------------------------------
    # Email Helpers
    # ------------------------------------------------------------------

    @property
    def is_email_verified(self):
        """
        Backward-compatible alias.
        """
        return self.email_verified

    def verify_email(self):
        """
        Mark email as verified.
        """
        if not self.email_verified:
            self.email_verified = True
            self.email_verified_at = timezone.now()

            self.save(
                update_fields=[
                    "email_verified",
                    "email_verified_at",
                ]
            )

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    #
    # IMPORTANT
    # ---------
    #
    # The methods below express two distinct concepts:
    #
    #   1. Capability checks — does this user hold an elevated role?
    #      (is_driver, is_agent, is_vendor, has_role)
    #
    #   2. Application-role checks — does this user hold *any* role
    #      within a given application namespace?
    #      (get_app_roles, can_access_app)
    #
    # Neither of these is a generic "can this authenticated user use
    # the platform" check. Normal platform features (browse, buy,
    # request a ride, chat) do not require a UserRole.
    #
    # All role-lookup methods use the same definition of "effective":
    #
    #     is_active=True
    #     revoked_at IS NULL
    #     expires_at IS NULL OR expires_at > now
    #
    # Do not re-implement these filters inline. Delegate to
    # UserRoleQuerySet.get_user_roles() where possible.
    # ------------------------------------------------------------------

    @cached_property
    def active_roles(self):
        """
        Return the set of currently effective (app_name, role_name)
        pairs held by this user.

        Cached on the instance for the lifetime of that instance.

        WARNING:
            If you mutate a UserRole for this user and then re-check
            this property on the same User instance, the cached set
            will be stale. Re-fetch the User instance or clear the
            cache with `user.__dict__.pop("active_roles", None)`.
        """

        now = timezone.now()

        return set(
            self.user_roles
            .filter(
                is_active=True,
                revoked_at__isnull=True,
            )
            .filter(
                models.Q(expires_at__isnull=True)
                | models.Q(expires_at__gt=now)
            )
            .values_list(
                "role__app_name",
                "role__name",
            )
        )

    def has_role(
        self,
        app,
        role_name,
    ):
        """
        Return whether this user currently holds the specified role.
        """

        return (
            app,
            role_name,
        ) in self.active_roles

    @property
    def is_driver(self):
        return self.has_role(
            "transport",
            "driver",
        )

    @property
    def is_agent(self):
        return self.has_role(
            "realestate",
            "agent",
        )

    @property
    def is_vendor(self):
        return self.has_role(
            "ecommerce",
            "vendor",
        )

    @property
    def is_banker(self):
        return self.has_role(
            "banking",
            "banker",
        )

    @property
    def is_content_creator(self):
        return self.has_role(
            "social",
            "content_creator",
        )

    def get_app_roles(
        self,
        app_name,
    ):
        """
        Return effective role assignments for this user within the
        given application.

        Effective means:

            is_active=True
            revoked_at IS NULL
            expires_at IS NULL OR expires_at > now
        """

        return (
            self.user_roles
            .filter(
                is_active=True,
                revoked_at__isnull=True,
                role__app_name=app_name,
            )
            .filter(
                models.Q(expires_at__isnull=True)
                | models.Q(expires_at__gt=timezone.now())
            )
            .select_related("role")
        )

    def can_access_app(
        self,
        app_name,
    ):
        """
        Return whether this user holds any effective role within the
        given application.

        SEMANTICS:

            This is a role-capability check, not a platform-access
            check. An ordinary user with no roles in an application
            will receive False here even though they may still use
            the platform's public features (browse, buy, request a
            ride, chat).

            If the intent is "is this user allowed to use the app at
            all", that is a policy question answered elsewhere, not
            by UserRole ownership.
        """

        return self.get_app_roles(app_name).exists()
    
