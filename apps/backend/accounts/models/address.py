# apps/backend/accounts/models/address.py

"""
Account Address Model.

Architectural boundary
----------------------

Address belongs to the accounts domain because it represents:

    - user contact information
    - postal/location information
    - billing/shipping identity information
    - account-level address visibility

This model must remain independent of feature applications such as:

    - ecommerce
    - transport
    - realestate
    - banking
    - social
    - loyalty
    - notifications
    - biometrics

Feature applications may reference Address, but Address must not
reference those applications.

IMPORTANT
---------

Address is intentionally country-neutral.

The model MUST NOT contain country-specific state/province choices.

The ``state`` field represents the first-level administrative
division used by the address's country, for example:

    Nigeria      -> Lagos
    United States -> California
    Canada       -> Ontario
    United Kingdom -> England
    Australia    -> New South Wales
    Germany      -> Bavaria
    France       -> Île-de-France

The country field identifies the country. The state field stores the
country-specific administrative subdivision as free-form text.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from core.models.metadata import ModelWithMetadata

from accounts.models.role import Role, UserRole
from accounts.validators.phone import PossiblePhoneNumberField


# ============================================================================
# Address QuerySet
# ============================================================================


class AddressQuerySet(models.QuerySet):
    """
    QuerySet for account-owned addresses.

    QuerySet methods should remain focused on database querying.

    Business/application decisions belong in services.
    """

    def for_user(self, user):
        """
        Return addresses belonging to a specific user.
        """
        return self.filter(user=user)

    def defaults(self):
        """
        Return default addresses.
        """
        return self.filter(is_default=True)

    def by_type(self, address_type):
        """
        Return addresses of a specific type.
        """
        return self.filter(address_type=address_type)

    def visible_to(self, user):
        """
        Return addresses visible to a user.

        Ownership is always respected.

        The visibility rule itself is implemented by
        Address.is_visible_to().
        """
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()

        if getattr(user, "is_superuser", False):
            return self.all()

        if hasattr(user, "pk"):
            return self.filter(
                models.Q(user=user)
                | models.Q(
                    role_visibility__user_assignments__user=user,
                    role_visibility__user_assignments__is_active=True,
                    role_visibility__user_assignments__revoked_at__isnull=True,
                )
            ).distinct()

        return self.none()

    def annotate_default(self, user):
        """
        Annotate addresses with the user's current default address IDs.

        These annotations are useful for GraphQL consumers that need to
        distinguish default shipping/billing addresses without performing
        additional queries.
        """

        default_shipping_address = getattr(
            user,
            "default_shipping_address",
            None,
        )

        default_billing_address = getattr(
            user,
            "default_billing_address",
            None,
        )

        shipping_pk = (
            default_shipping_address.pk
            if default_shipping_address
            else None
        )

        billing_pk = (
            default_billing_address.pk
            if default_billing_address
            else None
        )

        return self.annotate(
            user_default_shipping_address_pk=models.Value(
                shipping_pk,
                output_field=models.IntegerField(),
            ),
            user_default_billing_address_pk=models.Value(
                billing_pk,
                output_field=models.IntegerField(),
            ),
        )


AddressManager = models.Manager.from_queryset(AddressQuerySet)


# ============================================================================
# Address
# ============================================================================


class Address(ModelWithMetadata):
    """
    Account-owned postal/contact address.

    Address is part of the centralized accounts domain.

    Feature applications may consume addresses but must not own
    or modify the core Address model's domain responsibilities.

    The model is country-neutral and supports addresses worldwide.
    """

    # ------------------------------------------------------------------
    # Address Types
    # ------------------------------------------------------------------

    ADDRESS_TYPES = [
        ("home", _("Home")),
        ("work", _("Work")),
        ("billing", _("Billing")),
        ("shipping", _("Shipping")),
        ("other", _("Other")),
    ]

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES,
        default="home",
        db_index=True,
    )

    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_(
            "Whether this is the user's default address "
            "for this address type."
        ),
    )

    # ------------------------------------------------------------------
    # Role Visibility
    # ------------------------------------------------------------------

    role_visibility = models.ManyToManyField(
        Role,
        blank=True,
        related_name="visible_addresses",
        help_text=_(
            "Application roles that are allowed to view "
            "this address."
        ),
    )

    # ------------------------------------------------------------------
    # Recipient
    # ------------------------------------------------------------------

    first_name = models.CharField(
        max_length=256,
        blank=True,
    )

    last_name = models.CharField(
        max_length=256,
        blank=True,
    )

    company_name = models.CharField(
        max_length=256,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Address Information
    # ------------------------------------------------------------------

    street_address_1 = models.CharField(
        max_length=256,
        blank=True,
    )

    street_address_2 = models.CharField(
        max_length=256,
        blank=True,
    )

    city = models.CharField(
        max_length=256,
        blank=True,
    )

    city_area = models.CharField(
        max_length=128,
        blank=True,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Country-neutral administrative division
    # ------------------------------------------------------------------

    state = models.CharField(
        max_length=256,
        blank=True,
        help_text=_(
            "First-level administrative division for the selected "
            "country, such as state, province, region, territory, "
            "county, or equivalent."
        ),
    )

    country = CountryField(
        default="NG",
    )

    country_area = models.CharField(
        max_length=128,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    phone = PossiblePhoneNumberField(
        blank=True,
        null=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    validation_skipped = models.BooleanField(
        default=False,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ------------------------------------------------------------------
    # Manager
    # ------------------------------------------------------------------

    objects = AddressManager()

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

        ordering = [
            "-is_default",
            "-updated_at",
            "address_type",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "address_type",
                ],
                condition=models.Q(is_default=True),
                name="accounts_one_default_address_per_type",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_default",
                ],
                name="addr_user_default_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "address_type",
                ],
                name="accounts_address_user_type_idx",
            ),
            models.Index(
                fields=[
                    "country",
                    "state",
                ],
                name="addr_country_state_idx",
            ),
            GinIndex(
                fields=[
                    "street_address_1",
                    "city",
                    "country_area",
                ],
                name="accounts_address_search_idx",
                opclasses=[
                    "gin_trgm_ops",
                    "gin_trgm_ops",
                    "gin_trgm_ops",
                ],
            ),
        ]

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self):
        return _(
            "%(address_type)s address for %(user)s"
        ) % {
            "address_type": self.get_address_type_display(),
            "user": self.user,
        }

    # ------------------------------------------------------------------
    # Derived Properties
    # ------------------------------------------------------------------

    @property
    def full_name(self):
        """
        Return the recipient's full name.
        """

        return " ".join(
            part
            for part in [
                self.first_name.strip(),
                self.last_name.strip(),
            ]
            if part
        )

    @property
    def country_name(self):
        """
        Return the human-readable country name.
        """

        return self.country.name if self.country else None

    @property
    def state_name(self):
        """
        Return the stored administrative division.

        This property is intentionally country-neutral.

        The value may represent:

            - state
            - province
            - region
            - territory
            - county
            - prefecture
            - or another first-level administrative division

        The country determines the semantic meaning.
        """

        return self.state or None

    @property
    def address_type_display(self):
        """
        GraphQL/API-friendly address type display value.
        """

        return self.get_address_type_display()

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def is_visible_to(self, user):
        """
        Determine whether a user may view this address.

        Rules:

            1. The owner can always view the address.
            2. Unauthenticated users cannot view it.
            3. Superusers can view it.
            4. Other users require an active role explicitly granted
               through role_visibility.
        """

        if user == self.user:
            return True

        if not user or not getattr(
            user,
            "is_authenticated",
            False,
        ):
            return False

        if getattr(user, "is_superuser", False):
            return True

        requester_role_ids = (
            UserRole.get_user_roles(user)
            .values_list(
                "role_id",
                flat=True,
            )
        )

        return self.role_visibility.filter(
            id__in=requester_role_ids,
        ).exists()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def as_data(self):
        """
        Return address data suitable for creating another Address.

        Ownership and role visibility are intentionally excluded.

        The caller must explicitly provide the destination user.
        """

        data = model_to_dict(
            self,
            exclude=[
                "id",
                "user",
                "role_visibility",
            ],
        )

        country = data.get("country")

        if hasattr(country, "code"):
            data["country"] = country.code

        phone = data.get("phone")

        if (
            hasattr(phone, "as_e164")
            and not self.validation_skipped
        ):
            data["phone"] = phone.as_e164

        return data

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def get_copy(self, *, user=None):
        """
        Create a new Address copied from this address.

        The new address:

            - belongs to the supplied user, or the original owner
            - does not copy role visibility
            - does not automatically become default
        """

        destination_user = user or self.user

        data = self.as_data()

        # A copied address should never unexpectedly become
        # the user's default address.
        data["is_default"] = False

        return Address.objects.create(
            user=destination_user,
            **data,
        )
