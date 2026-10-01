# apps/backend/realestate/mutations/document_signature.py

"""
Document Signature Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.document_signature import DocumentSignature
from realestate.models.document import Document
from graphq.realestate.types.document_signature import DocumentSignatureNode



# =============================================================================
# Input Types
# =============================================================================

class DocumentSignatureInput(graphene.InputObjectType):
    """Input for document signature creation."""
    
    document_id = graphene.ID(required=True)
    signature_image = graphene.String(required=True)  # Base64 encoded image or file path


class DocumentSignatureUpdateInput(graphene.InputObjectType):
    """Input for document signature update."""
    
    id = graphene.ID(required=True)
    signature_image = graphene.String(required=False)


# =============================================================================
# Create Document Signature Mutation
# =============================================================================

class CreateDocumentSignatureMutation(relay.ClientIDMutation):
    """
    Create a new document signature.
    
    Allows authorized users to sign documents that require signatures.
    Only staff, property owners, and agents can sign documents.
    """
    
    class Input:
        document_id = graphene.ID(required=True)
        signature_image = graphene.String(required=True)
    
    document_signature = graphene.Field(DocumentSignatureNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new document signature.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DocumentSignatureInput data
        
        Returns:
            CreateDocumentSignatureMutation instance
        """
        errors = {}
        
        # Extract input
        document_id = input.get('document_id')
        signature_image = input.get('signature_image')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate signature image
        if not signature_image:
            errors['signature_image'] = ['Signature image is required.']
            return cls(success=False, errors=errors)
        
        # Resolve document
        try:
            pk = from_global_id(document_id)[1]
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            errors['document_id'] = ['Document not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['document_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if document requires signature
        if not document.requires_signature:
            errors['document'] = ['This document does not require a signature.']
            return cls(success=False, errors=errors)
        
        # Check if user has already signed this document
        if DocumentSignature.objects.filter(document=document, user=user).exists():
            errors['signature'] = ['You have already signed this document.']
            return cls(success=False, errors=errors)
        
        # Check authorization - user must be staff, owner, or agent
        property_obj = document.package.property if hasattr(document, 'package') else None
        
        is_authorized = (
            user.is_staff or
            (property_obj and hasattr(property_obj, 'owner') and property_obj.owner and 
             hasattr(property_obj.owner, 'user') and property_obj.owner.user == user) or
            (property_obj and hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to sign this document.']
            return cls(success=False, errors=errors)
        
        try:
            # Get IP address from request
            ip_address = None
            if hasattr(info.context, 'META'):
                x_forwarded_for = info.context.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = info.context.META.get('REMOTE_ADDR')
            
            # Create document signature
            document_signature = DocumentSignature.objects.create(
                document=document,
                user=user,
                signature_image=signature_image,
                ip_address=ip_address or '0.0.0.0',
            )
            
            # Update document status if all signatures are complete
            cls._check_document_completion(document)
            
            return cls(
                document_signature=document_signature,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)
    
    @classmethod
    def _check_document_completion(cls, document):
        """
        Check if all required signatures are complete and update document status.
        
        Args:
            document: The document to check
        """
        # This is a placeholder - implement your business logic for
        # determining when a document is fully signed
        # For example, check if all required parties have signed
        pass


# =============================================================================
# Update Document Signature Mutation
# =============================================================================

class UpdateDocumentSignatureMutation(relay.ClientIDMutation):
    """
    Update a document signature.
    
    Only the signature image can be updated, and only by the user who signed.
    """
    
    class Input:
        document_id = graphene.ID(required=True)
        signature_image = graphene.String(required=True)
    
    document_signature = graphene.Field(DocumentSignatureNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing document signature.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DocumentSignatureUpdateInput data
        
        Returns:
            UpdateDocumentSignatureMutation instance
        """
        errors = {}
        
        # Extract input
        signature_id = input.get('id')
        signature_image = input.get('signature_image')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document signature
        try:
            pk = from_global_id(signature_id)[1]
            document_signature = DocumentSignature.objects.get(pk=pk)
        except DocumentSignature.DoesNotExist:
            errors['id'] = ['Document signature not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the signer or staff can update
        if document_signature.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this signature.']
            return cls(success=False, errors=errors)
        
        # Validate signature image
        if not signature_image:
            errors['signature_image'] = ['Signature image is required.']
            return cls(success=False, errors=errors)
        
        try:
            # Update signature image
            document_signature.signature_image = signature_image
            document_signature.save()
            
            return cls(
                document_signature=document_signature,
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
# Delete Document Signature Mutation
# =============================================================================

class DeleteDocumentSignatureMutation(relay.ClientIDMutation):
    """
    Delete a document signature.
    
    Only staff or the signature owner can delete a signature.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force deletion even if document is already signed"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a document signature.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document signature ID to delete
            force: Force deletion even if document is signed
        
        Returns:
            DeleteDocumentSignatureMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document signature
        try:
            pk = from_global_id(id)[1]
            document_signature = DocumentSignature.objects.get(pk=pk)
        except DocumentSignature.DoesNotExist:
            errors['id'] = ['Document signature not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the signer or staff can delete
        if document_signature.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this signature.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            document_signature.delete()
            
            return cls(
                deleted_id=deleted_id,
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
# Verify Document Signature Mutation
# =============================================================================

class VerifyDocumentSignatureMutation(relay.ClientIDMutation):
    """
    Verify a document signature.
    
    Staff can verify signatures to confirm their authenticity.
    """
    
    class Input:
        id = graphene.ID(required=True)
        verified = graphene.Boolean(required=True)
        verification_notes = graphene.String(required=False)
    
    document_signature = graphene.Field(DocumentSignatureNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, verified, verification_notes=None):
        """
        Verify a document signature.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document signature ID to verify
            verified: Verification status
            verification_notes: Optional verification notes
        
        Returns:
            VerifyDocumentSignatureMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can verify signatures
        if not user.is_staff:
            errors['permission'] = ['Only staff members can verify signatures.']
            return cls(success=False, errors=errors)
        
        # Resolve document signature
        try:
            pk = from_global_id(id)[1]
            document_signature = DocumentSignature.objects.get(pk=pk)
        except DocumentSignature.DoesNotExist:
            errors['id'] = ['Document signature not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Store verification status in metadata
            # Since the model doesn't have verification fields, we'll use a related model or metadata
            # This is a placeholder - implement based on your requirements
            
            # For now, we'll just return success
            # You may want to add a Verification model or add fields to DocumentSignature
            
            return cls(
                document_signature=document_signature,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkSignDocumentsMutation(relay.ClientIDMutation):
    """
    Bulk sign multiple documents.
    
    Allows a user to sign multiple documents at once.
    """
    
    class Input:
        document_ids = graphene.List(graphene.ID, required=True)
        signature_image = graphene.String(required=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, document_ids, signature_image):
        """
        Bulk sign multiple documents.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            document_ids: List of document IDs to sign
            signature_image: Signature image for all documents
        
        Returns:
            BulkSignDocumentsMutation instance
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
        
        # Validate signature image
        if not signature_image:
            errors['signature_image'] = ['Signature image is required.']
            return cls(success=False, errors=errors)
        
        for document_id in document_ids:
            try:
                # Use the create signature mutation for each document
                result = CreateDocumentSignatureMutation.mutate_and_get_payload(
                    root, info, {
                        'document_id': document_id,
                        'signature_image': signature_image,
                    }
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'document_id': document_id,
                        'status': 'success',
                        'signature_id': result.document_signature.id if result.document_signature else None,
                    })
                else:
                    failure_count += 1
                    errors[document_id] = result.errors
                    results.append({
                        'document_id': document_id,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[document_id] = [str(e)]
                results.append({
                    'document_id': document_id,
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


class BulkDeleteDocumentSignaturesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple document signatures.
    
    Allows deleting multiple signatures at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, force=False):
        """
        Bulk delete document signatures.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of document signature IDs to delete
            force: Force deletion
        
        Returns:
            BulkDeleteDocumentSignaturesMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for signature_id in ids:
            try:
                pk = from_global_id(signature_id)[1]
                document_signature = DocumentSignature.objects.get(pk=pk)
                
                # Check permission
                if document_signature.user != user and not user.is_staff:
                    failed_ids.append(signature_id)
                    errors[signature_id] = ['Permission denied.']
                    continue
                
                document_signature.delete()
                deleted_ids.append(signature_id)
                
            except DocumentSignature.DoesNotExist:
                failed_ids.append(signature_id)
                errors[signature_id] = ['Document signature not found.']
            except Exception as e:
                failed_ids.append(signature_id)
                errors[signature_id] = [str(e)]
        
        return cls(
            deleted_ids=deleted_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Get Signature Status Mutation
# =============================================================================

class GetSignatureStatusMutation(relay.ClientIDMutation):
    """
    Get the signature status for a document.
    
    Returns information about who has signed and who still needs to sign.
    """
    
    class Input:
        document_id = graphene.ID(required=True)
    
    is_fully_signed = graphene.Boolean()
    signature_count = graphene.Int()
    required_signatures = graphene.Int()
    signers = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, document_id):
        """
        Get signature status for a document.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            document_id: Document ID to check
        
        Returns:
            GetSignatureStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document
        try:
            pk = from_global_id(document_id)[1]
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            errors['document_id'] = ['Document not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['document_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get all signatures for this document
            signatures = DocumentSignature.objects.filter(document=document)
            signature_count = signatures.count()
            
            # Get signer information
            signers = []
            for sig in signatures:
                signers.append({
                    'user_id': sig.user.id,
                    'username': sig.user.username,
                    'email': sig.user.email,
                    'signed_at': sig.signed_at.isoformat() if sig.signed_at else None,
                    'ip_address': sig.ip_address,
                })
            
            # Determine if fully signed (implement your business logic)
            # For example, check if all required parties have signed
            is_fully_signed = False
            required_signatures = 1  # Default, implement your logic
            
            return cls(
                is_fully_signed=is_fully_signed,
                signature_count=signature_count,
                required_signatures=required_signatures,
                signers=signers,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class DocumentSignatureMutations(graphene.ObjectType):
    """All document signature mutations."""
    
    # CRUD operations
    create_document_signature = CreateDocumentSignatureMutation.Field()
    update_document_signature = UpdateDocumentSignatureMutation.Field()
    delete_document_signature = DeleteDocumentSignatureMutation.Field()
    
    # Verification
    verify_document_signature = VerifyDocumentSignatureMutation.Field()
    
    # Bulk operations
    bulk_sign_documents = BulkSignDocumentsMutation.Field()
    bulk_delete_document_signatures = BulkDeleteDocumentSignaturesMutation.Field()
    
    # Status
    get_signature_status = GetSignatureStatusMutation.Field()