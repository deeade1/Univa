'''import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from accounts.models import MagicLoginToken


class MagicLoginTokenNode(DjangoObjectType):
    class Meta:
        model = MagicLoginToken
        fields = "__all__"
        filter_fields = {
            '': ['exact', 'icontains', 'istartswith'],
            '': ['exact', 'icontains'],
            '': ['exact'],
            '': ['exact'],
        }
        interfaces = (relay.Node, )'''