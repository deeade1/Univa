from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from realestate.models  import Neighborhood
from graphene_gis.converter import gis_converter

class NeighborhoodNode(OptimizedDjangoObjectType):
    class Meta:
        model = Neighborhood
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains"],
            "avg_price": ["exact", "lt", "gt"],
            "school_rating": ["exact", "lt", "gt"],
            "crime_rate": ["exact", "lt", "gt"],
            "amenities_score": ["exact", "lt", "gt"],
            
        }
        interfaces = (Node,)
    


