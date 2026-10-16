# graphq/ecommerce/tests/test_admin_order_mutations.py

"""
Tests for admin order mutations: force cancel, force fulfill,
update tracking, add note, and the staff gate on mark-as-paid.
"""

from __future__ import annotations

from graphql_relay import from_global_id, to_global_id

from ecommerce.models.order import Order


# =====================================================================
# HELPERS (inlined to avoid package import issues)
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

ORDER_QUERY = """
query GetOrder($id: ID!) {
  order(id: $id) {
    id
    number
    status
    lines { id quantity quantityUnfulfilled }
  }
}
"""

FORCE_CANCEL = """
mutation ForceCancel($id: ID!, $reason: String) {
  orderForceCancel(input: { id: $id, reason: $reason }) {
    order { id status canCancel events { type } }
    errors { field message code }
  }
}
"""

FORCE_FULFILL = """
mutation ForceFulfill($orderId: ID!, $lines: [OrderFulfillLineInput!]!, $trackingNumber: String) {
  orderForceFulfill(input: {
    orderId: $orderId,
    lines: $lines,
    trackingNumber: $trackingNumber,
  }) {
    order { id status }
    fulfillment { id status trackingNumber composedId }
    errors { field message code }
  }
}
"""

UPDATE_TRACKING = """
mutation UpdateTracking($fulfillmentId: ID!, $trackingNumber: String!) {
  orderUpdateTracking(input: {
    fulfillmentId: $fulfillmentId,
    trackingNumber: $trackingNumber,
  }) {
    fulfillment { id trackingNumber }
    errors { field message code }
  }
}
"""

ADD_NOTE = """
mutation AddNote($id: ID!, $message: String!) {
  orderAddNote(input: { id: $id, message: $message }) {
    order { id events { type parameters } }
    errors { field message code }
  }
}
"""

MARK_PAID = """
mutation MarkPaid($id: ID!) {
  orderMarkAsPaid(input: { id: $id }) {
    order { id chargeStatus }
    errors { field message code }
  }
}
"""


# =====================================================================
# SHARED ORDER-CREATION HELPER
# =====================================================================


def _complete_an_order(
    gql_client,
    channel,
    anonymous_user,
    address_a,
    variant,
    shipping_method,
):
    """
    Create a full order via checkout flow, then return (order_gid, line_gid).

    Line GID is looked up directly from the database — we do NOT go
    through the GraphQL `order(id: ...)` query, because that query
    is access-controlled (anonymous users can't read arbitrary orders).
    Direct DB access is safe in tests.
    """
    guest_ctx = FakeRequest(anonymous_user)

    result = gql_client.execute(
        CHECKOUT_CREATE,
        variables={
            "channelSlug": channel.slug,
            "email": "admin-test@example.com",
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
    order_gid = _assert_ok(result, "checkoutComplete")["orderId"]

    # Direct DB lookup — bypasses the access-controlled GraphQL query.
    _, order_pk = from_global_id(order_gid)
    order = Order.objects.get(pk=order_pk)
    line = order.lines.first()
    line_gid = _gid("OrderLineNode", line.pk)

    return order_gid, line_gid


# =====================================================================
# TESTS
# =====================================================================


class TestOrderForceCancel:

    def test_staff_can_force_cancel(
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
        order_gid, _ = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            FORCE_CANCEL,
            variables={"id": order_gid, "reason": "Admin override"},
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderForceCancel")
        assert payload["order"]["status"] == "CANCELED"
        assert any(
            e["type"] == "canceled" for e in payload["order"]["events"]
        )

    def test_non_staff_cannot_force_cancel(
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
        order_gid, _ = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(user_a)
        result = gql_client.execute(
            FORCE_CANCEL,
            variables={"id": order_gid},
            context_value=ctx,
        )
        assert "errors" in result
        assert any(
            "permission" in e["message"].lower()
            for e in result["errors"]
        )


class TestOrderForceFulfill:

    def test_staff_can_force_fulfill(
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
        order_gid, line_gid = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            FORCE_FULFILL,
            variables={
                "orderId": order_gid,
                "lines": [{"orderLineId": line_gid, "quantity": "1"}],
                "trackingNumber": "ADMIN-TRACK-001",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderForceFulfill")
        assert payload["fulfillment"]["status"] == "FULFILLED"
        assert (
            payload["fulfillment"]["trackingNumber"]
            == "ADMIN-TRACK-001"
        )
        assert payload["order"]["status"] == "PARTIALLY_FULFILLED"


class TestOrderUpdateTracking:

    def test_staff_can_update_tracking(
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
        order_gid, line_gid = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        admin_ctx = FakeRequest(staff_user)

        result = gql_client.execute(
            FORCE_FULFILL,
            variables={
                "orderId": order_gid,
                "lines": [{"orderLineId": line_gid, "quantity": "1"}],
                "trackingNumber": "ORIGINAL-TRACK",
            },
            context_value=admin_ctx,
        )
        fulfillment_gid = _assert_ok(
            result, "forceFulfill"
        )["fulfillment"]["id"]

        result = gql_client.execute(
            UPDATE_TRACKING,
            variables={
                "fulfillmentId": fulfillment_gid,
                "trackingNumber": "NEW-TRACK-002",
            },
            context_value=admin_ctx,
        )
        payload = _assert_ok(result, "orderUpdateTracking")
        assert payload["fulfillment"]["trackingNumber"] == "NEW-TRACK-002"


class TestOrderAddNote:

    def test_staff_can_add_note(
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
        order_gid, _ = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ADD_NOTE,
            variables={
                "id": order_gid,
                "message": "Customer called about delivery",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderAddNote")
        notes = [
            e for e in payload["order"]["events"]
            if e["type"] == "note_added"
        ]
        assert len(notes) == 1
        assert (
            notes[0]["parameters"]["message"]
            == "Customer called about delivery"
        )


class TestOrderMarkAsPaidStaffGate:

    def test_staff_can_mark_as_paid(
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
        order_gid, _ = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            MARK_PAID,
            variables={"id": order_gid},
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderMarkAsPaid")
        assert payload["order"]["chargeStatus"] == "FULL"

    def test_non_staff_cannot_mark_as_paid(
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
        order_gid, _ = _complete_an_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method,
        )

        ctx = FakeRequest(user_a)
        result = gql_client.execute(
            MARK_PAID,
            variables={"id": order_gid},
            context_value=ctx,
        )
        assert "errors" in result
        assert any(
            "permission" in e["message"].lower()
            for e in result["errors"]
        )