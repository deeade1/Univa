import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.giftcard import ( 
   GiftCardNode,
   GiftCardTagNode,
   GiftCardEventNode,
                                    
)
# =============================================================================
# Schema Registration
# =============================================================================


class GiftCardQuery(graphene.ObjectType):
    # Node queries
    gift_card = Node.Field(GiftCardNode)
    all_gift_cards = DjangoFilterConnectionField(GiftCardNode)
    gift_card_tag = Node.Field(GiftCardTagNode)
    all_gift_card_tags = DjangoFilterConnectionField(GiftCardTagNode)
    gift_card_event = Node.Field(GiftCardEventNode)
    all_gift_card_events = DjangoFilterConnectionField(GiftCardEventNode)