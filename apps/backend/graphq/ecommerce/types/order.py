# graphq/ecommerce/types/order.py

"""
GraphQL Nodes for the Order domain.

Exposes Order, OrderLine, Fulfillment, FulfillmentLine, OrderEvent,
OrderGrantedRefund, and OrderTrackingEvent.

Money fields (MoneyField / TaxedMoneyField) auto-convert via the
converters registered in graphq.core.types.money.

Line/fulfillment/event collections are exposed as plain lists —
they are bounded by the order lifetime. For admin pagination over
large result sets, use the top-level connection fields in
`graphq.ecommerce.schema.order`.
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from ecommerce.models.order import (
    Fulfillment,
    FulfillmentLine,
    Order,
    OrderEvent,
    OrderGrantedRefund,
    OrderGrantedRefundLine,
    OrderLine,
    OrderTrackingEvent,
)
from graphq.core.enums import (
    FulfillmentStatusEnum,
    OrderAuthorizeStatusEnum,
    OrderChargeStatusEnum,
    OrderGrantedRefundStatusEnum,
    OrderOriginEnum,
    OrderStatusEnum,
)
from graphq.core.types.money import Money, TaxedMoney
from graphq.core.types.scalars import JSONScalar


# =====================================================================
# ORDER LINE
# =====================================================================


class OrderLineNode(DjangoObjectType):
    """A line item on an order."""

    total_price = graphene.Field(TaxedMoney)
    unit_price = graphene.Field(TaxedMoney)
    undiscounted_unit_price = graphene.Field(TaxedMoney)
    undiscounted_total_price = graphene.Field(TaxedMoney)
    unit_discount = graphene.Field(Money)
    quantity_unfulfilled = graphene.Decimal()

    # `metadata` is a JSONField on the model. Explicit JSONScalar
    # serializes it as a JSON object rather than a JSON string.
    metadata = JSONScalar()

    class Meta:
        model = OrderLine
        interfaces = (Node,)
        fields = (
            "id",
            "order",
            "variant",
            "product_name",
            "variant_name",
            "translated_product_name",
            "translated_variant_name",
            "product_sku",
            "product_variant_id",
            "is_shipping_required",
            "is_gift",
            "is_gift_card",
            "quantity",
            "quantity_fulfilled",
            "quantity_unit",
            "currency",
            "unit_discount",
            "unit_discount_type",
            "unit_discount_reason",
            "unit_discount_value",
            "unit_price",
            "undiscounted_unit_price",
            "total_price",
            "undiscounted_total_price",
            "tax_rate",
            "tax_class_name",
            "voucher_code",
            "created_at",
            # "metadata" declared explicitly above
        )

    def resolve_unit_discount(self, info):
        return self.unit_discount

    def resolve_quantity_unfulfilled(self, info):
        return self.quantity_unfulfilled


# =====================================================================
# FULFILLMENT
# =====================================================================


class FulfillmentLineNode(DjangoObjectType):
    """A line inside a fulfillment."""

    class Meta:
        model = FulfillmentLine
        interfaces = (Node,)
        fields = (
            "id",
            "order_line",
            "fulfillment",
            "quantity",
        )


class FulfillmentNode(DjangoObjectType):
    """A shipment or pickup for an order."""

    status = FulfillmentStatusEnum()

    composed_id = graphene.String()
    total_quantity = graphene.Decimal()
    is_tracking_number_url = graphene.Boolean()
    lines = graphene.List(graphene.NonNull(FulfillmentLineNode))

    metadata = JSONScalar()

    class Meta:
        model = Fulfillment
        interfaces = (Node,)
        fields = (
            "id",
            "fulfillment_order",
            "order",
            # "status" declared explicitly above
            "tracking_number",
            "created_at",
            "shipping_refund_amount",
            "total_refund_amount",
            # "metadata" declared explicitly above
        )

    def resolve_composed_id(self, info):
        return self.composed_id

    def resolve_total_quantity(self, info):
        return self.get_total_quantity()

    def resolve_is_tracking_number_url(self, info):
        return self.is_tracking_number_url

    def resolve_lines(self, info):
        return self.lines.all().order_by("-id")


# =====================================================================
# ORDER EVENT
# =====================================================================


class OrderEventNode(DjangoObjectType):
    """An event in the order's audit trail."""

    type = graphene.String(
        description=(
            "Event type identifier (lowercase, e.g. 'placed', "
            "'canceled', 'fulfillment_fulfilled_items')."
        ),
    )

    # `parameters` is a JSONField on the model.
    parameters = JSONScalar()

    class Meta:
        model = OrderEvent
        interfaces = (Node,)
        fields = (
            "id",
            "date",
            # "type" declared explicitly above
            "order",
            "user",
            # "parameters" declared explicitly above
            "related",
        )


