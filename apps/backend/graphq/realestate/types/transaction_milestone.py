from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType
from realestate.models  import TransactionMilestone

class TransactionMilestoneNode(OptimizedDjangoObjectType):
    class Meta:
        model = TransactionMilestone
        fields = "__all__"
        filter_fields = {
            "transaction": ["exact"],
            "name": ["exact", "icontains"],
            "due_date": ["exact", "lt", "gt"],
            "completed_date": ["exact", "lt", "gt"],
            "required": ["exact"],
        }
        interfaces = (Node,)
