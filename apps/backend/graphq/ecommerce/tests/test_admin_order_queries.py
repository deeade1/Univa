# graphq/ecommerce/tests/test_admin_order_queries.py

"""
Tests for admin order queries: staff bypass on allOrders, and
orderByNumber.
"""

from __future__ import annotations

from graphql_relay import from_global_id, to_global_id

from ecommerce.models.order import Order


# =====================================================================
# HELPERS
# =====================================================================


class FakeRequest:
    """Minimal context object matching what resolvers read."""

    def __init__(self, user, session=None):
        self.user = user
        self.session = session if session is not None else {}
        self.META = {"REMOTE_ADDR": "127.0.0.1"}


def _gid(node_type: str, pk) -> str:
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
    checkout { token lineCount }
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
    checkout { token isCompletable }
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

ALL_ORDERS = """
query AllOrders($first: Int!) {
  allOrders(first: $first) {
    edges {
      node { id number userEmail }
    }
  }
}
"""

ORDER_BY_NUMBER = """
query OrderByNumber($number: Int!) {
  orderByNumber(number: $number) {
    id
    number
    userEmail
  }
}
"""


# =====================================================================
# SHARED ORDER-CREATION HELPER
# =====================================================================


def _create_order(
    gql_client, channel, anonymous_user, address_a, variant,
    shipping_method, email,
):
    """
    Create a full order via the guest checkout flow.
    Returns the order's Relay global ID.
    """
    guest_ctx = FakeRequest(anonymous_user)

    result = gql_client.execute(
        CHECKOUT_CREATE,
        variables={"channelSlug": channel.slug, "email": email},
        context_value=guest_ctx,
    )
    token = _assert_ok(result, "checkoutCreate")["checkout"]["token"]

    result = gql_client.execute(
        CHECKOUT_ADD_LINE,
        variables={
            "token": token,
            "variantId": _gid("ProductVariantNode", variant.pk),
            "quantity": "1",
        },
        context_value=guest_ctx,
    )
    _assert_ok(result, "checkoutAddLine")

    for snippet, args in [
        (
            CHECKOUT_SET_SHIPPING_ADDRESS,
            {"token": token, "addressId": _gid("AddressNode", address_a.pk)},
        ),
        (
            CHECKOUT_SET_BILLING_ADDRESS,
            {"token": token, "addressId": _gid("AddressNode", address_a.pk)},
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
            snippet, variables=args, context_value=guest_ctx
        )
        _assert_ok(result, "setup")

    result = gql_client.execute(
        CHECKOUT_COMPLETE,
        variables={"token": token},
        context_value=guest_ctx,
    )
    return _assert_ok(result, "checkoutComplete")["orderId"]


def _order_number_from_gid(order_gid: str) -> int:
    """
    Read the order number directly from the database.

    We do NOT use the GraphQL `order(id: ...)` query because it's
    access-controlled — anonymous and non-staff users cannot read
    arbitrary orders through it. The test has direct DB access.
    """
    _, order_pk = from_global_id(order_gid)
    return Order.objects.get(pk=order_pk).number


# =====================================================================
# TESTS
# =====================================================================


class TestAdminOrderQueries:

    def test_staff_sees_all_orders(
        self,
        gql_client,
        channel,
        anonymous_user,
        staff_user,
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
        _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "one@example.com",
        )
        _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "two@example.com",
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ALL_ORDERS,
            variables={"first": 10},
            context_value=ctx,
        )
        assert "errors" not in result, result.get("errors")
        edges = result["data"]["allOrders"]["edges"]
        emails = {edge["node"]["userEmail"] for edge in edges}
        assert "one@example.com" in emails
        assert "two@example.com" in emails

    def test_regular_user_sees_only_own_orders(
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
        _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "guest@example.com",
        )

        ctx = FakeRequest(user_a)
        result = gql_client.execute(
            ALL_ORDERS,
            variables={"first": 10},
            context_value=ctx,
        )
        assert "errors" not in result, result.get("errors")
        edges = result["data"]["allOrders"]["edges"]
        assert edges == []

    def test_staff_can_lookup_by_number(
        self,
        gql_client,
        channel,
        anonymous_user,
        staff_user,
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
        order_gid = _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "bynumber@example.com",
        )

        # Read the number directly from the DB.
        number = _order_number_from_gid(order_gid)

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ORDER_BY_NUMBER,
            variables={"number": number},
            context_value=ctx,
        )
        assert "errors" not in result, result.get("errors")
        found = result["data"]["orderByNumber"]
        assert found is not None
        assert found["number"] == number

    def test_non_staff_cannot_lookup_by_number(
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
        order_gid = _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "bynum2@example.com",
        )

        # Read the number directly from the DB.
        number = _order_number_from_gid(order_gid)

        ctx = FakeRequest(user_a)
        result = gql_client.execute(
            ORDER_BY_NUMBER,
            variables={"number": number},
            context_value=ctx,
        )
        assert "errors" in result