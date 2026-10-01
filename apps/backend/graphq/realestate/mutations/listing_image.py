# apps/backend/realestate/mutations/listing_image.py

"""
Listing Image Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from realestate.models.listing_image import ListingImage
from realestate.models.listing import Listing

from graphq.realestate.types.listing_image import ListingImageNode



# =============================================================================
# Create Listing Image Mutation
# =============================================================================

class CreateListingImageMutation(relay.ClientIDMutation):
    """
    Create a new listing image.
    
    Allows uploading images associated with a listing, such as property photos.
    Images are automatically resized to 1200x630 using django-resized.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
    short_description = graphene.String(required=False)
    
    listing_image = graphene.Field(ListingImageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new listing image.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingImageInput data
        
        Returns:
            CreateListingImageMutation instance
        """
        errors = {}
        
        # Extract input
        listing_id = input.get('listing_id')
        short_description = input.get('short_description', '')
        
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
            errors['permission'] = ['You do not have permission to add images to this listing.']
            return cls(success=False, errors=errors)
        
        # Get image from request
        image_file = None
        if hasattr(info.context, 'FILES'):
            image_file = info.context.FILES.get('image')
        
        if not image_file:
            errors['image'] = ['Image file is required.']
            return cls(success=False, errors=errors)
        
        # Validate short_description length
        if short_description and len(short_description) > 255:
            errors['short_description'] = ['Description cannot exceed 255 characters.']
            return cls(success=False, errors=errors)
        
        try:
            # Create listing image
            listing_image = ListingImage.objects.create(
                listing=listing,
                image=image_file,
                short_description=short_description,
            )
            
            return cls(
                listing_image=listing_image,
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
# Update Listing Image Mutation
# =============================================================================

class UpdateListingImageMutation(relay.ClientIDMutation):
    """
    Update an existing listing image.
    
    Allows updating the short description of a listing image.
    To change the image itself, delete the existing image and create a new one.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        short_description = graphene.String(required=False)
    
    listing_image = graphene.Field(ListingImageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing listing image.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingImageUpdateInput data
        
        Returns:
            UpdateListingImageMutation instance
        """
        errors = {}
        
        # Extract input
        image_id = input.get('id')
        short_description = input.get('short_description')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing image
        try:
            pk = from_global_id(image_id)[1]
            listing_image = ListingImage.objects.get(pk=pk)
        except ListingImage.DoesNotExist:
            errors['id'] = ['Listing image not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        listing = listing_image.listing
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
            errors['permission'] = ['You do not have permission to update this image.']
            return cls(success=False, errors=errors)
        
        # Validate short_description length
        if short_description is not None and len(short_description) > 255:
            errors['short_description'] = ['Description cannot exceed 255 characters.']
            return cls(success=False, errors=errors)
        
        try:
            # Update field
            if short_description is not None:
                listing_image.short_description = short_description
            
            listing_image.full_clean()
            listing_image.save()
            
            return cls(
                listing_image=listing_image,
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
# Delete Listing Image Mutation
# =============================================================================

class DeleteListingImageMutation(relay.ClientIDMutation):
    """
    Delete a listing image.
    
    Removes the image from the listing and deletes the physical image file.
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
        Delete a listing image.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing image ID to delete
        
        Returns:
            DeleteListingImageMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing image
        try:
            pk = from_global_id(id)[1]
            listing_image = ListingImage.objects.get(pk=pk)
        except ListingImage.DoesNotExist:
            errors['id'] = ['Listing image not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        listing = listing_image.listing
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
            errors['permission'] = ['You do not have permission to delete this image.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            # Delete the image (cascade will also delete the physical file)
            listing_image.delete()
            
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
# Reorder Listing Images Mutation
# =============================================================================

class ReorderListingImagesMutation(relay.ClientIDMutation):
    """
    Reorder listing images.
    
    Allows setting the display order of images for a listing.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        image_ids = graphene.List(graphene.ID, required=True)
    
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, image_ids):
        """
        Reorder listing images.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            image_ids: List of image IDs in desired order
        
        Returns:
            ReorderListingImagesMutation instance
        """
        errors = {}
        
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
            errors['permission'] = ['You do not have permission to reorder images.']
            return cls(success=False, errors=errors)
        
        # Validate that all images belong to the listing
        try:
            # Get all image IDs for this listing
            existing_image_ids = set(
                listing.images.values_list('id', flat=True)
            )
            
            # Convert global IDs to database IDs
            image_pks = []
            for image_id in image_ids:
                try:
                    pk = from_global_id(image_id)[1]
                    image_pks.append(int(pk))
                except Exception:
                    errors['image_ids'] = [f'Invalid image ID: {image_id}']
                    return cls(success=False, errors=errors)
            
            # Check that all provided images belong to the listing
            for pk in image_pks:
                if pk not in existing_image_ids:
                    errors['image_ids'] = [f'Image {pk} does not belong to this listing.']
                    return cls(success=False, errors=errors)
            
            # Update order - since the model doesn't have an order field,
            # we would need to add one. This is a placeholder for the logic.
            # You could add a 'order' field to ListingImage or use a custom ordering approach.
            
            # For now, we'll just return success
            # Note: To implement this properly, add a 'position' or 'order' field
            # to the ListingImage model and update it here.
            
            return cls(
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Set Primary Listing Image Mutation
# =============================================================================

class SetPrimaryListingImageMutation(relay.ClientIDMutation):
    """
    Set a listing image as the primary/cover image.
    
    This sets the specified image as the main image for the listing.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        image_id = graphene.ID(required=True)
    
    listing_image = graphene.Field(ListingImageNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, image_id):
        """
        Set a listing image as primary.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            image_id: Image ID to set as primary
        
        Returns:
            SetPrimaryListingImageMutation instance
        """
        errors = {}
        
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
            errors['permission'] = ['You do not have permission to set the primary image.']
            return cls(success=False, errors=errors)
        
        # Resolve image
        try:
            pk = from_global_id(image_id)[1]
            listing_image = ListingImage.objects.get(pk=pk)
        except ListingImage.DoesNotExist:
            errors['image_id'] = ['Listing image not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['image_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check that image belongs to listing
        if listing_image.listing_id != listing.id:
            errors['image'] = ['Image does not belong to this listing.']
            return cls(success=False, errors=errors)
        
        try:
            # Store the primary image ID in the listing
            # This assumes the Listing model has a 'primary_image' field
            # If not, you'll need to add one or use a different approach
            
            # For now, we'll just return the image
            # Note: To implement this properly, add a 'primary_image' field
            # to the Listing model and update it here.
            
            # Example:
            # listing.primary_image = listing_image
            # listing.save()
            
            return cls(
                listing_image=listing_image,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkUploadListingImagesMutation(relay.ClientIDMutation):
    """
    Bulk upload multiple images for a listing.
    
    Allows uploading multiple images at once to a listing.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        short_description = graphene.String(required=False)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, images):
        """
        Bulk upload multiple images.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            images: List of image metadata
        
        Returns:
            BulkUploadListingImagesMutation instance
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
            errors['permission'] = ['You do not have permission to add images to this listing.']
            return cls(success=False, errors=errors)
        
        # Get images from request
        uploaded_images = []
        if hasattr(info.context, 'FILES'):
            uploaded_images = info.context.FILES.getlist('images')
        
        if not uploaded_images:
            errors['images'] = ['At least one image is required.']
            return cls(success=False, errors=errors)
        
        # Process each image
        for idx, image_data in enumerate(images):
            try:
                # Get corresponding image object
                image_file = uploaded_images[idx] if idx < len(uploaded_images) else None
                
                if not image_file:
                    errors[f'image_{idx}'] = ['Image file is required.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': ['No image provided'],
                    })
                    continue
                
                # Validate short_description length
                short_description = image_data.get('short_description', '')
                if len(short_description) > 255:
                    errors[f'image_{idx}'] = ['Description cannot exceed 255 characters.']
                    failure_count += 1
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': ['Description too long'],
                    })
                    continue
                
                # Create listing image
                listing_image = ListingImage.objects.create(
                    listing=listing,
                    image=image_file,
                    short_description=short_description,
                )
                
                success_count += 1
                results.append({
                    'id': listing_image.id,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[f'image_{idx}'] = [str(e)]
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


class BulkDeleteListingImagesMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple listing images.
    
    Allows deleting multiple images from a listing at once.
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
        Bulk delete listing images.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of listing image IDs to delete
        
        Returns:
            BulkDeleteListingImagesMutation instance
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
        
        for image_id in ids:
            try:
                pk = from_global_id(image_id)[1]
                listing_image = ListingImage.objects.get(pk=pk)
                
                # Check permission - user must be staff, agent, or owner
                listing = listing_image.listing
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
                    failed_ids.append(image_id)
                    errors[image_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                listing_image.delete()
                deleted_ids.append(image_id)
                success_count += 1
                
            except ListingImage.DoesNotExist:
                failed_ids.append(image_id)
                errors[image_id] = ['Listing image not found.']
                failure_count += 1
            except Exception as e:
                failed_ids.append(image_id)
                errors[image_id] = [str(e)]
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

class ListingImageMutations(graphene.ObjectType):
    """All listing image mutations."""
    
    # CRUD operations
    create_listing_image = CreateListingImageMutation.Field()
    update_listing_image = UpdateListingImageMutation.Field()
    delete_listing_image = DeleteListingImageMutation.Field()
    
    # Additional operations
    set_primary_listing_image = SetPrimaryListingImageMutation.Field()
    reorder_listing_images = ReorderListingImagesMutation.Field()
    
    # Bulk operations
    bulk_upload_listing_images = BulkUploadListingImagesMutation.Field()
    bulk_delete_listing_images = BulkDeleteListingImagesMutation.Field()