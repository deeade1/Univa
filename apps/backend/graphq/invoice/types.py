import graphene
from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from invoice.models import Invoice


class InvoiceNode(OptimizedDjangoObjectType):
    class Meta:
        model = Invoice
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "number": ["exact", "icontains", "istartswith"],
            "created": ["exact", "gt", "lt"],
            "order": ["exact"],
        }

    @staticmethod
    def resolve_order(root, info):
        # Only use query() if you need optimization, otherwise just return the object
        return root.order
    
    


class InvoiceErrorCode(graphene.Enum):
    INVALID_STATUS = "INVALID_STATUS"
    NOT_READY = "NOT_READY"
    URL_NOT_SET = "URL_NOT_SET"
    NUMBER_NOT_SET = "NUMBER_NOT_SET"
    EMAIL_NOT_SET = "EMAIL_NOT_SET"