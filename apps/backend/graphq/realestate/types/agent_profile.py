from graphene_django import DjangoObjectType
from graphene import Node
from realestate.models  import AgentProfile

class AgentProfileNode(DjangoObjectType):
    """
    GraphQL type for AgentProfile - Public/profile information.
    This is what clients see and what's displayed publicly.
    """
    
    class Meta:
        model = AgentProfile
        fields = "__all__"
        filter_fields = {
            "realestate_agent_profile": ["exact"],
            "company_name": ["exact", "icontains"],
            "created_at": ["gte", "lte"],
           
        }
        interfaces = (Node,)
    
    