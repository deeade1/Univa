import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Message, MessageReaction
from .subscriptions import OnMessageReaction, OnNewMessage


@receiver(post_save, sender=Message)
def message_created(sender, instance, created, **kwargs):
    if created:
        # Trigger GraphQL subscription
        OnNewMessage.broadcast(
            group=str(instance.chatroom.id),
            payload={"message": instance}
        )
        
        # Send WebSocket notification to all participants
        channel_layer = get_channel_layer()
        for participant in instance.chatroom.participants.all():
            if participant != instance.sender:  # Don't notify sender
                async_to_sync(channel_layer.group_send)(
                    f"user_{participant.id}",
                    {
                        "type": "chat.message",
                        "message": {
                            "id": str(instance.id),
                            "chatroom_id": str(instance.chatroom.id),
                            "sender_id": str(instance.sender.id),
                            "text": instance.text,
                            "timestamp": instance.timestamp.isoformat(),
                            "is_read": False,
                            "is_disappearing": instance.is_disappearing,
                            "disappear_at": instance.disappear_at.isoformat() if instance.disappear_at else None
                        }
                    }
                )

@receiver(post_save, sender=MessageReaction)
@receiver(post_delete, sender=MessageReaction)
def reaction_changed(sender, instance, **kwargs):
    # Trigger GraphQL subscription
    OnMessageReaction.broadcast(
        group=str(instance.message.chatroom.id),
        payload={
            "message_id": str(instance.message.id),
            "reaction": instance
        }
    )
    
    # Send WebSocket notification to all participants
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{instance.message.chatroom.id}",
        {
            "type": "reaction.notification",
            "message_id": str(instance.message.id),
            "user_id": str(instance.user.id),
            "reaction": instance.reaction if kwargs.get('created', True) else None
        }
    )

@receiver(pre_save, sender=Message)
def check_expired_messages(sender, instance, **kwargs):
    # Automatically delete expired disappearing messages
    if instance.is_disappearing and instance.disappear_at and timezone.now() > instance.disappear_at:
        instance.delete()
        raise Exception("Message has expired and been deleted")
    