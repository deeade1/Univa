# apps/backend/realestate/mutations/search.py

"""
Search Profile Mutations for Real Estate Relay GraphQL API.
"""

import json
import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.search import SearchProfile
from realestate.models.listing import Listing
from realestate.constants import NOTIFICATION_FREQUENCY
from graphq.realestate.types.search import SearchProfileNode
from graphq.realestate.types.listing import ListingNode



# =============================================================================
# Create Search Profile Mutation
# =============================================================================

class CreateSearchProfileMutation(relay.ClientIDMutation):
    """
    Create a new search profile.
    
    Search profiles allow users to save property search filters
    and receive notifications when new matching properties are listed.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_filters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    search_profile = graphene.Field(SearchProfileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new search profile.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: SearchProfileInput data
        
        Returns:
            CreateSearchProfileMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        search_filters = input.get('search_filters', {})
        notification_frequency = input.get('notification_frequency', 'instant')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate search_filters
        if isinstance(search_filters, str):
            try:
                search_filters = json.loads(search_filters)
            except json.JSONDecodeError:
                errors['search_filters'] = ['Invalid JSON format for search filters.']
                return cls(success=False, errors=errors)
        
        if not isinstance(search_filters, dict):
            errors['search_filters'] = ['Search filters must be a JSON object.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency
        valid_frequencies = [choice[0] for choice in NOTIFICATION_FREQUENCY]
        if notification_frequency not in valid_frequencies:
            errors['notification_frequency'] = [
                f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
            ]
            return cls(success=False, errors=errors)
        
        # Check for duplicate name for this user
        if SearchProfile.objects.filter(user=user, name__iexact=name).exists():
            errors['name'] = ['You already have a search profile with this name.']
            return cls(success=False, errors=errors)
        
        try:
            # Create search profile
            search_profile = SearchProfile.objects.create(
                user=user,
                name=name.strip(),
                search_filters=search_filters,
                is_active=True,
                notification_frequency=notification_frequency,
                last_notified=None,
            )
            
            return cls(
                search_profile=search_profile,
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
# Update Search Profile Mutation
# =============================================================================

class UpdateSearchProfileMutation(relay.ClientIDMutation):
    """
    Update an existing search profile.
    
    Allows updating the name, search filters, active status, and notification frequency.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_filters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    search_profile = graphene.Field(SearchProfileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing search profile.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: SearchProfileUpdateInput data
        
        Returns:
            UpdateSearchProfileMutation instance
        """
        errors = {}
        
        # Extract input
        profile_id = input.get('id')
        name = input.get('name')
        search_filters = input.get('search_filters')
        is_active = input.get('is_active')
        notification_frequency = input.get('notification_frequency')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve search profile
        try:
            pk = from_global_id(profile_id)[1]
            search_profile = SearchProfile.objects.get(pk=pk)
        except SearchProfile.DoesNotExist:
            errors['id'] = ['Search profile not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can update
        if search_profile.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this search profile.']
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None:
            if not name or not name.strip():
                errors['name'] = ['Name is required.']
                return cls(success=False, errors=errors)
            
            # Check for duplicate name (excluding current)
            if SearchProfile.objects.filter(
                user=user,
                name__iexact=name
            ).exclude(pk=search_profile.pk).exists():
                errors['name'] = ['You already have a search profile with this name.']
                return cls(success=False, errors=errors)
        
        # Validate search_filters if provided
        if search_filters is not None:
            if isinstance(search_filters, str):
                try:
                    search_filters = json.loads(search_filters)
                except json.JSONDecodeError:
                    errors['search_filters'] = ['Invalid JSON format for search filters.']
                    return cls(success=False, errors=errors)
            
            if not isinstance(search_filters, dict):
                errors['search_filters'] = ['Search filters must be a JSON object.']
                return cls(success=False, errors=errors)
        
        # Validate notification frequency if provided
        if notification_frequency is not None:
            valid_frequencies = [choice[0] for choice in NOTIFICATION_FREQUENCY]
            if notification_frequency not in valid_frequencies:
                errors['notification_frequency'] = [
                    f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
                ]
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                search_profile.name = name.strip()
            if search_filters is not None:
                search_profile.search_filters = search_filters
            if is_active is not None:
                search_profile.is_active = is_active
            if notification_frequency is not None:
                search_profile.notification_frequency = notification_frequency
            
            search_profile.full_clean()
            search_profile.save()
            
            return cls(
                search_profile=search_profile,
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
# Delete Search Profile Mutation
# =============================================================================

class DeleteSearchProfileMutation(relay.ClientIDMutation):
    """
    Delete a search profile.
    
    Removes a search profile from the user's account.
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
        Delete a search profile.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Search profile ID to delete
        
        Returns:
            DeleteSearchProfileMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve search profile
        try:
            pk = from_global_id(id)[1]
            search_profile = SearchProfile.objects.get(pk=pk)
        except SearchProfile.DoesNotExist:
            errors['id'] = ['Search profile not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can delete
        if search_profile.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this search profile.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            search_profile.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Toggle Search Profile Status Mutation
# =============================================================================

class ToggleSearchProfileStatusMutation(relay.ClientIDMutation):
    """
    Toggle the active status of a search profile.
    
    This is a convenience mutation for enabling/disabling a search profile.
    """
    
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=True)
    
    search_profile = graphene.Field(SearchProfileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, is_active):
        """
        Toggle search profile active status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Search profile ID
            is_active: New active status
        
        Returns:
            ToggleSearchProfileStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve search profile
        try:
            pk = from_global_id(id)[1]
            search_profile = SearchProfile.objects.get(pk=pk)
        except SearchProfile.DoesNotExist:
            errors['id'] = ['Search profile not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if search_profile.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this search profile.']
            return cls(success=False, errors=errors)
        
        try:
            search_profile.is_active = is_active
            search_profile.save()
            
            return cls(
                search_profile=search_profile,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Execute Search Profile Mutation
# =============================================================================

class ExecuteSearchProfileMutation(relay.ClientIDMutation):
    """
    Execute a search profile and return matching listings.
    
    This mutation runs the saved search filters and returns matching properties.
    """
    
    class Input:
        profile_id = graphene.ID(required=True)
        limit = graphene.Int(required=False, default_value=20)
        offset = graphene.Int(required=False, default_value=0)
    
    results = graphene.List(ListingNode)
    total_count = graphene.Int()
    search_filters = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, profile_id, limit=20, offset=0):
        """
        Execute a search profile.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            profile_id: Search profile ID
            limit: Number of results to return
            offset: Results offset for pagination
        
        Returns:
            ExecuteSearchProfileMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve search profile
        try:
            pk = from_global_id(profile_id)[1]
            search_profile = SearchProfile.objects.get(pk=pk)
        except SearchProfile.DoesNotExist:
            errors['profile_id'] = ['Search profile not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['profile_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner or staff can execute
        if search_profile.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to execute this search profile.']
            return cls(success=False, errors=errors)
        
        try:
            # Execute the search
            queryset = search_profile.execute_search()
            
            # Apply pagination
            total_count = queryset.count()
            results = queryset[offset:offset + limit] if limit else queryset
            
            return cls(
                results=results,
                total_count=total_count,
                search_filters=search_profile.search_filters,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Duplicate Search Profile Mutation
# =============================================================================

class DuplicateSearchProfileMutation(relay.ClientIDMutation):
    """
    Duplicate a search profile.
    
    Creates a new search profile with the same filters as an existing one.
    """
    
    class Input:
        id = graphene.ID(required=True)
        new_name = graphene.String(required=False)
    
    search_profile = graphene.Field(SearchProfileNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, new_name=None):
        """
        Duplicate a search profile.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Search profile ID to duplicate
            new_name: Optional name for the new profile
        
        Returns:
            DuplicateSearchProfileMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve search profile
        try:
            pk = from_global_id(id)[1]
            source_profile = SearchProfile.objects.get(pk=pk)
        except SearchProfile.DoesNotExist:
            errors['id'] = ['Search profile not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if source_profile.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to duplicate this search profile.']
            return cls(success=False, errors=errors)
        
        try:
            # Generate new name
            if not new_name:
                new_name = f"{source_profile.name} (Copy)"
            
            # Check if name already exists for this user
            if SearchProfile.objects.filter(user=user, name__iexact=new_name).exists():
                # Add a number suffix
                counter = 1
                base_name = new_name
                while SearchProfile.objects.filter(user=user, name__iexact=new_name).exists():
                    new_name = f"{base_name} {counter}"
                    counter += 1
            
            # Create duplicate
            new_profile = SearchProfile.objects.create(
                user=user,
                name=new_name,
                search_filters=source_profile.search_filters,
                is_active=False,  # Duplicates start as inactive
                notification_frequency=source_profile.notification_frequency,
                last_notified=None,
            )
            
            return cls(
                search_profile=new_profile,
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

class BulkCreateSearchProfilesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple search profiles.
    
    Allows creating multiple search profiles at once.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        search_filters = graphene.JSONString(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create search profiles.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            profiles: List of search profile inputs
        
        Returns:
            BulkCreateSearchProfilesMutation instance
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
        
        for idx, profile_input in enumerate(profiles):
            try:
                # Use the create mutation for each profile
                result = CreateSearchProfileMutation.mutate_and_get_payload(
                    root, info, profile_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'profile_id': result.search_profile.id if result.search_profile else None,
                    })
                else:
                    failure_count += 1
                    errors[f'profile_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'profile_{idx}'] = [str(e)]
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


class BulkDeleteSearchProfilesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple search profiles.
    
    Allows deleting multiple search profiles at once.
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
        Bulk delete search profiles.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of search profile IDs to delete
        
        Returns:
            BulkDeleteSearchProfilesMutation instance
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
        
        for profile_id in ids:
            try:
                pk = from_global_id(profile_id)[1]
                search_profile = SearchProfile.objects.get(pk=pk)
                
                # Check permission
                if search_profile.user != user and not user.is_staff:
                    errors[profile_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                search_profile.delete()
                deleted_ids.append(profile_id)
                success_count += 1
                
            except SearchProfile.DoesNotExist:
                errors[profile_id] = ['Search profile not found.']
                failure_count += 1
            except Exception as e:
                errors[profile_id] = [str(e)]
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

class SearchProfileMutations(graphene.ObjectType):
    """All search profile mutations."""
    
    # CRUD operations
    create_search_profile = CreateSearchProfileMutation.Field()
    update_search_profile = UpdateSearchProfileMutation.Field()
    delete_search_profile = DeleteSearchProfileMutation.Field()
    
    # Status management
    toggle_search_profile_status = ToggleSearchProfileStatusMutation.Field()
    
    # Search execution
    execute_search_profile = ExecuteSearchProfileMutation.Field()
    
    # Additional operations
    duplicate_search_profile = DuplicateSearchProfileMutation.Field()
    
    # Bulk operations
    bulk_create_search_profiles = BulkCreateSearchProfilesMutation.Field()
    bulk_delete_search_profiles = BulkDeleteSearchProfilesMutation.Field()