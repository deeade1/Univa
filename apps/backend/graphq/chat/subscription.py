import graphene
from channels_graphql_ws import Subscription
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AnonymousUser

from .types import (
    MessageNode, 
    MessageReactionNode,
    UserStatusNode,
    ChatRoomNode,
    StatusUpdateNode,
    CallNode,
)
from graphq.accounts.types import UserNode

# -------------------------------
# New Message Subscription
# -------------------------------



class OnNewMessage(Subscription):
    """Trigger when a new message is created."""

    message = graphene.Field(MessageNode)
    chatroom_id = graphene.ID()
    sender_id = graphene.ID()
    message_type = graphene.String()

    class Arguments:
        chatroom_ids = graphene.List(graphene.ID)

    # -------------------------
    def subscribe(self, info, chatroom_ids=None):
        # 🔥 Correct way to get websocket user
        user = info.context.channels_scope.get("user")

        if not user or not user.is_authenticated:
            return []

        if not chatroom_ids:
            return []

        return [f"chatroom_{cid}" for cid in chatroom_ids]

    # -------------------------
    def publish(self, info, chatroom_ids=None):
        message_obj = self.get("message")
        if not message_obj:
            return OnNewMessage.SKIP

        # 🔥 Correct user reference
        user = info.context.channels_scope.get("user")
        current_user_id = str(user.id) if user else None

        chatroom_id = str(message_obj.chatroom_id)
        sender_id = str(message_obj.sender_id)

        # Skip sending to sender
        if current_user_id == sender_id:
            return OnNewMessage.SKIP

        # Determine type
        if getattr(message_obj, "image", None):
            m_type = "image"
        elif getattr(message_obj, "file", None):
            m_type = "file"
        elif getattr(message_obj, "reply_to", None):
            m_type = "reply"
        else:
            m_type = "text"

        return OnNewMessage(
            message=message_obj,
            chatroom_id=chatroom_id,
            sender_id=sender_id,
            message_type=m_type,
        )


# -------------------------------
# Message Read Status Subscription
# -------------------------------
class OnMessageRead(Subscription):
    chatroom_id = graphene.ID()
    reader_id = graphene.ID()
    message_ids = graphene.List(graphene.ID)
    read_at = graphene.DateTime()

    class Arguments:
        chatroom_id = graphene.ID()

    def subscribe(self, info, chatroom_id=None):
        user = info.context.user
        if not user.is_authenticated:
            return []

        if not chatroom_id:
            return []

        return [f"chatroom_read_{chatroom_id}"]

    def publish(self, info, chatroom_id=None):
        event_chatroom_id = self["chatroom_id"]
        reader_id = self["reader_id"]

        # do not send to the same user
        if str(info.context.user.id) == str(reader_id):
            return OnMessageRead.SKIP

        return OnMessageRead(
            chatroom_id=event_chatroom_id,
            reader_id=reader_id,
            message_ids=self["message_ids"],
            read_at=timezone.now(),
        )

    @classmethod
    def notify_messages_read(cls, chatroom_id, reader_id, message_ids):
        cls.broadcast(
            group=f"chatroom_read_{chatroom_id}",
            payload={
                "chatroom_id": chatroom_id,
                "reader_id": reader_id,
                "message_ids": message_ids,
            },
        )

