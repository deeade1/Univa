import graphene
from graphene import relay
from graphql import GraphQLError
from investors.services.investor import InvestorService
from investors.services.opportunity import OpportunityService
from graphq.utils import get_node_instance
from investors.services.plan import PlanService
from investors.models import (
    Investor,
    InvestmentOpportunity,
    InvestmentPlan,
    InvestmentCommitment,
    Investment
)
from investors.services.commitment import CommitmentService
from graphq.investors.types import (
    InvestorNode,
    InvestmentOpportunityNode,
    InvestmentPlanNode,
    InvestmentCommitmentNode,
)

from investors.lifecycle.commitment import (
    InvestmentCommitmentLifecycle,
)

from investors.services.investment import InvestmentService
from graphq.investors.types import InvestmentNode

def get_investor_from_global_id(global_id):
    return get_node_instance(
        global_id,
        node_type=InvestorNode,
        model=Investor,
        invalid_id_message="Invalid investor ID.",
        not_found_message="Investor not found.",
    )


def get_investment_opportunity_from_global_id(global_id):
    return get_node_instance(
        global_id,
        node_type=InvestmentOpportunityNode,
        model=InvestmentOpportunity,
        invalid_id_message="Invalid investment opportunity ID.",
        not_found_message="Investment opportunity not found.",
    )
def get_investment_plan_from_global_id(global_id):
    return get_node_instance(
        global_id,
        node_type=InvestmentPlanNode,
        model=InvestmentPlan,
        invalid_id_message="Invalid investment plan ID.",
        not_found_message="Investment plan not found.",
    )

def get_investment_commitment_from_global_id(global_id):
    return get_node_instance(
        global_id,
        node_type=InvestmentCommitmentNode,
        model=InvestmentCommitment,
        invalid_id_message="Invalid investment commitment ID.",
        not_found_message="Investment commitment not found.",
    )

def get_investment_from_global_id(global_id):
    return get_node_instance(
        global_id,
        node_type=InvestmentNode,
        model=Investment,
        invalid_id_message="Invalid investment ID.",
        not_found_message="Investment not found.",
    )
    
    
