# apps/backend/realestate/mutations/document_package.py

"""
Document Package Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from realestate.models.document_package import DocumentPackage
from realestate.models.listing import Listing

from graphq.realestate.types.document_package import DocumentPackageNode

# =============================================================================
# Input Types
# =============================================================================

class DocumentPackageInput(graphene.InputObjectType):
    """Input for document package creation."""
    
    property_id = graphene.ID(required=True)
    title = graphene.String(required=True)


class DocumentPackageUpdateInput(graphene.InputObjectType):
    """Input for document package update."""
    
    id = graphene.ID(required=True)
    property_id = graphene.ID(required=True)
    title = graphene.String(required=True)
    title = graphene.String(required=False)
    is_completed = graphene.Boolean(required=False)


# =============================================================================
# Create Document Package Mutation
# =============================================================================

class CreateDocumentPackageMutation(relay.ClientIDMutation):
    """
    Create a new document package.
    
    Document packages group related documents for a property,
    such as purchase agreements, inspection reports, and closing documents.
    """
    
    class Input:
        id = graphene.ID(required=True)
        property_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        title = graphene.String(required=False)
        is_completed = graphene.Boolean(required=False)
    
    document_package = graphene.Field(DocumentPackageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new document package.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DocumentPackageInput data
        
        Returns:
            CreateDocumentPackageMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        title = input.get('title')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate title
        if not title or not title.strip():
            errors['title'] = ['Title is required.']
            return cls(success=False, errors=errors)
        
        # Resolve property
        try:
            pk = from_global_id(property_id)[1]
            property_obj = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['property_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['property_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to create document packages for this property.']
            return cls(success=False, errors=errors)
        
        # Check for duplicate package title for this property
        if DocumentPackage.objects.filter(property=property_obj, title__iexact=title).exists():
            errors['title'] = ['A document package with this title already exists for this property.']
            return cls(success=False, errors=errors)
        
        try:
            # Create document package
            document_package = DocumentPackage.objects.create(
                property=property_obj,
                title=title.strip(),
                created_by=user,
                is_completed=False,
            )
            
            return cls(
                document_package=document_package,
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
# Update Document Package Mutation
# =============================================================================

class UpdateDocumentPackageMutation(relay.ClientIDMutation):
    """
    Update an existing document package.
    
    Allows updating the title and completion status of a document package.
    """
    
    class Input:
        id = graphene.ID(required=True)
        property_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        title = graphene.String(required=False)
        is_completed = graphene.Boolean(required=False)
    
    document_package = graphene.Field(DocumentPackageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing document package.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DocumentPackageUpdateInput data
        
        Returns:
            UpdateDocumentPackageMutation instance
        """
        errors = {}
        
        # Extract input
        package_id = input.get('id')
        title = input.get('title')
        is_completed = input.get('is_completed')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document package
        try:
            pk = from_global_id(package_id)[1]
            document_package = DocumentPackage.objects.get(pk=pk)
        except DocumentPackage.DoesNotExist:
            errors['id'] = ['Document package not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only creator or staff can update
        if document_package.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this document package.']
            return cls(success=False, errors=errors)
        
        # Validate title if provided
        if title is not None:
            if not title or not title.strip():
                errors['title'] = ['Title is required.']
                return cls(success=False, errors=errors)
            
            # Check for duplicate title (excluding current package)
            if DocumentPackage.objects.filter(
                property=document_package.property,
                title__iexact=title
            ).exclude(pk=document_package.pk).exists():
                errors['title'] = ['A document package with this title already exists for this property.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if title is not None:
                document_package.title = title.strip()
            if is_completed is not None:
                document_package.is_completed = is_completed
            
            document_package.full_clean()
            document_package.save()
            
            return cls(
                document_package=document_package,
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
# Delete Document Package Mutation
# =============================================================================

class DeleteDocumentPackageMutation(relay.ClientIDMutation):
    """
    Delete a document package.
    
    This will also delete all documents associated with the package
    (cascade delete).
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force delete even if package has documents"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a document package.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document package ID to delete
            force: Force deletion even if package has documents
        
        Returns:
            DeleteDocumentPackageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document package
        try:
            pk = from_global_id(id)[1]
            document_package = DocumentPackage.objects.get(pk=pk)
        except DocumentPackage.DoesNotExist:
            errors['id'] = ['Document package not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only creator or staff can delete
        if document_package.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this document package.']
            return cls(success=False, errors=errors)
        
        # Check if package has documents
        document_count = document_package.documents.count() if hasattr(document_package, 'documents') else 0
        
        if document_count > 0 and not force:
            errors['documents'] = [
                f'This document package contains {document_count} documents. '
                'Delete the documents first or use force=True to delete all.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            document_package.delete()
            
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
# Complete Document Package Mutation
# =============================================================================

class CompleteDocumentPackageMutation(relay.ClientIDMutation):
    """
    Mark a document package as completed.
    
    This is a convenience mutation for marking a package as complete
    without needing to send a full update.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    document_package = graphene.Field(DocumentPackageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Mark a document package as completed.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document package ID to complete
        
        Returns:
            CompleteDocumentPackageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document package
        try:
            pk = from_global_id(id)[1]
            document_package = DocumentPackage.objects.get(pk=pk)
        except DocumentPackage.DoesNotExist:
            errors['id'] = ['Document package not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only creator or staff can complete
        if document_package.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to complete this document package.']
            return cls(success=False, errors=errors)
        
        # Check if already completed
        if document_package.is_completed:
            errors['status'] = ['Document package is already completed.']
            return cls(success=False, errors=errors)
        
        try:
            document_package.is_completed = True
            document_package.save()
            
            return cls(
                document_package=document_package,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Reopen Document Package Mutation
# =============================================================================

class ReopenDocumentPackageMutation(relay.ClientIDMutation):
    """
    Reopen a completed document package.
    
    This allows reopening a package that was marked as completed
    to add or modify documents.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    document_package = graphene.Field(DocumentPackageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Reopen a completed document package.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document package ID to reopen
        
        Returns:
            ReopenDocumentPackageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document package
        try:
            pk = from_global_id(id)[1]
            document_package = DocumentPackage.objects.get(pk=pk)
        except DocumentPackage.DoesNotExist:
            errors['id'] = ['Document package not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only creator or staff can reopen
        if document_package.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to reopen this document package.']
            return cls(success=False, errors=errors)
        
        # Check if already not completed
        if not document_package.is_completed:
            errors['status'] = ['Document package is already open.']
            return cls(success=False, errors=errors)
        
        try:
            document_package.is_completed = False
            document_package.save()
            
            return cls(
                document_package=document_package,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Duplicate Document Package Mutation
# =============================================================================

class DuplicateDocumentPackageMutation(relay.ClientIDMutation):
    """
    Duplicate a document package.
    
    Creates a new document package with the same title (with "Copy" suffix)
    but without the documents.
    """
    
    class Input:
        id = graphene.ID(required=True)
        new_title = graphene.String(required=False)
    
    document_package = graphene.Field(DocumentPackageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, new_title=None):
        """
        Duplicate a document package.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Document package ID to duplicate
            new_title: Optional title for the new package
        
        Returns:
            DuplicateDocumentPackageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve document package
        try:
            pk = from_global_id(id)[1]
            source_package = DocumentPackage.objects.get(pk=pk)
        except DocumentPackage.DoesNotExist:
            errors['id'] = ['Document package not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only creator or staff can duplicate
        if source_package.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to duplicate this document package.']
            return cls(success=False, errors=errors)
        
        try:
            # Generate new title
            if not new_title:
                new_title = f"{source_package.title} (Copy)"
            
            # Check if title already exists for this property
            if DocumentPackage.objects.filter(
                property=source_package.property,
                title__iexact=new_title
            ).exists():
                # Add a number suffix
                counter = 1
                base_title = new_title
                while DocumentPackage.objects.filter(
                    property=source_package.property,
                    title__iexact=new_title
                ).exists():
                    new_title = f"{base_title} {counter}"
                    counter += 1
            
            # Create duplicate (without documents)
            new_package = DocumentPackage.objects.create(
                property=source_package.property,
                title=new_title,
                created_by=user,
                is_completed=False,  # Duplicates start as incomplete
            )
            
            return cls(
                document_package=new_package,
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
# Bulk Operations
# =============================================================================

class BulkDeleteDocumentPackagesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple document packages.
    
    Allows deleting multiple document packages at once with options.
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
        Bulk delete document packages.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of document package IDs to delete
            force: Force delete even if packages have documents
        
        Returns:
            BulkDeleteDocumentPackagesMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for package_id in ids:
            try:
                pk = from_global_id(package_id)[1]
                document_package = DocumentPackage.objects.get(pk=pk)
                
                # Check permission
                if document_package.created_by != user and not user.is_staff:
                    failed_ids.append(package_id)
                    errors[package_id] = ['Permission denied.']
                    continue
                
                # Check if package has documents
                document_count = document_package.documents.count() if hasattr(document_package, 'documents') else 0
                
                if document_count > 0 and not force:
                    failed_ids.append(package_id)
                    errors[package_id] = [
                        f'Package has {document_count} documents. Use force=True to delete all.'
                    ]
                    continue
                
                document_package.delete()
                deleted_ids.append(package_id)
                
            except DocumentPackage.DoesNotExist:
                failed_ids.append(package_id)
                errors[package_id] = ['Document package not found.']
            except Exception as e:
                failed_ids.append(package_id)
                errors[package_id] = [str(e)]
        
        return cls(
            deleted_ids=deleted_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


class BulkUpdateDocumentPackagesMutation(relay.ClientIDMutation):
    """
    Bulk update multiple document packages.
    
    Allows updating common fields across multiple document packages at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        is_completed = graphene.Boolean(required=False)
    
    updated_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, **kwargs):
        """
        Bulk update document packages.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of document package IDs to update
            kwargs: Fields to update
        
        Returns:
            BulkUpdateDocumentPackagesMutation instance
        """
        errors = {}
        updated_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for package_id in ids:
            try:
                pk = from_global_id(package_id)[1]
                document_package = DocumentPackage.objects.get(pk=pk)
                
                # Check permission
                if document_package.created_by != user and not user.is_staff:
                    failed_ids.append(package_id)
                    errors[package_id] = ['Permission denied.']
                    continue
                
                # Apply updates
                if kwargs.get('is_completed') is not None:
                    document_package.is_completed = kwargs['is_completed']
                
                document_package.full_clean()
                document_package.save()
                updated_ids.append(package_id)
                
            except DocumentPackage.DoesNotExist:
                failed_ids.append(package_id)
                errors[package_id] = ['Document package not found.']
            except ValidationError as e:
                failed_ids.append(package_id)
                errors[package_id] = e.message_dict
            except Exception as e:
                failed_ids.append(package_id)
                errors[package_id] = [str(e)]
        
        return cls(
            updated_ids=updated_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class DocumentPackageMutations(graphene.ObjectType):
    """All document package mutations."""
    
    # CRUD operations
    create_document_package = CreateDocumentPackageMutation.Field()
    update_document_package = UpdateDocumentPackageMutation.Field()
    delete_document_package = DeleteDocumentPackageMutation.Field()
    
    # Status operations
    complete_document_package = CompleteDocumentPackageMutation.Field()
    reopen_document_package = ReopenDocumentPackageMutation.Field()
    
    # Additional operations
    duplicate_document_package = DuplicateDocumentPackageMutation.Field()
    
    # Bulk operations
    bulk_delete_document_packages = BulkDeleteDocumentPackagesMutation.Field()
    bulk_update_document_packages = BulkUpdateDocumentPackagesMutation.Field()