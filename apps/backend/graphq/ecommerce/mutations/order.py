# graphq/ecommerce/mutations/order.py

"""
Order GraphQL mutations.

Every mutation returns a payload with:
    - the affected order (or null on hard failure)
    - an `errors` list (never raises; errors are structured)

Business errors are always returned in the payload, not as
GraphQL-level errors.

Every mutation refreshes the order instance before returning it,
so computed fields reflect the current database state.
"""

from __future__ import annotations

from decimal import Decimal

import graphene
from django.core.exceptions import ValidationError as DjangoValidationError
from graphene import relay
from graphql_relay import from_global_id, to_global_id

from ecommerce.models.enums.errors import OrderErrorCode
from ecommerce.models.order import Order, OrderLine
from ecommerce.services.order import (
    FulfillmentError,
    FulfillmentLineInput,
    FulfillmentNotPossible,
    OrderNotCancelable,
    OrderNotConfirmable,
    cancel_fulfillment,
    cancel_order,
    confirm_order,
    create_fulfillment,
    get_fulfillment_by_id,
    mark_order_as_paid,
)
from ecommerce.services.order.payment import (
    OrderPaymentError,
    create_execution_for_order_payment,
    create_payment_for_order,
)
from ecommerce.services.order.refund import (
    OrderNotRefundable,
    RefundAmountInvalid,
    RefundError,
    create_refund_for_order,
    execute_refund_for_order,
)
from graphq.ecommerce.types.errors import OrderError
from graphq.ecommerce.types.order import FulfillmentNode, OrderNode
from univa_jwt.decorators import staff_member_required


# =====================================================================
# HELPERS
# =====================================================================


def _resolve_pk_or_error(
    global_id: str,
    *,
    field: str = "id",
    entity_label: str = "ID",
):
    """
    Decode a Relay global ID and return (pk, error).
    """
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        return None, OrderError(
            message=f"Invalid {entity_label}.",
            code=OrderErrorCode.INVALID,
            field=field,
        )

    if not pk:
        return None, OrderError(
            message=f"Invalid {entity_label}.",
            code=OrderErrorCode.INVALID,
            field=field,
        )

    return pk, None


def _get_order_or_error(order_gid: str):
    """Return (order, error)."""
    pk, error = _resolve_pk_or_error(
        order_gid, field="id", entity_label="order ID"
    )
    if error is not None:
        return None, error

    try:
        order = Order.objects.filter(pk=pk).first()
    except (DjangoValidationError, ValueError):
        return None, OrderError(
            message="Malformed order ID.",
            code=OrderErrorCode.INVALID,
            field="id",
        )

    if order is None:
        return None, OrderError(
            message="Order not found.",
            code=OrderErrorCode.NOT_FOUND,
            field="id",
        )

    return order, None


def _get_fulfillment_or_error(fulfillment_gid: str):
    """Return (fulfillment, error)."""
    pk, error = _resolve_pk_or_error(
        fulfillment_gid, field="id", entity_label="fulfillment ID"
    )
    if error is not None:
        return None, error

    try:
        fulfillment = get_fulfillment_by_id(pk)
    except (DjangoValidationError, ValueError):
        return None, OrderError(
            message="Malformed fulfillment ID.",
            code=OrderErrorCode.INVALID,
            field="id",
        )

    if fulfillment is None:
        return None, OrderError(
            message="Fulfillment not found.",
            code=OrderErrorCode.NOT_FOUND,
            field="id",
        )

    return fulfillment, None


def _get_order_line_or_error(line_gid: str, order: Order):
    """Return (order_line, error)."""
    pk, error = _resolve_pk_or_error(
        line_gid, field="lines", entity_label="line ID"
    )
    if error is not None:
        return None, error

    try:
        line = OrderLine.objects.filter(pk=pk, order=order).first()
    except (DjangoValidationError, ValueError):
        return None, OrderError(
            message="Malformed line ID.",
            code=OrderErrorCode.INVALID,
            field="lines",
        )

    if line is None:
        return None, OrderError(
            message="Order line not found.",
            code=OrderErrorCode.NOT_FOUND,
            field="lines",
        )

    return line, None


# =====================================================================
# INPUT TYPES
# =====================================================================


class OrderFulfillLineInput(graphene.InputObjectType):
    """A single line to fulfill."""

    order_line_id = graphene.ID(required=True)
    quantity = graphene.Decimal(required=True)


# =====================================================================
# MUTATIONS
# =====================================================================


