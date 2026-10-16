# graphq/ecommerce/tests/test_order_payment_flow.py

"""
End-to-end test: checkoutComplete creates an Order with a canonical
Payment attached; executing the Payment updates Order.charge_status.
"""

from __future__ import annotations

from graphql_relay import from_global_id, to_global_id

from ecommerce.models.order import Order
from payment.canonical.models import Payment, PaymentExecution


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
# PROVIDER + TASK STUBS
# =====================================================================
#
# These tests exercise the order → payment pipeline, not the Paystack
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
    chargeStatus
    isFullyPaid
    payment {
      id
      reference
      status
      amount
      currency
    }
  }
}
"""


# =====================================================================
# ORDER HELPER
# =====================================================================


def _create_order(
    gql_client, channel, anonymous_user, address_a, variant,
    shipping_method, email,
):
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
            "quantity": "2",
        },
        context_value=guest_ctx,
    )
    _assert_ok(result, "checkoutAddLine")

    for snippet, args in [
        (CHECKOUT_SET_SHIPPING_ADDRESS,
         {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
        (CHECKOUT_SET_BILLING_ADDRESS,
         {"token": token, "addressId": _gid("AddressNode", address_a.pk)}),
        (CHECKOUT_SET_SHIPPING_METHOD,
         {"token": token,
          "shippingMethodId": _gid("ShippingMethodNode", shipping_method.pk)}),
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


# =====================================================================
# TESTS
# =====================================================================


class TestOrderPaymentFlow:

    def test_checkout_creates_payment(
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
            variant, shipping_method, "payment-test@example.com",
        )

        _, order_pk = from_global_id(order_gid)
        order = Order.objects.get(pk=order_pk)

        assert order.payment_id is not None

        payment = Payment.objects.get(pk=order.payment_id)
        assert payment.status == Payment.Status.PENDING
        assert payment.source_type == "order"
        assert payment.source_id == str(order.pk)

    def test_order_start_payment_creates_execution_and_marks_paid(
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
        """
        `orderStartPayment` enqueues a Celery task. In tests we
        monkeypatch `.delay` to run the orchestrator synchronously
        and stub the Paystack adapter so no network call leaves.
        """
        _stub_paystack_adapter(monkeypatch)
        _stub_celery_task(monkeypatch)

        order_gid = _create_order(
            gql_client, channel, anonymous_user, address_a,
            variant, shipping_method, "payment-flow@example.com",
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            """
            mutation StartPayment($id: ID!, $provider: String!, $routeType: String!) {
              orderStartPayment(input: {
                id: $id, provider: $provider, routeType: $routeType
              }) {
                order { id number chargeStatus }
                paymentExecutionId
                errors { field message code }
              }
            }
            """,
            variables={
                "id": order_gid,
                "provider": "paystack",
                "routeType": "univa_internal",
            },
            context_value=ctx,
        )
        payload = _assert_ok(result, "orderStartPayment")
        assert payload["paymentExecutionId"] is not None

        _, order_pk = from_global_id(order_gid)
        order = Order.objects.get(pk=order_pk)
        assert order.charge_status == "full"

    def test_order_query_exposes_payment(
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
            variant, shipping_method, "payment-query@example.com",
        )

        ctx = FakeRequest(staff_user)
        result = gql_client.execute(
            ORDER_QUERY,
            variables={"id": order_gid},
            context_value=ctx,
        )
        assert "errors" not in result, result.get("errors")
        order = result["data"]["order"]
        assert order is not None
        assert order["payment"] is not None
        assert order["payment"]["reference"] is not None
        assert order["payment"]["status"] == "PENDING"
        assert order["payment"]["currency"] == "NGN"