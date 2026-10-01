from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from realestate.models  import ListingType

class ListingTypeNode(OptimizedDjangoObjectType):
    class Meta:
        model = ListingType
        fields = "__all__"
        filter_fields = {
            "property_type": ["exact", "icontains"],
            "created": ["gte", "lte"],
            "updated": ["gte", "lte"],
        }
        interfaces = (Node,)