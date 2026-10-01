# graphq/realestate/types/property_proximity.py

from graphene_django import DjangoObjectType
from graphene import Node
from graphq.realestate.filters import PropertyProximityFilter

from realestate.models import  PropertyProximity
class PropertyProximityNode(DjangoObjectType):
    class Meta:
        model = PropertyProximity
        interfaces = (Node,)
        fields = "__all__"
        filterset_class = PropertyProximityFilter
