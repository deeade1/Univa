import graphene
from django_filters import FilterSet, OrderingFilter
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_optimizer import query

from graphq.invoice.types import InvoiceNode
from invoice.models import Invoice


class InvoiceFilter(FilterSet):
    order_by = OrderingFilter(fields=("pk", "created", "number"))

    class Meta:
        model = Invoice
        fields = {
            "number": ["exact", "icontains", "istartswith"],
            "created": ["exact", "gt", "lt"],
            "order": ["exact"],
        }

class InvoiceQuery(graphene.ObjectType):
    # Connection field with filtering
    all_invoices = DjangoFilterConnectionField(
        InvoiceNode, 
        filterset_class=InvoiceFilter
    )
    
    # Single invoice by ID
    invoice = Node.Field(InvoiceNode)

    @staticmethod
    def resolve_all_invoices(root, info, **kwargs):
        return Invoice.objects.select_related("order").all()