"""
Base subscription classes
"""
import graphene
from channels_graphql_ws import Subscription
from graphql_relay import from_global_id
class BaseTransportSubscription(Subscription):
    class Meta:
        abstract = True  # <-- tells channels_graphql_ws this is not a concrete subscription

    @staticmethod
    def get_group_name(entity_type, entity_id, event_type=None):
        if event_type:
            return f"{entity_type}_{entity_id}_{event_type}"
        return f"{entity_type}_{entity_id}"
    
    @classmethod
    def trigger_event(cls, entity_type, entity_id, event_type, payload):
        group_name = cls.get_group_name(entity_type, entity_id, event_type)
        cls.broadcast(group=group_name, payload=payload)


class GenericSubscription(BaseTransportSubscription):
    """Generic subscription that can handle any transport event"""
    
    event_type = graphene.String()
    entity_type = graphene.String()
    entity_id = graphene.ID()
    payload = graphene.JSONString()
    
    class Arguments:
        entity_type = graphene.String(required=True)
        entity_id = graphene.ID(required=True)
        event_type = graphene.String(required=True)
    
    @staticmethod
    def subscribe(root, info, entity_type, entity_id, event_type):
        group_name = BaseTransportSubscription.get_group_name(entity_type, entity_id, event_type)
        return [group_name]
    
    @staticmethod
    def publish(payload, info, entity_type, entity_id, event_type):
        return GenericSubscription(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload.get('data', {})
        )