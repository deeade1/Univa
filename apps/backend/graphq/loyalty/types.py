# graphq/loyalty/types.py

import graphene
from graphene import Node
from graphene_django.types import DjangoObjectType

from loyalty.models import (
    LoyaltyHistory,
    LoyaltyRewardTier,
    LoyaltyReward,
)


class LoyaltyHistoryNode(DjangoObjectType):
    class Meta:
        model = LoyaltyHistory
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "reward": ["exact", "icontains"],
            "date_redeemed": ["exact", "year__gt", "year__lt"],
            "user__email": ["icontains"],
        }


class LoyaltyRewardTierNode(DjangoObjectType):
    class Meta:
        model = LoyaltyRewardTier
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "points_needed": ["exact", "gte", "lte"],
            "reward": ["exact", "icontains"],
            "description": ["icontains"],
            "active": ["exact"],
        }


class LoyaltyRewardNode(DjangoObjectType):
    class Meta:
        model = LoyaltyReward
        interfaces = (Node,)
        fields = [
            "id", "user", "reward_type", "discount_percent",
            "expires", "created_at",
        ]
        filter_fields = {
            "user": ["exact"],
            "reward_type": ["exact"],
            "expires": ["exact", "gte", "lte"],
        }