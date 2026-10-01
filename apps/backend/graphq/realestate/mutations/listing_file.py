# apps/backend/realestate/mutations/listing_file.py

"""
Listing File Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from realestate.models.listing_file import ListingFile
from realestate.models.listing import Listing
from graphq.realestate.types.listing_file import ListingFileNode



# =============================================================================
# Create Listing File Mutation
# =============================================================================

class CreateListingFileMutation(relay.ClientIDMutation):
    """
    Create a new listing file.
    
    Allows uploading files associated with a listing, such as property
    documents, floor plans, or inspection reports.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        short_description = graphene.String(required=False)
        for_customer = graphene.Boolean(required=False, default_value=True)
        
    listing_file = graphene.Field(ListingFileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new listing file.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingFileInput data
        
        Returns:
            CreateListingFileMutation instance
        """
        errors = {}
        
        # Extract input
        listing_id = input.get('listing_id')
        name = input.get('name')
        short_description = input.get('short_description', '')
        for_customer = input.get('for_customer', True)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        is_authorized = (
            user.is_staff or
            (hasattr(listing, 'agent') and listing.agent and 
             hasattr(listing.agent, 'profile') and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user) or
            (hasattr(listing, 'owner') and listing.owner and 
             hasattr(listing.owner, 'user') and 
             listing.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to add files to this listing.']
            return cls(success=False, errors=errors)
        
        # Get file from request
        file_obj = None
        if hasattr(info.context, 'FILES'):
            file_obj = info.context.FILES.get('file')
        
        if not file_obj:
            errors['file'] = ['File is required.']
            return cls(success=False, errors=errors)
        
        try:
            # Create listing file
            listing_file = ListingFile.objects.create(
                listing=listing,
                name=name.strip(),
                short_description=short_description,
                file=file_obj,
                for_customer=for_customer,
            )
            
            return cls(
                listing_file=listing_file,
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
# Update Listing File Mutation
# =============================================================================

class UpdateListingFileMutation(relay.ClientIDMutation):
    """
    Update an existing listing file.
    
    Allows updating the file name, description, and customer visibility.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        short_description = graphene.String(required=False)
        for_customer = graphene.Boolean(required=False, default_value=True)
        
    listing_file = graphene.Field(ListingFileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing listing file.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingFileUpdateInput data
        
        Returns:
            UpdateListingFileMutation instance
        """
        errors = {}
        
        # Extract input
        file_id = input.get('id')
        name = input.get('name')
        short_description = input.get('short_description')
        for_customer = input.get('for_customer')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing file
        try:
            pk = from_global_id(file_id)[1]
            listing_file = ListingFile.objects.get(pk=pk)
        except ListingFile.DoesNotExist:
            errors['id'] = ['Listing file not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        listing = listing_file.listing
        is_authorized = (
            user.is_staff or
            (hasattr(listing, 'agent') and listing.agent and 
             hasattr(listing.agent, 'profile') and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user) or
            (hasattr(listing, 'owner') and listing.owner and 
             hasattr(listing.owner, 'user') and 
             listing.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to update this file.']
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None and not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                listing_file.name = name.strip()
            if short_description is not None:
                listing_file.short_description = short_description
            if for_customer is not None:
                listing_file.for_customer = for_customer
            
            listing_file.full_clean()
            listing_file.save()
            
            return cls(
                listing_file=listing_file,
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
# Delete Listing File Mutation
# =============================================================================

class DeleteListingFileMutation(relay.ClientIDMutation):
    """
    Delete a listing file.
    
    Removes the file from the listing and deletes the physical file.
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
        Delete a listing file.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing file ID to delete
        
        Returns:
            DeleteListingFileMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing file
        try:
            pk = from_global_id(id)[1]
            listing_file = ListingFile.objects.get(pk=pk)
        except ListingFile.DoesNotExist:
            errors['id'] = ['Listing file not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        listing = listing_file.listing
        is_authorized = (
            user.is_staff or
            (hasattr(listing, 'agent') and listing.agent and 
             hasattr(listing.agent, 'profile') and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user) or
            (hasattr(listing, 'owner') and listing.owner and 
             hasattr(listing.owner, 'user') and 
             listing.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to delete this file.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            # Delete the file (cascade will also delete the physical file)
            listing_file.delete()
            
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
# Toggle Listing File Visibility Mutation
# =============================================================================

class ToggleListingFileVisibilityMutation(relay.ClientIDMutation):
    """
    Toggle customer visibility for a listing file.
    
    This is a convenience mutation for showing/hiding files from customers.
    """
    
    class Input:
        id = graphene.ID(required=True)
        for_customer = graphene.Boolean(required=True)
    
    listing_file = graphene.Field(ListingFileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, for_customer):
        """
        Toggle listing file visibility.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing file ID
            for_customer: New visibility setting
        
        Returns:
            ToggleListingFileVisibilityMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing file
        try:
            pk = from_global_id(id)[1]
            listing_file = ListingFile.objects.get(pk=pk)
        except ListingFile.DoesNotExist:
            errors['id'] = ['Listing file not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        listing = listing_file.listing
        is_authorized = (
            user.is_staff or
            (hasattr(listing, 'agent') and listing.agent and 
             hasattr(listing.agent, 'profile') and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user) or
            (hasattr(listing, 'owner') and listing.owner and 
             hasattr(listing.owner, 'user') and 
             listing.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to modify this file.']
            return cls(success=False, errors=errors)
        
        try:
            listing_file.for_customer = for_customer
            listing_file.save()
            
            return cls(
                listing_file=listing_file,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Upload Listing Files Mutation
# =============================================================================

class BulkUploadListingFilesMutation(relay.ClientIDMutation):
    """
    Bulk upload multiple files for a listing.
    
    Allows uploading multiple files at once to a listing.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        short_description = graphene.String(required=False)
        for_customer = graphene.Boolean(required=False, default_value=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk upload multiple files.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            files: List of file metadata
        
        Returns:
            BulkUploadListingFilesMutation instance
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
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_authorized = (
            user.is_staff or
            (hasattr(listing, 'agent') and listing.agent and 
             hasattr(listing.agent, 'profile') and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user) or
            (hasattr(listing, 'owner') and listing.owner and 
             hasattr(listing.owner, 'user') and 
             listing.owner.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to add files to this listing.']
            return cls(success=False, errors=errors)
        
        # Get files from request
        uploaded_files = []
        if hasattr(info.context, 'FILES'):
            uploaded_files = info.context.FILES.getlist('files')
        
        if not uploaded_files:
            errors['files'] = ['At least one file is required.']
            return cls(success=False, errors=errors)
        
        # Process each file
        for idx, file_data in enumerate(files):
            try:
                # Get corresponding file object
                file_obj = uploaded_files[idx] if idx < len(uploaded_files) else None
                
                if not file_obj:
                    errors[f'file_{idx}'] = ['File is required.']
                    failure_count += 1
                    results.append({
                        'name': file_data.get('name'),
                        'status': 'failed',
                        'errors': ['No file provided'],
                    })
                    continue
                
                # Validate name
                name = file_data.get('name', '')
                if not name or not name.strip():
                    errors[f'file_{idx}'] = ['Name is required.']
                    failure_count += 1
                    results.append({
                        'name': name,
                        'status': 'failed',
                        'errors': ['Name is required'],
                    })
                    continue
                
                # Create listing file
                listing_file = ListingFile.objects.create(
                    listing=listing,
                    name=name.strip(),
                    short_description=file_data.get('short_description', ''),
                    file=file_obj,
                    for_customer=file_data.get('for_customer', True),
                )
                
                success_count += 1
                results.append({
                    'id': listing_file.id,
                    'name': listing_file.name,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[f'file_{idx}'] = [str(e)]
                results.append({
                    'name': file_data.get('name'),
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
# Bulk Delete Listing Files Mutation
# =============================================================================

class BulkDeleteListingFilesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple listing files.
    
    Allows deleting multiple files from a listing at once.
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
        Bulk delete listing files.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of listing file IDs to delete
        
        Returns:
            BulkDeleteListingFilesMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for file_id in ids:
            try:
                pk = from_global_id(file_id)[1]
                listing_file = ListingFile.objects.get(pk=pk)
                
                # Check permission - user must be staff, agent, or owner
                listing = listing_file.listing
                is_authorized = (
                    user.is_staff or
                    (hasattr(listing, 'agent') and listing.agent and 
                     hasattr(listing.agent, 'profile') and 
                     hasattr(listing.agent.profile, 'user') and 
                     listing.agent.profile.user == user) or
                    (hasattr(listing, 'owner') and listing.owner and 
                     hasattr(listing.owner, 'user') and 
                     listing.owner.user == user)
                )
                
                if not is_authorized:
                    failed_ids.append(file_id)
                    errors[file_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                listing_file.delete()
                deleted_ids.append(file_id)
                success_count += 1
                
            except ListingFile.DoesNotExist:
                failed_ids.append(file_id)
                errors[file_id] = ['Listing file not found.']
                failure_count += 1
            except Exception as e:
                failed_ids.append(file_id)
                errors[file_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class ListingFileMutations(graphene.ObjectType):
    """All listing file mutations."""
    
    # CRUD operations
    create_listing_file = CreateListingFileMutation.Field()
    update_listing_file = UpdateListingFileMutation.Field()
    delete_listing_file = DeleteListingFileMutation.Field()
    
    # Additional operations
    toggle_listing_file_visibility = ToggleListingFileVisibilityMutation.Field()
    
    # Bulk operations
    bulk_upload_listing_files = BulkUploadListingFilesMutation.Field()
    bulk_delete_listing_files = BulkDeleteListingFilesMutation.Field()