# apps/backend/realestate/mutations/listing.py

"""
Listing Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphene_gis.scalars import PointScalar
from graphql_relay import from_global_id, to_global_id

import logging
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from realestate.models.listing import Listing
from realestate.models.listing_type import ListingType
from realestate.models.listing_category import ListingCategory
from realestate.models.listing_image import ListingImage
from realestate.models.agent import Agent
from realestate.models.neighborhood import Neighborhood
from accounts.models import Address
from graphq.realestate.types.listing import ListingNode

logger = logging.getLogger(__name__)

# =============================================================================
# Create Listing Mutation
# =============================================================================

class CreateListingMutation(relay.ClientIDMutation):
    """
    Create a new property listing.
    
    Creates a complete property listing with all related fields including
    location, features, pricing, and relationships.
    """
    
    class Input:
        # Required fields
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        listing_type_id = graphene.ID(required=True)
        property_area = graphene.String(required=True)
        price = graphene.Decimal(required=True)
        free_from = graphene.Date(required=True)
        
        # Address and location
        address_id = graphene.ID(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        
        # Basic property info
        property_status = graphene.String(required=False, default_value="draft")
        property_for = graphene.String(required=False, default_value="S")
        is_published = graphene.Boolean(required=False, default_value=False)
        
        # Location fields
        country = graphene.String(required=False)
        country_code = graphene.String(required=False)
        state_province = graphene.String(required=False)
        city = graphene.String(required=False)
        local_area = graphene.String(required=False)
        postal_code = graphene.String(required=False)
        estate_name = graphene.String(required=False)
        full_address = graphene.String(required=False)
        
        # Land-specific fields
        land_size = graphene.Float(required=False)
        land_unit = graphene.String(required=False)
        total_plots = graphene.Int(required=False)
        plots_available = graphene.Int(required=False)
        
        # Building-specific fields
        bedrooms = graphene.Int(required=False)
        bathrooms = graphene.Int(required=False)
        garage = graphene.Int(required=False, default_value=0)
        square_feet = graphene.Float(required=False)
        ceiling_height = graphene.Float(required=False)
        lot_size = graphene.Float(required=False)
        
        # Property condition
        property_condition = graphene.String(required=False, default_value="good")
        
        # Pricing
        price_metric = graphene.String(required=False, default_value="total_price")
        price_per_plot = graphene.Decimal(required=False)
        currency = graphene.String(required=False, default_value="USD")
        
        # Property details
        year_built = graphene.Int(required=False)
        slug = graphene.String(required=False)
        
        # Property features
        has_legal_documents = graphene.Boolean(required=False, default_value=False)
        is_gated_community = graphene.Boolean(required=False, default_value=False)
        has_road_access = graphene.Boolean(required=False, default_value=True)
        has_c_of_o = graphene.Boolean(required=False, default_value=False)
        has_governors_consent = graphene.Boolean(required=False, default_value=False)
        
        # Relationships
        agent_id = graphene.ID(required=False)
        owner_id = graphene.ID(required=False)
        reviewer_id = graphene.ID(required=False)
        property_category_id = graphene.ID(required=False)
    
    listing = graphene.Field(ListingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingInput data
        
        Returns:
            CreateListingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate required fields
        required_fields = ['title', 'description', 'listing_type_id', 'property_area', 'price', 'free_from']
        for field in required_fields:
            if not input.get(field):
                errors[field] = [f'{field} is required.']
                return cls(success=False, errors=errors)
        
        # Validate price
        if input.get('price') and input['price'] <= 0:
            errors['price'] = ['Price must be positive.']
            return cls(success=False, errors=errors)
        
        # Resolve listing type
        try:
            pk = from_global_id(input['listing_type_id'])[1]
            listing_type = ListingType.objects.get(pk=pk)
        except ListingType.DoesNotExist:
            errors['listing_type_id'] = ['Listing type not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_type_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Resolve address if provided
        address = None
        if input.get('address_id'):
            try:
                pk = from_global_id(input['address_id'])[1]
                address = Address.objects.get(pk=pk)
            except Address.DoesNotExist:
                errors['address_id'] = ['Address not found.']
                return cls(success=False, errors=errors)
        
        # Resolve agent if provided
        agent = None
        if input.get('agent_id'):
            try:
                pk = from_global_id(input['agent_id'])[1]
                agent = Agent.objects.get(pk=pk)
            except Agent.DoesNotExist:
                errors['agent_id'] = ['Agent not found.']
                return cls(success=False, errors=errors)
        
        # Resolve owner if provided
        owner = None
        if input.get('owner_id'):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(input['owner_id'])[1]
                owner = User.objects.get(pk=pk)
            except Exception as e:
                errors['owner_id'] = ['Owner not found.']
                return cls(success=False, errors=errors)
        
        # Resolve reviewer if provided
        reviewer = None
        if input.get('reviewer_id'):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(input['reviewer_id'])[1]
                reviewer = User.objects.get(pk=pk)
            except Exception as e:
                errors['reviewer_id'] = ['Reviewer not found.']
                return cls(success=False, errors=errors)
        
        # Resolve property category if provided
        property_category = None
        if input.get('property_category_id'):
            try:
                pk = from_global_id(input['property_category_id'])[1]
                property_category = ListingCategory.objects.get(pk=pk)
            except ListingCategory.DoesNotExist:
                errors['property_category_id'] = ['Property category not found.']
                return cls(success=False, errors=errors)
        
        # Generate slug if not provided
        slug = input.get('slug')
        if not slug:
            slug = slugify(input['title'])
            counter = 1
            original_slug = slug
            while Listing.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Create location point
        location_point = None
        if input.get('latitude') and input.get('longitude'):
            try:
                location_point = Point(input['longitude'], input['latitude'], srid=4326)
            except Exception as e:
                errors['location'] = [f'Invalid coordinates: {str(e)}']
                return cls(success=False, errors=errors)
        
        try:
            # Create listing
            listing = Listing.objects.create(
                title=input['title'],
                description=input['description'],
                listing_type=listing_type,
                property_area=input['property_area'],
                price=input['price'],
                free_from=input['free_from'],
                address=address,
                agent=agent,
                owner=owner or user,
                reviewer=reviewer,
                property_category=property_category,
                slug=slug,
                property_status=input.get('property_status', 'draft'),
                property_for=input.get('property_for', 'S'),
                is_published=input.get('is_published', False),
                country=input.get('country'),
                country_code=input.get('country_code'),
                state_province=input.get('state_province'),
                city=input.get('city'),
                local_area=input.get('local_area'),
                postal_code=input.get('postal_code'),
                estate_name=input.get('estate_name'),
                full_address=input.get('full_address'),
                land_size=input.get('land_size'),
                land_unit=input.get('land_unit'),
                total_plots=input.get('total_plots'),
                plots_available=input.get('plots_available'),
                bedrooms=input.get('bedrooms'),
                bathrooms=input.get('bathrooms'),
                garage=input.get('garage', 0),
                square_feet=input.get('square_feet'),
                ceiling_height=input.get('ceiling_height'),
                lot_size=input.get('lot_size'),
                property_condition=input.get('property_condition', 'good'),
                price_metric=input.get('price_metric', 'total_price'),
                price_per_plot=input.get('price_per_plot'),
                currency=input.get('currency', 'USD'),
                year_built=input.get('year_built'),
                has_legal_documents=input.get('has_legal_documents', False),
                is_gated_community=input.get('is_gated_community', False),
                has_road_access=input.get('has_road_access', True),
                has_c_of_o=input.get('has_c_of_o', False),
                has_governors_consent=input.get('has_governors_consent', False),
                location_point=location_point,
            )
            
            return cls(
                listing=listing,
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
# Update Listing Mutation
# =============================================================================

class UpdateListingMutation(relay.ClientIDMutation):
    """
    Update an existing listing.
    
    Allows updating all fields of a listing including location,
    features, pricing, and relationships.
    """
    
    class Input:
        # Required fields
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        listing_type_id = graphene.ID(required=True)
        property_area = graphene.String(required=True)
        price = graphene.Decimal(required=True)
        free_from = graphene.Date(required=True)
        
        # Address and location
        address_id = graphene.ID(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        
        # Basic property info
        property_status = graphene.String(required=False, default_value="draft")
        property_for = graphene.String(required=False, default_value="S")
        is_published = graphene.Boolean(required=False, default_value=False)
        
        # Location fields
        country = graphene.String(required=False)
        country_code = graphene.String(required=False)
        state_province = graphene.String(required=False)
        city = graphene.String(required=False)
        local_area = graphene.String(required=False)
        postal_code = graphene.String(required=False)
        estate_name = graphene.String(required=False)
        full_address = graphene.String(required=False)
        
        # Land-specific fields
        land_size = graphene.Float(required=False)
        land_unit = graphene.String(required=False)
        total_plots = graphene.Int(required=False)
        plots_available = graphene.Int(required=False)
        
        # Building-specific fields
        bedrooms = graphene.Int(required=False)
        bathrooms = graphene.Int(required=False)
        garage = graphene.Int(required=False, default_value=0)
        square_feet = graphene.Float(required=False)
        ceiling_height = graphene.Float(required=False)
        lot_size = graphene.Float(required=False)
        
        # Property condition
        property_condition = graphene.String(required=False, default_value="good")
        
        # Pricing
        price_metric = graphene.String(required=False, default_value="total_price")
        price_per_plot = graphene.Decimal(required=False)
        currency = graphene.String(required=False, default_value="USD")
        
        # Property details
        year_built = graphene.Int(required=False)
        slug = graphene.String(required=False)
        
        # Property features
        has_legal_documents = graphene.Boolean(required=False, default_value=False)
        is_gated_community = graphene.Boolean(required=False, default_value=False)
        has_road_access = graphene.Boolean(required=False, default_value=True)
        has_c_of_o = graphene.Boolean(required=False, default_value=False)
        has_governors_consent = graphene.Boolean(required=False, default_value=False)
        
        # Relationships
        agent_id = graphene.ID(required=False)
        owner_id = graphene.ID(required=False)
        reviewer_id = graphene.ID(required=False)
        property_category_id = graphene.ID(required=False)
    
    listing = graphene.Field(ListingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ListingUpdateInput data
        
        Returns:
            UpdateListingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(input['id'])[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be owner, agent, or staff
        is_authorized = (
            user.is_staff or
            (listing.owner and listing.owner == user) or
            (listing.agent and listing.agent.profile and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to update this listing.']
            return cls(success=False, errors=errors)
        
        # Validate price
        if input.get('price') and input['price'] <= 0:
            errors['price'] = ['Price must be positive.']
            return cls(success=False, errors=errors)
        
        # Resolve related objects if provided
        if input.get('listing_type_id'):
            try:
                pk = from_global_id(input['listing_type_id'])[1]
                listing.listing_type = ListingType.objects.get(pk=pk)
            except ListingType.DoesNotExist:
                errors['listing_type_id'] = ['Listing type not found.']
                return cls(success=False, errors=errors)
        
        if input.get('address_id'):
            try:
                pk = from_global_id(input['address_id'])[1]
                listing.address = Address.objects.get(pk=pk)
            except Address.DoesNotExist:
                errors['address_id'] = ['Address not found.']
                return cls(success=False, errors=errors)
        
        if input.get('agent_id'):
            try:
                pk = from_global_id(input['agent_id'])[1]
                listing.agent = Agent.objects.get(pk=pk)
            except Agent.DoesNotExist:
                errors['agent_id'] = ['Agent not found.']
                return cls(success=False, errors=errors)
        
        if input.get('owner_id'):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(input['owner_id'])[1]
                listing.owner = User.objects.get(pk=pk)
            except Exception as e:
                errors['owner_id'] = ['Owner not found.']
                return cls(success=False, errors=errors)
        
        if input.get('reviewer_id'):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(input['reviewer_id'])[1]
                listing.reviewer = User.objects.get(pk=pk)
            except Exception as e:
                errors['reviewer_id'] = ['Reviewer not found.']
                return cls(success=False, errors=errors)
        
        if input.get('property_category_id'):
            try:
                pk = from_global_id(input['property_category_id'])[1]
                listing.property_category = ListingCategory.objects.get(pk=pk)
            except ListingCategory.DoesNotExist:
                errors['property_category_id'] = ['Property category not found.']
                return cls(success=False, errors=errors)
        
        # Update slug if title changed
        if input.get('title') and input.get('title') != listing.title:
            new_slug = slugify(input['title'])
            counter = 1
            original_slug = new_slug
            while Listing.objects.filter(slug=new_slug).exclude(pk=listing.pk).exists():
                new_slug = f"{original_slug}-{counter}"
                counter += 1
            listing.slug = new_slug
        
        # Update location
        if input.get('latitude') and input.get('longitude'):
            try:
                listing.location_point = Point(input['longitude'], input['latitude'], srid=4326)
            except Exception as e:
                errors['location'] = [f'Invalid coordinates: {str(e)}']
                return cls(success=False, errors=errors)
        
        # Update fields
        updatable_fields = [
            'title', 'description', 'price', 'property_area',
            'property_status', 'property_for', 'is_published', 'free_from',
            'country', 'country_code', 'state_province', 'city',
            'local_area', 'postal_code', 'estate_name', 'full_address',
            'land_size', 'land_unit', 'total_plots', 'plots_available',
            'bedrooms', 'bathrooms', 'garage', 'square_feet',
            'ceiling_height', 'lot_size', 'property_condition',
            'price_metric', 'price_per_plot', 'currency', 'year_built',
            'has_legal_documents', 'is_gated_community', 'has_road_access',
            'has_c_of_o', 'has_governors_consent'
        ]
        
        for field in updatable_fields:
            if field in input and input[field] is not None:
                setattr(listing, field, input[field])
        
        try:
            listing.full_clean()
            listing.save()
            
            return cls(
                listing=listing,
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
# Delete Listing Mutation
# =============================================================================

class DeleteListingMutation(relay.ClientIDMutation):
    """
    Delete a listing.
    
    Removes a property listing and all associated files and images.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force deletion even if there are active transactions"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing ID to delete
            force: Force deletion even if there are active transactions
        
        Returns:
            DeleteListingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_authorized = (
            user.is_staff or
            (listing.owner and listing.owner == user) or
            (listing.agent and listing.agent.profile and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to delete this listing.']
            return cls(success=False, errors=errors)
        
        # Check if listing has active transactions
        if not force:
            try:
                from ..models.transaction import Transaction
                if Transaction.objects.filter(listing=listing, status__in=['pending', 'active']).exists():
                    errors['in_use'] = [
                        'Cannot delete listing with active transactions. '
                        'Use force=True to override.'
                    ]
                    return cls(success=False, errors=errors)
            except ImportError:
                pass
        
        try:
            deleted_id = id
            listing.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Publish Listing Mutation
# =============================================================================

class PublishListingMutation(relay.ClientIDMutation):
    """
    Publish a listing.
    
    Changes the listing status to 'published' and makes it visible to the public.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    listing = graphene.Field(ListingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Publish a listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing ID to publish
        
        Returns:
            PublishListingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_authorized = (
            user.is_staff or
            (listing.owner and listing.owner == user) or
            (listing.agent and listing.agent.profile and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to publish this listing.']
            return cls(success=False, errors=errors)
        
        try:
            listing.is_published = True
            listing.property_status = 'published'
            listing.save()
            
            return cls(
                listing=listing,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Unpublish Listing Mutation
# =============================================================================

class UnpublishListingMutation(relay.ClientIDMutation):
    """
    Unpublish a listing.
    
    Changes the listing status to 'draft' and hides it from public view.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    listing = graphene.Field(ListingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Unpublish a listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Listing ID to unpublish
        
        Returns:
            UnpublishListingMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['id'] = ['Listing not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_authorized = (
            user.is_staff or
            (listing.owner and listing.owner == user) or
            (listing.agent and listing.agent.profile and 
             hasattr(listing.agent.profile, 'user') and 
             listing.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to unpublish this listing.']
            return cls(success=False, errors=errors)
        
        try:
            listing.is_published = False
            listing.property_status = 'draft'
            listing.save()
            
            return cls(
                listing=listing,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Check Listing Compliance Mutation
# =============================================================================

class CheckListingComplianceMutation(relay.ClientIDMutation):
    """
    Check listing compliance.
    
    Validates that a listing meets all requirements for publication.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
    
    is_compliant = graphene.Boolean()
    issues = graphene.JSONString()
    compliance_score = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id):
        """
        Check listing compliance.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID to check
        
        Returns:
            CheckListingComplianceMutation instance
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
        
        try:
            issues = []
            
            # Check required fields
            if not listing.title:
                issues.append({'issue': 'Title is required', 'severity': 'high'})
            
            if not listing.description:
                issues.append({'issue': 'Description is required', 'severity': 'high'})
            
            if not listing.price or listing.price <= 0:
                issues.append({'issue': 'Valid price is required', 'severity': 'high'})
            
            # Check location
            if not listing.location_point:
                issues.append({'issue': 'Location coordinates are required', 'severity': 'high'})
            
            # Check listing type requirements
            if listing.listing_type:
                if listing.listing_type.requires_land_details and not listing.land_size:
                    issues.append({'issue': 'Land size is required for this property type', 'severity': 'medium'})
                
                if listing.listing_type.requires_building_details and not listing.square_feet:
                    issues.append({'issue': 'Square footage is required for this property type', 'severity': 'medium'})
            
            # Check for duplicate listings
            if Listing.objects.filter(
                title__iexact=listing.title,
                location_point__isnull=False
            ).exclude(pk=listing.pk).exists():
                issues.append({'issue': 'Similar listing may already exist', 'severity': 'low'})
            
            # Calculate compliance score
            compliance_score = max(0, 100 - (len(issues) * 10))
            is_compliant = len(issues) == 0
            
            return cls(
                is_compliant=is_compliant,
                issues=issues,
                compliance_score=compliance_score,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class ListingMutations(graphene.ObjectType):
    """All listing mutations."""
    
    # CRUD operations
    create_listing = CreateListingMutation.Field()
    update_listing = UpdateListingMutation.Field()
    delete_listing = DeleteListingMutation.Field()
    
    # Publishing
    publish_listing = PublishListingMutation.Field()
    unpublish_listing = UnpublishListingMutation.Field()
    
    # Compliance
    check_listing_compliance = CheckListingComplianceMutation.Field()