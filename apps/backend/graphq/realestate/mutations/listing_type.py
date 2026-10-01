# apps/backend/realestate/mutations/listing_type.py

"""
Listing Type Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction

from realestate.models.listing_type import ListingType
from realestate.constants import PROPERTY_TYPES

from  graphq.realestate.types.listing_type import ListingTypeNode


# =============================================================================
# Create Listing Type Mutation
# =============================================================================

class CreateListingTypeMutation(relay.ClientIDMutation):
    """
    Create a new listing type.
    
    Listing types define the categories of properties that can be listed,
    such as Residential, Commercial, Land, etc.
    """
    
    class Input:
        property_type = graphene.String(required=True)
        requires_land_details = graphene.Boolean(required=False, default_value=False)
        requires_building_details = graphene.Boolean(required=False, default_value=True)
        supports_plot_sales = graphene.Boolean(required=False, default_value=False)

    
    listing_type = graphene.Field(ListingTypeNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new listing type.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingTypeInput data
        
        Returns:
            CreateListingTypeMutation instance
        """
        errors = {}
        
        # Extract input
        property_type = input.get('property_type')
        requires_land_details = input.get('requires_land_details', False)
        requires_building_details = input.get('requires_building_details', True)
        supports_plot_sales = input.get('supports_plot_sales', False)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can create listing types
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create listing types.']
            return cls(success=False, errors=errors)
        
        # Validate property_type
        if not property_type:
            errors['property_type'] = ['Property type is required.']
            return cls(success=False, errors=errors)
        
        # Check if property_type is valid
        valid_types = [choice[0] for choice in PROPERTY_TYPES]
        if property_type not in valid_types:
            errors['property_type'] = [
                f'Invalid property type. Must be one of: {", ".join(valid_types)}'
            ]
            return cls(success=False, errors=errors)
        
        # Check if listing type already exists
        if ListingType.objects.filter(property_type=property_type).exists():
            errors['property_type'] = ['Listing type with this property type already exists.']
            return cls(success=False, errors=errors)
        
        try:
            # Create listing type
            listing_type = ListingType.objects.create(
                property_type=property_type,
                requires_land_details=requires_land_details,
                requires_building_details=requires_building_details,
                supports_plot_sales=supports_plot_sales,
            )
            
            return cls(
                listing_type=listing_type,
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
# Update Listing Type Mutation
# =============================================================================

class UpdateListingTypeMutation(relay.ClientIDMutation):
    """
    Update an existing listing type.
    
    Allows updating the details of a property type category.
    """
    
    class Input:
        property_type = graphene.String(required=True)
        requires_land_details = graphene.Boolean(required=False, default_value=False)
        requires_building_details = graphene.Boolean(required=False, default_value=True)
        supports_plot_sales = graphene.Boolean(required=False, default_value=False)

    
    listing_type = graphene.Field(ListingTypeNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing listing type.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingTypeUpdateInput data
        
        Returns:
            UpdateListingTypeMutation instance
        """
        errors = {}
        
        # Extract input
        listing_type_id = input.get('id')
        property_type = input.get('property_type')
        requires_land_details = input.get('requires_land_details')
        requires_building_details = input.get('requires_building_details')
        supports_plot_sales = input.get('supports_plot_sales')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can update listing types
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update listing types.']
            return cls(success=False, errors=errors)
        
        # Resolve listing type
        try:
            pk = from_global_id(listing_type_id)[1]
            listing_type = ListingType.objects.get(pk=pk)
        except ListingType.DoesNotExist:
            errors['id'] = ['Listing type not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate property_type if provided
        if property_type is not None:
            # Check if property_type is valid
            valid_types = [choice[0] for choice in PROPERTY_TYPES]
            if property_type not in valid_types:
                errors['property_type'] = [
                    f'Invalid property type. Must be one of: {", ".join(valid_types)}'
                ]
                return cls(success=False, errors=errors)
            
            # Check if property_type already exists (excluding current)
            if ListingType.objects.filter(property_type=property_type).exclude(pk=pk).exists():
                errors['property_type'] = ['Listing type with this property type already exists.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if property_type is not None:
                listing_type.property_type = property_type
            if requires_land_details is not None:
                listing_type.requires_land_details = requires_land_details
            if requires_building_details is not None:
                listing_type.requires_building_details = requires_building_details
            if supports_plot_sales is not None:
                listing_type.supports_plot_sales = supports_plot_sales
            
            listing_type.full_clean()
            listing_type.save()
            
            return cls(
                listing_type=listing_type,
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
# Delete Listing Type Mutation
# =============================================================================

class DeleteListingTypeMutation(relay.ClientIDMutation):
    """
    Delete a listing type.
    
    Removes a property type category. This will only succeed if no listings
    are using this type.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force deletion even if listings exist"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a listing type.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing type ID to delete
            force: Force deletion even if listings exist
        
        Returns:
            DeleteListingTypeMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete listing types
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete listing types.']
            return cls(success=False, errors=errors)
        
        # Resolve listing type
        try:
            pk = from_global_id(id)[1]
            listing_type = ListingType.objects.get(pk=pk)
        except ListingType.DoesNotExist:
            errors['id'] = ['Listing type not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if listing type is in use
        if not force:
            # Check if any listings use this type
            # This assumes the Listing model has a listing_type ForeignKey
            try:
                from ..models.listing import Listing
                if Listing.objects.filter(listing_type=listing_type).exists():
                    errors['in_use'] = [
                        'Cannot delete listing type that is in use by listings. '
                        'Use force=True to override.'
                    ]
                    return cls(success=False, errors=errors)
            except ImportError:
                # Listing model not found - skip check
                pass
            except Exception as e:
                errors['check'] = [str(e)]
                return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            listing_type.delete()
            
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
# Bulk Operations
# =============================================================================

class BulkCreateListingTypesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple listing types.
    
    Allows creating multiple property types at once.
    """
    
    class Input:
        property_type = graphene.String(required=True)
        requires_land_details = graphene.Boolean(required=False, default_value=False)
        requires_building_details = graphene.Boolean(required=False, default_value=True)
        supports_plot_sales = graphene.Boolean(required=False, default_value=False)

    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_types):
        """
        Bulk create listing types.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_types: List of listing type inputs
        
        Returns:
            BulkCreateListingTypesMutation instance
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
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create listing types.']
            return cls(success=False, errors=errors)
        
        valid_types = [choice[0] for choice in PROPERTY_TYPES]
        
        for idx, type_data in enumerate(listing_types):
            try:
                property_type = type_data.get('property_type')
                
                # Validate property_type
                if not property_type:
                    errors[f'item_{idx}'] = ['Property type is required.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': ['Property type is required'],
                    })
                    continue
                
                if property_type not in valid_types:
                    errors[f'item_{idx}'] = [f'Invalid property type: {property_type}']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': [f'Invalid property type: {property_type}'],
                    })
                    continue
                
                # Check if exists
                if ListingType.objects.filter(property_type=property_type).exists():
                    errors[f'item_{idx}'] = [f'Listing type {property_type} already exists.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': [f'Listing type {property_type} already exists'],
                    })
                    continue
                
                # Create listing type
                listing_type = ListingType.objects.create(
                    property_type=property_type,
                    requires_land_details=type_data.get('requires_land_details', False),
                    requires_building_details=type_data.get('requires_building_details', True),
                    supports_plot_sales=type_data.get('supports_plot_sales', False),
                )
                
                success_count += 1
                results.append({
                    'index': idx,
                    'id': listing_type.id,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[f'item_{idx}'] = [str(e)]
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


class BulkDeleteListingTypesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple listing types.
    
    Allows deleting multiple property types at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, force=False):
        """
        Bulk delete listing types.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of listing type IDs to delete
            force: Force deletion even if listings exist
        
        Returns:
            BulkDeleteListingTypesMutation instance
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
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete listing types.']
            return cls(success=False, errors=errors)
        
        for type_id in ids:
            try:
                pk = from_global_id(type_id)[1]
                listing_type = ListingType.objects.get(pk=pk)
                
                # Check if in use
                if not force:
                    try:
                        from ..models.listing import Listing
                        if Listing.objects.filter(listing_type=listing_type).exists():
                            failed_ids.append(type_id)
                            errors[type_id] = ['Listing type is in use. Use force=True to override.']
                            failure_count += 1
                            continue
                    except ImportError:
                        pass
                
                listing_type.delete()
                deleted_ids.append(type_id)
                success_count += 1
                
            except ListingType.DoesNotExist:
                failed_ids.append(type_id)
                errors[type_id] = ['Listing type not found.']
                failure_count += 1
            except Exception as e:
                failed_ids.append(type_id)
                errors[type_id] = [str(e)]
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

class ListingTypeMutations(graphene.ObjectType):
    """All listing type mutations."""
    
    # CRUD operations
    create_listing_type = CreateListingTypeMutation.Field()
    update_listing_type = UpdateListingTypeMutation.Field()
    delete_listing_type = DeleteListingTypeMutation.Field()
    
    # Bulk operations
    bulk_create_listing_types = BulkCreateListingTypesMutation.Field()
    bulk_delete_listing_types = BulkDeleteListingTypesMutation.Field()