# apps/backend/realestate/mutations/virtual_tour.py

"""
Virtual Tour Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.virtual_tour import VirtualTour
from realestate.models.listing import Listing
from graphq.realestate.types.virtual_tour import VirtualTourNode

# =============================================================================
# Input Types
# =============================================================================

class VirtualTourInput(graphene.InputObjectType):
    """Input for virtual tour creation."""
    
    property_id = graphene.ID(required=True)
    tour_url = graphene.String(required=True)
    thumbnail = graphene.String(required=False)
    is_primary = graphene.Boolean(required=False, default_value=False)


class VirtualTourUpdateInput(graphene.InputObjectType):
    """Input for virtual tour update."""
    
    id = graphene.ID(required=True)
    tour_url = graphene.String(required=False)
    thumbnail = graphene.String(required=False)
    is_primary = graphene.Boolean(required=False)


# =============================================================================
# Create Virtual Tour Mutation
# =============================================================================

class CreateVirtualTourMutation(relay.ClientIDMutation):
    """
    Create a new virtual tour.
    
    Adds a virtual tour URL and thumbnail for a property.
    Only one virtual tour can be marked as primary per property.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        tour_url = graphene.String(required=True)
        thumbnail = graphene.String(required=False)
        is_primary = graphene.Boolean(required=False, default_value=False)
        
    virtual_tour = graphene.Field(VirtualTourNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new virtual tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: VirtualTourInput data
        
        Returns:
            CreateVirtualTourMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        tour_url = input.get('tour_url')
        thumbnail = input.get('thumbnail')
        is_primary = input.get('is_primary', False)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate tour_url
        if not tour_url:
            errors['tour_url'] = ['Tour URL is required.']
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
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to add virtual tours to this property.']
            return cls(success=False, errors=errors)
        
        try:
            # If this tour is primary, unset any existing primary tour
            if is_primary:
                VirtualTour.objects.filter(
                    property=property_obj,
                    is_primary=True
                ).update(is_primary=False)
            
            # Create virtual tour
            virtual_tour = VirtualTour.objects.create(
                property=property_obj,
                tour_url=tour_url,
                thumbnail=thumbnail,
                is_primary=is_primary,
            )
            
            return cls(
                virtual_tour=virtual_tour,
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
# Update Virtual Tour Mutation
# =============================================================================

class UpdateVirtualTourMutation(relay.ClientIDMutation):
    """
    Update an existing virtual tour.
    
    Allows updating the tour URL, thumbnail, and primary status.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        tour_url = graphene.String(required=True)
        thumbnail = graphene.String(required=False)
        is_primary = graphene.Boolean(required=False, default_value=False)
    
    virtual_tour = graphene.Field(VirtualTourNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing virtual tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: VirtualTourUpdateInput data
        
        Returns:
            UpdateVirtualTourMutation instance
        """
        errors = {}
        
        # Extract input
        virtual_tour_id = input.get('id')
        tour_url = input.get('tour_url')
        thumbnail = input.get('thumbnail')
        is_primary = input.get('is_primary')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve virtual tour
        try:
            pk = from_global_id(virtual_tour_id)[1]
            virtual_tour = VirtualTour.objects.get(pk=pk)
        except VirtualTour.DoesNotExist:
            errors['id'] = ['Virtual tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        property_obj = virtual_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to update this virtual tour.']
            return cls(success=False, errors=errors)
        
        # Validate tour_url if provided
        if tour_url is not None and not tour_url:
            errors['tour_url'] = ['Tour URL is required.']
            return cls(success=False, errors=errors)
        
        try:
            # If setting this tour as primary, unset any existing primary tour
            if is_primary is True:
                VirtualTour.objects.filter(
                    property=property_obj,
                    is_primary=True
                ).exclude(pk=virtual_tour.pk).update(is_primary=False)
            
            # Update fields
            if tour_url is not None:
                virtual_tour.tour_url = tour_url
            if thumbnail is not None:
                virtual_tour.thumbnail = thumbnail
            if is_primary is not None:
                virtual_tour.is_primary = is_primary
            
            virtual_tour.full_clean()
            virtual_tour.save()
            
            return cls(
                virtual_tour=virtual_tour,
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
# Delete Virtual Tour Mutation
# =============================================================================

class DeleteVirtualTourMutation(relay.ClientIDMutation):
    """
    Delete a virtual tour.
    
    Removes a virtual tour from the property.
    If it was the primary tour, the next newest tour becomes primary.
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
        Delete a virtual tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Virtual tour ID to delete
        
        Returns:
            DeleteVirtualTourMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve virtual tour
        try:
            pk = from_global_id(id)[1]
            virtual_tour = VirtualTour.objects.get(pk=pk)
        except VirtualTour.DoesNotExist:
            errors['id'] = ['Virtual tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        property_obj = virtual_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to delete this virtual tour.']
            return cls(success=False, errors=errors)
        
        try:
            was_primary = virtual_tour.is_primary
            deleted_id = id
            
            virtual_tour.delete()
            
            # If a primary tour was deleted, set the next newest tour as primary
            if was_primary:
                next_tour = VirtualTour.objects.filter(
                    property=property_obj
                ).order_by('-created_at').first()
                
                if next_tour:
                    next_tour.is_primary = True
                    next_tour.save()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Set Primary Virtual Tour Mutation
# =============================================================================

class SetPrimaryVirtualTourMutation(relay.ClientIDMutation):
    """
    Set a virtual tour as the primary tour for a property.
    
    This is a convenience mutation for setting a tour as primary.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    virtual_tour = graphene.Field(VirtualTourNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Set a virtual tour as primary.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Virtual tour ID to set as primary
        
        Returns:
            SetPrimaryVirtualTourMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve virtual tour
        try:
            pk = from_global_id(id)[1]
            virtual_tour = VirtualTour.objects.get(pk=pk)
        except VirtualTour.DoesNotExist:
            errors['id'] = ['Virtual tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        property_obj = virtual_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to modify virtual tours for this property.']
            return cls(success=False, errors=errors)
        
        # Check if already primary
        if virtual_tour.is_primary:
            errors['tour'] = ['This virtual tour is already the primary tour.']
            return cls(success=False, errors=errors)
        
        try:
            # Unset existing primary
            VirtualTour.objects.filter(
                property=property_obj,
                is_primary=True
            ).update(is_primary=False)
            
            # Set this tour as primary
            virtual_tour.is_primary = True
            virtual_tour.save()
            
            return cls(
                virtual_tour=virtual_tour,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateVirtualToursMutation(relay.ClientIDMutation):
    """
    Bulk create multiple virtual tours.
    
    Allows creating multiple virtual tours at once for different properties.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        tour_url = graphene.String(required=True)
        thumbnail = graphene.String(required=False)
        is_primary = graphene.Boolean(required=False, default_value=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create virtual tours.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            tours: List of virtual tour inputs
        
        Returns:
            BulkCreateVirtualToursMutation instance
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
        
        for idx, tour_input in enumerate(tours):
            try:
                # Use the create mutation for each tour
                result = CreateVirtualTourMutation.mutate_and_get_payload(
                    root, info, tour_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'tour_id': result.virtual_tour.id if result.virtual_tour else None,
                    })
                else:
                    failure_count += 1
                    errors[f'tour_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'tour_{idx}'] = [str(e)]
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


class BulkDeleteVirtualToursMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple virtual tours.
    
    Allows deleting multiple virtual tours at once.
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
        Bulk delete virtual tours.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of virtual tour IDs to delete
        
        Returns:
            BulkDeleteVirtualToursMutation instance
        """
        errors = {}
        deleted_ids = []
        success_count = 0
        failure_count = 0
        
        # Track properties that need primary tour update
        properties_to_update = set()
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for tour_id in ids:
            try:
                pk = from_global_id(tour_id)[1]
                virtual_tour = VirtualTour.objects.get(pk=pk)
                
                # Check permission
                property_obj = virtual_tour.property
                is_authorized = (
                    user.is_staff or
                    (hasattr(property_obj, 'agent') and property_obj.agent and 
                     hasattr(property_obj.agent, 'profile') and 
                     hasattr(property_obj.agent.profile, 'user') and 
                     property_obj.agent.profile.user == user) or
                    (hasattr(property_obj, 'owner') and property_obj.owner and 
                     property_obj.owner == user)
                )
                
                if not is_authorized:
                    errors[tour_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                # Track if primary for later update
                if virtual_tour.is_primary:
                    properties_to_update.add(property_obj.id)
                
                virtual_tour.delete()
                deleted_ids.append(tour_id)
                success_count += 1
                
            except VirtualTour.DoesNotExist:
                errors[tour_id] = ['Virtual tour not found.']
                failure_count += 1
            except Exception as e:
                errors[tour_id] = [str(e)]
                failure_count += 1
        
        # Update primary tours for affected properties
        for property_id in properties_to_update:
            try:
                property_obj = Listing.objects.get(pk=property_id)
                next_tour = VirtualTour.objects.filter(
                    property=property_obj
                ).order_by('-created_at').first()
                
                if next_tour:
                    next_tour.is_primary = True
                    next_tour.save()
            except Listing.DoesNotExist:
                pass
        
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

class VirtualTourMutations(graphene.ObjectType):
    """All virtual tour mutations."""
    
    # CRUD operations
    create_virtual_tour = CreateVirtualTourMutation.Field()
    update_virtual_tour = UpdateVirtualTourMutation.Field()
    delete_virtual_tour = DeleteVirtualTourMutation.Field()
    
    # Primary tour management
    set_primary_virtual_tour = SetPrimaryVirtualTourMutation.Field()
    
    # Bulk operations
    bulk_create_virtual_tours = BulkCreateVirtualToursMutation.Field()
    bulk_delete_virtual_tours = BulkDeleteVirtualToursMutation.Field()