import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphene import Node
from investors.models import (
    Investor, 
    InvestmentOpportunity, 
    InvestmentPlan,
    InvestmentCommitment,
)
from graphq.investors.types import (
    InvestorNode,
    InvestmentOpportunityNode,
    InvestmentPlanNode,
    InvestmentCommitmentNode,
)
from investors.models import InvestmentPlan
from graphq.investors.types import InvestmentPlanNode

class InvestorQueries(graphene.ObjectType):
    investor = Node.Field(InvestorNode)
    all_investors = DjangoFilterConnectionField(InvestorNode)

    investment_opportunity = Node.Field(InvestmentOpportunityNode)
    all_investment_opportunities = DjangoFilterConnectionField(
        InvestmentOpportunityNode,
    )
    
    investment_plan = Node.Field(InvestmentPlanNode)

    all_investment_plans = DjangoFilterConnectionField(
        InvestmentPlanNode,
    )
    
    investment_commitment = Node.Field(
        InvestmentCommitmentNode,
    )

    all_investment_commitments = DjangoFilterConnectionField(
        InvestmentCommitmentNode,
    )



    def resolve_all_investors(self, info, **kwargs):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        return Investor.objects.select_related("user").all()

    def resolve_all_investment_opportunities(self, info, **kwargs):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        return InvestmentOpportunity.objects.all()
    
    def resolve_all_investment_plans(self, info, **kwargs):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        return InvestmentPlan.objects.select_related(
            "opportunity",
        ).all()
        
    def resolve_all_investment_commitments(self, info, **kwargs):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        return InvestmentCommitment.objects.select_related(
            "investor",
            "opportunity",
            "plan",
        ).all()