class OrderCancel(relay.ClientIDMutation):
    """Cancel an order and release any stock allocations."""

    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, reason=""):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderCancel(order=None, errors=[error])

        user = (
            info.context.user
            if info.context.user.is_authenticated
            else None
        )

        try:
            cancel_order(order, user=user, reason=reason or "")
        except OrderNotCancelable as e:
            return OrderCancel(
                order=order,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.NOT_CANCELABLE,
                    )
                ],
            )

        order.refresh_from_db()
        return OrderCancel(order=order, errors=[])


class OrderConfirm(relay.ClientIDMutation):
    """Move an unconfirmed order to unfulfilled."""

    class Input:
        id = graphene.ID(required=True)

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderConfirm(order=None, errors=[error])

        user = (
            info.context.user
            if info.context.user.is_authenticated
            else None
        )

        try:
            confirm_order(order, user=user)
        except OrderNotConfirmable as e:
            return OrderConfirm(
                order=order,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.NOT_CONFIRMABLE,
                    )
                ],
            )

        order.refresh_from_db()
        return OrderConfirm(order=order, errors=[])


class OrderMarkAsPaid(relay.ClientIDMutation):
    """Manually mark an order as paid. Staff only."""

    class Input:
        id = graphene.ID(required=True)
        payment_reference = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    @staff_member_required
    def mutate_and_get_payload(
        cls, root, info, id, payment_reference=None
    ):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderMarkAsPaid(order=None, errors=[error])

        user = (
            info.context.user
            if info.context.user.is_authenticated
            else None
        )

        try:
            mark_order_as_paid(
                order,
                payment_reference=payment_reference,
                user=user,
            )
        except Exception as e:
            return OrderMarkAsPaid(
                order=order,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.PAYMENT_ERROR,
                    )
                ],
            )

        order.refresh_from_db()
        return OrderMarkAsPaid(order=order, errors=[])


class OrderFulfill(relay.ClientIDMutation):
    """Create a fulfillment for one or more order lines."""

    class Input:
        order_id = graphene.ID(required=True)
        lines = graphene.List(
            graphene.NonNull(OrderFulfillLineInput),
            required=True,
        )
        tracking_number = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    fulfillment = graphene.Field(FulfillmentNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, order_id, lines, tracking_number=""
    ):
        order, error = _get_order_or_error(order_id)
        if error is not None:
            return OrderFulfill(
                order=None, fulfillment=None, errors=[error]
            )

        line_inputs = []
        errors = []

        for i, line in enumerate(lines):
            order_line, line_error = _get_order_line_or_error(
                line.order_line_id, order
            )
            if line_error is not None:
                line_error.field = f"lines[{i}].orderLineId"
                errors.append(line_error)
                continue

            try:
                quantity_decimal = Decimal(str(line.quantity))
            except Exception:
                errors.append(
                    OrderError(
                        message="Invalid quantity.",
                        code=OrderErrorCode.INVALID_QUANTITY,
                        field=f"lines[{i}].quantity",
                    )
                )
                continue

            line_inputs.append(
                FulfillmentLineInput(
                    order_line=order_line,
                    quantity=quantity_decimal,
                )
            )

        if errors:
            return OrderFulfill(
                order=order, fulfillment=None, errors=errors
            )

        user = (
            info.context.user
            if info.context.user.is_authenticated
            else None
        )

        try:
            fulfillment = create_fulfillment(
                order,
                line_inputs,
                tracking_number=tracking_number or "",
                user=user,
            )
        except FulfillmentNotPossible as e:
            return OrderFulfill(
                order=order,
                fulfillment=None,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.FULFILLMENT_NOT_POSSIBLE,
                    )
                ],
            )
        except FulfillmentError as e:
            return OrderFulfill(
                order=order,
                fulfillment=None,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.INVALID,
                    )
                ],
            )

        order.refresh_from_db()
        return OrderFulfill(
            order=order, fulfillment=fulfillment, errors=[]
        )


class OrderCancelFulfillment(relay.ClientIDMutation):
    """Cancel a fulfillment and return quantities to stock."""

    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    fulfillment = graphene.Field(FulfillmentNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, reason=""):
        fulfillment, error = _get_fulfillment_or_error(id)
        if error is not None:
            return OrderCancelFulfillment(
                order=None, fulfillment=None, errors=[error]
            )

        order = fulfillment.order
        user = (
            info.context.user
            if info.context.user.is_authenticated
            else None
        )

        try:
            cancel_fulfillment(
                fulfillment, user=user, reason=reason or ""
            )
        except FulfillmentError as e:
            return OrderCancelFulfillment(
                order=order,
                fulfillment=fulfillment,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.CANNOT_CANCEL_FULFILLMENT,
                    )
                ],
            )

        order.refresh_from_db()
        fulfillment.refresh_from_db()
        return OrderCancelFulfillment(
            order=order, fulfillment=fulfillment, errors=[]
        )


