import graphene
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.ecommerce.types.order import (
    FulfillmentLineNode, 
    FulfillmentNode,
    OrderEventNode, 
    OrderGrantedRefundNode,
    OrderLineNode, 
    OrderNode
)
from ecommerce.models.order import (
    Fulfillment, 
    FulfillmentLine, 
    Order, 
    OrderEvent,
    OrderGrantedRefund, 
    OrderLine
)


# --- Helper ---
def get_instance_or_error(model, id, name="object"):
    """Decode Relay global ID and fetch instance or raise GraphQLError."""
    try:
        _, pk = from_global_id(id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{name.capitalize()} not found")
    except Exception:
        raise GraphQLError(f"Invalid {name} ID")


# ----------------------------
# ORDER MUTATIONS
# ----------------------------

class CreateOrder(relay.ClientIDMutation):
    class Input:
        number = graphene.String(required=True)
        user_email = graphene.String(required=False)
        currency = graphene.String(required=True)
        channel_id = graphene.ID(required=False)

    order = graphene.Field(OrderNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        order = Order.objects.create(
            number=input["number"],
            user_email=input.get("user_email"),
            currency=input["currency"],
        )
        if input.get("channel_id"):
            from channel.models import Channel
            _, channel_pk = from_global_id(input["channel_id"])
            order.channel_id = channel_pk
            order.save(update_fields=["channel_id"])
        return CreateOrder(order=order, success=True)


class UpdateOrder(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        user_email = graphene.String()
        status = graphene.String()
        currency = graphene.String()

    order = graphene.Field(OrderNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        order = get_instance_or_error(Order, input["id"], "order")
        for field, value in input.items():
            if field != "id" and value is not None:
                setattr(order, field, value)
        order.save()
        return UpdateOrder(order=order, success=True)


class DeleteOrder(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        order = get_instance_or_error(Order, input["id"], "order")
        order.delete()
        return DeleteOrder(success=True)


# ----------------------------
# ORDER LINE MUTATIONS
# ----------------------------

class CreateOrderLine(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        product_sku = graphene.String(required=True)
        quantity = graphene.Int(required=True)
        unit_price = graphene.Float(required=True)

    order_line = graphene.Field(OrderLineNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        _, order_pk = from_global_id(input["order_id"])
        line = OrderLine.objects.create(
            order_id=order_pk,
            product_sku=input["product_sku"],
            quantity=input["quantity"],
            unit_price_amount=input["unit_price"],
        )
        return CreateOrderLine(order_line=line, success=True)


class UpdateOrderLine(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        quantity = graphene.Int()
        unit_price = graphene.Float()

    order_line = graphene.Field(OrderLineNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        line = get_instance_or_error(OrderLine, input["id"], "order line")
        if input.get("quantity") is not None:
            line.quantity = input["quantity"]
        if input.get("unit_price") is not None:
            line.unit_price_amount = input["unit_price"]
        line.save()
        return UpdateOrderLine(order_line=line, success=True)


class DeleteOrderLine(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        line = get_instance_or_error(OrderLine, input["id"], "order line")
        line.delete()
        return DeleteOrderLine(success=True)


# ----------------------------
# FULFILLMENT MUTATIONS
# ----------------------------

class CreateFulfillment(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        tracking_number = graphene.String(required=False)

    fulfillment = graphene.Field(FulfillmentNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        _, order_pk = from_global_id(input["order_id"])
        fulfillment = Fulfillment.objects.create(
            order_id=order_pk, tracking_number=input.get("tracking_number")
        )
        return CreateFulfillment(fulfillment=fulfillment, success=True)


class UpdateFulfillment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        tracking_number = graphene.String()
        status = graphene.String()

    fulfillment = graphene.Field(FulfillmentNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        fulfillment = get_instance_or_error(Fulfillment, input["id"], "fulfillment")
        for field, value in input.items():
            if field != "id" and value is not None:
                setattr(fulfillment, field, value)
        fulfillment.save()
        return UpdateFulfillment(fulfillment=fulfillment, success=True)


class DeleteFulfillment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        fulfillment = get_instance_or_error(Fulfillment, input["id"], "fulfillment")
        fulfillment.delete()
        return DeleteFulfillment(success=True)


# ----------------------------
# ORDER GRANTED REFUND MUTATIONS
# ----------------------------

class CreateOrderGrantedRefund(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        amount = graphene.Float(required=True)
        reason = graphene.String(required=False)

    refund = graphene.Field(OrderGrantedRefundNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        _, order_pk = from_global_id(input["order_id"])
        refund = OrderGrantedRefund.objects.create(
            order_id=order_pk,
            amount_amount=input["amount"],
            reason=input.get("reason", ""),
        )
        return CreateOrderGrantedRefund(refund=refund, success=True)


class DeleteOrderGrantedRefund(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        refund = get_instance_or_error(OrderGrantedRefund, input["id"], "refund")
        refund.delete()
        return DeleteOrderGrantedRefund(success=True)


# ----------------------------
# ORDER EVENT MUTATIONS
# ----------------------------

class CreateOrderEvent(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        type = graphene.String(required=True)
        message = graphene.String(required=False)

    event = graphene.Field(OrderEventNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        _, order_pk = from_global_id(input["order_id"])
        event = OrderEvent.objects.create(
            order_id=order_pk,
            type=input["type"],
            message=input.get("message", ""),
            user=getattr(info.context, "user", None),
        )
        return CreateOrderEvent(event=event, success=True)


class DeleteOrderEvent(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        event = get_instance_or_error(OrderEvent, input["id"], "order event")
        event.delete()
        return DeleteOrderEvent(success=True)


# ----------------------------
# ROOT MUTATION GROUP
# ----------------------------

class OrderMutations(graphene.ObjectType):
    # Order
    create_order = CreateOrder.Field()
    update_order = UpdateOrder.Field()
    delete_order = DeleteOrder.Field()

    # Order Lines
    create_order_line = CreateOrderLine.Field()
    update_order_line = UpdateOrderLine.Field()
    delete_order_line = DeleteOrderLine.Field()

    # Fulfillment
    create_fulfillment = CreateFulfillment.Field()
    update_fulfillment = UpdateFulfillment.Field()
    delete_fulfillment = DeleteFulfillment.Field()

    # Refunds
    create_order_granted_refund = CreateOrderGrantedRefund.Field()
    delete_order_granted_refund = DeleteOrderGrantedRefund.Field()

    # Events
    create_order_event = CreateOrderEvent.Field()
    delete_order_event = DeleteOrderEvent.Field()
