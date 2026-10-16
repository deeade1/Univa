"""
Investor domain services.

This module contains the application/domain operations for Investor.

Architectural boundary
----------------------

InvestorService is responsible for:

    - creating Investor records
    - updating investor profile data
    - activating investors
    - suspending investors
    - closing investors

The service does NOT own:

    - GraphQL concerns
    - HTTP concerns
    - audit persistence
    - notification delivery
    - payment processing
    - investment calculations
    - lifecycle transition policy

Lifecycle-specific transition rules should remain in the Investor lifecycle
layer and be introduced separately.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from investors.models import Investor


User = get_user_model()


class InvestorService:
    """
    Canonical service for Investor domain operations.
    """

    @staticmethod
    def _validate_user(user):
        if user is None:
            raise ValidationError({"user": "User is required."})

        if not isinstance(user, User):
            raise ValidationError({"user": "A valid user is required."})

    @staticmethod
    def _validate_reference(reference):
        if not reference:
            raise ValidationError({"reference": "Reference is required."})

    @staticmethod
    @transaction.atomic
    def create(
        *,
        user,
        reference,
        display_name="",
        metadata=None,
        status=Investor.Status.PENDING,
    ):
        """
        Create an Investor profile for a user.
        """
        InvestorService._validate_user(user)
        InvestorService._validate_reference(reference)

        if Investor.objects.filter(user=user).exists():
            raise ValidationError(
                {"user": "An investor profile already exists for this user."}
            )

        if metadata is None:
            metadata = {}

        investor = Investor(
            user=user,
            reference=reference,
            display_name=display_name,
            metadata=metadata,
            status=status,
        )

        investor.full_clean()
        investor.save()

        return investor

    @staticmethod
    @transaction.atomic
    def update(
        investor,
        *,
        reference=None,
        display_name=None,
        metadata=None,
    ):
        """
        Update mutable investor profile fields.

        None means that the corresponding field should remain unchanged.
        """
        if investor is None:
            raise ValidationError({"investor": "Investor is required."})

        if reference is not None:
            investor.reference = reference

        if display_name is not None:
            investor.display_name = display_name

        if metadata is not None:
            investor.metadata = metadata

        investor.full_clean()
        investor.save()

        return investor

    @staticmethod
    @transaction.atomic
    def activate(investor):
        """
        Activate an investor.
        """
        if investor is None:
            raise ValidationError({"investor": "Investor is required."})

        investor.status = Investor.Status.ACTIVE
        investor.full_clean()
        investor.save(update_fields=["status", "updated_at"])

        return investor

    @staticmethod
    @transaction.atomic
    def suspend(investor):
        """
        Suspend an investor.
        """
        if investor is None:
            raise ValidationError({"investor": "Investor is required."})

        investor.status = Investor.Status.SUSPENDED
        investor.full_clean()
        investor.save(update_fields=["status", "updated_at"])

        return investor

    @staticmethod
    @transaction.atomic
    def close(investor):
        """
        Close an investor.
        """
        if investor is None:
            raise ValidationError({"investor": "Investor is required."})

        investor.status = Investor.Status.CLOSED
        investor.full_clean()
        investor.save(update_fields=["status", "updated_at"])

        return investor