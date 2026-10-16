import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from investors.models import (
    Investor, 
    InvestmentOpportunity, 
    InvestmentCommitment,
    Investment
)
from investors.models.plan import InvestmentPlan


class InvestorNode(DjangoObjectType):
    class Meta:
        model = Investor
        fields = (
            "id",
            "reference",
            "status",
            "display_name",
            "metadata",
            "created_at",
            "updated_at",
        )
        filter_fields = {
            "reference": ["exact", "icontains", "istartswith"],
            "status": ["exact"],
            "display_name": ["exact", "icontains", "istartswith"],
        }
        interfaces = (Node,)


class InvestmentOpportunityNode(DjangoObjectType):
    class Meta:
        model = InvestmentOpportunity
        fields = (
            "id",
            "reference",
            "name",
            "description",
            "currency",
            "minimum_amount",
            "maximum_amount",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        )
        filter_fields = {
            "reference": ["exact", "icontains", "istartswith"],
            "name": ["exact", "icontains", "istartswith"],
            "status": ["exact"],
            "currency": ["exact"],
        }
        interfaces = (Node,)
        

class InvestmentPlanNode(DjangoObjectType):
    class Meta:
        model = InvestmentPlan
        fields = (
            "id",
            "opportunity",
            "reference",
            "name",
            "description",
            "status",
            "minimum_amount",
            "maximum_amount",
            "duration_days",
            "expected_return_rate",
            "metadata",
            "created_at",
            "updated_at",
        )
        filter_fields = {
            "reference": ["exact", "icontains", "istartswith"],
            "name": ["exact", "icontains", "istartswith"],
            "status": ["exact"],
        }
        interfaces = (Node,)

class InvestmentCommitmentNode(DjangoObjectType):
    class Meta:
        model = InvestmentCommitment
        fields = (
            "id",
            "investor",
            "opportunity",
            "plan",
            "reference",
            "amount",
            "currency",
            "status",
            "expires_at",
            "created_at",
            "updated_at",
        )
        filter_fields = {
            "reference": ["exact", "icontains", "istartswith"],
            "status": ["exact"],
            "currency": ["exact"],
        }
        interfaces = (Node,)
        
class InvestmentNode(DjangoObjectType):
    class Meta:
        model = Investment
        fields = (
            "id",
            "investor",
            "opportunity",
            "plan",
            "commitment",
            "reference",
            "amount",
            "currency",
            "status",
            "started_at",
            "matured_at",
            "closed_at",
            "cancelled_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        filter_fields = {
            "reference": ["exact", "icontains", "istartswith"],
            "status": ["exact"],
            "currency": ["exact"],
        }
        interfaces = (Node,)