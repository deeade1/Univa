import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from graphql import GraphQLError

from chat.models import (Call, ChatRoom, Message, MessageReaction,
                         StatusUpdate, StatusView, UserStatus)

logger = logging.getLogger(__name__)
User = get_user_model()

#Model-driven asynchronous tasks
@shared_task(bind=True, max_retries=3)
def cleanup_disappearing_messages(self):
    """Task to delete messages that have passed their disappearance time."""
    try:
        now = timezone.now()
        messages_to_delete = Message.objects.filter(
        is_disappearing=True,
        disappear_at__lte=now
        )

        count = messages_to_delete.count()
        messages_to_delete.delete()
        logger.info(f"Deleted {count} disappearing messages")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up disappearing messages: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task
def expire_status_updates():
    """
    Task to delete status updates that have expired.
    """
    try:
        now = timezone.now()
        expired_statuses = StatusUpdate.objects.filter(
        expires_at__lte=now
        )

        count = expired_statuses.count()
        expired_statuses.delete()
        logger.info(f"Deleted {count} expired status updates")
        return count
    except Exception as e:
        logger.error(f"Error expiring status updates: {str(e)}")
        raise
@shared_task
def update_user_last_seen(user_id):
    """
    Update user's last seen timestamp when they go offline.
    """
    try:
        user_status = UserStatus.objects.get(user_id=user_id)
        if not user_status.online:
            user_status.last_seen = timezone.now()
            user_status.save()
            logger.info(f"Updated last seen for user {user_id}")
    except UserStatus.DoesNotExist:
         logger.warning(f"UserStatus not found for user {user_id}")
    except Exception as e:
         logger.error(f"Error updating last seen for user {user_id}: {str(e)}")
    raise

@shared_task
def notify_message_recipients(message_id):
    """
    Send push notifications to chat participants about new message.
    """
    try:
        message = Message.objects.select_related('chatroom').get(id=message_id)
        chatroom = message.chatroom

    # Get recipients (all participants except sender)
        recipients = chatroom.participants.exclude(id=message.sender_id)
    
    # In a real app, you would integrate with a push notification service here
        for recipient in recipients:
            logger.info(f"Notifying {recipient.username} about new message in {chatroom.name}")
            
            # Example email notification (replace with push notifications)
            if recipient.email:
                send_mail(
                    subject=f"New message in {chatroom.name}",
                    message=f"You have a new message from {message.sender.username}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=True
                )
    except Message.DoesNotExist:
        logger.warning(f"Message {message_id} not found for notification")
    except Exception as e:
        logger.error(f"Error notifying recipients about message {message_id}: {str(e)}")
        raise
@shared_task
def process_message_reaction(reaction_id):
    """
    Process message reaction (analytics, notifications, etc.)
    """
    try:
        reaction = MessageReaction.objects.select_related(
        'message', 'user', 'message__chatroom'
        ).get(id=reaction_id)

        # Example: Notify message sender about reaction
        if reaction.message.sender_id != reaction.user_id:
            logger.info(f"User {reaction.user.dirst_name} reacted to message from {reaction.message.sender.username}")
            
            # In a real app, send push notification here
    except MessageReaction.DoesNotExist:
        logger.warning(f"Reaction {reaction_id} not found")
    except Exception as e:
        logger.error(f"Error processing reaction {reaction_id}: {str(e)}")
        raise