# =====================================================================
# ORDER GRANTED REFUND
# =====================================================================


class OrderGrantedRefundLineNode(DjangoObjectType):
    """A line within a granted refund."""

    class Meta:
        model = OrderGrantedRefundLine
        interfaces = (Node,)
        fields = (
            "id",
            "order_line",
            "quantity",
            "reason",
            "granted_refund",
        )


class OrderGrantedRefundNode(DjangoObjectType):
    """A refund granted against an order."""

    status = OrderGrantedRefundStatusEnum()

    amount = graphene.Field(Money)
    lines = graphene.List(graphene.NonNull(OrderGrantedRefundLineNode))

    class Meta:
        model = OrderGrantedRefund
        interfaces = (Node,)
        fields = (
            "id",
            "created_at",
            "updated_at",
            "currency",
            "reason",
            "user",
            "order",
            "shipping_costs_included",
            # "status" declared explicitly above
        )

    def resolve_lines(self, info):
        return self.lines.all().order_by("id")


# =====================================================================
# ORDER TRACKING EVENT
# =====================================================================


class OrderTrackingEventNode(DjangoObjectType):
    """A real-time tracking event for an order."""

    class Meta:
        model = OrderTrackingEvent
        interfaces = (Node,)
        fields = (
            "id",
            "order",
            "event_type",
            "event_timestamp",
            "location",
            "latitude",
            "longitude",
            "carrier",
            "tracking_number",
            "estimated_delivery",
            "actual_delivery",
            "event_data",
        )


# =====================================================================
# ORDER
# =====================================================================


