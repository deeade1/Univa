# graphq/realestate/types.py
from graphene_django import DjangoObjectType
from graphene import Node
from graphene_gis.converter import gis_converter 
from realestate.models import Client 
  
class ClientNode(DjangoObjectType):

    class Meta:
        model = Client
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'search_radius_km': ['exact', 'gte', 'lte'],
            'price_range_min': ['exact', 'gte', 'lte'],
            'price_range_max': ['exact', 'gte', 'lte'],
            "user": ["exact"],
        }

    
    
    



