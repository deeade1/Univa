import graphene
from graphene_django.filter import DjangoFilterConnectionField

from chat.models import (
    Call,
    ChatRoom,
    Message,
    MessageReaction,
    UserStatus,
    StatusUpdate,
    StatusView,
)
from graphq.accounts.types import UserNode
from graphq.chat.types import (CallNode, ChatRoomNode, MessageNode,
                               MessageReactionNode, StatusUpdateNode,
                               StatusViewNode, UserStatusNode)


# Query Class
class ChatQueries(graphene.ObjectType):
    chatroom = graphene.Field(ChatRoomNode, id=graphene.ID(required=True))
    message = graphene.Field(MessageNode, id=graphene.ID(required=True))
    user_status = graphene.Field(UserStatusNode, id=graphene.ID(required=True))
    message_reaction = graphene.Field(MessageReactionNode, id=graphene.ID(required=True))
    status_update = graphene.Field(StatusUpdateNode, id=graphene.ID(required=True))
    call = graphene.Field(CallNode, id=graphene.ID(required=True))
    all_chatrooms = DjangoFilterConnectionField(ChatRoomNode)
    all_messages = DjangoFilterConnectionField(MessageNode)
    all_message_reactions = DjangoFilterConnectionField(MessageReactionNode)
    all_user_statuses = DjangoFilterConnectionField(UserStatusNode)
    all_status_updates = DjangoFilterConnectionField(StatusUpdateNode)
    all_status_views = DjangoFilterConnectionField(StatusViewNode)
    all_calls = DjangoFilterConnectionField(CallNode)

    def resolve_all_chatrooms(self, info, **kwargs):
        return ChatRoom.objects.all()

    def resolve_all_messages(self, info, **kwargs):
        return Message.objects.all()

    def resolve_all_message_reactions(self, info, **kwargs):
        return MessageReaction.objects.all()

    def resolve_all_user_statuses(self, info, **kwargs):
        return UserStatus.objects.all()

    def resolve_all_status_updates(self, info, **kwargs):
        return StatusUpdate.objects.all()

    def resolve_all_status_views(self, info, **kwargs):
        return StatusView.objects.all()

    def resolve_all_calls(self, info, **kwargs):
        return Call.objects.all()