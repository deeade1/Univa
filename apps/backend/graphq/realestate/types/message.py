from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from realestate.models  import Message

class MessageNode(OptimizedDjangoObjectType):
    class Meta:
        model = Message
        fields = "__all__"
        filter_fields = {
            "thread": ["exact"],
            "sender": ["exact"],
            'content': ['exact', 'icontains'],
            "read": ["exact"],
            "timestamp": ["exact", "lt", "gt"],
        }
        interfaces = (Node,)

 