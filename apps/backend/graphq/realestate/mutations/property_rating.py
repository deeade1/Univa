# apps/backend/realestate/mutations/property_rating.py

"""
Property Rating Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.property_rating import PropertyRating
from realestate.models.listing import Listing

from graphq.realestate.types.property_rating import PropertyRatingNode
# =============================================================================
# Input Types
# =============================================================================

class PropertyRatingInput(graphene.InputObjectType):
    """Input for property rating creation."""
    
    property_id = graphene.ID(required=True)
    rating = graphene.Int(required=True)
    review = graphene.String(required=False)


class PropertyRatingUpdateInput(graphene.InputObjectType):
    """Input for property rating update."""
    
    id = graphene.ID(required=True)
    rating = graphene.Int(required=False)
    review = graphene.String(required=False)


# =============================================================================
# Create Property Rating Mutation
# =============================================================================

class CreatePropertyRatingMutation(relay.ClientIDMutation):
    """
    Create a new property rating.
    
    Allows users to rate properties they have transacted with.
    Users can only rate a property once.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        review = graphene.String(required=False)
    
    property_rating = graphene.Field(PropertyRatingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new property rating.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyRatingInput data
        
        Returns:
            CreatePropertyRatingMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        rating = input.get('rating')
        review = input.get('review', '')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate rating
        if rating < 1 or rating > 5:
            errors['rating'] = ['Rating must be between 1 and 5.']
            return cls(success=False, errors=errors)
        
        # Validate review length
        if review and len(review) > 2000:
            errors['review'] = ['Review cannot exceed 2000 characters.']
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
        
        # Check if user is the owner of the property
        if property_obj.owner and property_obj.owner == user:
            errors['permission'] = ['You cannot rate your own property.']
            return cls(success=False, errors=errors)
        
        # Check if user has already rated this property
        if PropertyRating.objects.filter(property=property_obj, user=user).exists():
            errors['rating'] = ['You have already rated this property.']
            return cls(success=False, errors=errors)
        
        # Check if user has completed a transaction for this property
        # Skip this check for staff members
        if not user.is_staff:
            try:
                from ..models.transaction import Transaction
                has_transaction = Transaction.objects.filter(
                    property=property_obj,
                    buyer__user=user,
                    status='completed'
                ).exists()
                
                if not has_transaction:
                    errors['permission'] = [
                        'You must have completed a transaction to rate this property.'
                    ]
                    return cls(success=False, errors=errors)
            except ImportError:
                # Transaction model not found - skip check
                pass
        
        try:
            # Create property rating
            property_rating = PropertyRating.objects.create(
                property=property_obj,
                user=user,
                rating=rating,
                review=review,
            )
            
            # Update property average rating
            cls._update_property_average_rating(property_obj)
            
            return cls(
                property_rating=property_rating,
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
    def _update_property_average_rating(cls, property_obj):
        """
        Update the property's average rating.
        
        Args:
            property_obj: The property to update
        """
        from django.db.models import Avg
        
        avg_rating = PropertyRating.objects.filter(
            property=property_obj
        ).aggregate(avg=Avg('rating'))['avg']
        
        if avg_rating is not None:
            property_obj.average_rating = round(avg_rating, 2)
            property_obj.save(update_fields=['average_rating'])


# =============================================================================
# Update Property Rating Mutation
# =============================================================================

class UpdatePropertyRatingMutation(relay.ClientIDMutation):
    """
    Update an existing property rating.
    
    Allows users to update their rating or review.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        review = graphene.String(required=False)
    
    property_rating = graphene.Field(PropertyRatingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing property rating.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyRatingUpdateInput data
        
        Returns:
            UpdatePropertyRatingMutation instance
        """
        errors = {}
        
        # Extract input
        rating_id = input.get('id')
        rating = input.get('rating')
        review = input.get('review')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve property rating
        try:
            pk = from_global_id(rating_id)[1]
            property_rating = PropertyRating.objects.get(pk=pk)
        except PropertyRating.DoesNotExist:
            errors['id'] = ['Property rating not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the rating owner or staff can update
        if property_rating.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this rating.']
            return cls(success=False, errors=errors)
        
        # Validate rating if provided
        if rating is not None and (rating < 1 or rating > 5):
            errors['rating'] = ['Rating must be between 1 and 5.']
            return cls(success=False, errors=errors)
        
        # Validate review length if provided
        if review is not None and len(review) > 2000:
            errors['review'] = ['Review cannot exceed 2000 characters.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if rating is not None:
                property_rating.rating = rating
            if review is not None:
                property_rating.review = review
            
            property_rating.full_clean()
            property_rating.save()
            
            # Update property average rating
            cls._update_property_average_rating(property_rating.property)
            
            return cls(
                property_rating=property_rating,
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
    def _update_property_average_rating(cls, property_obj):
        """
        Update the property's average rating.
        
        Args:
            property_obj: The property to update
        """
        from django.db.models import Avg
        
        avg_rating = PropertyRating.objects.filter(
            property=property_obj
        ).aggregate(avg=Avg('rating'))['avg']
        
        if avg_rating is not None:
            property_obj.average_rating = round(avg_rating, 2)
            property_obj.save(update_fields=['average_rating'])


# =============================================================================
# Delete Property Rating Mutation
# =============================================================================

class DeletePropertyRatingMutation(relay.ClientIDMutation):
    """
    Delete a property rating.
    
    Removes a rating and updates the property's average rating.
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
        Delete a property rating.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Rating ID to delete
        
        Returns:
            DeletePropertyRatingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve property rating
        try:
            pk = from_global_id(id)[1]
            property_rating = PropertyRating.objects.get(pk=pk)
        except PropertyRating.DoesNotExist:
            errors['id'] = ['Property rating not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the rating owner or staff can delete
        if property_rating.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this rating.']
            return cls(success=False, errors=errors)
        
        try:
            property_obj = property_rating.property
            deleted_id = id
            
            property_rating.delete()
            
            # Update property average rating
            cls._update_property_average_rating(property_obj)
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)
    
    @classmethod
    def _update_property_average_rating(cls, property_obj):
        """
        Update the property's average rating.
        
        Args:
            property_obj: The property to update
        """
        from django.db.models import Avg
        
        avg_rating = PropertyRating.objects.filter(
            property=property_obj
        ).aggregate(avg=Avg('rating'))['avg']
        
        if avg_rating is not None:
            property_obj.average_rating = round(avg_rating, 2)
        else:
            property_obj.average_rating = None
        
        property_obj.save(update_fields=['average_rating'])


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreatePropertyRatingsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple property ratings.
    
    Allows creating multiple ratings at once.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        review = graphene.String(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create property ratings.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ratings: List of rating inputs
        
        Returns:
            BulkCreatePropertyRatingsMutation instance
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
        
        for idx, rating_input in enumerate(ratings):
            try:
                # Use the create mutation for each rating
                result = CreatePropertyRatingMutation.mutate_and_get_payload(
                    root, info, rating_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'rating_id': result.property_rating.id if result.property_rating else None,
                    })
                else:
                    failure_count += 1
                    errors[f'rating_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'rating_{idx}'] = [str(e)]
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


class BulkDeletePropertyRatingsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple property ratings.
    
    Allows deleting multiple ratings at once.
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
        Bulk delete property ratings.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of rating IDs to delete
        
        Returns:
            BulkDeletePropertyRatingsMutation instance
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
        
        # Track properties that need average update
        properties_to_update = set()
        
        for rating_id in ids:
            try:
                pk = from_global_id(rating_id)[1]
                property_rating = PropertyRating.objects.get(pk=pk)
                
                # Check permission
                if property_rating.user != user and not user.is_staff:
                    errors[rating_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                # Track property for average update
                properties_to_update.add(property_rating.property_id)
                
                property_rating.delete()
                deleted_ids.append(rating_id)
                success_count += 1
                
            except PropertyRating.DoesNotExist:
                errors[rating_id] = ['Property rating not found.']
                failure_count += 1
            except Exception as e:
                errors[rating_id] = [str(e)]
                failure_count += 1
        
        # Update average ratings for affected properties
        for property_id in properties_to_update:
            try:
                property_obj = Listing.objects.get(pk=property_id)
                CreatePropertyRatingMutation._update_property_average_rating(property_obj)
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

class PropertyRatingMutations(graphene.ObjectType):
    """All property rating mutations."""
    
    # CRUD operations
    create_property_rating = CreatePropertyRatingMutation.Field()
    update_property_rating = UpdatePropertyRatingMutation.Field()
    delete_property_rating = DeletePropertyRatingMutation.Field()
    
    # Bulk operations
    bulk_create_property_ratings = BulkCreatePropertyRatingsMutation.Field()
    bulk_delete_property_ratings = BulkDeletePropertyRatingsMutation.Field()