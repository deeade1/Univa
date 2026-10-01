import logging
import graphene
from graphene import relay, Boolean, String, Field, ID, Decimal, Int
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from univa_jwt.decorators import login_required
from graphq.realestate.types.listing_category import ListingCategoryNode
from realestate.models import ListingCategory

logger = logging.getLogger(__name__)
 
class CreateListingCategory(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        parent_id = graphene.ID()
        description = graphene.JSONString()
    
    
    listing_category = graphene.Field(ListingCategoryNode)
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.has_perm('realestate.add_listingcategory'):
            raise GraphQLError("Permission denied")
        
        try:
            parent = None
            if 'parent_id' in input:
                parent_id = from_global_id(input['parent_id'])[1]
                parent = ListingCategory.objects.get(id=parent_id)
            
            listing_category = ListingCategory.objects.create(
                name=input['name'],
                slug=input['slug'],
                parent=parent,
                description=input.get('description'),
                background_image=info.context.FILES.get('background_image')
            )
            
            return cls(listing_category=listing_category)
        except Exception as e:
            logger.error(f"Error creating ListingCategory: {e}")
            raise GraphQLError("Failed to create category")

class UpdateListingCategory(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()
        parent_id = graphene.ID()
        description = graphene.JSONString()
        
    
    listing_category = graphene.Field(ListingCategoryNode)
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.has_perm('realestate.change_listingcategory'):
            raise GraphQLError("Permission denied")
        
        try:
            category_id = from_global_id(input['id'])[1]
            listing_category = ListingCategory.objects.get(id=category_id)
            
            if 'name' in input:
                listing_category.name = input['name']
            if 'slug' in input:
                listing_category.slug = input['slug']
            if 'parent_id' in input:
                if input['parent_id']:
                    parent_id = from_global_id(input['parent_id'])[1]
                    listing_category.parent = ListingCategory.objects.get(id=parent_id)
                else:
                    listing_category.parent = None
            if 'description' in input:
                listing_category.description = input['description']
            if 'background_image' in info.context.FILES:
                listing_category.background_image = info.context.FILES['background_image']
            
            listing_category.save()
            return cls(listing_category=listing_category)
        except Exception as e:
            logger.error(f"Error updating ListingCategory: {e}")
            raise GraphQLError("Failed to update category")

class DeleteListingCategory(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.has_perm('realestate.delete_listingcategory'):
            raise GraphQLError("Permission denied")
        
        try:
            category_id = from_global_id(input['id'])[1]
            listing_category = ListingCategory.objects.get(id=category_id)
            listing_category.delete()
            return cls(success=True)
        except Exception as e:
            logger.error(f"Error deleting ListingCategory: {e}")
            raise GraphQLError("Failed to delete category")        
    

class ListingCategoryMutations(graphene.ObjectType):
    create_listing_category = CreateListingCategory.Field()
    update_listing_category = UpdateListingCategory.Field()
    delete_listing_category = DeleteListingCategory.Field()