# apps/backend/realestate/mutations/message_thread.py

"""
Message Thread Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.message_thread import MessageThread
from realestate.models.listing import Listing
from graphq.realestate.types.message_thread import MessageThreadNode

# =============================================================================
# Input Types
# =============================================================================

class MessageThreadInput(graphene.InputObjectType):
    """Input for message thread creation."""
    
    property_id = graphene.ID(required=False)
    participant_ids = graphene.List(graphene.ID, required=True)


class MessageThreadUpdateInput(graphene.InputObjectType):
    """Input for message thread update."""
    
    id = graphene.ID(required=True)
    property_id = graphene.ID(required=False)


class AddParticipantInput(graphene.InputObjectType):
    """Input for adding a participant to a thread."""
    
    thread_id = graphene.ID(required=True)
    participant_id = graphene.ID(required=True)


class RemoveParticipantInput(graphene.InputObjectType):
    """Input for removing a participant from a thread."""
    
    thread_id = graphene.ID(required=True)
    participant_id = graphene.ID(required=True)


# =============================================================================
# Create Message Thread Mutation
# =============================================================================

class CreateMessageThreadMutation(relay.ClientIDMutation):
    """
    Create a new message thread.
    
    Creates a thread for participants to discuss a property or general topics.
    The creator is automatically added as a participant.
    """
    
    class Input:
        property_id = graphene.ID(required=False)
        participant_ids = graphene.List(graphene.ID, required=True)
    
    message_thread = graphene.Field(MessageThreadNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new message thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageThreadInput data
        
        Returns:
            CreateMessageThreadMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        participant_ids = input.get('participant_ids', [])
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate participants
        if not participant_ids:
            errors['participant_ids'] = ['At least one participant is required.']
            return cls(success=False, errors=errors)
        
        # Resolve property if provided
        property_obj = None
        if property_id:
            try:
                pk = from_global_id(property_id)[1]
                property_obj = Listing.objects.get(pk=pk)
            except Listing.DoesNotExist:
                errors['property_id'] = ['Property not found.']
                return cls(success=False, errors=errors)
            except Exception as e:
                errors['property_id'] = [str(e)]
                return cls(success=False, errors=errors)
        
        # Build participant list
        participants = [user]
        
        for participant_id in participant_ids:
            try:
                pk = from_global_id(participant_id)[1]
                participant = User.objects.get(pk=pk)
                
                # Don't add duplicates
                if participant not in participants:
                    participants.append(participant)
                    
            except Exception as e:
                errors[f'participant_{participant_id}'] = ['User not found.']
                return cls(success=False, errors=errors)
        
        try:
            # Create message thread
            message_thread = MessageThread.objects.create(
                property=property_obj,
            )
            
            # Add all participants
            message_thread.participants.set(participants)
            
            return cls(
                message_thread=message_thread,
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
# Update Message Thread Mutation
# =============================================================================

class UpdateMessageThreadMutation(relay.ClientIDMutation):
    """
    Update a message thread.
    
    Allows updating the property associated with a thread.
    """
    
    class Input:
        property_id = graphene.ID(required=False)
        participant_ids = graphene.List(graphene.ID, required=True)
    
    message_thread = graphene.Field(MessageThreadNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update a message thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageThreadUpdateInput data
        
        Returns:
            UpdateMessageThreadMutation instance
        """
        errors = {}
        
        # Extract input
        thread_id = input.get('id')
        property_id = input.get('property_id')
        
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
            errors['id'] = ['Message thread not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be a participant
        if user not in message_thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        # Resolve property if provided
        if property_id:
            try:
                pk = from_global_id(property_id)[1]
                property_obj = Listing.objects.get(pk=pk)
                message_thread.property = property_obj
            except Listing.DoesNotExist:
                errors['property_id'] = ['Property not found.']
                return cls(success=False, errors=errors)
        
        try:
            message_thread.full_clean()
            message_thread.save()
            
            return cls(
                message_thread=message_thread,
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
# Delete Message Thread Mutation
# =============================================================================

class DeleteMessageThreadMutation(relay.ClientIDMutation):
    """
    Delete a message thread.
    
    Removes a message thread and all associated messages and attachments.
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
        Delete a message thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Thread ID to delete
        
        Returns:
            DeleteMessageThreadMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve thread
        try:
            pk = from_global_id(id)[1]
            message_thread = MessageThread.objects.get(pk=pk)
        except MessageThread.DoesNotExist:
            errors['id'] = ['Message thread not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete threads
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete threads.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            message_thread.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Add Participant to Thread Mutation
# =============================================================================

class AddParticipantToThreadMutation(relay.ClientIDMutation):
    """
    Add a participant to a message thread.
    
    Allows adding a new user to an existing thread.
    """
    
    class Input:
        property_id = graphene.ID(required=False)
        participant_ids = graphene.List(graphene.ID, required=True)
    
    message_thread = graphene.Field(MessageThreadNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Add a participant to a thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: AddParticipantInput data
        
        Returns:
            AddParticipantToThreadMutation instance
        """
        errors = {}
        
        # Extract input
        thread_id = input.get('thread_id')
        participant_id = input.get('participant_id')
        
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
        
        # Check permission - user must be a participant
        if user not in message_thread.participants.all() and not user.is_staff:
            errors['permission'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        # Resolve participant
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            pk = from_global_id(participant_id)[1]
            participant = User.objects.get(pk=pk)
        except Exception as e:
            errors['participant_id'] = ['User not found.']
            return cls(success=False, errors=errors)
        
        # Check if participant is already in the thread
        if participant in message_thread.participants.all():
            errors['participant'] = ['User is already a participant in this thread.']
            return cls(success=False, errors=errors)
        
        try:
            # Add participant
            message_thread.participants.add(participant)
            
            return cls(
                message_thread=message_thread,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Remove Participant from Thread Mutation
# =============================================================================

class RemoveParticipantFromThreadMutation(relay.ClientIDMutation):
    """
    Remove a participant from a message thread.
    
    Allows removing a user from an existing thread.
    """
    
    class Input:
       property_id = graphene.ID(required=False)
       participant_ids = graphene.List(graphene.ID, required=True)
       
    message_thread = graphene.Field(MessageThreadNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Remove a participant from a thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: RemoveParticipantInput data
        
        Returns:
            RemoveParticipantFromThreadMutation instance
        """
        errors = {}
        
        # Extract input
        thread_id = input.get('thread_id')
        participant_id = input.get('participant_id')
        
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
        
        # Resolve participant
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            pk = from_global_id(participant_id)[1]
            participant = User.objects.get(pk=pk)
        except Exception as e:
            errors['participant_id'] = ['User not found.']
            return cls(success=False, errors=errors)
        
        # Check permission - user must be the one being removed or staff
        if user != participant and not user.is_staff:
            errors['permission'] = ['You do not have permission to remove this participant.']
            return cls(success=False, errors=errors)
        
        # Check if participant is in the thread
        if participant not in message_thread.participants.all():
            errors['participant'] = ['User is not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        # Don't allow removing the last participant
        if message_thread.participants.count() <= 1:
            errors['participant'] = ['Cannot remove the last participant from a thread.']
            return cls(success=False, errors=errors)
        
        try:
            # Remove participant
            message_thread.participants.remove(participant)
            
            return cls(
                message_thread=message_thread,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Leave Thread Mutation
# =============================================================================

class LeaveThreadMutation(relay.ClientIDMutation):
    """
    Leave a message thread.
    
    Allows a user to remove themselves from a thread.
    """
    
    class Input:
        thread_id = graphene.ID(required=True)
    
    message_thread = graphene.Field(MessageThreadNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, thread_id):
        """
        Leave a message thread.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            thread_id: Thread ID to leave
        
        Returns:
            LeaveThreadMutation instance
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
        if user not in message_thread.participants.all():
            errors['participant'] = ['You are not a participant in this thread.']
            return cls(success=False, errors=errors)
        
        # Don't allow leaving if last participant
        if message_thread.participants.count() <= 1:
            errors['participant'] = ['Cannot leave the last participant from a thread.']
            return cls(success=False, errors=errors)
        
        try:
            # Remove user from thread
            message_thread.participants.remove(user)
            
            return cls(
                message_thread=message_thread,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateMessageThreadsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple message threads.
    
    Allows creating multiple threads at once.
    """
    
    class Input:
        property_id = graphene.ID(required=False)
        participant_ids = graphene.List(graphene.ID, required=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create message threads.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            threads: List of thread inputs
        
        Returns:
            BulkCreateMessageThreadsMutation instance
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
        
        for idx, thread_input in enumerate(threads):
            try:
                # Use the create mutation for each thread
                result = CreateMessageThreadMutation.mutate_and_get_payload(
                    root, info, thread_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'thread_id': result.message_thread.id if result.message_thread else None,
                    })
                else:
                    failure_count += 1
                    errors[f'thread_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'thread_{idx}'] = [str(e)]
                results.append({
                    'index': idx,
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
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

class MessageThreadMutations(graphene.ObjectType):
    """All message thread mutations."""
    
    # CRUD operations
    create_message_thread = CreateMessageThreadMutation.Field()
    update_message_thread = UpdateMessageThreadMutation.Field()
    delete_message_thread = DeleteMessageThreadMutation.Field()
    
    # Participant management
    add_participant_to_thread = AddParticipantToThreadMutation.Field()
    remove_participant_from_thread = RemoveParticipantFromThreadMutation.Field()
    leave_thread = LeaveThreadMutation.Field()
    
    # Bulk operations
    bulk_create_message_threads = BulkCreateMessageThreadsMutation.Field()