@shared_task
def cleanup_old_calls(days_old=30):
    """
    Clean up call records older than specified days.
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
        deleted_count, _ = Call.objects.filter(
        end_time__lte=cutoff_date
        ).delete()
        logger.info(f"Deleted {deleted_count} old call records")
        return deleted_count
    except Exception as e:
         logger.error(f"Error cleaning up old calls: {str(e)}")
    raise

#GraphQL mutation-driven asynchronous tasks
@shared_task(bind=True)
def send_message_async(self, chatroom_id, sender_id, message_data):
    """
    Async implementation of SendMessage mutation.
    """
    try:
        with transaction.atomic():
            chatroom = ChatRoom.objects.get(id=chatroom_id)
            sender = User.objects.get(id=sender_id)

            # Create message
            message = Message.objects.create(
                chatroom=chatroom,
                sender=sender,
                **message_data
            )
            
            # Update chatroom's updated_at
            chatroom.save()
            
            logger.info(f"Created message {message.id} in chatroom {chatroom_id}")
            
            # Trigger notifications
            notify_message_recipients.delay(str(message.id))
            
            return {
                'id': str(message.id),
                'chatroom_id': str(chatroom_id),
                'sender_id': str(sender_id),
                'timestamp': message.timestamp.isoformat()
            }
    except ChatRoom.DoesNotExist:
        logger.warning(f"Chatroom {chatroom_id} not found")
        raise GraphQLError("Chatroom not found")
    except User.DoesNotExist:
        logger.warning(f"User {sender_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def create_chatroom_async(self, creator_id, chatroom_data):
    """
    Async implementation of CreateChatRoom mutation.
    """
    try:
        with transaction.atomic():
            creator = User.objects.get(id=creator_id)
            participant_ids = chatroom_data.pop('participant_ids', [])

            # Add creator to participants if not already present
            if creator_id not in participant_ids:
                participant_ids.append(creator_id)
            
            # Get participant objects
            participants = User.objects.filter(id__in=participant_ids)
            if len(participants) != len(participant_ids):
                raise GraphQLError("One or more participants not found")
            
            # Check for existing DM if not group
            if not chatroom_data.get('is_group', False) and len(participants) == 2:
                existing_dm = ChatRoom.objects.filter(
                    is_group=False,
                    participants=participants[0]
                ).filter(
                    participants=participants[1]
                ).first()
                
                if existing_dm:
                    logger.info(f"Returning existing DM {existing_dm.id}")
                    return {
                        'id': str(existing_dm.id),
                        'is_new': False
                    }
            
            # Create chatroom
            chatroom = ChatRoom.objects.create(
                **chatroom_data,
                admin=creator if chatroom_data.get('is_group', False) else None
            )
            chatroom.participants.set(participants)
            
            logger.info(f"Created chatroom {chatroom.id} with {len(participants)} participants")
            
            return {
                'id': str(chatroom.id),
                'is_new': True
            }
    except User.DoesNotExist:
        logger.warning(f"User {creator_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error creating chatroom: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def update_user_status_async(self, user_id, status_data):
    """
    Async implementation of UpdateUserStatus mutation.
    """
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            status, _ = UserStatus.objects.get_or_create(user=user)

            # Update fields
            if 'online' in status_data:
                status.online = status_data['online']
                if not status_data['online']:
                    update_user_last_seen.delay(user_id)
            
            if 'typing' in status_data:
                status.typing = status_data['typing']
            
            if 'typing_in' in status_data:
                if status_data['typing_in']:
                    chatroom = ChatRoom.objects.get(id=status_data['typing_in'])
                    if user not in chatroom.participants.all():
                        raise GraphQLError("Not a participant of this chat")
                    status.typing_in = chatroom
                else:
                    status.typing_in = None
            
            status.save()
            logger.info(f"Updated status for user {user_id}")
            
            return {
                'user_id': str(user_id),
                'online': status.online,
                'typing': status.typing,
                'typing_in': str(status.typing_in.id) if status.typing_in else None
            }
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except ChatRoom.DoesNotExist:
        logger.warning(f"Chatroom {status_data.get('typing_in')} not found")
        raise GraphQLError("Chatroom not found")
    except Exception as e:
        logger.error(f"Error updating user status: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def mark_messages_as_read_async(self, user_id, chatroom_id):
    """
    Async implementation of MarkMessagesAsRead mutation.
    """
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            chatroom = ChatRoom.objects.get(id=chatroom_id)

            if user not in chatroom.participants.all():
                raise GraphQLError("Not a participant of this chat")
            
            unread_messages = chatroom.messages.exclude(read_by=user)
            count = unread_messages.count()
            
            for message in unread_messages:
                message.read_by.add(user)
            
            logger.info(f"Marked {count} messages as read in chatroom {chatroom_id} for user {user_id}")
            
            return {
                'success': True,
                'count': count
            }
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except ChatRoom.DoesNotExist:
        logger.warning(f"Chatroom {chatroom_id} not found")
        raise GraphQLError("Chatroom not found")
    except Exception as e:
        logger.error(f"Error marking messages as read: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def react_to_message_async(self, message_id, user_id, reaction):
    """
    Async implementation of ReactToMessage mutation.
    """
    try:
        with transaction.atomic():
            message = Message.objects.select_related('chatroom').get(id=message_id)
            user = User.objects.get(id=user_id)

            if user not in message.chatroom.participants.all():
                raise GraphQLError("Not a participant of this chat")
            
            # Check if reaction is valid
            valid_reactions = dict(Message.REACTION_CHOICES).keys()
            if reaction not in valid_reactions:
                raise GraphQLError("Invalid reaction")
            
            # Create or update reaction
            reaction_obj, created = MessageReaction.objects.update_or_create(
                message=message,
                user=user,
                defaults={'reaction': reaction}
            )
            
            logger.info(f"{'Created' if created else 'Updated'} reaction {reaction} on message {message_id}")
            
            # Process reaction (analytics, notifications)
            process_message_reaction.delay(str(reaction_obj.id))
            
            return {
                'message_id': str(message_id),
                'user_id': str(user_id),
                'reaction': reaction,
                'is_new': created
            }
    except Message.DoesNotExist:
        logger.warning(f"Message {message_id} not found")
        raise GraphQLError("Message not found")
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error reacting to message: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def toggle_disappearing_messages_async(self, chatroom_id, admin_id, duration_seconds):
    """
    Async implementation of ToggleDisappearingMessages mutation.
    """
    try:
        with transaction.atomic():
            chatroom = ChatRoom.objects.get(id=chatroom_id)
            admin = User.objects.get(id=admin_id)

            if chatroom.admin != admin:
                raise GraphQLError("Only admin can change disappearing messages settings")
            
            chatroom.disappearing_messages_duration = duration_seconds
            chatroom.save()
            
            logger.info(f"Set disappearing messages duration to {duration_seconds} in chatroom {chatroom_id}")
            
            return {
                'chatroom_id': str(chatroom_id),
                'duration_seconds': duration_seconds
            }
    except ChatRoom.DoesNotExist:
        logger.warning(f"Chatroom {chatroom_id} not found")
        raise GraphQLError("Chatroom not found")
    except User.DoesNotExist:
        logger.warning(f"User {admin_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error toggling disappearing messages: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def create_status_update_async(self, user_id, status_data):
    """
    Async implementation of CreateStatusUpdate mutation.
    """
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)

            if status_data['type'] not in dict(StatusUpdate.STATUS_TYPES).keys():
                raise GraphQLError("Invalid status type")
            
            status = StatusUpdate.objects.create(
                user=user,
                **status_data
            )
            
            logger.info(f"Created status update {status.id} for user {user_id}")
            
            return {
                'id': str(status.id),
                'user_id': str(user_id),
                'type': status.type,
                'expires_at': status.expires_at.isoformat()
            }
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error creating status update: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def view_status_update_async(self, status_id, viewer_id):
    """
    Async implementation of ViewStatusUpdate mutation.
    """
    try:
        with transaction.atomic():
            status = StatusUpdate.objects.select_related('user').get(id=status_id)
            viewer = User.objects.get(id=viewer_id)

            if status.user == viewer:
                raise GraphQLError("Cannot view your own status")
            
            # Check if viewer is a contact (has a chat with status owner)
            if not ChatRoom.objects.filter(
                participants=viewer
            ).filter(
                participants=status.user
            ).exists():
                raise GraphQLError("Can only view statuses from your contacts")
            
            StatusView.objects.get_or_create(
                status=status,
                user=viewer
            )
            
            logger.info(f"User {viewer_id} viewed status {status_id}")
            
            return {
                'status_id': str(status_id),
                'viewer_id': str(viewer_id),
                'success': True
            }
    except StatusUpdate.DoesNotExist:
        logger.warning(f"Status {status_id} not found")
        raise GraphQLError("Status not found")
    except User.DoesNotExist:
        logger.warning(f"User {viewer_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error viewing status: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def initiate_call_async(self, caller_id, recipient_id, call_type):
    """
    Async implementation of InitiateCall mutation.
    """
    try:
        with transaction.atomic():
            caller = User.objects.get(id=caller_id)
            recipient = User.objects.get(id=recipient_id)

            # Create call record
            call = Call.objects.create(
                caller=caller,
                recipient=recipient,
                call_type=call_type,
                status='initiated'
            )
            
            logger.info(f"Initiated call {call.id} from {caller_id} to {recipient_id}")
            
            return {
                'call_id': str(call.id),
                'caller_id': str(caller_id),
                'recipient_id': str(recipient_id),
                'call_type': call_type
            }
    except User.DoesNotExist:
        logger.warning(f"User not found (caller: {caller_id}, recipient: {recipient_id})")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def answer_call_async(self, call_id, answerer_id, answer_data):
    """
    Async implementation of AnswerCall mutation.
    """
    try:
        with transaction.atomic():
            call = Call.objects.get(id=call_id)
            answerer = User.objects.get(id=answerer_id)

            if call.recipient != answerer:
                raise GraphQLError("Not authorized to answer this call")
            
            call.status = 'in_progress'
            call.sdp_answer = answer_data.get('sdp_answer')
            
            # Add ICE candidates if provided
            if answer_data.get('ice_candidates'):
                call.ice_candidates = answer_data['ice_candidates']
            
            call.save()
            
            logger.info(f"Call {call_id} answered by {answerer_id}")
            
            return {
                'call_id': str(call_id),
                'status': call.status,
                'success': True
            }
    except Call.DoesNotExist:
        logger.warning(f"Call {call_id} not found")
        raise GraphQLError("Call not found")
    except User.DoesNotExist:
        logger.warning(f"User {answerer_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error answering call: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def end_call_async(self, call_id, user_id):
    """
    Async implementation of EndCall mutation.
    """
    try:
        with transaction.atomic():
            call = Call.objects.get(id=call_id)
            user = User.objects.get(id=user_id)

            if call.caller != user and call.recipient != user:
                raise GraphQLError("Not authorized to end this call")
            
            call.status = 'completed'
            call.end_time = timezone.now()
            call.save()
            
            logger.info(f"Call {call_id} ended by {user_id}")
            
            return {
                'call_id': str(call_id),
                'status': call.status,
                'success': True
            }
    except Call.DoesNotExist:
        logger.warning(f"Call {call_id} not found")
        raise GraphQLError("Call not found")
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error ending call: {str(e)}")
        raise self.retry(exc=e, countdown=60)
@shared_task(bind=True)
def add_ice_candidate_async(self, call_id, user_id, candidate):
    """
    Async implementation of AddIceCandidate mutation.
    """
    try:
        with transaction.atomic():
            call = Call.objects.get(id=call_id)
            user = User.objects.get(id=user_id)

            if call.caller != user and call.recipient != user:
                raise GraphQLError("Not authorized to add ICE candidate")
            
            if not call.ice_candidates:
                call.ice_candidates = []
            
            call.ice_candidates.append(candidate)
            call.save()
            
            logger.info(f"Added ICE candidate to call {call_id}")
            
            return {
                'call_id': str(call_id),
                'success': True
            }
    except Call.DoesNotExist:
        logger.warning(f"Call {call_id} not found")
        raise GraphQLError("Call not found")
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found")
        raise GraphQLError("User not found")
    except Exception as e:
        logger.error(f"Error adding ICE candidate: {str(e)}")
        raise self.retry(exc=e, countdown=60)
#Periodic tasks
@shared_task
def send_chat_digest():
    """
    Send weekly digest of chat activity.
    """
    try:
    # Get active users from last week
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        active_users = User.objects.filter(
        last_login__gte=one_week_ago
        )

        for user in active_users:
            # Get unread messages count
            unread_count = Message.objects.filter(
                chatroom__participants=user
            ).exclude(
                read_by=user
            ).count()
            
            # Get missed calls
            missed_calls = Call.objects.filter(
                recipient=user,
                status='missed',
                start_time__gte=one_week_ago
            ).count()
            
            # Send email if there's activity
            if unread_count > 0 or missed_calls > 0:
                subject = "Your Weekly Chat Digest"
                message = f"Hi {user.username},\n\n"
                
                if unread_count > 0:
                    message += f"You have {unread_count} unread messages.\n"
                
                if missed_calls > 0:
                    message += f"You have {missed_calls} missed calls.\n"
                
                message += "\nVisit the app to catch up!"
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
                
                logger.info(f"Sent digest to {user.username}")
        
        return f"Sent digests to {active_users.count()} users"
    except Exception as e:
        logger.error(f"Error sending chat digest: {str(e)}")
        raise