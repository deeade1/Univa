"""
Canonical PaymentInstrument model for Univa.

A PaymentInstrument represents a financial instrument registered by
a party and authorized for payment use.

It does NOT store:

    - card PAN
    - CVV
    - PIN
    - bank password
    - OTP
    - provider credentials

Only normalized references/tokens and safe display information belong here.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentInstrument(models.Model):
    class InstrumentType(models.TextChoices):
        BANK_ACCOUNT = "bank_account", _("Bank Account")
        CARD = "card", _("Card")
        WALLET = "wallet", _("Wallet")
        ACCOUNT = "account", _("Account")
        OTHER = "other", _("Other")

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", _("Unverified")
        VERIFICATION_REQUIRED = (
            "verification_required",
            _("Verification Required"),
        )
        VERIFIED = "verified", _("Verified")
        FAILED = "failed", _("Failed")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        BLOCKED = "blocked", _("Blocked")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    reference = models.CharField(
        max_length=50,
        unique=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_instruments",
    )

    instrument_type = models.CharField(
        max_length=30,
        choices=InstrumentType.choices,
    )

    # Normalized institution/provider identifier.
    institution = models.CharField(
        max_length=100,
    )

    can_fund = models.BooleanField(
        default=False,
    )

    can_receive = models.BooleanField(
        default=False,
    )

    # Secure token/reference supplied or created by
    # the integration layer.
    secure_reference = models.CharField(
        max_length=255,
    )

    # Safe human-readable representation, e.g. ****1234.
    display_reference = models.CharField(
        max_length=100,
    )

    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )

    verification_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    blocked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expired_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "payment_canonical"
        db_table = "payment_canonical_instrument"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "owner",
                    "institution",
                    "secure_reference",
                ],
                name="payment_instrument_owner_institution_ref_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "owner",
                    "status",
                ],
                name="pay_instr_owner_status_idx",
            ),
            models.Index(
                fields=[
                    "owner",
                    "instrument_type",
                ],
                name="pay_instr_owner_type_idx",
            ),
            models.Index(
                fields=["institution"],
                name="pay_instr_institution_idx",
            ),
            models.Index(
                fields=["status"],
                name="pay_instr_status_idx",
            ),
        ]

    def __str__(self):
        return self.reference

    def clean(self):
        errors = {}

        # ---------------------------------------------------------
        # Institution
        # ---------------------------------------------------------
        if not self.institution:
            errors["institution"] = _(
                "Institution is required."
            )

        # ---------------------------------------------------------
        # Secure reference
        # ---------------------------------------------------------
        if not self.secure_reference:
            errors["secure_reference"] = _(
                "Secure reference is required."
            )

        # ---------------------------------------------------------
        # Display reference
        # ---------------------------------------------------------
        if not self.display_reference:
            errors["display_reference"] = _(
                "Display reference is required."
            )

        # ---------------------------------------------------------
        # Instrument capabilities
        # ---------------------------------------------------------
        if not self.can_fund and not self.can_receive:
            errors["can_fund"] = _(
                "An instrument must support funding, receiving, "
                "or both."
            )

        # ---------------------------------------------------------
        # Verification
        # ---------------------------------------------------------
        if (
            self.verification_status
            == self.VerificationStatus.VERIFIED
            and self.verified_at is None
        ):
            errors["verified_at"] = _(
                "Verified instruments must have a verification timestamp."
            )

        # ---------------------------------------------------------
        # Active instrument
        # ---------------------------------------------------------
        if self.status == self.Status.ACTIVE:
            if (
                self.verification_status
                != self.VerificationStatus.VERIFIED
            ):
                errors["status"] = _(
                    "An active instrument must be verified."
                )

            if self.activated_at is None:
                errors["activated_at"] = _(
                    "Active instruments must have an activation timestamp."
                )

        if errors:
            raise ValidationError(errors)

        # ---------------------------------------------------------
        # Instrument identity immutability
        # ---------------------------------------------------------
        if not self._state.adding and self.pk:
            previous = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "owner_id",
                    "instrument_type",
                    "institution",
                    "secure_reference",
                )
                .first()
            )

            if previous:
                immutable_fields = (
                    "owner_id",
                    "instrument_type",
                    "institution",
                    "secure_reference",
                )

                for field in immutable_fields:
                    current_value = getattr(self, field)
                    previous_value = previous[field]

                    if current_value != previous_value:
                        errors[field] = _(
                            "Instrument identity cannot be changed. "
                            "Register a new instrument instead."
                        )

        if errors:
            raise ValidationError(errors)

    # -------------------------------------------------------------
    # State helpers
    # -------------------------------------------------------------

    @property
    def is_verified(self):
        return (
            self.verification_status
            == self.VerificationStatus.VERIFIED
        )

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_blocked(self):
        return self.status == self.Status.BLOCKED

    @property
    def is_expired(self):
        return self.status == self.Status.EXPIRED

    @property
    def can_be_used(self):
        return (
            self.status == self.Status.ACTIVE
            and self.verification_status
            == self.VerificationStatus.VERIFIED
        )