class OrderNode(DjangoObjectType):
    """A customer order."""

    # --- Enums ----------------------------------------------------------
    status = OrderStatusEnum()
    origin = OrderOriginEnum()
    authorize_status = OrderAuthorizeStatusEnum()
    charge_status = OrderChargeStatusEnum()

    # --- Money ----------------------------------------------------------
    total = graphene.Field(TaxedMoney)
    subtotal = graphene.Field(TaxedMoney)
    undiscounted_total = graphene.Field(TaxedMoney)
    shipping_price = graphene.Field(TaxedMoney)
    undiscounted_shipping_price = graphene.Field(Money)
    base_shipping_price = graphene.Field(Money)
    total_authorized = graphene.Field(Money)
    total_charged = graphene.Field(Money)
    total_balance = graphene.Field(Money)

    # --- Convenience ----------------------------------------------------
    customer_email = graphene.String()
    total_quantity = graphene.Decimal()

    # --- Metadata -------------------------------------------------------
    metadata = JSONScalar()

    # --- Collections ----------------------------------------------------
    lines = graphene.List(graphene.NonNull(OrderLineNode))
    fulfillments = graphene.List(graphene.NonNull(FulfillmentNode))
    events = graphene.List(graphene.NonNull(OrderEventNode))
    granted_refunds = graphene.List(
        graphene.NonNull(OrderGrantedRefundNode)
    )
    tracking_events = graphene.List(
        graphene.NonNull(OrderTrackingEventNode)
    )
    payment = graphene.Field(
        "graphq.payment.canonical.types.PaymentNode",
        description=(
            "The canonical Payment attached to this order, if any."
        ),
    )

    # --- State helpers --------------------------------------------------
    is_fully_paid = graphene.Boolean()
    is_partly_paid = graphene.Boolean()
    is_draft = graphene.Boolean()
    is_unconfirmed = graphene.Boolean()
    is_expired = graphene.Boolean()
    is_open = graphene.Boolean()
    can_cancel = graphene.Boolean()

    class Meta:
        model = Order
        interfaces = (Node,)
        fields = (
            "id",
            "number",
            # "status" declared explicitly above
            # "origin" declared explicitly above
            # "authorize_status" declared explicitly above
            # "charge_status" declared explicitly above
            "created_at",
            "updated_at",
            "expired_at",
            "currency",
            "language_code",
            "user",
            "user_email",
            "billing_address",
            "shipping_address",
            "channel",
            "shipping_method",
            "shipping_method_name",
            "collection_point",
            "collection_point_name",
            "checkout_token",
            "voucher_code",
            "display_gross_prices",
            "customer_note",
            "weight",
            # "metadata" declared explicitly above
        )
        filter_fields = {
            "number": ["exact", "gt", "gte", "lt", "lte"],
            "status": ["exact"],
            "origin": ["exact"],
            "charge_status": ["exact"],
            "authorize_status": ["exact"],
            "created_at": ["exact", "gte", "lte"],
            "updated_at": ["exact", "gte", "lte"],
            "expired_at": ["exact", "gte", "lte", "isnull"],
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "user_email": ["exact", "icontains"],
            "channel": ["exact"],
            "channel__slug": ["exact"],
            "checkout_token": ["exact"],
            "currency": ["exact"],
            "priority_level": ["exact", "gte", "lte"],
            "is_prime": ["exact"],
            "is_business": ["exact"],
            "is_express": ["exact"],
        }

    # --- Money ----------------------------------------------------------

    def resolve_total(self, info):
        return self.total

    def resolve_subtotal(self, info):
        return self.subtotal

    def resolve_undiscounted_total(self, info):
        return self.undiscounted_total

    def resolve_shipping_price(self, info):
        return self.shipping_price

    def resolve_undiscounted_shipping_price(self, info):
        return self.undiscounted_base_shipping_price

    def resolve_base_shipping_price(self, info):
        return self.base_shipping_price

    def resolve_total_authorized(self, info):
        return self.total_authorized

    def resolve_total_charged(self, info):
        return self.total_charged

    def resolve_total_balance(self, info):
        return self.total_balance

    # --- Convenience ----------------------------------------------------

    def resolve_customer_email(self, info):
        return self.get_customer_email()

    def resolve_total_quantity(self, info):
        return self.get_total_quantity()

    # --- Collections ----------------------------------------------------

    def resolve_lines(self, info):
        return self.lines.all().order_by("created_at")

    def resolve_fulfillments(self, info):
        return self.fulfillments.all().order_by("fulfillment_order")

    def resolve_events(self, info):
        return self.events.all().order_by("date")

    def resolve_granted_refunds(self, info):
        return self.granted_refunds.all().order_by("created_at")

    def resolve_tracking_events(self, info):
        return self.tracking_events.all().order_by("event_timestamp")

    # --- State ----------------------------------------------------------

    def resolve_is_fully_paid(self, info):
        return self.is_fully_paid()

    def resolve_is_partly_paid(self, info):
        return self.is_partly_paid()

    def resolve_is_draft(self, info):
        return self.is_draft()

    def resolve_is_unconfirmed(self, info):
        return self.is_unconfirmed()

    def resolve_is_expired(self, info):
        return self.is_expired()

    def resolve_is_open(self, info):
        return self.is_open()

    def resolve_can_cancel(self, info):
        return self.can_cancel()
    def resolve_payment(self, info):
        from ecommerce.services.order.payment import get_order_payment
        return get_order_payment(self)


__all__ = [
    "OrderNode",
    "OrderLineNode",
    "FulfillmentNode",
    "FulfillmentLineNode",
    "OrderEventNode",
    "OrderGrantedRefundNode",
    "OrderGrantedRefundLineNode",
    "OrderTrackingEventNode",
]