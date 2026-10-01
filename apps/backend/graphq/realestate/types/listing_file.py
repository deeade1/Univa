from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene import Node
from realestate.models  import ListingFile

class ListingFileNode(OptimizedDjangoObjectType):
    class Meta:
        model = ListingFile
        fields = "__all__"
        filter_fields = {
            #"files": ["exact"],
            "name": ["exact", "icontains"],
            "created": ["gte", "lte"],
            "updated": ["gte", "lte"],
            "for_customer": ["exact"],
        }
        interfaces = (Node,)