class CreateInvestor(relay.ClientIDMutation):
    class Input:
        reference = graphene.String(required=True)
        display_name = graphene.String()
        metadata = graphene.JSONString()

    investor = graphene.Field(InvestorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError(
                "Authentication required."
            )

        investor = InvestorService.create(
            user=user,
            reference=input["reference"],
            display_name=input.get("display_name", ""),
            metadata=input.get("metadata"),
        )

        return cls(
            investor=investor,
            client_mutation_id=input.get("client_mutation_id"),
        )


class UpdateInvestor(relay.ClientIDMutation):
    """
    Update an existing Investor profile.
    """

    class Input:
        id = graphene.ID(required=True)
        reference = graphene.String()
        display_name = graphene.String()
        metadata = graphene.JSONString()

    investor = graphene.Field(InvestorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        actor = info.context.user

        if not actor.is_authenticated:
            raise GraphQLError("Authentication required.")

        investor = get_investor_from_global_id(input["id"])

        updates = {
            field: input[field]
            for field in ("reference", "display_name", "metadata")
            if field in input
        }

        if not updates:
            raise GraphQLError(
                "At least one field must be provided for update."
            )

        investor = InvestorService.update(
            investor=investor,
            actor=actor,
            **updates,
        )

        return cls(
            investor=investor,
            client_mutation_id=input.get("client_mutation_id"),
        )


class ActivateInvestor(relay.ClientIDMutation):
    """
    Activate an eligible Investor.
    """

    class Input:
        id = graphene.ID(required=True)

    investor = graphene.Field(InvestorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        actor = info.context.user

        if not actor.is_authenticated:
            raise GraphQLError("Authentication required.")

        investor = get_investor_from_global_id(input["id"])

        investor = InvestorService.activate(
            investor=investor,
            actor=actor,
        )

        return cls(
            investor=investor,
            client_mutation_id=input.get("client_mutation_id"),
        )


class SuspendInvestor(relay.ClientIDMutation):
    """
    Suspend an active Investor.
    """

    class Input:
        id = graphene.ID(required=True)

    investor = graphene.Field(InvestorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        actor = info.context.user

        if not actor.is_authenticated:
            raise GraphQLError("Authentication required.")

        investor = get_investor_from_global_id(input["id"])

        investor = InvestorService.suspend(
            investor=investor,
            actor=actor,
        )

        return cls(
            investor=investor,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CloseInvestor(relay.ClientIDMutation):
    """
    Close an Investor profile.
    """

    class Input:
        id = graphene.ID(required=True)

    investor = graphene.Field(InvestorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        actor = info.context.user

        if not actor.is_authenticated:
            raise GraphQLError("Authentication required.")

        investor = get_investor_from_global_id(input["id"])

        investor = InvestorService.close(
            investor=investor,
            actor=actor,
        )

        return cls(
            investor=investor,
            client_mutation_id=input.get("client_mutation_id"),
        )



class CreateInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        reference = graphene.String(required=True)
        name = graphene.String(required=True)
        description = graphene.String()
        currency = graphene.String()
        minimum_amount = graphene.Decimal(required=True)
        maximum_amount = graphene.Decimal()
        metadata = graphene.JSONString()

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = OpportunityService.create(
            reference=input["reference"],
            name=input["name"],
            description=input.get("description", ""),
            currency=input.get("currency", "NGN"),
            minimum_amount=input.get("minimum_amount"),
            maximum_amount=input.get("maximum_amount"),
            metadata=input.get("metadata"),
        )

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class UpdateInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        reference = graphene.String()
        name = graphene.String()
        description = graphene.String()
        currency = graphene.String()
        minimum_amount = graphene.Decimal()
        maximum_amount = graphene.Decimal()
        metadata = graphene.JSONString()

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["id"],
        )

        update_fields = (
            "reference",
            "name",
            "description",
            "currency",
            "minimum_amount",
            "maximum_amount",
            "metadata",
        )

        updates = {
            field: input[field]
            for field in update_fields
            if field in input
        }

        if not updates:
            raise GraphQLError(
                "At least one field must be provided for update."
            )

        opportunity = OpportunityService.update(
            opportunity,
            **updates,
        )

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class OpenInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["id"],
        )
        opportunity = OpportunityService.open(opportunity)

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class PauseInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["id"],
        )
        opportunity = OpportunityService.pause(opportunity)

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CloseInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["id"],
        )
        opportunity = OpportunityService.close(opportunity)

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CancelInvestmentOpportunity(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_opportunity = graphene.Field(InvestmentOpportunityNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["id"],
        )
        opportunity = OpportunityService.cancel(opportunity)

        return cls(
            investment_opportunity=opportunity,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CreateInvestmentPlan(relay.ClientIDMutation):
    class Input:
        opportunity_id = graphene.ID(required=True)
        reference = graphene.String(required=True)
        name = graphene.String(required=True)
        description = graphene.String()
        minimum_amount = graphene.Decimal(required=True)
        maximum_amount = graphene.Decimal()
        duration_days = graphene.Int()
        expected_return_rate = graphene.Decimal()
        metadata = graphene.JSONString()

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["opportunity_id"],
        )

        plan = PlanService.create(
            opportunity=opportunity,
            reference=input["reference"],
            name=input["name"],
            description=input.get("description", ""),
            minimum_amount=input["minimum_amount"],
            maximum_amount=input.get("maximum_amount"),
            duration_days=input.get("duration_days"),
            expected_return_rate=input.get("expected_return_rate"),
            metadata=input.get("metadata"),
        )

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class UpdateInvestmentPlan(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        reference = graphene.String()
        name = graphene.String()
        description = graphene.String()
        minimum_amount = graphene.Decimal()
        maximum_amount = graphene.Decimal()
        duration_days = graphene.Int()
        expected_return_rate = graphene.Decimal()
        metadata = graphene.JSONString()

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        plan = get_node_instance(
            input["id"],
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )

        update_fields = (
            "reference",
            "name",
            "description",
            "minimum_amount",
            "maximum_amount",
            "duration_days",
            "expected_return_rate",
            "metadata",
        )

        updates = {
            field: input[field]
            for field in update_fields
            if field in input
        }

        if not updates:
            raise GraphQLError(
                "At least one field must be provided for update."
            )

        plan = PlanService.update(plan, **updates)

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class ActivateInvestmentPlan(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        plan = get_node_instance(
            input["id"],
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )

        plan = PlanService.activate(plan)

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class PauseInvestmentPlan(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        plan = get_node_instance(
            input["id"],
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )

        plan = PlanService.pause(plan)

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CloseInvestmentPlan(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        plan = get_node_instance(
            input["id"],
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )

        plan = PlanService.close(plan)

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CancelInvestmentPlan(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_plan = graphene.Field(InvestmentPlanNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        plan = get_node_instance(
            input["id"],
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )

        plan = PlanService.cancel(plan)

        return cls(
            investment_plan=plan,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CreateInvestmentCommitment(relay.ClientIDMutation):
    class Input:
        opportunity_id = graphene.ID(required=True)
        plan_id = graphene.ID(required=True)
        reference = graphene.String(required=True)
        amount = graphene.Decimal(required=True)
        currency = graphene.String(required=True)

    investment_commitment = graphene.Field(InvestmentCommitmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        opportunity = get_investment_opportunity_from_global_id(
            input["opportunity_id"],
        )
        plan = get_investment_plan_from_global_id(
            input["plan_id"],
        )

        # Delegate commitment creation to the domain service.
        commitment = CommitmentService.create(
            investor=user,
            opportunity=opportunity,
            plan=plan,
            reference=input["reference"],
            amount=input["amount"],
            currency=input["currency"],
        )

        return cls(
            investment_commitment=commitment,
            client_mutation_id=input.get("client_mutation_id"),
        )

class ConfirmInvestmentCommitment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_commitment = graphene.Field(InvestmentCommitmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        commitment = get_investment_commitment_from_global_id(
            input["id"]
        )

        commitment = InvestmentCommitmentLifecycle.confirm(commitment)

        return cls(
            investment_commitment=commitment,
            client_mutation_id=input.get("client_mutation_id"),
        )


class FundInvestmentCommitment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_commitment = graphene.Field(InvestmentCommitmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        commitment = get_investment_commitment_from_global_id(
            input["id"]
        )

        commitment = InvestmentCommitmentLifecycle.fund(commitment)

        return cls(
            investment_commitment=commitment,
            client_mutation_id=input.get("client_mutation_id"),
        )


class CancelInvestmentCommitment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_commitment = graphene.Field(InvestmentCommitmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        commitment = get_investment_commitment_from_global_id(
            input["id"]
        )

        commitment = InvestmentCommitmentLifecycle.cancel(commitment)

        return cls(
            investment_commitment=commitment,
            client_mutation_id=input.get("client_mutation_id"),
        )


class ExpireInvestmentCommitment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    investment_commitment = graphene.Field(InvestmentCommitmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        commitment = get_investment_commitment_from_global_id(
            input["id"]
        )

        commitment = InvestmentCommitmentLifecycle.expire(commitment)

        return cls(
            investment_commitment=commitment,
            client_mutation_id=input.get("client_mutation_id"),
        )
        
        
class CreateInvestment(relay.ClientIDMutation):
    """
    Create an investment from the authenticated user's funded commitment.

    The commitment is the source of truth for the investor, opportunity,
    plan, amount, and currency.
    """

    class Input:
        commitment_id = graphene.ID(required=True)
        reference = graphene.String(required=True)

    investment = graphene.Field(InvestmentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        commitment = get_investment_commitment_from_global_id(
            input["commitment_id"]
        )

        # Commitment.investor references AUTH_USER_MODEL directly.
        if commitment.investor_id != user.pk:
            raise GraphQLError(
                "You do not have permission to invest using this commitment."
            )

        investment = InvestmentService.create(
            investor=commitment.investor,
            opportunity=commitment.opportunity,
            plan=commitment.plan,
            commitment=commitment,
            reference=input["reference"],
            amount=commitment.amount,
            currency=commitment.currency,
        )

        return cls(
            investment=investment,
            client_mutation_id=input.get("client_mutation_id"),
        )
        
        
class InvestorMutations(graphene.ObjectType):
    # Investor
    create_investor = CreateInvestor.Field()
    update_investor = UpdateInvestor.Field()
    activate_investor = ActivateInvestor.Field()
    suspend_investor = SuspendInvestor.Field()
    close_investor = CloseInvestor.Field()

    # Investment Opportunity
    create_investment_opportunity = (
        CreateInvestmentOpportunity.Field()
    )
    update_investment_opportunity = (
        UpdateInvestmentOpportunity.Field()
    )
    open_investment_opportunity = (
        OpenInvestmentOpportunity.Field()
    )
    pause_investment_opportunity = (
        PauseInvestmentOpportunity.Field()
    )
    close_investment_opportunity = (
        CloseInvestmentOpportunity.Field()
    )
    cancel_investment_opportunity = (
        CancelInvestmentOpportunity.Field()
    )
    # Investment Plan
    create_investment_plan = CreateInvestmentPlan.Field()
    update_investment_plan = UpdateInvestmentPlan.Field()
    activate_investment_plan = ActivateInvestmentPlan.Field()
    pause_investment_plan = PauseInvestmentPlan.Field()
    close_investment_plan = CloseInvestmentPlan.Field()
    cancel_investment_plan = CancelInvestmentPlan.Field()
    create_investment_commitment = CreateInvestmentCommitment.Field()
    
        # Investment Commitment
    create_investment_commitment = (
        CreateInvestmentCommitment.Field()
    )
    confirm_investment_commitment = (
        ConfirmInvestmentCommitment.Field()
    )
    fund_investment_commitment = (
        FundInvestmentCommitment.Field()
    )
    cancel_investment_commitment = (
        CancelInvestmentCommitment.Field()
    )
    expire_investment_commitment = (
        ExpireInvestmentCommitment.Field()
    )
    create_investment = CreateInvestment.Field()