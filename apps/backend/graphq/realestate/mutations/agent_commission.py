import graphene
from graphene import relay, Boolean, String, Field, ID, Decimal, Int
from django.db import transaction
from graphene import  relay
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphq.realestate.types.agent import AgentNode
from graphq.realestate.types.commission import CommissionPlanNode   
from graphq.realestate.types.agent_commission import AgentCommissionNode
from graphq.realestate.types.transaction import TransactionNode
 
from realestate.models import (
   AgentCommission, 
   CommissionPlan,
   Transaction,
   Agent,
)

# -------------------------
# AgentCommission Mutation
# -------------------------
class AgentCommissionMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=False)
        agent_id = ID(required=True)
        transaction_id = ID(required=True)
        commission_plan_id = ID(required=True)
        calculated_amount = Decimal(required=True)
        paid_amount = Decimal(required=False)
        paid_date = String(required=False)
        notes = String(required=False)

    commission = Field(AgentCommissionNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        agent = Agent.objects.get(pk=from_global_id(input['agent_id'])[1])
        transaction_obj = Transaction.objects.get(pk=from_global_id(input['transaction_id'])[1])
        plan = CommissionPlan.objects.get(pk=from_global_id(input['commission_plan_id'])[1])
        input['agent'] = agent
        input['transaction'] = transaction_obj
        input['commission_plan'] = plan

        commission_id = input.pop('id', None)
        if commission_id:
            commission = AgentCommission.objects.get(pk=from_global_id(commission_id)[1])
            if not commission:
                raise GraphQLError("AgentCommission not found")
            for k, v in input.items():
                setattr(commission, k, v)
            commission.save()
            message = "AgentCommission updated successfully"
        else:
            commission = AgentCommission.objects.create(**input)
            message = "AgentCommission created successfully"

        return cls(commission=commission, success=True, message=message)

# -------------------------
# Update AgentCommission Mutation
# -------------------------
class UpdateAgentCommissionMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)
        agent_id = ID(required=False)
        transaction_id = ID(required=False)
        commission_plan_id = ID(required=False)
        calculated_amount = Decimal(required=False)
        paid_amount = Decimal(required=False)
        paid_date = String(required=False)
        notes = String(required=False)

    commission = Field(AgentCommissionNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # Get the commission instance
        commission_id = input.pop('id')
        commission = AgentCommission.objects.get(pk=from_global_id(commission_id)[1])
        
        if not commission:
            raise GraphQLError("AgentCommission not found")

        # Update agent if provided
        if 'agent_id' in input and input['agent_id']:
            agent = Agent.objects.get(pk=from_global_id(input['agent_id'])[1])
            commission.agent = agent
            input.pop('agent_id')

        # Update transaction if provided
        if 'transaction_id' in input and input['transaction_id']:
            transaction_obj = Transaction.objects.get(pk=from_global_id(input['transaction_id'])[1])
            commission.transaction = transaction_obj
            input.pop('transaction_id')

        # Update commission plan if provided
        if 'commission_plan_id' in input and input['commission_plan_id']:
            plan = CommissionPlan.objects.get(pk=from_global_id(input['commission_plan_id'])[1])
            commission.commission_plan = plan
            input.pop('commission_plan_id')

        # Update remaining fields
        for k, v in input.items():
            if v is not None:  # Only update if value is provided
                setattr(commission, k, v)
        
        commission.save()
        
        return cls(
            commission=commission, 
            success=True, 
            message="AgentCommission updated successfully"
        )


# -------------------------
# Delete AgentCommission Mutation
# -------------------------
class DeleteAgentCommissionMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)

    success = Boolean()
    message = String()
    deleted_id = ID()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        commission_id = input.get('id')
        
        try:
            commission = AgentCommission.objects.get(pk=from_global_id(commission_id)[1])
            commission.delete()
            
            return cls(
                success=True,
                message="AgentCommission deleted successfully",
                deleted_id=commission_id
            )
        except AgentCommission.DoesNotExist:
            raise GraphQLError("AgentCommission not found")
        except Exception as e:
            raise GraphQLError(f"Error deleting AgentCommission: {str(e)}")


# -------------------------
# Optional: Batch Delete Mutation
# -------------------------
class BatchDeleteAgentCommissionMutation(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(ID, required=True)

    success = Boolean()
    message = String()
    deleted_count = Int()
    deleted_ids = graphene.List(ID)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        ids = input.get('ids', [])
        deleted_ids = []
        deleted_count = 0
        
        for global_id in ids:
            try:
                commission = AgentCommission.objects.get(pk=from_global_id(global_id)[1])
                commission.delete()
                deleted_ids.append(global_id)
                deleted_count += 1
            except AgentCommission.DoesNotExist:
                # Skip if not found, or you could raise an error
                continue
            except Exception as e:
                raise GraphQLError(f"Error deleting AgentCommission {global_id}: {str(e)}")
        
        return cls(
            success=True,
            message=f"{deleted_count} AgentCommission(s) deleted successfully",
            deleted_count=deleted_count,
            deleted_ids=deleted_ids
        )
        
class AgentCommissionMutations(graphene.ObjectType):
    update_agent_commission = UpdateAgentCommissionMutation.Field()
    delete_agent_commission = DeleteAgentCommissionMutation.Field()
    batch_delete_agent_commission = BatchDeleteAgentCommissionMutation.Field()