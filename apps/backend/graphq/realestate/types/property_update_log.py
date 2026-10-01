from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from realestate.models  import PropertyUpdateLog


class PropertyUpdateLogNode(OptimizedDjangoObjectType):
    class Meta:
        model = PropertyUpdateLog
        fields = "__all__"
        filter_fields = {
            "property__id": ["exact"],
            "updated_by__id": ["exact"],
            "timestamp": ["exact", "lt", "gt"],
        }
        interfaces = (Node,)