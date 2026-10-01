# graphq/warehouse/mutations.py
import graphene
from graphene import relay
from django.db import transaction
from graphql_relay import from_global_id 
from graphql import GraphQLError
from univa_jwt.decorators import login_required

from core.exceptions import InsufficientStock
from graphq.ecommerce.types.warehouse import (
    ChannelWarehouseNode,
    WarehouseNode
)
from graphq.ecommerce.types.inventory import (
    AllocationNode,
    PreorderAllocationNode, 
    PreorderReservationNode,
    ReservationNode, 
    StockNode
)
from graphq.ecommerce.types.product import ProductVariantNode
from graphq.ecommerce.types.checkout import CheckoutNode
from graphq.ecommerce.types.order import OrderNode

from ecommerce.models.warehouse import (
    Warehouse,
    ChannelWarehouse
)
from ecommerce.models.inventory import (
    Stock,
    Reservation,
    PreorderAllocation,
    PreorderReservation,
)
from ecommerce.services.warehouse.services import WarehouseService  


# ============================================================================
# INPUT TYPES
# ============================================================================

class WarehouseInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    address_id = graphene.ID(required=True)
    email = graphene.String()
    click_and_collect_option = graphene.String()
    is_private = graphene.Boolean()
    capacity_total = graphene.Int()
    timezone = graphene.String()
    operating_hours_start = graphene.String()
    operating_hours_end = graphene.String()


class StockInput(graphene.InputObjectType):
    warehouse_id = graphene.ID(required=True)
    product_variant_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)
    quantity_allocated = graphene.Int()


class StockAdjustmentInput(graphene.InputObjectType):
    warehouse_id = graphene.ID(required=True)
    product_variant_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)
    reason = graphene.String()


class ReservationInput(graphene.InputObjectType):
    checkout_line_id = graphene.ID(required=True)
    stock_id = graphene.ID(required=True)
    quantity_reserved = graphene.Int(required=True)
    reserved_until = graphene.DateTime(required=True)


class ChannelWarehouseInput(graphene.InputObjectType):
    channel_id = graphene.ID(required=True)
    warehouse_id = graphene.ID(required=True)
    sort_order = graphene.Int()


class PreorderAllocationInput(graphene.InputObjectType):
    order_line_id = graphene.ID(required=True)
    product_variant_channel_listing_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)


class PreorderReservationInput(graphene.InputObjectType):
    checkout_line_id = graphene.ID(required=True)
    product_variant_channel_listing_id = graphene.ID(required=True)
    quantity_reserved = graphene.Int(required=True)
    reserved_until = graphene.DateTime(required=True)


# ============================================================================
# BASE MUTATION CLASS
# ============================================================================

class BaseWarehouseMutation:
    """Base class for warehouse mutations with common error handling."""
    
    @classmethod
    def get_instance_or_error(cls, model, id_value, error_msg: str):
        """Get instance or raise GraphQLError."""
        try:
            _, pk = from_global_id(id_value)
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise GraphQLError(error_msg)
        except (ValueError, TypeError):
            raise GraphQLError(f"Invalid ID format: {id_value}")


# ============================================================================
# WAREHOUSE CRUD MUTATIONS
# ============================================================================

class WarehouseCreate(relay.ClientIDMutation, BaseWarehouseMutation):
    warehouse = graphene.Field(WarehouseNode)

    class Input:
        input = WarehouseInput(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, input):
        try:
            warehouse = Warehouse.objects.create(**input)
            return WarehouseCreate(warehouse=warehouse)
        except Exception as e:
            raise GraphQLError(f"Warehouse creation failed: {str(e)}")


class WarehouseUpdate(relay.ClientIDMutation, BaseWarehouseMutation):
    warehouse = graphene.Field(WarehouseNode)

    class Input:
        id = graphene.ID(required=True)
        input = WarehouseInput(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, id, input):
        warehouse = cls.get_instance_or_error(Warehouse, id, "Warehouse not found")
        for field, value in input.items():
            if value is not None:
                setattr(warehouse, field, value)
        warehouse.save()
        return WarehouseUpdate(warehouse=warehouse)


class WarehouseDelete(relay.ClientIDMutation, BaseWarehouseMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, id):
        warehouse = cls.get_instance_or_error(Warehouse, id, "Warehouse not found")
        warehouse.delete()
        return WarehouseDelete(success=True)




# ============================================================================
# CHANNEL WAREHOUSE MUTATIONS
# ============================================================================

class ChannelWarehouseCreate(relay.ClientIDMutation, BaseWarehouseMutation):
    channel_warehouse = graphene.Field(ChannelWarehouseNode)

    class Input:
        input = ChannelWarehouseInput(required=True)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        channel = cls.get_instance_or_error(Channel, input.channel_id, "Channel not found")
        warehouse = cls.get_instance_or_error(Warehouse, input.warehouse_id, "Warehouse not found")
        
        channel_warehouse, created = ChannelWarehouse.objects.get_or_create(
            channel=channel,
            warehouse=warehouse,
            defaults={'sort_order': input.get('sort_order', 0)}
        )
        
        if not created:
            raise GraphQLError("Channel-warehouse relationship already exists")
        
        return ChannelWarehouseCreate(channel_warehouse=channel_warehouse)


class ChannelWarehouseDelete(relay.ClientIDMutation, BaseWarehouseMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        channel_warehouse = cls.get_instance_or_error(
            ChannelWarehouse, id, "Channel-warehouse relationship not found"
        )
        channel_warehouse.delete()
        return ChannelWarehouseDelete(success=True)


# ============================================================================
# ROOT MUTATION
# ============================================================================

class WarehouseMutations(graphene.ObjectType):
    """Root warehouse mutations."""
    
    # Warehouse CRUD
    create_warehouse = WarehouseCreate.Field()
    update_warehouse = WarehouseUpdate.Field()
    delete_warehouse = WarehouseDelete.Field()
    # Channel warehouse
    create_channel_warehouse = ChannelWarehouseCreate.Field()
    delete_channel_warehouse = ChannelWarehouseDelete.Field()
    
   