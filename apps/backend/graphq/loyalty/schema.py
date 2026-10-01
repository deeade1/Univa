# graphq/loyalty/schema.py

import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField

from graphq.loyalty.types import (
    LoyaltyHistoryNode,
    LoyaltyRewardTierNode,
    LoyaltyRewardNode,
)


class LoyaltyQuery(graphene.ObjectType):
    loyalty_history = Node.Field(LoyaltyHistoryNode)
    loyalty_reward_tier = Node.Field(LoyaltyRewardTierNode)
    loyalty_reward = Node.Field(LoyaltyRewardNode)

    all_loyalty_history = DjangoFilterConnectionField(LoyaltyHistoryNode)
    all_loyalty_reward_tier = DjangoFilterConnectionField(LoyaltyRewardTierNode)
    all_loyalty_reward = DjangoFilterConnectionField(LoyaltyRewardNode)