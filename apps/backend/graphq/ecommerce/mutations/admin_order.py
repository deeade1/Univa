# graphq/ecommerce/mutations/admin_order.py

"""
Admin Order GraphQL mutations.

Staff-only operations on orders: force cancel, force fulfill,
update tracking, and add notes.

"Force" means "staff authority", not "bypass the state machine".
Each mutation delegates to the same canonical service functions
the customer path uses. The service still enforces lifecycle rules;
the decorator enforces "staff only".
"""

from __future__ import annotations

from decimal import Decimal

import graphene
from graphene import relay

from ecommerce.models.enums import OrderEvents
from ecommerce.models.enums.errors import OrderErrorCode
from ecommerce.models.order import Fulfillment, Order, OrderEvent
from ecommerce.services.order import (
    FulfillmentError,
    FulfillmentLineInput,
    FulfillmentNotPossible,
    OrderNotCancelable,
    cancel_order,
    create_fulfillment,
)
from graphq.ecommerce.mutations.order import (
    OrderFulfillLineInput,
    _get_fulfillment_or_error,
    _get_order_line_or_error,
    _get_order_or_error,
)
from graphq.ecommerce.types.errors import OrderError
from graphq.ecommerce.types.order import FulfillmentNode, OrderNode
from univa_jwt.decorators import staff_member_required


# =====================================================================
# FORCE CANCEL
# =====================================================================


class OrderForceCancel(relay.ClientIDMutation):
    """
    Staff-only cancel of any order.

    Still respects the state machine: an order that is already
    CANCELED, RETURNED, or EXPIRED cannot be force-cancelled either.
    The staff gate grants authority to act, not the right to break
    invariants.
    """

    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(
            required=False,
            description="Audit reason recorded on the OrderEvent.",
        )

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    @staff_member_required
    def mutate_and_get_payload(cls, root, info, id, reason=""):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderForceCancel(order=None, errors=[error])

        user = info.context.user

        try:
            cancel_order(order, user=user, reason=reason or "")
        except OrderNotCancelable as e:
            return OrderForceCancel(
                order=order,
                errors=[
                    OrderError(
                        message=str(e),
                        code=OrderErrorCode.NOT_CANCELABLE,
                    )
                ],
            )

        order.refresh_from_db()
        return OrderForceCancel(order=order, errors=[])


# =====================================================================
# FORCE FULFILL
# =====================================================================


class OrderForceFulfill(relay.ClientIDMutation):
    """
    Staff-only fulfillment creation.

    Delegates to the same `create_fulfillment` service the customer
    path uses. The service still validates quantity and lifecycle.
    """

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
    @staff_member_required
    def mutate_and_get_payload(
        cls, root, info, order_id, lines, tracking_number=""
    ):
        order, error = _get_order_or_error(order_id)
        if error is not None:
            return OrderForceFulfill(
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
            return OrderForceFulfill(
                order=order, fulfillment=None, errors=errors
            )

        user = info.context.user

        try:
            fulfillment = create_fulfillment(
                order,
                line_inputs,
                tracking_number=tracking_number or "",
                user=user,
            )
        except FulfillmentNotPossible as e:
            return OrderForceFulfill(
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
            return OrderForceFulfill(
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
        return OrderForceFulfill(
            order=order, fulfillment=fulfillment, errors=[]
        )


# =====================================================================
# UPDATE TRACKING
# =====================================================================


class OrderUpdateTracking(relay.ClientIDMutation):
    """
    Staff-only tracking number update.

    Direct single-field write — no service layer for this. If the
    operation grows (carrier integration, multi-tracking), extract
    to a service then.
    """

    class Input:
        fulfillment_id = graphene.ID(required=True)
        tracking_number = graphene.String(required=True)

    fulfillment = graphene.Field(FulfillmentNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    @staff_member_required
    def mutate_and_get_payload(
        cls, root, info, fulfillment_id, tracking_number
    ):
        fulfillment, error = _get_fulfillment_or_error(fulfillment_id)
        if error is not None:
            return OrderUpdateTracking(
                fulfillment=None, errors=[error]
            )

        new_tracking = (tracking_number or "").strip()

        if not new_tracking:
            return OrderUpdateTracking(
                fulfillment=fulfillment,
                errors=[
                    OrderError(
                        message="Tracking number is required.",
                        code=OrderErrorCode.REQUIRED,
                        field="trackingNumber",
                    )
                ],
            )

        fulfillment.tracking_number = new_tracking
        fulfillment.save(update_fields=["tracking_number"])

        OrderEvent.objects.create(
            order=fulfillment.order,
            type=OrderEvents.TRACKING_UPDATED,
            user=info.context.user,
            parameters={
                "fulfillment_id": fulfillment.pk,
                "tracking_number": new_tracking,
            },
        )

        fulfillment.refresh_from_db()
        return OrderUpdateTracking(
            fulfillment=fulfillment, errors=[]
        )


# =====================================================================
# ADD NOTE
# =====================================================================


class OrderAddNote(relay.ClientIDMutation):
    """
    Staff-only note appended to the order's event trail.

    Notes are stored as OrderEvent with type `note_added`. The
    message is preserved in the event's `parameters` payload.
    """

    class Input:
        id = graphene.ID(required=True)
        message = graphene.String(required=True)

    order = graphene.Field(OrderNode)
    errors = graphene.List(
        graphene.NonNull(OrderError), required=True
    )

    @classmethod
    @staff_member_required
    def mutate_and_get_payload(cls, root, info, id, message):
        order, error = _get_order_or_error(id)
        if error is not None:
            return OrderAddNote(order=None, errors=[error])

        text = (message or "").strip()

        if not text:
            return OrderAddNote(
                order=order,
                errors=[
                    OrderError(
                        message="Note message is required.",
                        code=OrderErrorCode.REQUIRED,
                        field="message",
                    )
                ],
            )

        OrderEvent.objects.create(
            order=order,
            type=OrderEvents.NOTE_ADDED,
            user=info.context.user,
            parameters={"message": text},
        )

        order.refresh_from_db()
        return OrderAddNote(order=order, errors=[])


# =====================================================================
# AGGREGATE
# =====================================================================


class AdminOrderMutations(graphene.ObjectType):
    """Admin order mutation root."""

    order_force_cancel = OrderForceCancel.Field()
    order_force_fulfill = OrderForceFulfill.Field()
    order_update_tracking = OrderUpdateTracking.Field()
    order_add_note = OrderAddNote.Field()


__all__ = [
    "AdminOrderMutations",
    "OrderForceCancel",
    "OrderForceFulfill",
    "OrderUpdateTracking",
    "OrderAddNote",
]