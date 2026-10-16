# graphq/ecommerce/tests/test_checkout_claim.py

"""
Tests for checkout claim (guest → user transfer).

Covers the service layer (`claim_checkout`) directly and the
GraphQL surface (`checkoutClaim` mutation).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from graphene.test import Client

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.enums.errors import ClaimErrorCode
from ecommerce.services.checkout.claim import (
    ClaimError,
    claim_checkout,
)


User = get_user_model()


# =====================================================================
# FIXTURES
# =====================================================================


@pytest.fixture
def channel_a(db):
    return Channel.objects.create(
        name="Channel A",
        slug="channel-a",
        currency_code="NGN",
        default_country="NG",
        is_active=True,
    )


@pytest.fixture
def channel_b(db):
    return Channel.objects.create(
        name="Channel B",
        slug="channel-b",
        currency_code="NGN",
        default_country="NG",
        is_active=True,
    )


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        email="a@example.com",
        password="secret",
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        email="b@example.com",
        password="secret",
    )


@pytest.fixture
def variant(db):
    """Minimal ProductVariant for claim tests."""
    from ecommerce.models.product import (
        Product,
        ProductType,
        ProductVariant,
    )

    product_type = ProductType.objects.create(
        name="Physical",
        slug="physical-claim-test",
        kind="normal",
        has_variants=True,
        is_shipping_required=True,
    )
    product = Product.objects.create(
        name="Claim Test Product",
        slug="claim-test-product",
        product_type=product_type,
    )
    return ProductVariant.objects.create(
        sku="CLAIM-TEST-SKU",
        product=product,
        name="Default",
        track_inventory=False,
    )


@pytest.fixture
def variant_b(db, variant):
    """A second variant for merge tests."""
    return variant.__class__.objects.create(
        sku="CLAIM-TEST-SKU-2",
        product=variant.product,
        name="Second",
        track_inventory=False,
    )


def _create_checkout(channel, *, user=None, email=None):
    return Checkout.objects.create(
        channel=channel,
        user=user,
        email=email,
        currency=channel.currency_code,
    )


def _add_line(checkout, variant, quantity):
    return CheckoutLine.objects.create(
        checkout=checkout,
        variant=variant,
        quantity=Decimal(str(quantity)),
        currency=checkout.currency,
        quantity_unit="unit",
    )


# =====================================================================
# SERVICE-LEVEL TESTS
# =====================================================================


class TestClaimCheckoutService:

    def test_claim_transfers_ownership_when_no_existing_cart(
        self, channel_a, user_a, variant,
    ):
        guest = _create_checkout(channel_a)
        _add_line(guest, variant, 2)

        claimed = claim_checkout(guest, user_a)

        assert claimed.pk == guest.pk
        claimed.refresh_from_db()
        assert claimed.user_id == user_a.pk

    def test_claim_is_idempotent_for_same_user(
        self, channel_a, user_a, variant,
    ):
        user_cart = _create_checkout(channel_a, user=user_a)
        _add_line(user_cart, variant, 1)

        result = claim_checkout(user_cart, user_a)

        assert result.pk == user_cart.pk
        assert result.user_id == user_a.pk

    def test_claim_refuses_other_users_cart(
        self, channel_a, user_a, user_b, variant,
    ):
        cart = _create_checkout(channel_a, user=user_a)
        _add_line(cart, variant, 1)

        with pytest.raises(ClaimError) as exc_info:
            claim_checkout(cart, user_b)

        assert exc_info.value.code == ClaimErrorCode.ALREADY_CLAIMED

    def test_claim_refuses_locked_checkout(
        self, channel_a, user_a,
    ):
        guest = _create_checkout(channel_a)
        guest.completing_started_at = timezone.now()
        guest.save(update_fields=["completing_started_at"])

        with pytest.raises(ClaimError) as exc_info:
            claim_checkout(guest, user_a)

        assert exc_info.value.code == ClaimErrorCode.LOCKED

    def test_claim_merges_lines_when_user_has_cart(
        self, channel_a, user_a, variant, variant_b,
    ):
        user_cart = _create_checkout(channel_a, user=user_a)
        _add_line(user_cart, variant, 1)

        guest = _create_checkout(channel_a)
        _add_line(guest, variant, 2)      # matching variant
        _add_line(guest, variant_b, 1)    # new variant

        result = claim_checkout(guest, user_a)

        assert result.pk == user_cart.pk

        lines = {
            line.variant_id: line.quantity
            for line in result.lines.all()
        }
        assert lines[variant.pk] == Decimal("3.000")
        assert lines[variant_b.pk] == Decimal("1.000")

        # Guest cart is gone.
        assert not Checkout.objects.filter(pk=guest.pk).exists()

    def test_claim_discards_empty_guest_cart(
        self, channel_a, user_a, variant,
    ):
        user_cart = _create_checkout(channel_a, user=user_a)
        _add_line(user_cart, variant, 1)

        guest = _create_checkout(channel_a)  # empty

        result = claim_checkout(guest, user_a)

        assert result.pk == user_cart.pk
        assert not Checkout.objects.filter(pk=guest.pk).exists()
        assert result.lines.count() == 1

    def test_claim_refuses_channel_mismatch(
        self, channel_a, channel_b, user_a, variant,
    ):
        user_cart = _create_checkout(channel_a, user=user_a)
        _add_line(user_cart, variant, 1)

        guest_on_b = _create_checkout(channel_b)
        _add_line(guest_on_b, variant, 1)

        with pytest.raises(ClaimError) as exc_info:
            claim_checkout(guest_on_b, user_a)

        assert exc_info.value.code == ClaimErrorCode.CHANNEL_MISMATCH


# =====================================================================
# GRAPHQL MUTATION TESTS
# =====================================================================


CLAIM_MUTATION = """
mutation Claim($token: UUID!) {
  checkoutClaim(input: { token: $token }) {
    checkout {
      id
      token
      lineCount
      user { id email }
    }
    errors { field message code }
  }
}
"""


@pytest.fixture
def gql_client():
    """Graphene test client bound to the project schema."""
    from backend.schema import schema as project_schema
    return Client(project_schema)


class FakeRequest:
    """Minimal context matching what the mutation reads."""

    def __init__(self, user):
        self.user = user


class TestCheckoutClaimMutation:

    def test_mutation_requires_authentication(
        self, gql_client, channel_a, variant,
    ):
        guest = _create_checkout(channel_a)
        _add_line(guest, variant, 1)

        result = gql_client.execute(
            CLAIM_MUTATION,
            variables={"token": str(guest.pk)},
            context_value=FakeRequest(AnonymousUser()),
        )

        payload = result["data"]["checkoutClaim"]
        assert payload["checkout"] is None
        assert payload["errors"][0]["code"] == "INVALID"

    def test_mutation_claims_successfully(
        self, gql_client, channel_a, user_a, variant,
    ):
        guest = _create_checkout(channel_a)
        _add_line(guest, variant, 2)

        result = gql_client.execute(
            CLAIM_MUTATION,
            variables={"token": str(guest.pk)},
            context_value=FakeRequest(user_a),
        )
        if result.get("errors"):
            raise AssertionError(
                f"GraphQL errors: {result['errors']}"
            )
        if result.get("data") is None:
            raise AssertionError(
                f"GraphQL returned no data. Full result: {result}"
            )
        payload = result["data"]["checkoutClaim"]
        assert payload["errors"] == []
        assert payload["checkout"]["token"] == str(guest.pk)
        assert payload["checkout"]["lineCount"] == 1
        assert payload["checkout"]["user"]["id"] is not None

    def test_mutation_returns_channel_mismatch(
        self, gql_client, channel_a, channel_b, user_a, variant,
    ):
        user_cart = _create_checkout(channel_a, user=user_a)
        _add_line(user_cart, variant, 1)

        guest_on_b = _create_checkout(channel_b)
        _add_line(guest_on_b, variant, 1)

        result = gql_client.execute(
            CLAIM_MUTATION,
            variables={"token": str(guest_on_b.pk)},
            context_value=FakeRequest(user_a),
        )

        payload = result["data"]["checkoutClaim"]
        assert payload["errors"][0]["code"] == "CHANNEL_MISMATCH"

    def test_mutation_returns_already_claimed(
        self, gql_client, channel_a, user_a, user_b, variant,
    ):
        cart = _create_checkout(channel_a, user=user_a)
        _add_line(cart, variant, 1)

        result = gql_client.execute(
            CLAIM_MUTATION,
            variables={"token": str(cart.pk)},
            context_value=FakeRequest(user_b),
        )

        payload = result["data"]["checkoutClaim"]
        assert payload["errors"][0]["code"] == "ALREADY_CLAIMED"

    def test_mutation_returns_locked(
        self, gql_client, channel_a, user_a,
    ):
        guest = _create_checkout(channel_a)
        guest.completing_started_at = timezone.now()
        guest.save(update_fields=["completing_started_at"])

        result = gql_client.execute(
            CLAIM_MUTATION,
            variables={"token": str(guest.pk)},
            context_value=FakeRequest(user_a),
        )

        payload = result["data"]["checkoutClaim"]
        assert payload["errors"][0]["code"] == "LOCKED"