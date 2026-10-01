# apps/backend/realestate/mutations/message.py

"""
Message Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.message import Message
from realestate.models.message_thread import MessageThread
from graphq.realestate.types.message import MessageNode



# =============================================================================
# Create Message Mutation
# =============================================================================

class CreateMessageMutation(relay.ClientIDMutation):
    """
    Create a new message in a thread.
    
    Adds a message to a thread and updates the thread's updated_at timestamp.
    """
    
    class Input:
        id = graphene.ID(required=True)
        content = graphene.String(required=False)
        read = graphene.Boolean(required=False)
    
    message = graphene.Field(MessageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new message.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageInput data
        
        Returns:
            CreateMessageMutation instance
        """
        errors = {}
        
        # Extract input
        thread_id = input.get('thread_id')
        content = input.get('content')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate content
        if not content or not content.strip():
            errors['content'] = ['Message content is required.']
            return cls(success=False, errors=errors)
        
        # Resolve thread
        try:
            pk = from_global_id(thread_id)[1]
            message_thread = MessageThread.objects.get(pk=pk)
        except MessageThread.DoesNotExist:
            errors['thread_id'] = ['Message thread not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['thread_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if user is a participant
        if user not in message_thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        try:
            # Create message
            message = Message.objects.create(
                thread=message_thread,
                sender=user,
                content=content.strip(),
                read=False,
            )
            
            # Update thread's updated_at
            message_thread.save()  # auto_now will handle the update
            
            return cls(
                message=message,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Message Mutation
# =============================================================================

class UpdateMessageMutation(relay.ClientIDMutation):
    """
    Update a message.
    
    Allows updating the content or read status of a message.
    Only the sender can update the content.
    """
    
    class Input:
        id = graphene.ID(required=True)
        content = graphene.String(required=False)
        read = graphene.Boolean(required=False)
    
    message = graphene.Field(MessageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update a message.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageUpdateInput data
        
        Returns:
            UpdateMessageMutation instance
        """
        errors = {}
        
        # Extract input
        message_id = input.get('id')
        content = input.get('content')
        read = input.get('read')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve message
        try:
            pk = from_global_id(message_id)[1]
            message = Message.objects.get(pk=pk)
        except Message.DoesNotExist:
            errors['id'] = ['Message not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only sender can update content
        if content is not None:
            if message.sender != user and not user.is_staff:
                errors['permission'] = ['Only the sender can update message content.']
                return cls(success=False, errors=errors)
            
            if not content or not content.strip():
                errors['content'] = ['Message content is required.']
                return cls(success=False, errors=errors)
        
        # Check permission for read status - only recipients can mark as read
        if read is not None:
            if message.sender == user and read is True and not user.is_staff:
                errors['permission'] = ['Senders cannot mark their own messages as read.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if content is not None:
                message.content = content.strip()
            if read is not None:
                message.read = read
            
            message.full_clean()
            message.save()
            
            return cls(
                message=message,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Message Mutation
# =============================================================================

class DeleteMessageMutation(relay.ClientIDMutation):
    """
    Delete a message.
    
    Removes a message from a thread. Only the sender or staff can delete.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Delete a message.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Message ID to delete
        
        Returns:
            DeleteMessageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve message
        try:
            pk = from_global_id(id)[1]
            message = Message.objects.get(pk=pk)
        except Message.DoesNotExist:
            errors['id'] = ['Message not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only sender or staff can delete
        if message.sender != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this message.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            message.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Mark Message as Read Mutation
# =============================================================================

class MarkMessageAsReadMutation(relay.ClientIDMutation):
    """
    Mark a message as read.
    
    This is a convenience mutation for marking a message as read.
    Only recipients can mark messages as read.
    """
    
    class Input:
        message_id = graphene.ID(required=True)
    
    message = graphene.Field(MessageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, message_id):
        """
        Mark a message as read.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            message_id: Message ID to mark as read
        
        Returns:
            MarkMessageAsReadMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve message
        try:
            pk = from_global_id(message_id)[1]
            message = Message.objects.get(pk=pk)
        except Message.DoesNotExist:
            errors['message_id'] = ['Message not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['message_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if user is the sender (cannot mark own messages as read)
        if message.sender == user:
            errors['permission'] = ['You cannot mark your own messages as read.']
            return cls(success=False, errors=errors)
        
        # Check if user is a participant in the thread
        if user not in message.thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        try:
            message.read = True
            message.save()
            
            return cls(
                message=message,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Mark Thread Messages as Read Mutation
# =============================================================================

class MarkThreadMessagesAsReadMutation(relay.ClientIDMutation):
    """
    Mark all messages in a thread as read for the current user.
    
    This is a convenience mutation for marking all unread messages
    in a thread as read.
    """
    
    class Input:
        thread_id = graphene.ID(required=True)
    
    success = graphene.Boolean()
    count = graphene.Int()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, thread_id):
        """
        Mark all messages in a thread as read.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            thread_id: Thread ID
        
        Returns:
            MarkThreadMessagesAsReadMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve thread
        try:
            pk = from_global_id(thread_id)[1]
            message_thread = MessageThread.objects.get(pk=pk)
        except MessageThread.DoesNotExist:
            errors['thread_id'] = ['Message thread not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['thread_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if user is a participant
        if user not in message_thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        try:
            # Get unread messages where user is not the sender
            unread_messages = Message.objects.filter(
                thread=message_thread,
                read=False
            ).exclude(sender=user)
            
            count = unread_messages.count()
            
            # Mark all as read
            unread_messages.update(read=True)
            
            return cls(
                success=True,
                count=count,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateMessagesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple messages.
    
    Allows creating multiple messages in a thread at once.
    """
    
    class Input:
        thread_id = graphene.ID(required=True)
        contents = graphene.List(graphene.String, required=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, thread_id, contents):
        """
        Bulk create messages.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            thread_id: Thread ID
            contents: List of message contents
        
        Returns:
            BulkCreateMessagesMutation instance
        """
        errors = {}
        results = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve thread
        try:
            pk = from_global_id(thread_id)[1]
            message_thread = MessageThread.objects.get(pk=pk)
        except MessageThread.DoesNotExist:
            errors['thread_id'] = ['Message thread not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['thread_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if user is a participant
        if user not in message_thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        for idx, content in enumerate(contents):
            try:
                if not content or not content.strip():
                    errors[f'message_{idx}'] = ['Message content is required.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': ['Content is required'],
                    })
                    continue
                
                # Create message
                message = Message.objects.create(
                    thread=message_thread,
                    sender=user,
                    content=content.strip(),
                    read=False,
                )
                
                success_count += 1
                results.append({
                    'index': idx,
                    'id': message.id,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[f'message_{idx}'] = [str(e)]
                results.append({
                    'index': idx,
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        # Update thread's updated_at
        if success_count > 0:
            message_thread.save()
        
        return cls(
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class MessageMutations(graphene.ObjectType):
    """All message mutations."""
    
    # CRUD operations
    create_message = CreateMessageMutation.Field()
    update_message = UpdateMessageMutation.Field()
    delete_message = DeleteMessageMutation.Field()
    
    # Read status
    mark_message_as_read = MarkMessageAsReadMutation.Field()
    mark_thread_messages_as_read = MarkThreadMessagesAsReadMutation.Field()
    
    # Bulk operations
    bulk_create_messages = BulkCreateMessagesMutation.Field()