class OrderStartPayment(relay.ClientIDMutation):
    """
    Create and enqueue a PaymentExecution for an order's Payment.

    Used for retry flows and for clients that disable auto-execution.
    If the order has no Payment yet, one is created first.
    """

    class Input:
        id = graphene.ID(required=True)
        provider = graphene.String(required=True)
        route_type = graphene.String(required=True)
        idempotency_key = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    payment_execution_id = graphene.ID()
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, id, provider, route_type, idempotency_key=None
    ):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderStartPayment(
                order=None, payment_execution_id=None, errors=[error]
            )

        if not order.payment_id:
            try:
                create_payment_for_order(order)
            except Exception as exc:
                return OrderStartPayment(
                    order=order,
                    payment_execution_id=None,
                    errors=[
                        OrderError(
                            message=str(exc),
                            code=OrderErrorCode.PAYMENT_ERROR,
                        )
                    ],
                )
            order.refresh_from_db()

        try:
            execution = create_execution_for_order_payment(
                order,
                provider=provider,
                route_type=route_type,
                idempotency_key=idempotency_key,
            )
        except OrderPaymentError as exc:
            return OrderStartPayment(
                order=order,
                payment_execution_id=None,
                errors=[
                    OrderError(
                        message=str(exc),
                        code=OrderErrorCode.PAYMENT_ERROR,
                    )
                ],
            )

        execution_gid = to_global_id(
            "PaymentExecutionNode", str(execution.pk)
        )

        order.refresh_from_db()
        return OrderStartPayment(
            order=order,
            payment_execution_id=execution_gid,
            errors=[],
        )


class OrderRefund(relay.ClientIDMutation):
    """
    Refund an order. Staff only.

    Creates the OrderGrantedRefund intent and, if `execute=True`,
    immediately enqueues the refund provider execution.
    """

    class Input:
        id = graphene.ID(required=True)
        amount = graphene.Decimal(required=False)
        reason = graphene.String(required=False)
        execute = graphene.Boolean(
            default_value=True,
            description=(
                "If true, immediately enqueue refund execution via "
                "the order's channel provider."
            ),
        )
        provider = graphene.String(
            required=False,
            description="Provider to use. Required when execute=True.",
        )

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    @staff_member_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        id,
        amount=None,
        reason="",
        execute=True,
        provider=None,
    ):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderRefund(order=None, errors=[error])

        try:
            create_refund_for_order(
                order,
                amount=amount,
                reason=reason or "",
                user=info.context.user,
            )
        except OrderNotRefundable as exc:
            return OrderRefund(
                order=order,
                errors=[
                    OrderError(
                        message=str(exc),
                        code=OrderErrorCode.NOT_REFUNDABLE,
                    )
                ],
            )
        except RefundAmountInvalid as exc:
            return OrderRefund(
                order=order,
                errors=[
                    OrderError(
                        message=str(exc),
                        code=OrderErrorCode.REFUND_AMOUNT_INVALID,
                    )
                ],
            )
        except RefundError as exc:
            return OrderRefund(
                order=order,
                errors=[
                    OrderError(
                        message=str(exc),
                        code=OrderErrorCode.PAYMENT_ERROR,
                    )
                ],
            )

        if execute:
            if not provider:
                return OrderRefund(
                    order=order,
                    errors=[
                        OrderError(
                            message=(
                                "provider is required when execute=True."
                            ),
                            code=OrderErrorCode.REQUIRED,
                            field="provider",
                        )
                    ],
                )
            try:
                execute_refund_for_order(
                    order,
                    provider=provider,
                )
            except RefundError as exc:
                return OrderRefund(
                    order=order,
                    errors=[
                        OrderError(
                            message=str(exc),
                            code=OrderErrorCode.PAYMENT_ERROR,
                        )
                    ],
                )

        order.refresh_from_db()
        return OrderRefund(order=order, errors=[])


# =====================================================================
# AGGREGATE
# =====================================================================


class OrderMutations(graphene.ObjectType):
    """Order mutation root."""

    order_cancel = OrderCancel.Field()
    order_confirm = OrderConfirm.Field()
    order_mark_as_paid = OrderMarkAsPaid.Field()
    order_fulfill = OrderFulfill.Field()
    order_cancel_fulfillment = OrderCancelFulfillment.Field()
    order_start_payment = OrderStartPayment.Field()
    order_refund = OrderRefund.Field()


__all__ = [
    "OrderMutations",
    "OrderCancel",
    "OrderConfirm",
    "OrderMarkAsPaid",
    "OrderFulfill",
    "OrderFulfillLineInput",
    "OrderCancelFulfillment",
    "OrderStartPayment",
    "OrderRefund",
]