import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.utils import timezone

from graphq.ecommerce.types.warehouse import ( 
   WarehouseNode,
   ChannelWarehouseNode
)


# =============================================================================
# Schema Registration
# =============================================================================


class WarehouseQuery(graphene.ObjectType):
   # Node queries
   warehouse = Node.Field(WarehouseNode)
   all_warehouses = DjangoFilterConnectionField(WarehouseNode)
   channel_warehouse = Node.Field(ChannelWarehouseNode)
   all_channel_warehouses = DjangoFilterConnectionField(ChannelWarehouseNode)