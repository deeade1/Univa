from graphene_django import DjangoObjectType
from graphene import Node
from realestate.models import CommissionPlan
    
class CommissionPlanNode(DjangoObjectType):
    class Meta:
        model = CommissionPlan
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains", "istartswith"],
            "plan_type": ["exact", "icontains"],
            "min_amount": ["gte", "lte"],
            "max_amount": ["gte", "lte"],
            "is_active": ["exact"],
            
        }  
 
 