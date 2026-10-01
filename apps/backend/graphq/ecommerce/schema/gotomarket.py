import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.gotomarket import ( 
   MarketItemNode,
   PurchaseNode,
   PurchaseItemNode,                                    
) 
# =============================================================================
# Schema Registration
# =============================================================================

class GoToMarketQuery(graphene.ObjectType):
   # Node queries
   market_item = Node.Field(MarketItemNode)
   all_market_items = DjangoFilterConnectionField(MarketItemNode)
   purchase = Node.Field(PurchaseNode)
   all_purchases = DjangoFilterConnectionField(PurchaseNode)
   purchase_item = Node.Field(PurchaseItemNode)
   all_purchase_items = DjangoFilterConnectionField(PurchaseItemNode)
