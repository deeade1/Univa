import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.utils import timezone

from graphq.ecommerce.types.shipping import (
   ShippingZoneNode,
   ShippingMethodNode,
   ShippingMethodChannelListingNode,
   ShippingMethodPostalCodeRuleNode,
   ShippingMethodTranslationNode
)


# =============================================================================
# Schema Registration
# =============================================================================


class ShippingQuery(graphene.ObjectType):
#     # Node queries
   shipping_zone = Node.Field(ShippingZoneNode)
   all_shipping_zones = DjangoFilterConnectionField(ShippingZoneNode)
   shipping_method = Node.Field(ShippingMethodNode)
   all_shipping_methods = DjangoFilterConnectionField(ShippingMethodNode)
   shipping_method_channel_listing = Node.Field(ShippingMethodChannelListingNode)
   all_shipping_method_channel_listings = DjangoFilterConnectionField(ShippingMethodChannelListingNode)
   shipping_method_postal_code_rule = Node.Field(ShippingMethodPostalCodeRuleNode)
   all_shipping_method_postal_code_rules = DjangoFilterConnectionField(ShippingMethodPostalCodeRuleNode)
   shipping_method_translation = Node.Field(ShippingMethodTranslationNode)
   all_shipping_method_translation = DjangoFilterConnectionField(ShippingMethodTranslationNode)
   