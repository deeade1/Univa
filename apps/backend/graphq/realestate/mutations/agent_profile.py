import graphene
from graphene import relay, Boolean, String, Field, ID, Decimal, Int
from django.contrib.auth import get_user_model
from django.db import transaction
from graphene import  relay
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphq.realestate.types.agent_profile import  AgentProfileNode
from graphq.accounts.types.user import  UserNode

User = get_user_model()

class CreateAgentProfileMutation(relay.ClientIDMutation):
    class Input:
        user = graphene.ID(required=True)
        license_id = graphene.String()
        company_name = graphene.String()
    
    user = graphene.Field(UserNode)
    agent_profile = graphene.Field(AgentProfileNode)
    success = graphene.String()
    
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required.")
        
        user_id = input.pop('user')
        user = get_instance_from_global_id(User, user_id)

        agent_profile, created = AgentProfile.objects.get_or_create(user=user)
        license_image = info.context.FILES
        company_logo = info.context.FILES
        for field, value in input.items():
            setattr(agent_profile, field, value)
        
        agent_profile.save()

        return CreateAgentProfileMutation(user=user, agent_profile=agent_profile, success=True)

class UpdateAgentProfileMutation(relay.ClientIDMutation):
    class Input:
        agent_profile_id = graphene.ID(required=True)
        license_id = graphene.String()
        company_name = graphene.String()
        
    
    agent_profile = graphene.Field(AgentProfileNode)
    
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required.")
        
        agent_profile_id = input.pop('agent_profile_id')
        agent_profile = AgentProfile.objects.get(pk=from_global_id(agent_profile_id)[1])
        license_image = info.context.FILES
        company_logo = info.context.FILES
        for field, value in input.items():
            setattr(agent_profile, field, value)
        
        agent_profile.save()

        return UpdateAgentProfileMutation(agent_profile=agent_profile, success=True)
    
class DeleteAgentProfileMutation(relay.ClientIDMutation):
    class Input:
        agent_profile_id = graphene.ID(required=True)
    
    success = graphene.Boolean()
    
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required.")
        
        agent_profile_id = input.pop('agent_profile_id')
        agent_profile = AgentProfile.objects.get(pk=from_global_id(agent_profile_id)[1])

        agent_profile.delete()

        return DeleteAgentProfileMutation(success=True)

class BatchDeleteAgentProfileMutation(relay.ClientIDMutation):
    class Input:
        agent_profile_ids = graphene.List(graphene.ID, required=True)
    
    success = graphene.Boolean()
    deleted_count = graphene.Int()
    deleted_ids = graphene.List(graphene.ID)
    
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required.")
        
        agent_profile_ids = input.pop('agent_profile_ids')
        deleted_count = 0
        deleted_ids = []

        for agent_profile_id in agent_profile_ids:
            try:
                agent_profile = AgentProfile.objects.get(pk=from_global_id(agent_profile_id)[1])
                agent_profile.delete()
                deleted_count += 1
                deleted_ids.append(agent_profile_id)
            except AgentProfile.DoesNotExist:
                continue

        return BatchDeleteAgentProfileMutation(
            success=True,
            deleted_count=deleted_count,
            deleted_ids=deleted_ids
        )


'''class UpdateAgentLocation(UpdateLocationMixin, relay.ClientIDMutation):
    class Input:
        agent_id = graphene.ID(required=True)
        latitude = graphene.Float(required=True)
        longitude = graphene.Float(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        update_location = cls.update_location(
            Agent,
            input['agent_id'],
            input['latitude'],
            input['longitude']
        )
        return UpdateAgentLocation(success=update_location.success)'''



class AgentProfileMutations(graphene.ObjectType):
    create_agent_profile = CreateAgentProfileMutation.Field()
    update_agent_profile = UpdateAgentProfileMutation.Field()
    delete_agent_profile = DeleteAgentProfileMutation.Field()
    batch_delete_agent_profile = BatchDeleteAgentProfileMutation.Field()