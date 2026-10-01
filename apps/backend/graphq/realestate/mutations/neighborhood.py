# apps/backend/realestate/mutations/neighborhood.py

"""
Neighborhood Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphene_gis.scalars import PolygonScalar, PointScalar
from graphql_relay import from_global_id

from django.contrib.gis.geos import GEOSGeometry, Polygon, Point
from django.core.exceptions import ValidationError
from django.db import transaction

from realestate.models.neighborhood import Neighborhood
from realestate.models.listing import Listing
from graphq.realestate.types.neighborhood import NeighborhoodNode
from graphq.realestate.types.listing import ListingNode


# =============================================================================
# Create Neighborhood Mutation
# =============================================================================

class CreateNeighborhoodMutation(relay.ClientIDMutation):
    """
    Create a new neighborhood.
    
    Neighborhoods define geographic areas with associated real estate metrics
    like average prices, school ratings, crime rates, and amenities scores.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        boundary = graphene.String(required=False)
        center_point = graphene.String(required=False)
        avg_price = graphene.Decimal(required=False)
        avg_price_per_sqft = graphene.Decimal(required=False)
        school_rating = graphene.Decimal(required=False)
        crime_rate = graphene.Decimal(required=False)
        amenities_score = graphene.Int(required=False)
    
    neighborhood = graphene.Field(NeighborhoodNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new neighborhood.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: NeighborhoodInput data
        
        Returns:
            CreateNeighborhoodMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        boundary_str = input.get('boundary')
        center_point_str = input.get('center_point')
        avg_price = input.get('avg_price')
        avg_price_per_sqft = input.get('avg_price_per_sqft')
        school_rating = input.get('school_rating')
        crime_rate = input.get('crime_rate')
        amenities_score = input.get('amenities_score')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can create neighborhoods
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create neighborhoods.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate boundary
        try:
            boundary = GEOSGeometry(boundary_str)
            if not isinstance(boundary, Polygon):
                errors['boundary'] = ['Boundary must be a Polygon geometry.']
                return cls(success=False, errors=errors)
            if not boundary.valid:
                errors['boundary'] = ['Invalid polygon geometry.']
                return cls(success=False, errors=errors)
        except Exception as e:
            errors['boundary'] = [f'Invalid boundary geometry: {str(e)}']
            return cls(success=False, errors=errors)
        
        # Validate center point
        try:
            center_point = GEOSGeometry(center_point_str)
            if not isinstance(center_point, Point):
                errors['center_point'] = ['Center point must be a Point geometry.']
                return cls(success=False, errors=errors)
            if not center_point.valid:
                errors['center_point'] = ['Invalid point geometry.']
                return cls(success=False, errors=errors)
        except Exception as e:
            errors['center_point'] = [f'Invalid center point: {str(e)}']
            return cls(success=False, errors=errors)
        
        # Verify center point is within boundary
        if not boundary.contains(center_point):
            errors['center_point'] = ['Center point must be within the boundary polygon.']
            return cls(success=False, errors=errors)
        
        # Validate avg price
        if avg_price <= 0:
            errors['avg_price'] = ['Average price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate avg price per sqft
        if avg_price_per_sqft <= 0:
            errors['avg_price_per_sqft'] = ['Average price per sqft must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate school rating
        if school_rating < 0 or school_rating > 5:
            errors['school_rating'] = ['School rating must be between 0 and 5.']
            return cls(success=False, errors=errors)
        
        # Validate crime rate
        if crime_rate < 0 or crime_rate > 100:
            errors['crime_rate'] = ['Crime rate must be between 0 and 100.']
            return cls(success=False, errors=errors)
        
        # Validate amenities score
        if amenities_score < 0:
            errors['amenities_score'] = ['Amenities score cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Check for duplicate name
        if Neighborhood.objects.filter(name__iexact=name).exists():
            errors['name'] = ['Neighborhood with this name already exists.']
            return cls(success=False, errors=errors)
        
        try:
            # Create neighborhood
            neighborhood = Neighborhood.objects.create(
                name=name.strip(),
                boundary=boundary,
                center_point=center_point,
                avg_price=avg_price,
                avg_price_per_sqft=avg_price_per_sqft,
                school_rating=school_rating,
                crime_rate=crime_rate,
                amenities_score=amenities_score,
            )
            
            return cls(
                neighborhood=neighborhood,
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
# Update Neighborhood Mutation
# =============================================================================

class UpdateNeighborhoodMutation(relay.ClientIDMutation):
    """
    Update an existing neighborhood.
    
    Allows updating all neighborhood attributes including geometry and metrics.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        boundary = graphene.String(required=False)
        center_point = graphene.String(required=False)
        avg_price = graphene.Decimal(required=False)
        avg_price_per_sqft = graphene.Decimal(required=False)
        school_rating = graphene.Decimal(required=False)
        crime_rate = graphene.Decimal(required=False)
        amenities_score = graphene.Int(required=False)
    
    neighborhood = graphene.Field(NeighborhoodNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing neighborhood.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: NeighborhoodUpdateInput data
        
        Returns:
            UpdateNeighborhoodMutation instance
        """
        errors = {}
        
        # Extract input
        neighborhood_id = input.get('id')
        name = input.get('name')
        boundary_str = input.get('boundary')
        center_point_str = input.get('center_point')
        avg_price = input.get('avg_price')
        avg_price_per_sqft = input.get('avg_price_per_sqft')
        school_rating = input.get('school_rating')
        crime_rate = input.get('crime_rate')
        amenities_score = input.get('amenities_score')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can update neighborhoods
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update neighborhoods.']
            return cls(success=False, errors=errors)
        
        # Resolve neighborhood
        try:
            pk = from_global_id(neighborhood_id)[1]
            neighborhood = Neighborhood.objects.get(pk=pk)
        except Neighborhood.DoesNotExist:
            errors['id'] = ['Neighborhood not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None:
            if not name or not name.strip():
                errors['name'] = ['Name is required.']
                return cls(success=False, errors=errors)
            
            if Neighborhood.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                errors['name'] = ['Neighborhood with this name already exists.']
                return cls(success=False, errors=errors)
        
        # Validate boundary if provided
        if boundary_str is not None:
            try:
                boundary = GEOSGeometry(boundary_str)
                if not isinstance(boundary, Polygon):
                    errors['boundary'] = ['Boundary must be a Polygon geometry.']
                    return cls(success=False, errors=errors)
                if not boundary.valid:
                    errors['boundary'] = ['Invalid polygon geometry.']
                    return cls(success=False, errors=errors)
            except Exception as e:
                errors['boundary'] = [f'Invalid boundary geometry: {str(e)}']
                return cls(success=False, errors=errors)
        
        # Validate center point if provided
        if center_point_str is not None:
            try:
                center_point = GEOSGeometry(center_point_str)
                if not isinstance(center_point, Point):
                    errors['center_point'] = ['Center point must be a Point geometry.']
                    return cls(success=False, errors=errors)
                if not center_point.valid:
                    errors['center_point'] = ['Invalid point geometry.']
                    return cls(success=False, errors=errors)
            except Exception as e:
                errors['center_point'] = [f'Invalid center point: {str(e)}']
                return cls(success=False, errors=errors)
        
        # Validate center point within boundary if both provided
        if boundary_str is not None and center_point_str is not None:
            if not boundary.contains(center_point):
                errors['center_point'] = ['Center point must be within the boundary polygon.']
                return cls(success=False, errors=errors)
        
        # Validate metrics
        if avg_price is not None and avg_price <= 0:
            errors['avg_price'] = ['Average price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if avg_price_per_sqft is not None and avg_price_per_sqft <= 0:
            errors['avg_price_per_sqft'] = ['Average price per sqft must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if school_rating is not None and (school_rating < 0 or school_rating > 5):
            errors['school_rating'] = ['School rating must be between 0 and 5.']
            return cls(success=False, errors=errors)
        
        if crime_rate is not None and (crime_rate < 0 or crime_rate > 100):
            errors['crime_rate'] = ['Crime rate must be between 0 and 100.']
            return cls(success=False, errors=errors)
        
        if amenities_score is not None and amenities_score < 0:
            errors['amenities_score'] = ['Amenities score cannot be negative.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                neighborhood.name = name.strip()
            if boundary_str is not None:
                neighborhood.boundary = boundary
            if center_point_str is not None:
                neighborhood.center_point = center_point
            if avg_price is not None:
                neighborhood.avg_price = avg_price
            if avg_price_per_sqft is not None:
                neighborhood.avg_price_per_sqft = avg_price_per_sqft
            if school_rating is not None:
                neighborhood.school_rating = school_rating
            if crime_rate is not None:
                neighborhood.crime_rate = crime_rate
            if amenities_score is not None:
                neighborhood.amenities_score = amenities_score
            
            neighborhood.full_clean()
            neighborhood.save()
            
            return cls(
                neighborhood=neighborhood,
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
# Delete Neighborhood Mutation
# =============================================================================

class DeleteNeighborhoodMutation(relay.ClientIDMutation):
    """
    Delete a neighborhood.
    
    Removes a neighborhood and its associated data.
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
        Delete a neighborhood.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Neighborhood ID to delete
            force: Force deletion even if listings exist
        
        Returns:
            DeleteNeighborhoodMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete neighborhoods
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete neighborhoods.']
            return cls(success=False, errors=errors)
        
        # Resolve neighborhood
        try:
            pk = from_global_id(id)[1]
            neighborhood = Neighborhood.objects.get(pk=pk)
        except Neighborhood.DoesNotExist:
            errors['id'] = ['Neighborhood not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if neighborhood has listings
        if not force:
            if Listing.objects.filter(neighborhood=neighborhood).exists():
                errors['in_use'] = [
                    'Cannot delete neighborhood that has listings. '
                    'Use force=True to override.'
                ]
                return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            neighborhood.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Find Properties in Neighborhood Mutation
# =============================================================================

class FindPropertiesInNeighborhoodMutation(relay.ClientIDMutation):
    """
    Find all properties within a neighborhood boundary.
    
    Returns listings that are geographically located within the
    neighborhood's polygon boundary.
    """
    
    class Input:
        neighborhood_id = graphene.ID(required=True)
        max_results = graphene.Int(required=False, default_value=50)
    
    properties = graphene.List(ListingNode)
    count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, neighborhood_id, max_results=50):
        """
        Find properties within a neighborhood.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            neighborhood_id: Neighborhood ID
            max_results: Maximum number of properties to return
        
        Returns:
            FindPropertiesInNeighborhoodMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve neighborhood
        try:
            pk = from_global_id(neighborhood_id)[1]
            neighborhood = Neighborhood.objects.get(pk=pk)
        except Neighborhood.DoesNotExist:
            errors['neighborhood_id'] = ['Neighborhood not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['neighborhood_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Find properties within neighborhood boundary
            # This uses the spatial query to find listings within the polygon
            properties = Listing.objects.filter(
                is_published=True,
                location_point__within=neighborhood.boundary
            )[:max_results]
            
            return cls(
                properties=properties,
                count=properties.count() if hasattr(properties, 'count') else len(properties),
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateNeighborhoodsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple neighborhoods.
    
    Allows creating multiple neighborhoods at once.
    """
    
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        boundary = graphene.String(required=False)
        center_point = graphene.String(required=False)
        avg_price = graphene.Decimal(required=False)
        avg_price_per_sqft = graphene.Decimal(required=False)
        school_rating = graphene.Decimal(required=False)
        crime_rate = graphene.Decimal(required=False)
        amenities_score = graphene.Int(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create neighborhoods.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            neighborhoods: List of neighborhood inputs
        
        Returns:
            BulkCreateNeighborhoodsMutation instance
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
            errors['permission'] = ['Only staff members can create neighborhoods.']
            return cls(success=False, errors=errors)
        
        for idx, neighborhood_input in enumerate(neighborhoods):
            try:
                # Use the create mutation for each neighborhood
                result = CreateNeighborhoodMutation.mutate_and_get_payload(
                    root, info, neighborhood_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'neighborhood_id': result.neighborhood.id if result.neighborhood else None,
                    })
                else:
                    failure_count += 1
                    errors[f'neighborhood_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'neighborhood_{idx}'] = [str(e)]
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


class BulkDeleteNeighborhoodsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple neighborhoods.
    
    Allows deleting multiple neighborhoods at once.
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
        Bulk delete neighborhoods.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of neighborhood IDs to delete
            force: Force deletion even if listings exist
        
        Returns:
            BulkDeleteNeighborhoodsMutation instance
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
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete neighborhoods.']
            return cls(success=False, errors=errors)
        
        for neighborhood_id in ids:
            try:
                pk = from_global_id(neighborhood_id)[1]
                neighborhood = Neighborhood.objects.get(pk=pk)
                
                # Check if in use
                if not force:
                    if Listing.objects.filter(neighborhood=neighborhood).exists():
                        errors[neighborhood_id] = ['Neighborhood has listings. Use force=True to override.']
                        failure_count += 1
                        continue
                
                neighborhood.delete()
                deleted_ids.append(neighborhood_id)
                success_count += 1
                
            except Neighborhood.DoesNotExist:
                errors[neighborhood_id] = ['Neighborhood not found.']
                failure_count += 1
            except Exception as e:
                errors[neighborhood_id] = [str(e)]
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

class NeighborhoodMutations(graphene.ObjectType):
    """All neighborhood mutations."""
    
    # CRUD operations
    create_neighborhood = CreateNeighborhoodMutation.Field()
    update_neighborhood = UpdateNeighborhoodMutation.Field()
    delete_neighborhood = DeleteNeighborhoodMutation.Field()
    
    # Spatial queries
    find_properties_in_neighborhood = FindPropertiesInNeighborhoodMutation.Field()
    
    # Bulk operations
    bulk_create_neighborhoods = BulkCreateNeighborhoodsMutation.Field()
    bulk_delete_neighborhoods = BulkDeleteNeighborhoodsMutation.Field()