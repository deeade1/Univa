# apps/backend/realestate/mutations/saved_search.py

"""
Saved Search Mutations for Real Estate Relay GraphQL API.
"""

import json
import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.saved_search import SavedSearch
from graphq.realestate.types.saved_search import SavedSearchNode


# =============================================================================
# Create Saved Search Mutation
# =============================================================================

class CreateSavedSearchMutation(relay.ClientIDMutation):
    """
    Create a new saved search.
    
    Allows users to save property search parameters for future use
    and automated notifications.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_parameters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
    
    saved_search = graphene.Field(SavedSearchNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new saved search.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: SavedSearchInput data
        
        Returns:
            CreateSavedSearchMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        search_parameters = input.get('search_parameters')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate search_parameters
        if not search_parameters:
            errors['search_parameters'] = ['Search parameters are required.']
            return cls(success=False, errors=errors)
        
        # Ensure search_parameters is a dict
        if isinstance(search_parameters, str):
            try:
                search_parameters = json.loads(search_parameters)
            except json.JSONDecodeError:
                errors['search_parameters'] = ['Invalid JSON format for search parameters.']
                return cls(success=False, errors=errors)
        
        if not isinstance(search_parameters, dict):
            errors['search_parameters'] = ['Search parameters must be a JSON object.']
            return cls(success=False, errors=errors)
        
        # Check for duplicate name for this user
        if SavedSearch.objects.filter(user=user, name__iexact=name).exists():
            errors['name'] = ['You already have a saved search with this name.']
            return cls(success=False, errors=errors)
        
        try:
            # Create saved search
            saved_search = SavedSearch.objects.create(
                user=user,
                name=name.strip(),
                search_parameters=search_parameters,
                is_active=True,
                last_notified=None,
            )
            
            return cls(
                saved_search=saved_search,
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
# Update Saved Search Mutation
# =============================================================================

class UpdateSavedSearchMutation(relay.ClientIDMutation):
    """
    Update an existing saved search.
    
    Allows updating the name, search parameters, or active status.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_parameters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
    
    saved_search = graphene.Field(SavedSearchNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing saved search.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: SavedSearchUpdateInput data
        
        Returns:
            UpdateSavedSearchMutation instance
        """
        errors = {}
        
        # Extract input
        search_id = input.get('id')
        name = input.get('name')
        search_parameters = input.get('search_parameters')
        is_active = input.get('is_active')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve saved search
        try:
            pk = from_global_id(search_id)[1]
            saved_search = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            errors['id'] = ['Saved search not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can update
        if saved_search.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this saved search.']
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None:
            if not name or not name.strip():
                errors['name'] = ['Name is required.']
                return cls(success=False, errors=errors)
            
            # Check for duplicate name (excluding current)
            if SavedSearch.objects.filter(
                user=user,
                name__iexact=name
            ).exclude(pk=saved_search.pk).exists():
                errors['name'] = ['You already have a saved search with this name.']
                return cls(success=False, errors=errors)
        
        # Validate search_parameters if provided
        if search_parameters is not None:
            if isinstance(search_parameters, str):
                try:
                    search_parameters = json.loads(search_parameters)
                except json.JSONDecodeError:
                    errors['search_parameters'] = ['Invalid JSON format for search parameters.']
                    return cls(success=False, errors=errors)
            
            if not isinstance(search_parameters, dict):
                errors['search_parameters'] = ['Search parameters must be a JSON object.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                saved_search.name = name.strip()
            if search_parameters is not None:
                saved_search.search_parameters = search_parameters
            if is_active is not None:
                saved_search.is_active = is_active
            
            saved_search.full_clean()
            saved_search.save()
            
            return cls(
                saved_search=saved_search,
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
# Delete Saved Search Mutation
# =============================================================================

class DeleteSavedSearchMutation(relay.ClientIDMutation):
    """
    Delete a saved search.
    
    Removes a saved search from the user's account.
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
        Delete a saved search.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Saved search ID to delete
        
        Returns:
            DeleteSavedSearchMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve saved search
        try:
            pk = from_global_id(id)[1]
            saved_search = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            errors['id'] = ['Saved search not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can delete
        if saved_search.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this saved search.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            saved_search.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Toggle Saved Search Status Mutation
# =============================================================================

class ToggleSavedSearchStatusMutation(relay.ClientIDMutation):
    """
    Toggle the active status of a saved search.
    
    This is a convenience mutation for enabling/disabling a saved search.
    """
    
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=True)
    
    saved_search = graphene.Field(SavedSearchNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, is_active):
        """
        Toggle saved search active status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Saved search ID
            is_active: New active status
        
        Returns:
            ToggleSavedSearchStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve saved search
        try:
            pk = from_global_id(id)[1]
            saved_search = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            errors['id'] = ['Saved search not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if saved_search.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this saved search.']
            return cls(success=False, errors=errors)
        
        try:
            saved_search.is_active = is_active
            saved_search.save()
            
            return cls(
                saved_search=saved_search,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Duplicate Saved Search Mutation
# =============================================================================

class DuplicateSavedSearchMutation(relay.ClientIDMutation):
    """
    Duplicate a saved search.
    
    Creates a new saved search with the same parameters as an existing one.
    """
    
    class Input:
        id = graphene.ID(required=True)
        new_name = graphene.String(required=False)
    
    saved_search = graphene.Field(SavedSearchNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, new_name=None):
        """
        Duplicate a saved search.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Saved search ID to duplicate
            new_name: Optional name for the new search
        
        Returns:
            DuplicateSavedSearchMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve saved search
        try:
            pk = from_global_id(id)[1]
            source_search = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            errors['id'] = ['Saved search not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if source_search.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to duplicate this saved search.']
            return cls(success=False, errors=errors)
        
        try:
            # Generate new name
            if not new_name:
                new_name = f"{source_search.name} (Copy)"
            
            # Check if name already exists for this user
            if SavedSearch.objects.filter(user=user, name__iexact=new_name).exists():
                # Add a number suffix
                counter = 1
                base_name = new_name
                while SavedSearch.objects.filter(user=user, name__iexact=new_name).exists():
                    new_name = f"{base_name} {counter}"
                    counter += 1
            
            # Create duplicate
            new_search = SavedSearch.objects.create(
                user=user,
                name=new_name,
                search_parameters=source_search.search_parameters,
                is_active=False,  # Duplicates start as inactive
                last_notified=None,
            )
            
            return cls(
                saved_search=new_search,
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

class BulkCreateSavedSearchesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple saved searches.
    
    Allows creating multiple saved searches at once.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_parameters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create saved searches.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            searches: List of saved search inputs
        
        Returns:
            BulkCreateSavedSearchesMutation instance
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
        
        for idx, search_input in enumerate(searches):
            try:
                # Use the create mutation for each search
                result = CreateSavedSearchMutation.mutate_and_get_payload(
                    root, info, search_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'search_id': result.saved_search.id if result.saved_search else None,
                    })
                else:
                    failure_count += 1
                    errors[f'search_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'search_{idx}'] = [str(e)]
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


class BulkDeleteSavedSearchesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple saved searches.
    
    Allows deleting multiple saved searches at once.
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
        Bulk delete saved searches.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of saved search IDs to delete
        
        Returns:
            BulkDeleteSavedSearchesMutation instance
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
        
        for search_id in ids:
            try:
                pk = from_global_id(search_id)[1]
                saved_search = SavedSearch.objects.get(pk=pk)
                
                # Check permission
                if saved_search.user != user and not user.is_staff:
                    errors[search_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                saved_search.delete()
                deleted_ids.append(search_id)
                success_count += 1
                
            except SavedSearch.DoesNotExist:
                errors[search_id] = ['Saved search not found.']
                failure_count += 1
            except Exception as e:
                errors[search_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class SavedSearchMutations(graphene.ObjectType):
    """All saved search mutations."""
    
    # CRUD operations
    create_saved_search = CreateSavedSearchMutation.Field()
    update_saved_search = UpdateSavedSearchMutation.Field()
    delete_saved_search = DeleteSavedSearchMutation.Field()
    
    # Status management
    toggle_saved_search_status = ToggleSavedSearchStatusMutation.Field()
    
    # Additional operations
    duplicate_saved_search = DuplicateSavedSearchMutation.Field()
    
    # Bulk operations
    bulk_create_saved_searches = BulkCreateSavedSearchesMutation.Field()
    bulk_delete_saved_searches = BulkDeleteSavedSearchesMutation.Field()