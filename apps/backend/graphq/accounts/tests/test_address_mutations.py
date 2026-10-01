# apps/backend/graphq/accounts/tests/test_address_mutations.py

"""
Tests for GraphQL address mutations.

These tests invoke Graphene mutations directly while still exercising
the canonical Univa JWT authentication boundary.

The mutation receives a real GraphQLResolveInfo object whose context
represents a request that has already passed through the JWT middleware.

Address tests are intentionally country-neutral.

The suite verifies that:

    - Nigerian addresses work.
    - International addresses work.
    - State/province/region values are not restricted to Nigeria.
    - Country codes are validated.
    - Address ownership is enforced.
    - Default-address rules are enforced.
    - Bulk mutations accept direct-test dictionaries.
"""

from __future__ import annotations

from types import SimpleNamespace

from django.test import TestCase
from graphql import GraphQLError, GraphQLResolveInfo
from graphql_relay import to_global_id

from accounts.models import User
from accounts.models.address import Address

from graphq.accounts.mutations.address import (
    AddressMutation,
    UpdateAddressMutation,
    DeleteAddressMutation,
    SetDefaultAddressMutation,
    BulkUpdateAddressesMutation,
)


# =============================================================================
# GRAPHQL TEST HELPERS
# =============================================================================


def make_context(user):
    """
    Build a request-like object representing an already-authenticated
    GraphQL request.
    """

    return SimpleNamespace(
        user=user,
        FILES={},
        META={
            "REMOTE_ADDR": "127.0.0.1",
        },

        # ------------------------------------------------------------------
        # Canonical Univa JWT middleware state.
        # ------------------------------------------------------------------

        univa_jwt_authenticated=True,
        _univa_jwt_authentication_complete=True,

        jwt_claims=None,
        univa_jwt=None,
        univa_jwt_user_id=getattr(
            user,
            "pk",
            None,
        ),
        univa_jwt_jti=None,
        univa_jwt_token_type="access",
        univa_jwt_issued_at=None,
        univa_jwt_expires_at=None,
        univa_jwt_issuer=None,
        univa_jwt_audience=None,
    )


def make_info(context):
    """
    Construct a graphql-core 3.x compatible GraphQLResolveInfo.

    Graphene 3 resolver/mutation signatures are:

        resolver(root, info, **kwargs)

    Therefore the authentication decorator must receive the
    GraphQL resolve-info object.
    """

    return GraphQLResolveInfo(
        field_name="testMutation",
        field_nodes=(),
        return_type=None,
        parent_type=None,
        path=None,
        schema=None,
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        context=context,
        is_awaitable=False,
    )


def make_mutation_info(user):
    """
    Build a complete authenticated GraphQLResolveInfo object.
    """

    return make_info(
        make_context(user),
    )


# =============================================================================
# SHARED TEST CASE
# =============================================================================


