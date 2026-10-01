import graphene
from graphene import relay, Boolean, String, Field, ID, Int
from django.contrib.auth import get_user_model
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id, to_global_id

from graphq.realestate.types.agent import AgentNode
from graphq.realestate.types.agent_rating import AgentRatingNode
from realestate.models import (
    Agent, 
    AgentRating,  
)
User = get_user_model()


# -------------------------
# AgentRating Mutation
# -------------------------
class CreateAgentRatingMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=False)
        agent_id = ID(required=True)
        user_id = ID(required=True)
        rating = Int(required=True)
        review = String(required=False)

    rating = Field(AgentRatingNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input): 
        agent = Agent.objects.get(pk=from_global_id(agent_id)[1])
        user = User.objects.get(pk=from_global_id(user_id)[1])
        input['agent'] = agent
        input['user'] = user

        rating_id = input.pop('id', None)
        if rating_id:
            rating = AgentRating.objects.get(pk=from_global_id(id)[1])
            
            if not rating:
                raise GraphQLError("AgentRating not found")
            for k, v in input.items():
                setattr(rating, k, v)
            rating.save()
            message = "AgentRating updated successfully"
        else:
            rating = AgentRating.objects.create(**input)
            message = "AgentRating created successfully"

        return cls(rating=rating, success=True, message=message)

class UpdateAgentRatingMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)
        rating = Int(required=False)
        review = String(required=False)

    rating = Field(AgentRatingNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        rating_id = input.pop('id')
        rating = AgentRating.objects.get(pk=from_global_id(rating_id)[1])
        
        if not rating:
            raise GraphQLError("AgentRating not found")
        
        for k, v in input.items():
            setattr(rating, k, v)
        rating.save()
        message = "AgentRating updated successfully"

        return cls(rating=rating, success=True, message=message)
    
class DeleteAgentRatingMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        rating_id = input.pop('id')
        rating = AgentRating.objects.get(pk=from_global_id(rating_id)[1])
        
        if not rating:
            raise GraphQLError("AgentRating not found")
        
        rating.delete()
        message = "AgentRating deleted successfully"

        return cls(success=True, message=message)
    
class AgentRatingMutations(graphene.ObjectType):
    create_agent_rating = CreateAgentRatingMutation.Field()
    update_agent_rating = UpdateAgentRatingMutation.Field()
    delete_agent_rating = DeleteAgentRatingMutation.Field()
