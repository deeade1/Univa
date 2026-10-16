# graphq/ecommerce/tests/test_order_refund_flow.py

"""
End-to-end refund flow tests.
"""

from __future__ import annotations

from decimal import Decimal

from graphql_relay import from_global_id, to_global_id

from ecommerce.models.enums import OrderGrantedRefundStatus
from ecommerce.models.order import Order, OrderGrantedRefund
from payment.canonical.models import Payment


# =====================================================================
# HELPERS
# =====================================================================


class FakeRequest:
    def __init__(self, user, session=None):
        self.user = user
        self.session = session if session is not None else {}
        self.META = {"REMOTE_ADDR": "127.0.0.1"}


def _gid(node_type: str, pk) -> str:
    return to_global_id(node_type, str(pk))


def _assert_ok(result: dict, step: str) -> dict:
    """
    Assert a GraphQL response has no top-level or payload errors.
    """
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


def _assert_error(result: dict, step: str) -> dict:
    """
    Assert a GraphQL response is well-formed and returns at least one
    payload error. Returns the payload for further assertions.
    """
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
    assert len(payload.get("errors") or []) > 0, (
        f"[{step}] expected payload errors, got none"
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
    token: $token, variantId: $variantId, quantity: $quantity
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
    token: $token, shippingMethodId: $shippingMethodId
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

ORDER_START_PAYMENT = """
mutation StartPayment($id: ID!, $provider: String!, $routeType: String!) {
  orderStartPayment(input: {
    id: $id, provider: $provider, routeType: $routeType
  }) {
    order { id chargeStatus }
    paymentExecutionId
    errors { field message code }
  }
}
"""

ORDER_REFUND = """
mutation Refund($id: ID!, $reason: String, $provider: String) {
  orderRefund(input: {
    id: $id, reason: $reason, execute: true, provider: $provider
  }) {
    order {
      id
      grantedRefunds {
        id
        status
        amount { amount currency }
        reason
      }
    }
    errors { field message code }
  }
}
"""


# =====================================================================
# PROVIDER + TASK STUBS
# =====================================================================
#
# These tests exercise the order/refund pipeline, not the Paystack
# HTTP translation. Stub the adapter's initiate() so no network call
# leaves the test, and run the Celery task synchronously.


def _stub_paystack_adapter(monkeypatch):
    from payment.canonical.models import PaymentExecution
    from payment.canonical.services.providers.registry import (
        ProviderRegistry,
    )
    from payment.canonical.services.providers.result import (
        ProviderResult,
    )

    adapter = ProviderRegistry.get("paystack")

    def _stub_initiate(execution):
        return ProviderResult(
            status=PaymentExecution.Status.COMPLETED,
            provider_reference=f"TEST-{execution.reference}",
            reconciliation_required=False,
        )

    monkeypatch.setattr(adapter, "initiate", _stub_initiate)


def _stub_celery_task(monkeypatch):
    from ecommerce.tasks import payment as payment_tasks
    from payment.canonical.models import PaymentExecution
    from payment.canonical.services.execution_orchestrator import (
        ExecutionOrchestrator,
    )

    def _sync_execute(execution_id):
        execution = PaymentExecution.objects.get(pk=execution_id)
        ExecutionOrchestrator.execute(execution)

    monkeypatch.setattr(
        payment_tasks.execute_order_payment_task,
        "delay",
        _sync_execute,
    )


# =====================================================================
# SHARED ORDER CREATION
# =====================================================================


def _create_paid_order(
    gql_client, channel, anonymous_user, staff_user, address_a,
    variant, shipping_method, email, monkeypatch,
):
    """Create an order, start payment, execute synchronously."""
    _stub_paystack_adapter(monkeypatch)
    _stub_celery_task(monkeypatch)

    guest_ctx = FakeRequest(anonymous_user)

    result = gql_client.execute(
        CHECKOUT_CREATE,
        variables={"channelSlug": channel.slug, "email": email},
        context_value=guest_ctx,
    )
    token = _assert_ok(result, "checkoutCreate")["checkout"]["token"]

    gql_client.execute(
        CHECKOUT_ADD_LINE,
        variables={
            "token": token,
            "variantId": _gid("ProductVariantNode", variant.pk),
            "quantity": "2",
        },
        context_value=guest_ctx,
    )

    for snippet, args in [
        (CHECKOUT_SET_SHIPPING_ADDRESS,
         {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
        (CHECKOUT_SET_BILLING_ADDRESS,
         {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
        (CHECKOUT_SET_SHIPPING_METHOD,
         {"token": token,
          "shippingMethodId": _gid("ShippingMethodNode", shipping_method.pk)}),
    ]:
        gql_client.execute(snippet, variables=args, context_value=guest_ctx)

    result = gql_client.execute(
        CHECKOUT_COMPLETE,
        variables={"token": token},
        context_value=guest_ctx,
    )
    order_gid = _assert_ok(result, "checkoutComplete")["orderId"]

    staff_ctx = FakeRequest(staff_user)
    result = gql_client.execute(
        ORDER_START_PAYMENT,
        variables={
            "id": order_gid,
            "provider": "paystack",
            "routeType": "univa_internal",
        },
        context_value=staff_ctx,
    )
    _assert_ok(result, "orderStartPayment")

    return order_gid


# =====================================================================
# TESTS
# =====================================================================


class TestOrderRefundFlow:

    def test_refund_creates_payment_and_refund_record(
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
        monkeypatch,
    ):
        order_gid = _create_paid_order(
            gql_client, channel, anonymous_user, staff_user,
            address_a, variant, shipping_method,
            "refund@example.com", monkeypatch,
        )

        staff_ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ORDER_REFUND,
            variables={
                "id": order_gid,
                "reason": "Customer request",
                "provider": "paystack",
            },
            context_value=staff_ctx,
        )
        payload = _assert_ok(result, "orderRefund")

        _, order_pk = from_global_id(order_gid)
        order = Order.objects.get(pk=order_pk)
        refunds = OrderGrantedRefund.objects.filter(order=order)
        assert refunds.count() == 1
        refund = refunds.first()
        assert refund.status in {
            OrderGrantedRefundStatus.PENDING,
            OrderGrantedRefundStatus.SUCCESS,
        }
        assert refund.amount_value > Decimal("0")

        refund_payment = Payment.objects.filter(
            source_type="refund",
            source_id=str(refund.pk),
        ).first()
        assert refund_payment is not None
        assert refund_payment.direction == Payment.Direction.DISBURSE

    def test_non_staff_cannot_refund(
        self,
        gql_client,
        channel,
        anonymous_user,
        user_a,
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
        monkeypatch,
    ):
        order_gid = _create_paid_order(
            gql_client, channel, anonymous_user, staff_user,
            address_a, variant, shipping_method,
            "refund-staff@example.com", monkeypatch,
        )

        user_ctx = FakeRequest(user_a)
        result = gql_client.execute(
            ORDER_REFUND,
            variables={
                "id": order_gid,
                "reason": "test",
                "provider": "paystack",
            },
            context_value=user_ctx,
        )
        assert "errors" in result
        assert any(
            "permission" in e["message"].lower()
            for e in result["errors"]
        )

    def test_unpaid_order_cannot_be_refunded(
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
        """Order created but never marked paid → refund refused."""
        guest_ctx = FakeRequest(anonymous_user)

        result = gql_client.execute(
            CHECKOUT_CREATE,
            variables={
                "channelSlug": channel.slug,
                "email": "unpaid@example.com",
            },
            context_value=guest_ctx,
        )
        token = _assert_ok(result, "checkoutCreate")["checkout"]["token"]

        gql_client.execute(
            CHECKOUT_ADD_LINE,
            variables={
                "token": token,
                "variantId": _gid("ProductVariantNode", variant.pk),
                "quantity": "1",
            },
            context_value=guest_ctx,
        )
        for snippet, args in [
            (CHECKOUT_SET_SHIPPING_ADDRESS,
             {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
            (CHECKOUT_SET_BILLING_ADDRESS,
             {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
            (CHECKOUT_SET_SHIPPING_METHOD,
             {"token": token,
              "shippingMethodId": _gid("ShippingMethodNode", shipping_method.pk)}),
        ]:
            gql_client.execute(snippet, variables=args, context_value=guest_ctx)

        result = gql_client.execute(
            CHECKOUT_COMPLETE,
            variables={"token": token},
            context_value=guest_ctx,
        )
        order_gid = _assert_ok(result, "checkoutComplete")["orderId"]

        staff_ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ORDER_REFUND,
            variables={
                "id": order_gid,
                "reason": "test",
                "provider": "paystack",
            },
            context_value=staff_ctx,
        )
        payload = _assert_error(result, "orderRefund")
        assert "charge_status" in payload["errors"][0]["message"]
        assert payload["errors"][0]["code"] == "NOT_REFUNDABLE"