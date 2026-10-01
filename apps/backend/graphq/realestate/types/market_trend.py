# graphq/realestate/types/market_trend.py

from graphene_django import DjangoObjectType
from graphene import Node
from graphq.realestate.filters import MarketTrendFilter
from realestate.models import MarketTrend

class MarketTrendNode(DjangoObjectType):
    class Meta:
        model = MarketTrend
        interfaces = (Node,)
        fields = "__all__"
        filterset_class = MarketTrendFilter