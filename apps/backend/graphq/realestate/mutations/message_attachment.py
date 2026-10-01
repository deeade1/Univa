# apps/backend/realestate/mutations/message_attachment.py

"""
Message Attachment Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.message_attachment import MessageAttachment
from realestate.models.message import Message
from graphq.realestate.types.message_attachment import MessageAttachmentNode




# =============================================================================
# Create Message Attachment Mutation
# =============================================================================

class CreateMessageAttachmentMutation(relay.ClientIDMutation):
    """
    Create a new message attachment.
    
    Allows users to attach files to their messages. Only the message sender
    can add attachments to a message.
    """
    
    class Input:
        id = graphene.ID(required=True)
        file_name = graphene.String(required=False)
        file_type = graphene.String(required=False)
    
    message_attachment = graphene.Field(MessageAttachmentNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new message attachment.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageAttachmentInput data
        
        Returns:
            CreateMessageAttachmentMutation instance
        """
        errors = {}
        
        # Extract input
        message_id = input.get('message_id')
        
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
        
        # Check permission - only the sender can add attachments
        if message.sender != user and not user.is_staff:
            errors['permission'] = ['You can only add attachments to your own messages.']
            return cls(success=False, errors=errors)
        
        # Get file from request
        file_obj = None
        if hasattr(info.context, 'FILES'):
            file_obj = info.context.FILES.get('file')
        
        if not file_obj:
            errors['file'] = ['File is required.']
            return cls(success=False, errors=errors)
        
        # Determine file type from file name
        file_name = file_obj.name
        file_type = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
        
        try:
            # Create message attachment
            message_attachment = MessageAttachment.objects.create(
                message=message,
                file=file_obj,
                file_name=file_name,
                file_type=file_type,
            )
            
            return cls(
                message_attachment=message_attachment,
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
# Update Message Attachment Mutation
# =============================================================================

class UpdateMessageAttachmentMutation(relay.ClientIDMutation):
    """
    Update a message attachment.
    
    Allows updating the file name and type metadata of an attachment.
    """
    
    class Input:
        id = graphene.ID(required=True)
        file_name = graphene.String(required=False)
        file_type = graphene.String(required=False)
    
    message_attachment = graphene.Field(MessageAttachmentNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update a message attachment.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MessageAttachmentUpdateInput data
        
        Returns:
            UpdateMessageAttachmentMutation instance
        """
        errors = {}
        
        # Extract input
        attachment_id = input.get('id')
        file_name = input.get('file_name')
        file_type = input.get('file_type')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve attachment
        try:
            pk = from_global_id(attachment_id)[1]
            message_attachment = MessageAttachment.objects.get(pk=pk)
        except MessageAttachment.DoesNotExist:
            errors['id'] = ['Message attachment not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the sender of the message can update
        if message_attachment.message.sender != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this attachment.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if file_name is not None:
                message_attachment.file_name = file_name
            if file_type is not None:
                message_attachment.file_type = file_type
            
            message_attachment.full_clean()
            message_attachment.save()
            
            return cls(
                message_attachment=message_attachment,
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
# Delete Message Attachment Mutation
# =============================================================================

class DeleteMessageAttachmentMutation(relay.ClientIDMutation):
    """
    Delete a message attachment.
    
    Removes an attachment from a message and deletes the physical file.
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
        Delete a message attachment.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Attachment ID to delete
        
        Returns:
            DeleteMessageAttachmentMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve attachment
        try:
            pk = from_global_id(id)[1]
            message_attachment = MessageAttachment.objects.get(pk=pk)
        except MessageAttachment.DoesNotExist:
            errors['id'] = ['Message attachment not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the sender of the message can delete
        if message_attachment.message.sender != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this attachment.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            message_attachment.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateMessageAttachmentsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple message attachments.
    
    Allows uploading multiple files to a message at once.
    """
    
    class Input:
        message_id = graphene.ID(required=True)
        id = graphene.ID(required=True)
        file_name = graphene.String(required=False)
        file_type = graphene.String(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create message attachments.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            message_id: Message ID
            attachments: List of attachment metadata
        
        Returns:
            BulkCreateMessageAttachmentsMutation instance
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
        
        # Check permission
        if message.sender != user and not user.is_staff:
            errors['permission'] = ['You can only add attachments to your own messages.']
            return cls(success=False, errors=errors)
        
        # Get files from request
        uploaded_files = []
        if hasattr(info.context, 'FILES'):
            uploaded_files = info.context.FILES.getlist('files')
        
        if not uploaded_files:
            errors['files'] = ['At least one file is required.']
            return cls(success=False, errors=errors)
        
        # Process each file
        for idx, attachment_data in enumerate(attachments):
            try:
                # Get corresponding file object
                file_obj = uploaded_files[idx] if idx < len(uploaded_files) else None
                
                if not file_obj:
                    errors[f'attachment_{idx}'] = ['File is required.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': ['No file provided'],
                    })
                    continue
                
                # Determine file type
                file_name = file_obj.name
                file_type = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
                
                # Create attachment
                message_attachment = MessageAttachment.objects.create(
                    message=message,
                    file=file_obj,
                    file_name=file_name,
                    file_type=file_type,
                )
                
                success_count += 1
                results.append({
                    'index': idx,
                    'id': message_attachment.id,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[f'attachment_{idx}'] = [str(e)]
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


class BulkDeleteMessageAttachmentsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple message attachments.
    
    Allows deleting multiple attachments from a message at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
    
    deleted_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids):
        """
        Bulk delete message attachments.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of attachment IDs to delete
        
        Returns:
            BulkDeleteMessageAttachmentsMutation instance
        """
        errors = {}
        deleted_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for attachment_id in ids:
            try:
                pk = from_global_id(attachment_id)[1]
                message_attachment = MessageAttachment.objects.get(pk=pk)
                
                # Check permission
                if message_attachment.message.sender != user and not user.is_staff:
                    errors[attachment_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                message_attachment.delete()
                deleted_ids.append(attachment_id)
                success_count += 1
                
            except MessageAttachment.DoesNotExist:
                errors[attachment_id] = ['Message attachment not found.']
                failure_count += 1
            except Exception as e:
                errors[attachment_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Get Message Attachments Mutation
# =============================================================================

class GetMessageAttachmentsMutation(relay.ClientIDMutation):
    """
    Get all attachments for a message.
    
    Returns all attachments associated with a message.
    """
    
    class Input:
        message_id = graphene.ID(required=True)
    
    attachments = graphene.List(MessageAttachmentNode)
    count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, message_id):
        """
        Get all attachments for a message.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            message_id: Message ID
        
        Returns:
            GetMessageAttachmentsMutation instance
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
        
        # Check permission - user must be sender or recipient
        is_participant = (
            message.sender == user or 
            message.recipient == user or
            user.is_staff
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to view attachments for this message.']
            return cls(success=False, errors=errors)
        
        try:
            attachments = MessageAttachment.objects.filter(message=message)
            
            return cls(
                attachments=attachments,
                count=attachments.count(),
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class MessageAttachmentMutations(graphene.ObjectType):
    """All message attachment mutations."""
    
    # CRUD operations
    create_message_attachment = CreateMessageAttachmentMutation.Field()
    update_message_attachment = UpdateMessageAttachmentMutation.Field()
    delete_message_attachment = DeleteMessageAttachmentMutation.Field()
    
    # Bulk operations
    bulk_create_message_attachments = BulkCreateMessageAttachmentsMutation.Field()
    bulk_delete_message_attachments = BulkDeleteMessageAttachmentsMutation.Field()
    
    # Query
    get_message_attachments = GetMessageAttachmentsMutation.Field()