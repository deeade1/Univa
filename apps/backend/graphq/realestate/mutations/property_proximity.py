# apps/backend/realestate/mutations/property_proximity.py

"""
Property Proximity Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.property_proximity import PropertyProximity
from realestate.models.listing import Listing
from realestate.models.client import Client
from graphq.realestate.types.property_proximity import PropertyProximityNode



# =============================================================================
# Create Property Proximity Mutation
# =============================================================================

class CreatePropertyProximityMutation(relay.ClientIDMutation):
    """
    Create a new property proximity record.
    
    Calculates and stores the distance between a property and a buyer's
    preferred location. This is used for proximity-based property recommendations.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        distance_km = graphene.Float(required=True)
        is_in_preferred_location = graphene.Boolean(required=False, default_value=False)

    
    proximity = graphene.Field(PropertyProximityNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new property proximity record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyProximityInput data
        
        Returns:
            CreatePropertyProximityMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        buyer_id = input.get('buyer_id')
        distance_km = input.get('distance_km')
        is_in_preferred_location = input.get('is_in_preferred_location', False)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate distance
        if distance_km < 0:
            errors['distance_km'] = ['Distance cannot be negative.']
            return cls(success=False, errors=errors)
        
        if distance_km > 1000:
            errors['distance_km'] = ['Distance cannot exceed 1000 km.']
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
        
        # Resolve buyer
        try:
            pk = from_global_id(buyer_id)[1]
            buyer = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['buyer_id'] = ['Buyer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['buyer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the buyer or staff can create proximity records
        if buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to create proximity records for this buyer.']
            return cls(success=False, errors=errors)
        
        # Check if proximity record already exists
        if PropertyProximity.objects.filter(property=property_obj, buyer=buyer).exists():
            errors['proximity'] = ['Proximity record already exists for this property and buyer.']
            return cls(success=False, errors=errors)
        
        try:
            # Create property proximity
            proximity = PropertyProximity.objects.create(
                property=property_obj,
                buyer=buyer,
                distance_km=distance_km,
                is_in_preferred_location=is_in_preferred_location,
            )
            
            return cls(
                proximity=proximity,
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
# Update Property Proximity Mutation
# =============================================================================

class UpdatePropertyProximityMutation(relay.ClientIDMutation):
    """
    Update an existing property proximity record.
    
    Allows updating the distance and preferred location status.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        distance_km = graphene.Float(required=True)
        is_in_preferred_location = graphene.Boolean(required=False, default_value=False)

    
    proximity = graphene.Field(PropertyProximityNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing property proximity record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyProximityUpdateInput data
        
        Returns:
            UpdatePropertyProximityMutation instance
        """
        errors = {}
        
        # Extract input
        proximity_id = input.get('id')
        distance_km = input.get('distance_km')
        is_in_preferred_location = input.get('is_in_preferred_location')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve proximity
        try:
            pk = from_global_id(proximity_id)[1]
            proximity = PropertyProximity.objects.get(pk=pk)
        except PropertyProximity.DoesNotExist:
            errors['id'] = ['Property proximity record not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the buyer or staff can update
        if proximity.buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this proximity record.']
            return cls(success=False, errors=errors)
        
        # Validate distance if provided
        if distance_km is not None:
            if distance_km < 0:
                errors['distance_km'] = ['Distance cannot be negative.']
                return cls(success=False, errors=errors)
            
            if distance_km > 1000:
                errors['distance_km'] = ['Distance cannot exceed 1000 km.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if distance_km is not None:
                proximity.distance_km = distance_km
            if is_in_preferred_location is not None:
                proximity.is_in_preferred_location = is_in_preferred_location
            
            proximity.full_clean()
            proximity.save()
            
            return cls(
                proximity=proximity,
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
# Delete Property Proximity Mutation
# =============================================================================

class DeletePropertyProximityMutation(relay.ClientIDMutation):
    """
    Delete a property proximity record.
    
    Removes a proximity record from the database.
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
        Delete a property proximity record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Proximity ID to delete
        
        Returns:
            DeletePropertyProximityMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve proximity
        try:
            pk = from_global_id(id)[1]
            proximity = PropertyProximity.objects.get(pk=pk)
        except PropertyProximity.DoesNotExist:
            errors['id'] = ['Property proximity record not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the buyer or staff can delete
        if proximity.buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this proximity record.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            proximity.delete()
            
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

class BulkCreatePropertyProximitiesMutation(relay.ClientIDMutation):
    """
    Bulk create multiple property proximity records.
    
    Allows creating multiple proximity records at once for different
    properties or buyers.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        distance_km = graphene.Float(required=True)
        is_in_preferred_location = graphene.Boolean(required=False, default_value=False)

    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create property proximities.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            proximities: List of property proximity inputs
        
        Returns:
            BulkCreatePropertyProximitiesMutation instance
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
        
        for idx, proximity_input in enumerate(proximities):
            try:
                # Use the create mutation for each proximity
                result = CreatePropertyProximityMutation.mutate_and_get_payload(
                    root, info, proximity_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'proximity_id': result.proximity.id if result.proximity else None,
                    })
                else:
                    failure_count += 1
                    errors[f'proximity_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'proximity_{idx}'] = [str(e)]
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


class BulkDeletePropertyProximitiesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple property proximity records.
    
    Allows deleting multiple proximity records at once.
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
        Bulk delete property proximities.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of proximity IDs to delete
        
        Returns:
            BulkDeletePropertyProximitiesMutation instance
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
        
        for proximity_id in ids:
            try:
                pk = from_global_id(proximity_id)[1]
                proximity = PropertyProximity.objects.get(pk=pk)
                
                # Check permission
                if proximity.buyer.user != user and not user.is_staff:
                    errors[proximity_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                proximity.delete()
                deleted_ids.append(proximity_id)
                success_count += 1
                
            except PropertyProximity.DoesNotExist:
                errors[proximity_id] = ['Property proximity record not found.']
                failure_count += 1
            except Exception as e:
                errors[proximity_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Calculate Proximity Mutation
# =============================================================================

class CalculateProximityMutation(relay.ClientIDMutation):
    """
    Calculate and store proximity between a property and a buyer's location.
    
    This mutation calculates the distance between a property and a buyer's
    preferred location and stores it in a PropertyProximity record.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
    
    proximity = graphene.Field(PropertyProximityNode)
    distance_km = graphene.Float()
    is_in_preferred_location = graphene.Boolean()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, property_id, buyer_id):
        """
        Calculate and store proximity.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            property_id: Property ID
            buyer_id: Buyer ID
        
        Returns:
            CalculateProximityMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
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
        
        # Resolve buyer
        try:
            pk = from_global_id(buyer_id)[1]
            buyer = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['buyer_id'] = ['Buyer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['buyer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to calculate proximity for this buyer.']
            return cls(success=False, errors=errors)
        
        try:
            # Calculate distance using the property's LocationModel
            distance_km = None
            is_in_preferred_location = False
            
            if property_obj.location_point and buyer.location_point:
                # Calculate distance in kilometers
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import Distance
                
                distance = property_obj.location_point.distance(buyer.location_point)
                # Convert to kilometers (assuming distance is in degrees)
                # This is a simplified calculation - use proper conversion
                distance_km = float(distance * 111.32)  # Approximate km per degree
                distance_km = round(distance_km, 2)
                
                # Check if within preferred location (using buyer's search radius)
                if hasattr(buyer, 'search_radius_km'):
                    is_in_preferred_location = distance_km <= buyer.search_radius_km
            
            # Create or update proximity record
            proximity, created = PropertyProximity.objects.update_or_create(
                property=property_obj,
                buyer=buyer,
                defaults={
                    'distance_km': distance_km or 0,
                    'is_in_preferred_location': is_in_preferred_location,
                }
            )
            
            return cls(
                proximity=proximity,
                distance_km=float(distance_km) if distance_km is not None else 0,
                is_in_preferred_location=is_in_preferred_location,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class PropertyProximityMutations(graphene.ObjectType):
    """All property proximity mutations."""
    
    # CRUD operations
    create_property_proximity = CreatePropertyProximityMutation.Field()
    update_property_proximity = UpdatePropertyProximityMutation.Field()
    delete_property_proximity = DeletePropertyProximityMutation.Field()
    
    # Calculations
    calculate_proximity = CalculateProximityMutation.Field()
    
    # Bulk operations
    bulk_create_property_proximities = BulkCreatePropertyProximitiesMutation.Field()
    bulk_delete_property_proximities = BulkDeletePropertyProximitiesMutation.Field()