class AddressMutationTestCase(TestCase):
    """
    Shared authenticated-user fixture for address mutation tests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="address-test@example.com",
            password="TestPassword123!",
        )

        update_fields = []

        if hasattr(
            self.user,
            "email_verified",
        ):
            self.user.email_verified = True
            update_fields.append(
                "email_verified",
            )

        if (
            hasattr(
                self.user,
                "is_active",
            )
            and not self.user.is_active
        ):
            self.user.is_active = True
            update_fields.append(
                "is_active",
            )

        if update_fields:
            self.user.save(
                update_fields=update_fields,
            )

        self.context = make_context(
            self.user,
        )

        self.info = make_mutation_info(
            self.user,
        )

    def create_address(
        self,
        *,
        address_type="home",
        is_default=False,
        street="1 Test Street",
        city="Lagos",
        state="Lagos",
        country="NG",
    ):
        """
        Create a test address.

        The state argument is intentionally free-form.
        """

        return Address.objects.create(
            user=self.user,
            street_address_1=street,
            city=city,
            state=state,
            postal_code="100001",
            country=country,
            address_type=address_type,
            is_default=is_default,
        )


# =============================================================================
# CREATE
# =============================================================================


class AddressCreateMutationTests(
    AddressMutationTestCase,
):

    def test_creates_address(self):
        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="10 Admiralty Way",
                city="Lagos",
                state="Lagos",
                postal_code="101233",
                country="NG",
                address_type="home",
                is_default=False,
            )
        )

        self.assertIsNotNone(
            result.address,
        )

        address = result.address

        self.assertEqual(
            address.street_address_1,
            "10 Admiralty Way",
        )

        self.assertEqual(
            address.city,
            "Lagos",
        )

        self.assertEqual(
            address.state,
            "Lagos",
        )

        self.assertEqual(
            address.country,
            "NG",
        )

    def test_creates_international_address(self):
        """
        Address must not be restricted to Nigerian states.
        """

        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="123 Market Street",
                city="San Francisco",
                state="California",
                postal_code="94105",
                country="US",
                address_type="home",
                is_default=False,
            )
        )

        address = result.address

        self.assertEqual(
            address.country,
            "US",
        )

        self.assertEqual(
            address.state,
            "California",
        )

        self.assertEqual(
            address.state_name,
            "California",
        )

    def test_creates_canadian_address(self):
        """
        Province-style administrative divisions must work.
        """

        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="100 King Street",
                city="Toronto",
                state="Ontario",
                postal_code="M5H 1J9",
                country="CA",
                address_type="home",
            )
        )

        address = result.address

        self.assertEqual(
            address.country,
            "CA",
        )

        self.assertEqual(
            address.state,
            "Ontario",
        )

    def test_creates_address_without_state(self):
        """
        State/province is not universally required.
        """

        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="1 Example Street",
                city="Singapore",
                state="",
                postal_code="018989",
                country="SG",
                address_type="home",
            )
        )

        address = result.address

        self.assertEqual(
            address.country,
            "SG",
        )

        self.assertEqual(
            address.state,
            "",
        )

    def test_rejects_invalid_country_code(self):
        with self.assertRaises(
            GraphQLError,
        ) as exc:
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="10 Test Street",
                city="Lagos",
                state="Lagos",
                country="NGA",
                address_type="home",
            )

        self.assertIn(
            "Invalid country code",
            str(exc.exception),
        )

    def test_accepts_non_nigerian_state_value(self):
        """
        A non-Nigerian administrative division must not be rejected.
        """

        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="221B Baker Street",
                city="London",
                state="England",
                country="GB",
                address_type="home",
            )
        )

        self.assertEqual(
            result.address.state,
            "England",
        )

    def test_new_default_address_clears_previous_default(self):
        old_address = self.create_address(
            address_type="home",
            is_default=True,
        )

        result = (
            AddressMutation.mutate_and_get_payload(
                None,
                self.info,
                street_address_1="20 New Street",
                city="Lagos",
                state="Lagos",
                country="NG",
                address_type="home",
                is_default=True,
            )
        )

        old_address.refresh_from_db()

        self.assertFalse(
            old_address.is_default,
        )

        self.assertTrue(
            result.address.is_default,
        )


# =============================================================================
# UPDATE
# =============================================================================


class AddressUpdateMutationTests(
    AddressMutationTestCase,
):

    def test_updates_owned_address(self):
        address = self.create_address()

        result = (
            UpdateAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
                city="Abuja",
                state="Federal Capital Territory",
                street_address_1="Updated Street",
            )
        )

        address.refresh_from_db()

        self.assertEqual(
            address.city,
            "Abuja",
        )

        self.assertEqual(
            address.state,
            "Federal Capital Territory",
        )

        self.assertEqual(
            address.street_address_1,
            "Updated Street",
        )

        self.assertEqual(
            result.address.pk,
            address.pk,
        )

    def test_updates_to_international_address(self):
        address = self.create_address(
            city="Lagos",
            state="Lagos",
            country="NG",
        )

        result = (
            UpdateAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
                city="Los Angeles",
                state="California",
                country="US",
            )
        )

        address.refresh_from_db()

        self.assertEqual(
            address.city,
            "Los Angeles",
        )

        self.assertEqual(
            address.state,
            "California",
        )

        self.assertEqual(
            address.country,
            "US",
        )

        self.assertEqual(
            result.address.pk,
            address.pk,
        )

    def test_cannot_update_another_users_address(self):
        other_user = User.objects.create_user(
            email="other-address@example.com",
            password="TestPassword123!",
        )

        address = Address.objects.create(
            user=other_user,
            street_address_1="Private Street",
            city="Lagos",
            state="Lagos",
            country="NG",
            address_type="home",
        )

        with self.assertRaises(
            GraphQLError,
        ) as exc:
            UpdateAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
                city="Hacked",
            )

        self.assertEqual(
            str(exc.exception),
            "Address not found or permission denied",
        )

    def test_rejects_invalid_country(self):
        address = self.create_address()

        with self.assertRaises(
            GraphQLError,
        ) as exc:
            UpdateAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
                country="NGA",
            )

        self.assertIn(
            "Invalid country code",
            str(exc.exception),
        )

    def test_allows_free_form_state_update(self):
        address = self.create_address()

        UpdateAddressMutation.mutate_and_get_payload(
            None,
            self.info,
            address_id=to_global_id(
                "Address",
                address.pk,
            ),
            state="Bavaria",
            country="DE",
        )

        address.refresh_from_db()

        self.assertEqual(
            address.state,
            "Bavaria",
        )

        self.assertEqual(
            address.country,
            "DE",
        )


# =============================================================================
# DELETE
# =============================================================================


class AddressDeleteMutationTests(
    AddressMutationTestCase,
):

    def test_deletes_owned_address(self):
        address = self.create_address()

        result = (
            DeleteAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
            )
        )

        self.assertTrue(
            result.success,
        )

        self.assertFalse(
            Address.objects.filter(
                pk=address.pk,
            ).exists(),
        )

    def test_cannot_delete_another_users_address(self):
        other_user = User.objects.create_user(
            email="delete-other@example.com",
            password="TestPassword123!",
        )

        address = Address.objects.create(
            user=other_user,
            street_address_1="Protected Street",
            city="Lagos",
            state="Lagos",
            country="NG",
            address_type="home",
        )

        with self.assertRaises(
            GraphQLError,
        ):
            DeleteAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    address.pk,
                ),
            )


# =============================================================================
# DEFAULT
# =============================================================================


class SetDefaultAddressMutationTests(
    AddressMutationTestCase,
):

    def test_sets_address_as_default(self):
        first = self.create_address(
            is_default=True,
        )

        second = self.create_address(
            street="Second Street",
        )

        result = (
            SetDefaultAddressMutation.mutate_and_get_payload(
                None,
                self.info,
                address_id=to_global_id(
                    "Address",
                    second.pk,
                ),
            )
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(
            first.is_default,
        )

        self.assertTrue(
            second.is_default,
        )

        self.assertEqual(
            result.address.pk,
            second.pk,
        )

    def test_default_is_scoped_to_address_type(self):
        home = self.create_address(
            address_type="home",
            is_default=True,
        )

        work = self.create_address(
            address_type="work",
            is_default=True,
            street="Work Street",
        )

        shipping = self.create_address(
            address_type="shipping",
            is_default=False,
            street="Shipping Street",
        )

        SetDefaultAddressMutation.mutate_and_get_payload(
            None,
            self.info,
            address_id=to_global_id(
                "Address",
                shipping.pk,
            ),
        )

        home.refresh_from_db()
        work.refresh_from_db()
        shipping.refresh_from_db()

        self.assertTrue(
            home.is_default,
        )

        self.assertTrue(
            work.is_default,
        )

        self.assertTrue(
            shipping.is_default,
        )


# =============================================================================
# BULK UPDATE
# =============================================================================


class BulkUpdateAddressMutationTests(
    AddressMutationTestCase,
):

    def test_bulk_updates_addresses(self):
        first = self.create_address(
            street="First Street",
        )

        second = self.create_address(
            street="Second Street",
            address_type="work",
        )

        result = (
            BulkUpdateAddressesMutation.mutate_and_get_payload(
                None,
                self.info,
                updates=[
                    {
                        "address_id": to_global_id(
                            "Address",
                            first.pk,
                        ),
                        "city": "Abuja",
                    },
                    {
                        "address_id": to_global_id(
                            "Address",
                            second.pk,
                        ),
                        "city": "Ibadan",
                    },
                ],
            )
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(
            first.city,
            "Abuja",
        )

        self.assertEqual(
            second.city,
            "Ibadan",
        )

        self.assertEqual(
            result.updated_count,
            2,
        )

    def test_bulk_update_accepts_international_states(self):
        first = self.create_address(
            street="First Street",
        )

        second = self.create_address(
            street="Second Street",
            address_type="work",
        )

        result = (
            BulkUpdateAddressesMutation.mutate_and_get_payload(
                None,
                self.info,
                updates=[
                    {
                        "address_id": to_global_id(
                            "Address",
                            first.pk,
                        ),
                        "city": "Toronto",
                        "state": "Ontario",
                        "country": "CA",
                    },
                    {
                        "address_id": to_global_id(
                            "Address",
                            second.pk,
                        ),
                        "city": "Munich",
                        "state": "Bavaria",
                        "country": "DE",
                    },
                ],
            )
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(
            first.city,
            "Toronto",
        )

        self.assertEqual(
            first.state,
            "Ontario",
        )

        self.assertEqual(
            first.country,
            "CA",
        )

        self.assertEqual(
            second.city,
            "Munich",
        )

        self.assertEqual(
            second.state,
            "Bavaria",
        )

        self.assertEqual(
            second.country,
            "DE",
        )

        self.assertEqual(
            result.updated_count,
            2,
        )

    def test_bulk_update_rejects_invalid_country(self):
        address = self.create_address()

        with self.assertRaises(
            GraphQLError,
        ):
            BulkUpdateAddressesMutation.mutate_and_get_payload(
                None,
                self.info,
                updates=[
                    {
                        "address_id": to_global_id(
                            "Address",
                            address.pk,
                        ),
                        "country": "NGA",
                    },
                ],
            )
