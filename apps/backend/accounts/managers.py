# apps/backend/accounts/managers.py

"""
User manager for the centralized Univa identity system.

The manager is intentionally domain-agnostic.

It is responsible for:
    - creating users
    - creating superusers
    - normalizing identity credentials
    - basic identity querysets

It is NOT responsible for:
    - roles
    - permissions
    - ecommerce
    - transport
    - real estate
    - banking
    - loyalty
    - biometrics
    - account provisioning
"""

from django.contrib.auth.models import BaseUserManager
from django.db import transaction
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Manager for the centralized Univa User model.
    """

    use_in_migrations = True

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_user(
        self,
        email=None,
        phone_number=None,
        password=None,
        **extra_fields,
    ):
        """
        Create and persist a regular user.

        Email and phone are both supported as identity credentials.

        A password is optional because Univa supports passwordless
        authentication flows such as OTP and magic links.
        """

        if not email and not phone_number:
            raise ValueError(
                _("Either email or phone number must be provided.")
            )

        if email:
            email = self.normalize_email(email)

        with transaction.atomic():
            user = self.model(
                email=email,
                phone_number=phone_number,
                **extra_fields,
            )

            if password is not None:
                user.set_password(password)
            else:
                user.set_unusable_password()

            user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        password=None,
        **extra_fields,
    ):
        """
        Create a Django administrative superuser.

        Role assignment deliberately does NOT happen here.

        Django administration is controlled by:
            is_staff
            is_superuser
        """

        if not email:
            raise ValueError(
                _("Superuser must have an email address.")
            )

        if not password:
            raise ValueError(
                _("Superuser must have a password.")
            )

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError(
                _("Superuser must have is_staff=True.")
            )

        if extra_fields["is_superuser"] is not True:
            raise ValueError(
                _("Superuser must have is_superuser=True.")
            )

        return self.create_user(
            email=email,
            password=password,
            **extra_fields,
        )

    # ------------------------------------------------------------------
    # Generic identity querysets
    # ------------------------------------------------------------------

    def active(self):
        """
        Return active users.
        """
        return self.get_queryset().filter(
            is_active=True,
        )

    def inactive(self):
        """
        Return inactive users.
        """
        return self.get_queryset().filter(
            is_active=False,
        )

    def staff(self):
        """
        Return Django staff users.
        """
        return self.get_queryset().filter(
            is_staff=True,
        )

    def non_staff(self):
        """
        Return non-staff users.
        """
        return self.get_queryset().filter(
            is_staff=False,
        )