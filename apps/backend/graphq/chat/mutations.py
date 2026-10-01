import graphene
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id
from django.contrib.auth import get_user_model
from chat.models import Call, ChatRoom, Message, MessageReaction, UserStatus
from graphq.accounts.types import UserNode
from graphq.chat.types import (CallNode, ChatRoomNode, MessageNode,
                               MessageReactionNode, StatusUpdateNode,
                               UserStatusNode, StatusViewNode)

from .subscription import OnNewMessage

class CreateChatRoom(relay.ClientIDMutation):
    class Input:
        participant_ids = graphene.List(graphene.String, required=True)
        name = graphene.String()
        is_group = graphene.Boolean(default_value=False)

    chatroom = graphene.Field(ChatRoomNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from chat.models import ChatRoom
        User = get_user_model()
        from graphql_relay.node.node import from_global_id

        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get participant_ids from input
        participant_ids = input.get("participant_ids", [])
        is_group = input.get("is_group", False)
        name = input.get("name")
        
        # Build participants list
        participants = [user]
        for pid in participant_ids:
            try:
                # Assuming pid is a global ID (like "VXNlcjo..."), decode it
                _, user_id = from_global_id(pid)
                p = User.objects.get(id=user_id)
                if p != user:
                    participants.append(p)
            except (User.DoesNotExist, ValueError, TypeError) as e:
                raise GraphQLError(f"User with ID '{pid}' not found or invalid")

        # If DM, check if it already exists
        if not is_group and len(participants) == 2:
            existing = (
                ChatRoom.objects
                .filter(is_group=False, participants=participants[0])
                .filter(participants=participants[1])
                .first()
            )
            if existing:
                return CreateChatRoom(chatroom=existing)

        chatroom = ChatRoom.objects.create(
            name=name or ", ".join([p.username for p in participants]),
            is_group=is_group,
            admin=user if is_group else None,
        )
        chatroom.participants.set(participants)

        return CreateChatRoom(chatroom=chatroom)

class UploadGroupPhoto(relay.ClientIDMutation):
    class Input:
        chatroom_id = graphene.String(required=True)
    
    chatroom = graphene.Field(ChatRoomNode)
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        chatroom_global_id = input["chatroom_id"]
        files = info.context.FILES
        
        if 'group_photo' not in files:
            raise GraphQLError("No group photo file provided")
        
        group_photo = files['group_photo']
        
        # Validate image
        valid_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if group_photo.content_type not in valid_image_types:
            raise GraphQLError(f"Invalid image type. Allowed: {', '.join(valid_image_types)}")
        
        # Validate file size (5MB max)
        if group_photo.size > 5 * 1024 * 1024:
            raise GraphQLError("Image file too large. Maximum size is 5MB")
        
        try:
            _, chatroom_uuid = from_global_id(chatroom_global_id)
            chatroom = ChatRoom.objects.get(id=chatroom_uuid)
            
            # Check if user is admin (for group chats) or participant (for DMs)
            if chatroom.is_group:
                if chatroom.admin != user:
                    raise GraphQLError("Only group admin can upload group photo")
            else:
                if user not in chatroom.participants.all():
                    raise GraphQLError("You are not a participant of this chat")
            
            # Upload the photo
            chatroom.group_photo = group_photo
            chatroom.save()
            
            print(f"✅ Group photo uploaded for chatroom: {chatroom.id}")
            
            # Notify participants
            from .subscriptions import OnGroupPhotoUpdated
            OnGroupPhotoUpdated.broadcast(
                group=str(chatroom.id),
                payload={
                    "chatroom_id": str(chatroom.id),
                    "group_photo_url": chatroom.group_photo.url if chatroom.group_photo else None
                }
            )
            
            return UploadGroupPhoto(chatroom=chatroom, success=True)
        except ChatRoom.DoesNotExist:
            raise GraphQLError("Chatroom not found")

class SendMessage(relay.ClientIDMutation):
    class Input:
        chatroom_id = graphene.String(required=True)  # This is a global ID
        text = graphene.String(required=True)
        reply_to = graphene.String()
        is_disappearing = graphene.Boolean(default_value=False)

    message = graphene.Field(MessageNode)
    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        print("🔵 SendMessage → Starting")

        user = info.context.user
        if not user.is_authenticated:
            print("❌ SendMessage → Not authenticated")
            raise Exception("Authentication required")

        print(f"👤 Authenticated user: {user.email}")

        chatroom_global_id = input["chatroom_id"]
        text = input["text"]
        reply_to = input.get("reply_to")
        is_disappearing = input.get("is_disappearing", False)

        if not text.strip():
            raise Exception("Message text required")

        from chat.models import ChatRoom, Message
        from graphql_relay.node.node import from_global_id  # Add this import

        # Decode the global ID to get the actual UUID
        try:
            _, chatroom_uuid = from_global_id(chatroom_global_id)
        except Exception as e:
            raise Exception(f"Invalid chatroom ID: {str(e)}")

        # Ensure the chatroom exists using the decoded UUID
        try:
            chatroom = ChatRoom.objects.get(id=chatroom_uuid)
        except ChatRoom.DoesNotExist:
            raise Exception("Chatroom does not exist")

        # Ensure sender is a participant
        if user not in chatroom.participants.all():
            chatroom.participants.add(user)

        # Handle reply_to if provided (also a global ID)
        reply_to_message = None
        if reply_to:
            try:
                _, reply_to_uuid = from_global_id(reply_to)
                reply_to_message = Message.objects.get(id=reply_to_uuid)
            except (ValueError, Message.DoesNotExist):
                # If reply_to is invalid, ignore it (or raise an error)
                print(f"⚠️ Invalid reply_to ID: {reply_to}")

        # Create the message
        message = Message.objects.create(
            chatroom=chatroom,
            sender=user,
            text=text,
            reply_to=reply_to_message,
            is_disappearing=is_disappearing,
        )

        print(f"📨 Message created → ID={message.id}")

        # Trigger GraphQL subscription
        OnNewMessage.notify_new_message(message)

        print(f"📡 Subscription broadcast sent for chatroom {chatroom_uuid}")

        return SendMessage(message=message, success=True)

class UpdateMessage(relay.ClientIDMutation):
    class Input:
        message_id = graphene.String(required=True)
        text = graphene.String()
        # For file attachments
    
    message = graphene.Field(MessageNode)
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        import mimetypes
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        message_global_id = input["message_id"]
        text = input.get("text")
        
        try:
            _, message_uuid = from_global_id(message_global_id)
            message = Message.objects.get(id=message_uuid)
            
            # Check ownership
            if message.sender != user:
                raise GraphQLError("You can only edit your own messages")
            
            # Check if message is too old (5 minutes max)
            from django.utils import timezone
            time_since_creation = timezone.now() - message.timestamp
            if time_since_creation.total_seconds() > 300:  # 5 minutes
                raise GraphQLError("Message is too old to edit")
            
            # Update text if provided
            if text is not None:
                message.text = text
            
            # Handle file uploads for attachments
            files = info.context.FILES
            
            if 'image' in files:
                image_file = files['image']
                # Validate image
                valid_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if image_file.content_type not in valid_image_types:
                    raise GraphQLError(f"Invalid image type. Allowed: {', '.join(valid_image_types)}")
                
                if image_file.size > 10 * 1024 * 1024:  # 10MB
                    raise GraphQLError("Image file too large. Maximum size is 10MB")
                
                message.image = image_file
            
            if 'file' in files:
                file_attachment = files['file']
                # Validate file size
                if file_attachment.size > 25 * 1024 * 1024:  # 25MB
                    raise GraphQLError("File too large. Maximum size is 25MB")
                
                message.file = file_attachment
            
            message.save()
            
            print(f"✅ Message updated: {message.id}")
            
            # Notify chatroom about message update
            from .subscriptions import OnMessageUpdated
            OnMessageUpdated.broadcast(
                group=str(message.chatroom.id),
                payload={
                    "message_id": str(message.id),
                    "updated_text": message.text,
                    "updated_at": message.timestamp.isoformat()
                }
            )
            
            return UpdateMessage(message=message, success=True)
        except Message.DoesNotExist:
            raise GraphQLError("Message not found")

class UpdateUserStatus(relay.ClientIDMutation):
    class Input:
        online = graphene.Boolean()
        typing = graphene.Boolean()
        typing_in = graphene.String()
    
    status = graphene.Field(UserStatusNode)  # Use string reference
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        online_value = input.get("online")
        typing_value = input.get("typing")
        typing_in_value = input.get("typing_in")
        
        # Get or create user status
        status, created = UserStatus.objects.get_or_create(user=user)
        
        # Update fields
        if online_value is not None:
            status.online = online_value
        
        if typing_value is not None:
            status.typing = typing_value
        
        if typing_in_value is not None:
            if typing_in_value == "" or typing_in_value.lower() == "null":
                status.typing_in = None
            else:
                try:
                    # Decode global ID
                    _, chatroom_uuid = from_global_id(typing_in_value)
                    chatroom = ChatRoom.objects.get(id=chatroom_uuid)
                    
                    # Check if user is a participant
                    if user not in chatroom.participants.all():
                        raise GraphQLError("Not a participant of this chat")
                    
                    status.typing_in = chatroom
                except ChatRoom.DoesNotExist:
                    raise GraphQLError("Chatroom not found")
                except Exception as e:
                    raise GraphQLError(f"Invalid chatroom ID: {str(e)}")
        
        status.save()
        return UpdateUserStatus(status=status)


class CreateStatusUpdate(relay.ClientIDMutation):
    class Input:
        status_type = graphene.String(required=True)
        text = graphene.String()
        # Files will come through multipart form data
    
    status = graphene.Field(StatusUpdateNode)
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from django.utils import timezone
        from graphql import GraphQLError
        import mimetypes
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        status_type = input.get("status_type")
        text = input.get("text", "")
        
        # Validate status type
        valid_types = dict(StatusUpdate.STATUS_TYPES).keys()
        if status_type not in valid_types:
            raise GraphQLError(f"Invalid status type. Must be one of: {', '.join(valid_types)}")
        
        # Check for existing active status
        recent_status = StatusUpdate.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).exists()
        
        if recent_status:
            raise GraphQLError("You already have an active status. Please wait for it to expire.")
        
        # Create status update
        status = StatusUpdate.objects.create(
            user=user,
            type=status_type,
            text=text,
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Handle file uploads
        files = info.context.FILES
        
        if status_type == 'image' and 'image' in files:
            image_file = files['image']
            # Validate image file
            valid_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in valid_image_types:
                status.delete()
                raise GraphQLError(f"Invalid image type. Allowed: {', '.join(valid_image_types)}")
            
            # Validate file size (5MB max)
            if image_file.size > 5 * 1024 * 1024:
                status.delete()
                raise GraphQLError("Image file too large. Maximum size is 5MB")
            
            status.image = image_file
            
        elif status_type == 'video' and 'video' in files:
            video_file = files['video']
            # Validate video file
            valid_video_types = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
            if video_file.content_type not in valid_video_types:
                status.delete()
                raise GraphQLError(f"Invalid video type. Allowed: {', '.join(valid_video_types)}")
            
            # Validate file size (20MB max)
            if video_file.size > 20 * 1024 * 1024:
                status.delete()
                raise GraphQLError("Video file too large. Maximum size is 20MB")
            
            status.video = video_file
        
        elif status_type in ['image', 'video']:
            # If status type requires a file but none was provided
            status.delete()
            raise GraphQLError(f"{status_type.capitalize()} status requires a file upload")
        
        status.save()
        
        print(f"✅ Status created: {status.id} by {user.username}")
        
        # Notify user's contacts about new status
        from .subscriptions import OnNewStatusUpdate
        OnNewStatusUpdate.broadcast(
            group=f"user_status_updates_{user.id}",
            payload={
                "status_id": str(status.id),
                "user_id": str(user.id),
                "type": status_type,
                "created_at": status.created_at.isoformat()
            }
        )
        
        return CreateStatusUpdate(status=status, success=True)

class DeleteStatusUpdate(relay.ClientIDMutation):
    class Input:
        status_id = graphene.String(required=True)
    
    success = graphene.Boolean()
    deleted_id = graphene.String()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        status_global_id = input["status_id"]
        
        try:
            _, status_uuid = from_global_id(status_global_id)
            status = StatusUpdate.objects.get(id=status_uuid)
            
            # Check ownership
            if status.user != user:
                raise GraphQLError("You can only delete your own status updates")
            
            status_id = str(status.id)
            status.delete()
            
            print(f"✅ Status deleted: {status_id}")
            
            return DeleteStatusUpdate(success=True, deleted_id=status_id)
        except StatusUpdate.DoesNotExist:
            raise GraphQLError("Status update not found")


class ViewStatusUpdate(relay.ClientIDMutation):
    class Input:
        status_id = graphene.String(required=True)
    
    success = graphene.Boolean()
    view = graphene.Field(StatusViewNode)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        from django.utils import timezone
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        status_global_id = input["status_id"]
        
        try:
            _, status_uuid = from_global_id(status_global_id)
            status = StatusUpdate.objects.get(id=status_uuid)
            
            # Check if status is expired
            if timezone.now() > status.expires_at:
                raise GraphQLError("This status has expired")
            
            # Can't view your own status
            if status.user == user:
                raise GraphQLError("You cannot view your own status")
            
            # Check if users have chatted before (are contacts)
            # Check if users have chatted before (are contacts)
            have_chatted = (
                ChatRoom.objects
                    .filter(is_group=False)
                    .filter(participants=user)
                    .filter(participants=status.user)
                    .exists()
            )

            
            if not have_chatted:
                raise GraphQLError("You can only view statuses from people you've chatted with")
            
            # Create or get status view
            view, created = StatusView.objects.get_or_create(
                status=status,
                user=user,
                defaults={'viewed_at': timezone.now()}
            )
            
            if created:
                print(f"✅ Status viewed: {status.id} by {user.username}")
                
                # Notify status owner
                from .subscriptions import OnStatusViewed
                OnStatusViewed.broadcast(
                    group=f"status_views_{status.id}",
                    payload={
                        "status_id": str(status.id),
                        "viewer_id": str(user.id),
                        "viewer_name": user.first_name or user.username,
                        "viewed_at": view.viewed_at.isoformat()
                    }
                )
            
            return ViewStatusUpdate(success=True, view=view)
        except StatusUpdate.DoesNotExist:
            raise GraphQLError("Status update not found")

class GetMyActiveStatus(graphene.relay.ClientIDMutation):
    class Input:
        pass  # No input needed
    
    status = graphene.Field(StatusUpdateNode)
    has_active = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from django.utils import timezone
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get user's active status (not expired)
        active_status = StatusUpdate.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        return GetMyActiveStatus(
            status=active_status,
            has_active=active_status is not None
        )


class GetStatusViews(graphene.relay.ClientIDMutation):
    class Input:
        status_id = graphene.String(required=True)
    
    views = graphene.List(StatusViewNode)
    view_count = graphene.Int()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        status_global_id = input["status_id"]
        
        try:
            _, status_uuid = from_global_id(status_global_id)
            status = StatusUpdate.objects.get(id=status_uuid)
            
            # Check ownership
            if status.user != user:
                raise GraphQLError("You can only view analytics for your own statuses")
            
            views = status.statusview_set.all().order_by('-viewed_at')
            
            return GetStatusViews(
                views=views,
                view_count=views.count()
            )
        except StatusUpdate.DoesNotExist:
            raise GraphQLError("Status update not found")

        
            
class MarkMessagesAsRead(relay.ClientIDMutation):
    class Input:
        chatroom_id = graphene.String(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get and decode chatroom ID
        chatroom_global_id = input["chatroom_id"]
        try:
            _, chatroom_uuid = from_global_id(chatroom_global_id)
            
            chatroom = ChatRoom.objects.get(id=chatroom_uuid)
            if user not in chatroom.participants.all():
                raise GraphQLError("Not a participant of this chat")
            
            unread_messages = chatroom.messages.exclude(read_by=user)
            for message in unread_messages:
                message.read_by.add(user)
            
            return MarkMessagesAsRead(success=True)
        except ChatRoom.DoesNotExist:
            raise GraphQLError("Chatroom not found")
        except Exception as e:
            raise GraphQLError(f"Invalid chatroom ID: {str(e)}")
        

class ReactToMessage(relay.ClientIDMutation):
    class Input:
        message_id = graphene.String(required=True)
        reaction = graphene.String(required=True)
    
    reaction = graphene.Field(MessageReactionNode)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        message_global_id = input["message_id"]
        reaction = input["reaction"]
        
        try:
            # Decode message ID
            _, message_uuid = from_global_id(message_global_id)
            message = Message.objects.get(id=message_uuid)
            
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
                defaults={'reaction': reaction}  # or 'emoji' depending on your model field
            )
            
            # Notify subscribers
            from .subscriptions import OnMessageReaction
            OnMessageReaction.broadcast(
                group=str(message.chatroom.id),
                payload={
                    "message_id": str(message.id),
                    "reaction": reaction_obj
                }
            )
            
            return ReactToMessage(reaction=reaction_obj)
        except Message.DoesNotExist:
            raise GraphQLError("Message not found")

class ToggleDisappearingMessages(relay.ClientIDMutation):
    class Input:
        chatroom_id = graphene.String(required=True)
        duration_seconds = graphene.Int()
    
    chatroom = graphene.Field(ChatRoomNode)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        chatroom_global_id = input["chatroom_id"]
        duration_seconds = input.get("duration_seconds")
        
        try:
            # Decode chatroom ID
            _, chatroom_uuid = from_global_id(chatroom_global_id)
            chatroom = ChatRoom.objects.get(id=chatroom_uuid)
            
            if chatroom.admin != user:
                raise GraphQLError("Only admin can change disappearing messages settings")
            
            chatroom.disappearing_messages_duration = duration_seconds
            chatroom.save()
            
            # Notify participants
            from .subscriptions import OnDisappearingMessagesChanged
            OnDisappearingMessagesChanged.broadcast(
                group=str(chatroom.id),
                payload={
                    "chatroom_id": str(chatroom.id),
                    "duration_seconds": duration_seconds
                }
            )
            
            return ToggleDisappearingMessages(chatroom=chatroom)
        except ChatRoom.DoesNotExist:
            raise GraphQLError("Chatroom not found")
        
class CreateStatusUpdate(relay.ClientIDMutation):
    class Input:
        status_type = graphene.String(required=True)  # Changed from 'type' to avoid conflict
        text = graphene.String()
    
    status = graphene.Field(StatusUpdateNode)
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        status_type = input["status_type"]
        text = input.get("text")
        
        if status_type not in dict(StatusUpdate.STATUS_TYPES).keys():
            raise GraphQLError("Invalid status type")
        
        status = StatusUpdate.objects.create(
            user=user,
            type=status_type,  # Use 'type' field in model
            text=text,
            # Note: File handling would need additional implementation
        )
        
        # Notify contacts
        from .subscriptions import OnNewStatusUpdate
        OnNewStatusUpdate.broadcast(
            group=f"user_status_updates_{user.id}",
            payload={"status": status}
        )
        
        return CreateStatusUpdate(status=status, success=True)


class ViewStatusUpdate(relay.ClientIDMutation):
    class Input:
        status_id = graphene.String(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get status ID from input
        status_global_id = input["status_id"]
        
        try:
            # Decode status ID
            _, status_uuid = from_global_id(status_global_id)
            status = StatusUpdate.objects.get(id=status_uuid)
            
            if status.user == user:
                raise GraphQLError("Cannot view your own status")
            
            # Check if user is a contact (in a chat with the status owner)
            if not ChatRoom.objects.filter(
                participants=user
            ).filter(
                participants=status.user
            ).exists():
                raise GraphQLError("Can only view statuses from your contacts")
            
            StatusView.objects.get_or_create(
                status=status,
                user=user
            )
            
            # Notify status owner
            from .subscriptions import OnStatusViewed
            OnStatusViewed.broadcast(
                group=f"status_views_{status.id}",
                payload={
                    "status_id": str(status.id),
                    "viewer_id": str(user.id)
                }
            )
            
            return ViewStatusUpdate(success=True)
        except StatusUpdate.DoesNotExist:
            raise GraphQLError("Status not found")
        
class InitiateCall(relay.ClientIDMutation):
    class Input:
        recipient_id = graphene.String(required=True)
        call_type = graphene.String(required=True)
    
    call = graphene.Field(CallNode)
    ice_servers = graphene.List(graphene.String)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from django.contrib.auth import get_user_model
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        recipient_global_id = input["recipient_id"]
        call_type = input["call_type"]
        
        # Decode recipient ID
        try:
            _, recipient_uuid = from_global_id(recipient_global_id)
            User = get_user_model()
            recipient = User.objects.get(id=recipient_uuid)
        except Exception as e:
            raise GraphQLError(f"Invalid recipient ID: {str(e)}")
        
        # Create call record
        call = Call.objects.create(
            caller=user,
            recipient=recipient,
            call_type=call_type,
            status='initiated'
        )
        
        # Return ICE servers (STUN/TURN)
        ice_servers = [
            "stun:stun.l.google.com:19302",
            "turn:localhost:3478?transport=udp"  # Your local TURN server
        ]
        
        return InitiateCall(call=call, ice_servers=ice_servers)
    
class AnswerCall(relay.ClientIDMutation):
    class Input:
        call_id = graphene.String(required=True)
        answer = graphene.String(required=True)
    
    call = graphene.Field(CallNode)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        call_global_id = input["call_id"]
        answer = input["answer"]
        
        try:
            # Decode call ID
            _, call_uuid = from_global_id(call_global_id)
            call = Call.objects.get(id=call_uuid)
            
            if call.recipient != user:
                raise GraphQLError("Not authorized to answer this call")
            
            call.status = 'in_progress'
            call.sdp_answer = answer
            call.save()
            
            return AnswerCall(call=call)
        except Call.DoesNotExist:
            raise GraphQLError("Call not found")
        
class EndCall(relay.ClientIDMutation):
    class Input:
        call_id = graphene.String(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from django.utils import timezone
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get call ID from input
        call_global_id = input["call_id"]
        
        try:
            # Decode call ID
            _, call_uuid = from_global_id(call_global_id)
            call = Call.objects.get(id=call_uuid)
            
            if call.caller != user and call.recipient != user:
                raise GraphQLError("Not authorized to end this call")
            
            call.status = 'completed'
            call.end_time = timezone.now()
            call.save()
            
            return EndCall(success=True)
        except Call.DoesNotExist:
            raise GraphQLError("Call not found")
        
class AddIceCandidate(relay.ClientIDMutation):
    class Input:
        call_id = graphene.String(required=True)
        candidate = graphene.String(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from graphql_relay.node.node import from_global_id
        from graphql import GraphQLError
        
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # Get values from input
        call_global_id = input["call_id"]
        candidate = input["candidate"]
        
        try:
            # Decode call ID
            _, call_uuid = from_global_id(call_global_id)
            call = Call.objects.get(id=call_uuid)
            
            if call.caller != user and call.recipient != user:
                raise GraphQLError("Not authorized to add ICE candidate")
            
            if not call.ice_candidates:
                call.ice_candidates = []
            
            call.ice_candidates.append(candidate)
            call.save()
            
            return AddIceCandidate(success=True)
        except Call.DoesNotExist:
            raise GraphQLError("Call not found")
        
        
class ChatMutations(graphene.ObjectType):
    send_message = SendMessage.Field()
    create_chatroom = CreateChatRoom.Field()
    update_user_status = UpdateUserStatus.Field()
    mark_messages_as_read = MarkMessagesAsRead.Field()
    react_to_message = ReactToMessage.Field()
    toggle_disappearing_messages = ToggleDisappearingMessages.Field()
    create_status_update = CreateStatusUpdate.Field()
    view_status_update = ViewStatusUpdate.Field()
    initiate_call = InitiateCall.Field()
    answer_call = AnswerCall.Field()
    end_call = EndCall.Field()
    add_ice_candidate = AddIceCandidate.Field()
    create_status_update = CreateStatusUpdate.Field()
    delete_status_update = DeleteStatusUpdate.Field()
    view_status_update = ViewStatusUpdate.Field()
    get_my_active_status = GetMyActiveStatus.Field()
    get_status_views = GetStatusViews.Field()
