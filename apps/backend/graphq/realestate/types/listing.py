
# graphq/realestate/types/listing.py

from graphene_django import DjangoObjectType
from graphene import Node
from graphq.realestate.filters import ListingFilter
from realestate.models import Listing

class ListingNode(DjangoObjectType):
    class Meta:
        model = Listing
        interfaces = (Node,)
        fields = "__all__"
        filterset_class = ListingFilter