# -------------------------------
# Message Reaction Subscription
# -------------------------------
class OnMessageReaction(Subscription):
    """Subscription triggers when a message reaction is added/removed."""
    
    reaction = graphene.Field(MessageReactionNode)
    message_id = graphene.ID()
    chatroom_id = graphene.ID()
    action = graphene.String()  # 'added', 'removed', 'changed'

    class Arguments:
        chatroom_id = graphene.ID()

    def subscribe(self, info, chatroom_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if chatroom_id:
            return [f"chatroom_reactions_{chatroom_id}"]
        return []

    def publish(self, info, chatroom_id=None):
        """Prepare subscription notification."""
        reaction_data = self["reaction"]
        action = self["action"]
        message_id = str(reaction_data.message.id)
        event_chatroom_id = str(reaction_data.message.chatroom.id)
        
        # Don't notify the user who reacted
        if str(info.context.user.id) == str(reaction_data.user.id):
            return OnMessageReaction.SKIP
            
        return OnMessageReaction(
            reaction=reaction_data,
            message_id=message_id,
            chatroom_id=event_chatroom_id,
            action=action
        )

    @classmethod
    def notify_reaction_added(cls, reaction):
        """Notify when a reaction is added."""
        cls.broadcast(
            group=f"chatroom_reactions_{reaction.message.chatroom.id}",
            payload={
                "reaction": reaction,
                "action": "added"
            }
        )

    @classmethod
    def notify_reaction_removed(cls, reaction):
        """Notify when a reaction is removed."""
        cls.broadcast(
            group=f"chatroom_reactions_{reaction.message.chatroom.id}",
            payload={
                "reaction": reaction,
                "action": "removed"
            }
        )

# -------------------------------
# User Typing Status Subscription
# -------------------------------
class OnUserTyping(Subscription):
    """Subscription triggers when a user starts/stops typing."""
    
    user = graphene.Field(lambda: UserNode)
    chatroom_id = graphene.ID()
    is_typing = graphene.Boolean()
    user_status = graphene.Field(UserStatusNode)

    class Arguments:
        chatroom_id = graphene.ID()

    def subscribe(self, info, chatroom_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if chatroom_id:
            return [f"chatroom_typing_{chatroom_id}"]
        return []

    def publish(self, info, chatroom_id=None):
        """Prepare subscription notification."""
        user_data = self["user"]
        event_chatroom_id = self["chatroom_id"]
        is_typing = self["is_typing"]
        user_status = self["user_status"]
        
        # Don't notify the typing user
        if str(info.context.user.id) == str(user_data.id):
            return OnUserTyping.SKIP
            
        return OnUserTyping(
            user=user_data,
            chatroom_id=event_chatroom_id,
            is_typing=is_typing,
            user_status=user_status
        )

    @classmethod
    def notify_typing_status(cls, user, chatroom_id, is_typing, user_status):
        """Notify when typing status changes."""
        cls.broadcast(
            group=f"chatroom_typing_{chatroom_id}",
            payload={
                "user": user,
                "chatroom_id": chatroom_id,
                "is_typing": is_typing,
                "user_status": user_status
            }
        )

# -------------------------------
# User Online Status Subscription
# -------------------------------
class OnUserOnlineStatus(Subscription):
    """Subscription triggers when user online status changes."""
    
    user = graphene.Field(lambda: UserNode)
    is_online = graphene.Boolean()
    last_seen = graphene.DateTime()
    user_status = graphene.Field(UserStatusNode)

    class Arguments:
        user_ids = graphene.List(graphene.ID)

    def subscribe(self, info, user_ids=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        groups = []
        if user_ids:
            for user_id in user_ids:
                groups.append(f"user_status_{user_id}")
        else:
            # Subscribe to contacts' status (you might want to implement contact logic)
            groups.append(f"user_status_global")
        
        return groups

    def publish(self, info, user_ids=None):
        """Prepare subscription notification."""
        user_data = self["user"]
        is_online = self["is_online"]
        last_seen = self["last_seen"]
        user_status = self["user_status"]
        
        # Don't notify the user about their own status
        if str(info.context.user.id) == str(user_data.id):
            return OnUserOnlineStatus.SKIP
            
        # Filter by subscribed user IDs
        if user_ids and str(user_data.id) not in user_ids:
            return OnUserOnlineStatus.SKIP
            
        return OnUserOnlineStatus(
            user=user_data,
            is_online=is_online,
            last_seen=last_seen,
            user_status=user_status
        )

    @classmethod
    def notify_online_status(cls, user, is_online, last_seen, user_status):
        """Notify when online status changes."""
        cls.broadcast(
            group=f"user_status_{user.id}",
            payload={
                "user": user,
                "is_online": is_online,
                "last_seen": last_seen,
                "user_status": user_status
            }
        )
        cls.broadcast(
            group="user_status_global",
            payload={
                "user": user,
                "is_online": is_online,
                "last_seen": last_seen,
                "user_status": user_status
            }
        )

# -------------------------------
# Chat Room Updates Subscription
# -------------------------------
class OnChatRoomUpdate(Subscription):
    """Subscription triggers when chat room details change."""
    
    chatroom = graphene.Field(ChatRoomNode)
    action = graphene.String()  # 'updated', 'participant_added', 'participant_removed', 'admin_changed'
    updated_fields = graphene.List(graphene.String)

    class Arguments:
        chatroom_id = graphene.ID()

    def subscribe(self, info, chatroom_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if chatroom_id:
            return [f"chatroom_updates_{chatroom_id}"]
        return []

    def publish(self, info, chatroom_id=None):
        """Prepare subscription notification."""
        chatroom_data = self["chatroom"]
        action = self["action"]
        updated_fields = self["updated_fields"]
        
        return OnChatRoomUpdate(
            chatroom=chatroom_data,
            action=action,
            updated_fields=updated_fields
        )

    @classmethod
    def notify_chatroom_update(cls, chatroom, action, updated_fields=None):
        """Notify when chat room is updated."""
        cls.broadcast(
            group=f"chatroom_updates_{chatroom.id}",
            payload={
                "chatroom": chatroom,
                "action": action,
                "updated_fields": updated_fields or []
            }
        )

# -------------------------------
# Status Updates Subscription
# -------------------------------
class OnNewStatusUpdate(Subscription):
    """Subscription triggers when a contact posts a new status update."""
    
    status_update = graphene.Field(StatusUpdateNode)
    user = graphene.Field(lambda: UserNode)

    class Arguments:
        user_ids = graphene.List(graphene.ID)  # Contacts to watch

    def subscribe(self, info, user_ids=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Subscribe to contacts' status updates
        # You might want to implement contact/follow logic here
        groups = [f"user_status_updates_{user.id}"]
        if user_ids:
            for user_id in user_ids:
                groups.append(f"status_updates_{user_id}")
        
        return groups

    def publish(self, info, user_ids=None):
        """Prepare subscription notification."""
        status_data = self["status_update"]
        user_data = self["user"]
        
        # Don't notify the user about their own status
        if str(info.context.user.id) == str(user_data.id):
            return OnNewStatusUpdate.SKIP
            
        # Filter by subscribed user IDs
        if user_ids and str(user_data.id) not in user_ids:
            return OnNewStatusUpdate.SKIP
            
        return OnNewStatusUpdate(
            status_update=status_data,
            user=user_data
        )

    @classmethod
    def notify_new_status(cls, status_update):
        """Notify about new status updates."""
        cls.broadcast(
            group=f"status_updates_{status_update.user.id}",
            payload={
                "status_update": status_update,
                "user": status_update.user
            }
        )
        # Also notify the user's contacts
        cls.broadcast(
            group=f"user_status_updates_{status_update.user.id}",
            payload={
                "status_update": status_update,
                "user": status_update.user
            }
        )

# -------------------------------
# Status View Subscription
# -------------------------------
class OnStatusViewed(Subscription):
    """Subscription triggers when someone views a status update."""
    
    status_id = graphene.ID()
    viewer = graphene.Field(lambda: UserNode)
    viewed_at = graphene.DateTime()

    class Arguments:
        status_id = graphene.ID()

    def subscribe(self, info, status_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if status_id:
            return [f"status_views_{status_id}"]
        return []

    def publish(self, info, status_id=None):
        """Prepare subscription notification."""
        event_status_id = self["status_id"]
        viewer_data = self["viewer"]
        
        # Don't notify the status owner about their own views
        # You might want to get the status owner here
        if str(info.context.user.id) == str(viewer_data.id):
            return OnStatusViewed.SKIP
            
        return OnStatusViewed(
            status_id=event_status_id,
            viewer=viewer_data,
            viewed_at=timezone.now()
        )

    @classmethod
    def notify_status_viewed(cls, status_id, viewer):
        """Notify when a status is viewed."""
        cls.broadcast(
            group=f"status_views_{status_id}",
            payload={
                "status_id": status_id,
                "viewer": viewer
            }
        )

# -------------------------------
# Call Events Subscription
# -------------------------------
class OnCallEvent(Subscription):
    """Subscription triggers for call-related events."""
    
    call = graphene.Field(CallNode)
    event_type = graphene.String()  # 'incoming', 'answered', 'rejected', 'ended', 'missed'
    caller = graphene.Field(lambda: UserNode)
    recipient = graphene.Field(lambda: UserNode)

    class Arguments:
        user_id = graphene.ID()

    def subscribe(self, info, user_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Users subscribe to their own call events
        return [f"calls_{user.id}"]

    def publish(self, info, user_id=None):
        """Prepare subscription notification."""
        call_data = self["call"]
        event_type = self["event_type"]
        caller_data = call_data.caller
        recipient_data = call_data.recipient
        
        requesting_user_id = str(info.context.user.id)
        
        # Only send to involved users
        if requesting_user_id not in [str(caller_data.id), str(recipient_data.id)]:
            return OnCallEvent.SKIP
            
        return OnCallEvent(
            call=call_data,
            event_type=event_type,
            caller=caller_data,
            recipient=recipient_data
        )

    @classmethod
    def notify_call_event(cls, call, event_type):
        """Notify about call events."""
        # Notify both caller and recipient
        cls.broadcast(
            group=f"calls_{call.caller.id}",
            payload={
                "call": call,
                "event_type": event_type
            }
        )
        cls.broadcast(
            group=f"calls_{call.recipient.id}",
            payload={
                "call": call,
                "event_type": event_type
            }
        )

# -------------------------------
# WebRTC Signaling Subscription
# -------------------------------
class OnWebRTCSignal(Subscription):
    """Subscription for WebRTC signaling (offer, answer, ICE candidates)."""
    
    signal_type = graphene.String()  # 'offer', 'answer', 'ice_candidate'
    call_id = graphene.ID()
    data = graphene.JSONString()
    from_user = graphene.Field(lambda: UserNode)

    class Arguments:
        call_id = graphene.ID()

    def subscribe(self, info, call_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if call_id:
            return [f"webrtc_{call_id}"]
        return []

    def publish(self, info, call_id=None):
        """Prepare subscription notification."""
        signal_type = self["signal_type"]
        event_call_id = self["call_id"]
        data = self["data"]
        from_user = self["from_user"]
        
        # Don't send the signal back to the sender
        if str(info.context.user.id) == str(from_user.id):
            return OnWebRTCSignal.SKIP
            
        return OnWebRTCSignal(
            signal_type=signal_type,
            call_id=event_call_id,
            data=data,
            from_user=from_user
        )

    @classmethod
    def notify_webrtc_signal(cls, call_id, signal_type, data, from_user):
        """Notify about WebRTC signaling."""
        cls.broadcast(
            group=f"webrtc_{call_id}",
            payload={
                "signal_type": signal_type,
                "call_id": call_id,
                "data": data,
                "from_user": from_user
            }
        )

# -------------------------------
# Message Deleted Subscription
# -------------------------------
class OnMessageDeleted(Subscription):
    """Subscription triggers when a message is deleted."""
    
    message_id = graphene.ID()
    chatroom_id = graphene.ID()
    deleted_by = graphene.Field(lambda: UserNode)
    deleted_at = graphene.DateTime()

    class Arguments:
        chatroom_id = graphene.ID()

    def subscribe(self, info, chatroom_id=None):
        """Client subscription handler."""
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        if chatroom_id:
            return [f"chatroom_deletes_{chatroom_id}"]
        return []

    def publish(self, info, chatroom_id=None):
        """Prepare subscription notification."""
        message_id = self["message_id"]
        event_chatroom_id = self["chatroom_id"]
        deleted_by = self["deleted_by"]
        
        return OnMessageDeleted(
            message_id=message_id,
            chatroom_id=event_chatroom_id,
            deleted_by=deleted_by,
            deleted_at=timezone.now()
        )

    @classmethod
    def notify_message_deleted(cls, message_id, chatroom_id, deleted_by):
        """Notify when a message is deleted."""
        cls.broadcast(
            group=f"chatroom_deletes_{chatroom_id}",
            payload={
                "message_id": message_id,
                "chatroom_id": chatroom_id,
                "deleted_by": deleted_by
            }
        )

# -------------------------------
# Main Subscription Class
# -------------------------------
class ChatSubscriptions(graphene.ObjectType):
    """GraphQL subscriptions for chat features."""
    
    on_new_message = OnNewMessage.Field()
    on_message_read = OnMessageRead.Field()
    on_message_reaction = OnMessageReaction.Field()
    on_user_typing = OnUserTyping.Field()
    on_user_online_status = OnUserOnlineStatus.Field()
    on_chat_room_update = OnChatRoomUpdate.Field()
    on_new_status_update = OnNewStatusUpdate.Field()
    on_status_viewed = OnStatusViewed.Field()
    on_call_event = OnCallEvent.Field()
    on_webrtc_signal = OnWebRTCSignal.Field()
    on_message_deleted = OnMessageDeleted.Field()