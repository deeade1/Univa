# apps/backend/realestate/mutations/location_preference.py

"""
Location Preference Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction

from realestate.models.location_preference import LocationPreference

from graphq.realestate.types.location_preference import LocationPreferenceNode
from graphq.realestate.types.listing import ListingNode
# =============================================================================
# Create Location Preference Mutation
# =============================================================================

class CreateLocationPreferenceMutation(relay.ClientIDMutation):
    """
    Create a new location preference.
    
    Location preferences allow users to save geographic search areas
    for quick property searches.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
    
    location_preference = graphene.Field(LocationPreferenceNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Create a new location preference.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LocationPreferenceInput data
        
        Returns:
            CreateLocationPreferenceMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        latitude = input.get('latitude')
        longitude = input.get('longitude')
        radius_km = input.get('radius_km', 5)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate coordinates
        if latitude is None or longitude is None:
            errors['coordinates'] = ['Both latitude and longitude are required.']
            return cls(success=False, errors=errors)
        
        if not (-90 <= latitude <= 90):
            errors['latitude'] = ['Latitude must be between -90 and 90.']
            return cls(success=False, errors=errors)
        
        if not (-180 <= longitude <= 180):
            errors['longitude'] = ['Longitude must be between -180 and 180.']
            return cls(success=False, errors=errors)
        
        # Validate radius
        if radius_km <= 0:
            errors['radius_km'] = ['Radius must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Check for duplicate name for this user
        if LocationPreference.objects.filter(user=user, name__iexact=name).exists():
            errors['name'] = ['You already have a location preference with this name.']
            return cls(success=False, errors=errors)
        
        try:
            # Create location point
            location_point = Point(longitude, latitude, srid=4326)
            
            # Create location preference
            location_preference = LocationPreference.objects.create(
                name=name.strip(),
                location_point=location_point,
                radius_km=radius_km,
                user=user,
            )
            
            return cls(
                location_preference=location_preference,
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
# Update Location Preference Mutation
# =============================================================================

class UpdateLocationPreferenceMutation(relay.ClientIDMutation):
    """
    Update an existing location preference.
    
    Allows updating the name, location, or radius of a saved preference.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
    
    location_preference = graphene.Field(LocationPreferenceNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing location preference.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LocationPreferenceUpdateInput data
        
        Returns:
            UpdateLocationPreferenceMutation instance
        """
        errors = {}
        
        # Extract input
        preference_id = input.get('id')
        name = input.get('name')
        latitude = input.get('latitude')
        longitude = input.get('longitude')
        radius_km = input.get('radius_km')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve location preference
        try:
            pk = from_global_id(preference_id)[1]
            location_preference = LocationPreference.objects.get(pk=pk)
        except LocationPreference.DoesNotExist:
            errors['id'] = ['Location preference not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can update
        if location_preference.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this location preference.']
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None:
            if not name or not name.strip():
                errors['name'] = ['Name is required.']
                return cls(success=False, errors=errors)
            
            # Check for duplicate name (excluding current)
            if LocationPreference.objects.filter(
                user=user,
                name__iexact=name
            ).exclude(pk=location_preference.pk).exists():
                errors['name'] = ['You already have a location preference with this name.']
                return cls(success=False, errors=errors)
        
        # Validate coordinates if provided
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90):
                errors['latitude'] = ['Latitude must be between -90 and 90.']
                return cls(success=False, errors=errors)
            
            if not (-180 <= longitude <= 180):
                errors['longitude'] = ['Longitude must be between -180 and 180.']
                return cls(success=False, errors=errors)
        
        # Validate radius if provided
        if radius_km is not None and radius_km <= 0:
            errors['radius_km'] = ['Radius must be greater than 0.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                location_preference.name = name.strip()
            
            if latitude is not None and longitude is not None:
                location_preference.location_point = Point(longitude, latitude, srid=4326)
            
            if radius_km is not None:
                location_preference.radius_km = radius_km
            
            location_preference.full_clean()
            location_preference.save()
            
            return cls(
                location_preference=location_preference,
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
# Delete Location Preference Mutation
# =============================================================================

class DeleteLocationPreferenceMutation(relay.ClientIDMutation):
    """
    Delete a location preference.
    
    Removes a saved location preference from the user's account.
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
        Delete a location preference.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Location preference ID to delete
        
        Returns:
            DeleteLocationPreferenceMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve location preference
        try:
            pk = from_global_id(id)[1]
            location_preference = LocationPreference.objects.get(pk=pk)
        except LocationPreference.DoesNotExist:
            errors['id'] = ['Location preference not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can delete
        if location_preference.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this location preference.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            location_preference.delete()
            
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

class BulkCreateLocationPreferencesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple location preferences.
    
    Allows creating multiple location preferences at once.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, preferences):
        """
        Bulk create location preferences.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            preferences: List of location preference inputs
        
        Returns:
            BulkCreateLocationPreferencesMutation instance
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
        
        for idx, preference_input in enumerate(preferences):
            try:
                # Use the create mutation for each preference
                result = CreateLocationPreferenceMutation.mutate_and_get_payload(
                    root, info, preference_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'preference_id': result.location_preference.id if result.location_preference else None,
                    })
                else:
                    failure_count += 1
                    errors[f'preference_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'preference_{idx}'] = [str(e)]
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


class BulkDeleteLocationPreferencesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple location preferences.
    
    Allows deleting multiple preferences at once.
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
        Bulk delete location preferences.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of preference IDs to delete
        
        Returns:
            BulkDeleteLocationPreferencesMutation instance
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
        
        for preference_id in ids:
            try:
                pk = from_global_id(preference_id)[1]
                location_preference = LocationPreference.objects.get(pk=pk)
                
                # Check permission - only the owner or staff can delete
                if location_preference.user != user and not user.is_staff:
                    errors[preference_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                location_preference.delete()
                deleted_ids.append(preference_id)
                success_count += 1
                
            except LocationPreference.DoesNotExist:
                errors[preference_id] = ['Location preference not found.']
                failure_count += 1
            except Exception as e:
                errors[preference_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Find Properties Near Preference Mutation
# =============================================================================

class FindPropertiesNearPreferenceMutation(relay.ClientIDMutation):
    """
    Find properties near a location preference.
    
    Returns properties within the radius of a saved location preference.
    """
    
    class Input:
        preference_id = graphene.ID(required=True)
        limit = graphene.Int(required=False, default_value=20)
    
    properties = graphene.Field(ListingNode)
    count = graphene.Int()
    radius_km = graphene.Int()
    center_latitude = graphene.Float()
    center_longitude = graphene.Float()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, preference_id, limit=20):
        """
        Find properties near a location preference.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            preference_id: Preference ID
            limit: Maximum number of properties to return
        
        Returns:
            FindPropertiesNearPreferenceMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve location preference
        try:
            pk = from_global_id(preference_id)[1]
            location_preference = LocationPreference.objects.get(pk=pk)
        except LocationPreference.DoesNotExist:
            errors['preference_id'] = ['Location preference not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['preference_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner or staff can view
        if location_preference.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to view this location preference.']
            return cls(success=False, errors=errors)
        
        try:
            # Find properties within radius
            from ..models.listing import Listing
            
            properties = Listing.objects.filter(
                is_published=True,
                location_point__isnull=False
            ).nearby(
                location_preference.location_point,
                location_preference.radius_km
            )[:limit]
            
            return cls(
                properties=properties,
                count=properties.count() if hasattr(properties, 'count') else len(properties),
                radius_km=location_preference.radius_km,
                center_latitude=location_preference.latitude,
                center_longitude=location_preference.longitude,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class LocationPreferenceMutations(graphene.ObjectType):
    """All location preference mutations."""
    
    # CRUD operations
    create_location_preference = CreateLocationPreferenceMutation.Field()
    update_location_preference = UpdateLocationPreferenceMutation.Field()
    delete_location_preference = DeleteLocationPreferenceMutation.Field()
    
    # Bulk operations
    bulk_create_location_preferences = BulkCreateLocationPreferencesMutation.Field()
    bulk_delete_location_preferences = BulkDeleteLocationPreferencesMutation.Field()
    
    # Search
    find_properties_near_preference = FindPropertiesNearPreferenceMutation.Field()