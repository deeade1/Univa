# graphq/ecommerce/tests/test_ecommerce_end_to_end.py

"""
End-to-end integration tests for the customer ecommerce journey.

Exercises the real service layer + real DB through the GraphQL adapter.
Every step asserts on state transitions so a failure points at the
exact link in the chain that broke.

Covered flows:

    Test 1: Guest checkout → order → cancel
    Test 2: Guest cart → JWT sign-in claim → order
    Test 3: Full order lifecycle (mark-paid → fulfill → cancel-fulfillment)

No mocks. No fakes beyond the JWT sign-in context wrapper.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from graphene.test import Client

from accounts.models import Address
from ecommerce.models.channel import Channel
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.inventory import Stock
from ecommerce.models.shipping import (
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingZone,
)
from ecommerce.models.warehouse import Warehouse


User = get_user_model()


# =====================================================================
# TEST CLIENT
# =====================================================================


@pytest.fixture
def gql_client():
    """Graphene test client bound to the project schema."""
    from backend.schema import schema as project_schema
    return Client(project_schema)


class FakeRequest:
    """Minimal context object for GraphQL execution."""

    def __init__(self, user, session=None):
        self.user = user
        self.session = session if session is not None else {}
        self.META = {"REMOTE_ADDR": "127.0.0.1"}


# =====================================================================
# CHANNEL
# =====================================================================


@pytest.fixture
def channel(db):
    return Channel.objects.create(
        name="Test Channel",
        slug="test-channel",
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


# =====================================================================
# USERS
# =====================================================================


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        email="a@example.com",
        password="secret",
    )


@pytest.fixture
def staff_user(db):
    """Staff user for admin operations and staff-only queries."""
    return User.objects.create_user(
        email="staff@example.com",
        password="staffsecret",
        is_staff=True,
    )


@pytest.fixture
def anonymous_user():
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()


# =====================================================================
# ADDRESSES
# =====================================================================


@pytest.fixture
def address_a(db, user_a):
    return Address.objects.create(
        user=user_a,
        address_type="shipping",
        is_default=True,
        first_name="Test",
        last_name="User",
        company_name="",
        street_address_1="123 Test St",
        street_address_2="",
        city="Lagos",
        city_area="",
        postal_code="100001",
        state="Lagos",
        country="NG",
        country_area="",
        phone="+2348000000000",
        validation_skipped=False,
    )


# =====================================================================
# PRODUCT CATALOG
# =====================================================================


@pytest.fixture
def product_type(db):
    return ProductType.objects.create(
        name="Physical",
        slug="physical-e2e",
        kind="normal",
        has_variants=True,
        is_shipping_required=True,
    )


@pytest.fixture
def product(db, product_type):
    return Product.objects.create(
        name="E2E Test Product",
        slug="e2e-test-product",
        product_type=product_type,
    )


@pytest.fixture
def variant(db, product):
    return ProductVariant.objects.create(
        sku="E2E-SKU-001",
        product=product,
        name="Default",
        track_inventory=True,
    )


@pytest.fixture
def variant_b(db, product):
    return ProductVariant.objects.create(
        sku="E2E-SKU-002",
        product=product,
        name="Second",
        track_inventory=True,
    )


@pytest.fixture
def product_listing(db, product, channel):
    return ProductChannelListing.objects.create(
        product=product,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("1000.00"),
        visible_in_listings=True,
    )


@pytest.fixture
def variant_listing(db, variant, channel):
    return ProductVariantChannelListing.objects.create(
        variant=variant,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("1000.00"),
    )


@pytest.fixture
def variant_b_listing(db, variant_b, channel):
    return ProductVariantChannelListing.objects.create(
        variant=variant_b,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("500.00"),
    )


# =====================================================================
# WAREHOUSE + STOCK
# =====================================================================


@pytest.fixture
def warehouse(db, channel, address_a):
    wh = Warehouse.objects.create(
        name="Main Warehouse",
        slug="main-warehouse-e2e",
        address=address_a,
    )
    wh.channels.add(channel)
    return wh


@pytest.fixture
def stock(db, warehouse, variant):
    return Stock.objects.create(
        warehouse=warehouse,
        product_variant=variant,
        quantity=Decimal("100.000"),
    )


@pytest.fixture
def stock_b(db, warehouse, variant_b):
    return Stock.objects.create(
        warehouse=warehouse,
        product_variant=variant_b,
        quantity=Decimal("100.000"),
        
    )


# =====================================================================
# SHIPPING
# =====================================================================


@pytest.fixture
def shipping_zone(db, channel):
    zone = ShippingZone.objects.create(
        name="Test Zone",
        description="E2E test zone",
        is_active=True,
        default=True,
    )
    zone.channels.add(channel)
    return zone


@pytest.fixture
def shipping_method(db, shipping_zone, channel):
    method = ShippingMethod.objects.create(
        name="Standard Shipping",
        type="price",
        status="active",
        is_active=True,
        shipping_zone=shipping_zone,
    )
    ShippingMethodChannelListing.objects.create(
        shipping_method=method,
        channel=channel,
        price_amount=Decimal("500.00"),
        currency="NGN",
        is_active=True,
    )
    return method


# =====================================================================
# HELPERS
# =====================================================================


def _gid(node_type: str, pk) -> str:
    from graphql_relay import to_global_id
    return to_global_id(node_type, str(pk))


def _assert_ok(result: dict, step: str) -> dict:
    assert "errors" not in result, (
        f"[{step}] GraphQL errors: {result.get('errors')}"
    )
    assert result.get("data") is not None, (
        f"[{step}] GraphQL returned no data: {result}"
    )
    data = result["data"]
    field_name = next(iter(data.keys()))
    payload = data[field_name]
    assert payload is not None, (
        f"[{step}] payload for {field_name} was None"
    )
    assert payload.get("errors") == [], (
        f"[{step}] payload errors: {payload.get('errors')}"
    )
    return payload


# =====================================================================
# GRAPHQL SNIPPETS
# =====================================================================


CHECKOUT_CREATE = """
mutation CreateCheckout($channelSlug: String!, $email: String) {
  checkoutCreate(input: { channelSlug: $channelSlug, email: $email }) {
    checkout { token email }
    errors { field message code }
  }
}
"""

CHECKOUT_ADD_LINE = """
mutation AddLine($token: UUID!, $variantId: ID!, $quantity: Decimal!) {
  checkoutAddLine(input: {
    token: $token,
    variantId: $variantId,
    quantity: $quantity,
  }) {
    checkout {
      token
      lineCount
      totalQuantity
      subtotal { gross { amount currency } }
      total { gross { amount currency } }
    }
    checkoutLine { id quantity }
    errors { field message code }
  }
}
"""

CHECKOUT_SET_SHIPPING_ADDRESS = """
mutation SetShipping($token: UUID!, $addressId: ID!) {
  checkoutSetShippingAddress(input: { token: $token, addressId: $addressId }) {
    checkout { token isCompletable }
    errors { field message code }
  }
}
"""

CHECKOUT_SET_BILLING_ADDRESS = """
mutation SetBilling($token: UUID!, $addressId: ID!) {
  checkoutSetBillingAddress(input: { token: $token, addressId: $addressId }) {
    checkout { token isCompletable }
    errors { field message code }
  }
}
"""

CHECKOUT_SET_SHIPPING_METHOD = """
mutation SetShippingMethod($token: UUID!, $shippingMethodId: ID!) {
  checkoutSetShippingMethod(input: {
    token: $token,
    shippingMethodId: $shippingMethodId,
  }) {
    checkout {
      token
      isCompletable
      shippingPrice { gross { amount currency } }
      total { gross { amount currency } }
    }
    errors { field message code }
  }
}
"""

CHECKOUT_COMPLETE = """
mutation Complete($token: UUID!) {
  checkoutComplete(input: { token: $token }) {
    checkout { token }
    orderId
    errors { field message code }
  }
}
"""

ORDER_QUERY = """
query GetOrder($id: ID!) {
  order(id: $id) {
    id
    number
    status
    origin
    chargeStatus
    user { id email }
    totalQuantity
    subtotal { gross { amount currency } }
    shippingPrice { gross { amount currency } }
    total { gross { amount currency } }
    lines {
      id
      productName
      productSku
      quantity
      quantityFulfilled
      quantityUnfulfilled
      unitPrice { gross { amount currency } }
      totalPrice { gross { amount currency } }
    }
    events { type date }
  }
}
"""

ORDER_CANCEL = """
mutation CancelOrder($id: ID!, $reason: String) {
  orderCancel(input: { id: $id, reason: $reason }) {
    order { id status canCancel events { type } }
    errors { field message code }
  }
}
"""

ORDER_MARK_AS_PAID = """
mutation MarkPaid($id: ID!, $paymentReference: String) {
  orderMarkAsPaid(input: {
    id: $id,
    paymentReference: $paymentReference,
  }) {
    order {
      id
      chargeStatus
      isFullyPaid
      totalCharged { amount currency }
      totalBalance { amount currency }
      events { type }
    }
    errors { field message code }
  }
}
"""

ORDER_FULFILL = """
mutation Fulfill($orderId: ID!, $lines: [OrderFulfillLineInput!]!, $trackingNumber: String) {
  orderFulfill(input: {
    orderId: $orderId,
    lines: $lines,
    trackingNumber: $trackingNumber,
  }) {
    order {
      id
      status
      fulfillments { id status composedId trackingNumber }
      events { type }
    }
    fulfillment { id status composedId trackingNumber }
    errors { field message code }
  }
}
"""

ORDER_CANCEL_FULFILLMENT = """
mutation CancelFulfillment($id: ID!, $reason: String) {
  orderCancelFulfillment(input: { id: $id, reason: $reason }) {
    order { id status fulfillments { id status } }
    fulfillment { id status }
    errors { field message code }
  }
}
"""

CHECKOUT_BY_TOKEN = """
query CheckoutByToken($token: UUID!) {
  checkoutByToken(token: $token) {
    id
    token
    user { id email }
    lineCount
  }
}
"""


# =====================================================================
# TEST 1 — Guest checkout → order → cancel
# =====================================================================


class TestGuestCheckoutToOrder:

    def test_full_guest_checkout_and_cancel(
        self,
        gql_client,
        channel,
        anonymous_user,
        staff_user,              # ← staff for order(id:) queries
        address_a,
        product,
        variant,
        product_listing,
        variant_listing,
        warehouse,
        stock,
        shipping_zone,
        shipping_method,
    ):
        guest_ctx = FakeRequest(anonymous_user)
        staff_ctx = FakeRequest(staff_user)

        # --- 1. Create checkout ---------------------------------
        result = gql_client.execute(
            CHECKOUT_CREATE,
            variables={
                "channelSlug": channel.slug,
                "email": "guest@example.com",
            },
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutCreate")
        token = payload["checkout"]["token"]
        assert payload["checkout"]["email"] == "guest@example.com"

        # --- 2. Add a line --------------------------------------
        result = gql_client.execute(
            CHECKOUT_ADD_LINE,
            variables={
                "token": token,
                "variantId": _gid("ProductVariantNode", variant.pk),
                "quantity": "2",
            },
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutAddLine")
        assert payload["checkout"]["lineCount"] == 1
        assert payload["checkout"]["totalQuantity"] == "2.000"
        assert payload["checkout"]["subtotal"]["gross"]["amount"] == 2000

        # --- 3. Shipping address --------------------------------
        result = gql_client.execute(
            CHECKOUT_SET_SHIPPING_ADDRESS,
            variables={
                "token": token,
                "addressId": _gid("AddressNode", address_a.pk),
            },
            context_value=guest_ctx,
        )
        _assert_ok(result, "checkoutSetShippingAddress")

        # --- 4. Billing address ---------------------------------
        result = gql_client.execute(
            CHECKOUT_SET_BILLING_ADDRESS,
            variables={
                "token": token,
                "addressId": _gid("AddressNode", address_a.pk),
            },
            context_value=guest_ctx,
        )
        _assert_ok(result, "checkoutSetBillingAddress")

        # --- 5. Shipping method ---------------------------------
        result = gql_client.execute(
            CHECKOUT_SET_SHIPPING_METHOD,
            variables={
                "token": token,
                "shippingMethodId": _gid(
                    "ShippingMethodNode", shipping_method.pk
                ),
            },
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutSetShippingMethod")
        assert payload["checkout"]["isCompletable"] is True
        assert (
            payload["checkout"]["shippingPrice"]["gross"]["amount"] == 500
        )

        # --- 6. Complete checkout → order -----------------------
        result = gql_client.execute(
            CHECKOUT_COMPLETE,
            variables={"token": token},
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutComplete")
        order_gid = payload["orderId"]
        assert order_gid is not None

        # --- 7. Order exists with correct state -----------------
        # Use staff context — anonymous users can't query order(id:).
        result = gql_client.execute(
            ORDER_QUERY,
            variables={"id": order_gid},
            context_value=staff_ctx,
        )
        assert "errors" not in result, result.get("errors")
        order = result["data"]["order"]
        assert order is not None
        assert order["status"] == "UNFULFILLED"
        assert order["origin"] == "CHECKOUT"
        assert order["chargeStatus"] == "NONE"
        assert order["totalQuantity"] == "2.000"
        assert order["subtotal"]["gross"]["amount"] == 2000
        assert order["shippingPrice"]["gross"]["amount"] == 500
        assert order["total"]["gross"]["amount"] == 2500
        assert len(order["lines"]) == 1
        assert order["lines"][0]["quantityUnfulfilled"] == "2.000"
        assert order["lines"][0]["quantityFulfilled"] == "0.000"
        assert any(e["type"] == "placed" for e in order["events"])

        # --- 8. Cancel the order --------------------------------
        # orderCancel is not staff-gated; guest context works.
        result = gql_client.execute(
            ORDER_CANCEL,
            variables={"id": order_gid, "reason": "E2E test"},
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "orderCancel")
        assert payload["order"]["status"] == "CANCELED"
        assert payload["order"]["canCancel"] is False
        assert any(
            e["type"] == "canceled" for e in payload["order"]["events"]
        )


# =====================================================================
# TEST 2 — Guest cart claimed on JWT sign-in
# =====================================================================


class TestSignInClaimsGuestCart:

    def test_sign_in_claims_cart(
        self,
        gql_client,
        channel,
        anonymous_user,
        user_a,
        address_a,
        product,
        variant,
        product_listing,
        variant_listing,
        warehouse,
        stock,
        shipping_zone,
        shipping_method,
    ):
        session = {}
        guest_ctx = FakeRequest(anonymous_user, session=session)

        result = gql_client.execute(
            CHECKOUT_CREATE,
            variables={
                "channelSlug": channel.slug,
                "email": "guest@example.com",
            },
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutCreate")
        token = payload["checkout"]["token"]

        session["anonymous_checkout_token"] = token

        result = gql_client.execute(
            CHECKOUT_ADD_LINE,
            variables={
                "token": token,
                "variantId": _gid("ProductVariantNode", variant.pk),
                "quantity": "1",
            },
            context_value=guest_ctx,
        )
        payload = _assert_ok(result, "checkoutAddLine")
        assert payload["checkout"]["subtotal"]["gross"]["amount"] == 1000

        SIGN_IN = """
        mutation SignIn($contact: String!, $password: String!) {
          signIn(input: { contact: $contact, password: $password }) {
            token
            refreshToken
            user { id email }
          }
        }
        """
        session_ctx = FakeRequest(anonymous_user, session=session)

        result = gql_client.execute(
            SIGN_IN,
            variables={
                "contact": user_a.email,
                "password": "secret",
            },
            context_value=session_ctx,
        )
        assert "errors" not in result, result.get("errors")
        sign_in = result["data"]["signIn"]
        assert sign_in is not None
        assert sign_in["token"] is not None

        assert "anonymous_checkout_token" not in session

        result = gql_client.execute(
            CHECKOUT_BY_TOKEN,
            variables={"token": token},
            context_value=FakeRequest(user_a),
        )
        assert "errors" not in result, result.get("errors")
        checkout = result["data"]["checkoutByToken"]
        assert checkout is not None
        assert checkout["user"] is not None
        assert checkout["user"]["email"] == user_a.email
        assert checkout["lineCount"] == 1


# =====================================================================
# TEST 3 — Full order lifecycle on a completed checkout
# =====================================================================


class TestOrderLifecycle:

    @pytest.fixture
    def completed_order_gid(
        self,
        gql_client,
        channel,
        anonymous_user,
        address_a,
        product,
        variant,
        product_listing,
        variant_listing,
        warehouse,
        stock,
        shipping_zone,
        shipping_method,
    ):
        """Create + complete a checkout, return the order global ID."""
        guest_ctx = FakeRequest(anonymous_user)

        result = gql_client.execute(
            CHECKOUT_CREATE,
            variables={
                "channelSlug": channel.slug,
                "email": "lifecycle@example.com",
            },
            context_value=guest_ctx,
        )
        token = _assert_ok(result, "checkoutCreate")["checkout"]["token"]

        result = gql_client.execute(
            CHECKOUT_ADD_LINE,
            variables={
                "token": token,
                "variantId": _gid("ProductVariantNode", variant.pk),
                "quantity": "2",
            },
            context_value=guest_ctx,
        )
        _assert_ok(result, "checkoutAddLine")

        for snippet, args in [
            (
                CHECKOUT_SET_SHIPPING_ADDRESS,
                {
                    "token": token,
                    "addressId": _gid("AddressNode", address_a.pk),
                },
            ),
            (
                CHECKOUT_SET_BILLING_ADDRESS,
                {
                    "token": token,
                    "addressId": _gid("AddressNode", address_a.pk),
                },
            ),
            (
                CHECKOUT_SET_SHIPPING_METHOD,
                {
                    "token": token,
                    "shippingMethodId": _gid(
                        "ShippingMethodNode", shipping_method.pk
                    ),
                },
            ),
        ]:
            result = gql_client.execute(
                snippet,
                variables=args,
                context_value=guest_ctx,
            )
            _assert_ok(result, "setup")

        result = gql_client.execute(
            CHECKOUT_COMPLETE,
            variables={"token": token},
            context_value=guest_ctx,
        )
        return _assert_ok(result, "checkoutComplete")["orderId"]

    def test_mark_paid_fulfill_then_cancel_fulfillment(
        self,
        gql_client,
        anonymous_user,
        staff_user,
        completed_order_gid,
    ):
        # All mutations in this test are staff-gated; use staff context.
        ctx = FakeRequest(staff_user)

        # --- 1. Mark order as paid ------------------------------
        result = gql_client.execute(
            ORDER_MARK_AS_PAID,
            variables={
                "id": completed_order_gid,
                "paymentReference": "E2E-PAYMENT-REF",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderMarkAsPaid")
        assert payload["order"]["chargeStatus"] == "FULL"
        assert payload["order"]["isFullyPaid"] is True
        assert payload["order"]["totalBalance"]["amount"] == 0

        # --- 2. Fetch line IDs to fulfill -----------------------
        result = gql_client.execute(
            ORDER_QUERY,
            variables={"id": completed_order_gid},
            context_value=ctx,
        )
        order = result["data"]["order"]
        line = order["lines"][0]
        assert line["quantityUnfulfilled"] == "2.000"

        # --- 3. Fulfill 1 of 2 ----------------------------------
        result = gql_client.execute(
            ORDER_FULFILL,
            variables={
                "orderId": completed_order_gid,
                "lines": [
                    {"orderLineId": line["id"], "quantity": "1"}
                ],
                "trackingNumber": "E2E-TRACK-001",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderFulfill")
        assert payload["order"]["status"] == "PARTIALLY_FULFILLED"
        assert payload["fulfillment"]["status"] == "FULFILLED"
        assert payload["fulfillment"]["trackingNumber"] == "E2E-TRACK-001"

        fulfillment_gid = payload["fulfillment"]["id"]

        # --- 4. Cancel the fulfillment --------------------------
        result = gql_client.execute(
            ORDER_CANCEL_FULFILLMENT,
            variables={
                "id": fulfillment_gid,
                "reason": "E2E rollback",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderCancelFulfillment")
        assert payload["fulfillment"]["status"] == "CANCELED"
        assert payload["order"]["status"] == "UNFULFILLED"

        # --- 5. Verify quantity restored ------------------------
        result = gql_client.execute(
            ORDER_QUERY,
            variables={"id": completed_order_gid},
            context_value=ctx,
        )
        order = result["data"]["order"]
        assert order["lines"][0]["quantityFulfilled"] == "0.000"
        assert order["lines"][0]["quantityUnfulfilled"] == "2.000"