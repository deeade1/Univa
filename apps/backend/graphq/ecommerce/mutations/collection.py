# apps/backend/ecommerce/mutations/collection.py

"""
Collection Mutations for Relay GraphQL API.
"""

import graphene
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id
from graphene import relay
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from ecommerce.models.collection import Collection, CollectionProduct, CollectionTranslation, CollectionChannelListing
from ecommerce.models.product import Product
from ecommerce.models.channel import Channel

from graphq.ecommerce.types.collection import CollectionNode, CollectionChannelListingNode


# =============================================================================
# Create Collection Mutation
# =============================================================================

class CreateCollectionMutation(relay.ClientIDMutation):
    """Create a new collection."""
    
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=False)
        description = graphene.JSONString(required=False)
        background_image = graphene.String(required=False)
        background_image_alt = graphene.String(required=False)
        products = graphene.String(required=False)
        channel_listings = graphene.String(required=False)
        translations = graphene.String(required=False)

    
    collection = graphene.Field(CollectionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new collection with products, channel listings, and translations.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CollectionInput data
        
        Returns:
            CreateCollectionMutation instance
        """
        errors = {}
        
        # Extract input data
        name = input.get('name')
        slug = input.get('slug')
        description = input.get('description')
        background_image = input.get('background_image')
        background_image_alt = input.get('background_image_alt')
        products_data = input.get('products', [])
        channel_listings_data = input.get('channel_listings', [])
        translations_data = input.get('translations', [])
        
        # Validate required fields
        if not name:
            errors['name'] = ['This field is required.']
            return cls(success=False, errors=errors)
        
        # Auto-generate slug if not provided
        if not slug:
            slug = slugify(name)
        
        # Check slug uniqueness
        if Collection.objects.filter(slug=slug).exists():
            errors['slug'] = ['Collection with this slug already exists.']
            return cls(success=False, errors=errors)
        
        try:
            # Create collection
            collection = Collection.objects.create(
                name=name,
                slug=slug,
                description=description or {},
                background_image=background_image,
                background_image_alt=background_image_alt or '',
            )
            
            # Add products through the through model
            for product_data in products_data:
                product_id = product_data.get('product_id')
                sort_order = product_data.get('sort_order', 0)
                
                try:
                    pk = from_global_id(product_id)[1]
                    product = Product.objects.get(pk=pk)
                    
                    CollectionProduct.objects.create(
                        collection=collection,
                        product=product,
                        sort_order=sort_order,
                    )
                except Product.DoesNotExist:
                    errors.setdefault('products', []).append(
                        f'Product with ID {product_id} not found.'
                    )
                except Exception as e:
                    errors.setdefault('products', []).append(str(e))
            
            # Create channel listings
            for listing_data in channel_listings_data:
                channel_id = listing_data.get('channel_id')
                is_published = listing_data.get('is_published', False)
                published_at = listing_data.get('published_at')
                
                try:
                    pk = from_global_id(channel_id)[1]
                    channel = Channel.objects.get(pk=pk)
                    
                    CollectionChannelListing.objects.create(
                        collection=collection,
                        channel=channel,
                        is_published=is_published,
                        published_at=published_at,
                    )
                except Channel.DoesNotExist:
                    errors.setdefault('channel_listings', []).append(
                        f'Channel with ID {channel_id} not found.'
                    )
                except Exception as e:
                    errors.setdefault('channel_listings', []).append(str(e))
            
            # Create translations
            for translation_data in translations_data:
                language_code = translation_data.get('language_code')
                trans_name = translation_data.get('name')
                trans_description = translation_data.get('description')
                trans_slug = translation_data.get('slug')
                
                if not language_code:
                    continue
                
                # Auto-generate translation slug if not provided
                if not trans_slug and trans_name:
                    trans_slug = slugify(trans_name)
                
                CollectionTranslation.objects.create(
                    collection=collection,
                    language_code=language_code,
                    name=trans_name or name,
                    description=trans_description or description,
                    slug=trans_slug or slug,
                )
            
            # Return success response
            return cls(
                collection=collection,
                success=True,
                errors=errors
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Collection Mutation
# =============================================================================

class UpdateCollectionMutation(relay.ClientIDMutation):
    """Update an existing collection."""
    
    class Input:
        language_code = graphene.String(required=True)
        name = graphene.String(required=False)
        description = graphene.JSONString(required=False)
        slug = graphene.String(required=False)
      
    
    collection = graphene.Field(CollectionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing collection.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateCollectionInput data
        
        Returns:
            UpdateCollectionMutation instance
        """
        errors = {}
        
        # Extract input
        collection_id = input.get('id')
        name = input.get('name')
        slug = input.get('slug')
        description = input.get('description')
        background_image = input.get('background_image')
        background_image_alt = input.get('background_image_alt')
        products_data = input.get('products')
        channel_listings_data = input.get('channel_listings')
        translations_data = input.get('translations')
        replace_products = input.get('replace_products', False)
        replace_channel_listings = input.get('replace_channel_listings', False)
        replace_translations = input.get('replace_translations', False)
        
        # Resolve collection ID
        try:
            pk = from_global_id(collection_id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate slug uniqueness (if changed)
        if slug and slug != collection.slug:
            if Collection.objects.filter(slug=slug).exclude(pk=pk).exists():
                errors['slug'] = ['Collection with this slug already exists.']
                return cls(success=False, errors=errors)
        
        try:
            # Update collection fields
            if name is not None:
                collection.name = name
            if slug is not None:
                collection.slug = slug
            if description is not None:
                collection.description = description
            if background_image is not None:
                collection.background_image = background_image
            if background_image_alt is not None:
                collection.background_image_alt = background_image_alt
            
            collection.save()
            
            # Update products
            if products_data is not None:
                if replace_products:
                    # Replace all products
                    collection.products.clear()
                
                # Add or update products
                for product_data in products_data:
                    product_id = product_data.get('product_id')
                    sort_order = product_data.get('sort_order', 0)
                    
                    try:
                        pk = from_global_id(product_id)[1]
                        product = Product.objects.get(pk=pk)
                        
                        # Check if product already exists in collection
                        collection_product, created = CollectionProduct.objects.get_or_create(
                            collection=collection,
                            product=product,
                            defaults={'sort_order': sort_order}
                        )
                        
                        if not created and sort_order is not None:
                            collection_product.sort_order = sort_order
                            collection_product.save()
                            
                    except Product.DoesNotExist:
                        errors.setdefault('products', []).append(
                            f'Product with ID {product_id} not found.'
                        )
                    except Exception as e:
                        errors.setdefault('products', []).append(str(e))
            
            # Update channel listings
            if channel_listings_data is not None:
                if replace_channel_listings:
                    # Replace all channel listings
                    collection.channel_listings.all().delete()
                
                # Add or update channel listings
                for listing_data in channel_listings_data:
                    channel_id = listing_data.get('channel_id')
                    is_published = listing_data.get('is_published', False)
                    published_at = listing_data.get('published_at')
                    
                    try:
                        pk = from_global_id(channel_id)[1]
                        channel = Channel.objects.get(pk=pk)
                        
                        # Check if listing already exists
                        listing, created = CollectionChannelListing.objects.get_or_create(
                            collection=collection,
                            channel=channel,
                            defaults={
                                'is_published': is_published,
                                'published_at': published_at,
                            }
                        )
                        
                        if not created:
                            listing.is_published = is_published
                            if published_at is not None:
                                listing.published_at = published_at
                            listing.save()
                            
                    except Channel.DoesNotExist:
                        errors.setdefault('channel_listings', []).append(
                            f'Channel with ID {channel_id} not found.'
                        )
                    except Exception as e:
                        errors.setdefault('channel_listings', []).append(str(e))
            
            # Update translations
            if translations_data is not None:
                if replace_translations:
                    # Replace all translations
                    collection.translations.all().delete()
                
                # Add or update translations
                for translation_data in translations_data:
                    language_code = translation_data.get('language_code')
                    trans_name = translation_data.get('name')
                    trans_description = translation_data.get('description')
                    trans_slug = translation_data.get('slug')
                    
                    if not language_code:
                        continue
                    
                    # Auto-generate translation slug if not provided
                    if not trans_slug and trans_name:
                        trans_slug = slugify(trans_name)
                    
                    # Check if translation already exists
                    translation, created = CollectionTranslation.objects.get_or_create(
                        collection=collection,
                        language_code=language_code,
                        defaults={
                            'name': trans_name or collection.name,
                            'description': trans_description or collection.description,
                            'slug': trans_slug or collection.slug,
                        }
                    )
                    
                    if not created:
                        if trans_name is not None:
                            translation.name = trans_name
                        if trans_description is not None:
                            translation.description = trans_description
                        if trans_slug is not None:
                            translation.slug = trans_slug
                        translation.save()
            
            # Return success response
            return cls(
                collection=collection,
                success=True,
                errors=errors
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Collection Mutation
# =============================================================================

class DeleteCollectionMutation(relay.ClientIDMutation):
    """Delete a collection."""
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Delete a collection.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Collection ID to delete
        
        Returns:
            DeleteCollectionMutation instance
        """
        errors = {}
        
        # Resolve collection ID
        try:
            pk = from_global_id(id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Delete the collection (cascades to related models)
            deleted_id = id
            collection.delete()
            
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
# Add Products to Collection Mutation
# =============================================================================

class AddProductsToCollectionMutation(relay.ClientIDMutation):
    """Add products to an existing collection."""
    
    class Input:
        collection_id = graphene.ID(required=True)
        products = graphene.String(required=True)
        product_id = graphene.ID(required=True)
        sort_order = graphene.Int(required=False, default_value=0)
    
    collection = graphene.Field(CollectionNode)
    added_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, collection_id, products):
        """
        Add products to a collection.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            collection_id: Collection ID
            products: List of products to add
        
        Returns:
            AddProductsToCollectionMutation instance
        """
        errors = {}
        added_count = 0
        
        # Resolve collection
        try:
            pk = from_global_id(collection_id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['collection_id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['collection_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            for product_data in products:
                product_id = product_data.get('product_id')
                sort_order = product_data.get('sort_order', 0)
                
                try:
                    pk = from_global_id(product_id)[1]
                    product = Product.objects.get(pk=pk)
                    
                    # Check if product already exists in collection
                    _, created = CollectionProduct.objects.get_or_create(
                        collection=collection,
                        product=product,
                        defaults={'sort_order': sort_order}
                    )
                    
                    if created:
                        added_count += 1
                        
                except Product.DoesNotExist:
                    errors.setdefault('products', []).append(
                        f'Product with ID {product_id} not found.'
                    )
                except Exception as e:
                    errors.setdefault('products', []).append(str(e))
            
            return cls(
                collection=collection,
                added_count=added_count,
                success=len(errors) == 0,
                errors=errors
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Remove Products from Collection Mutation
# =============================================================================

class RemoveProductsFromCollectionMutation(relay.ClientIDMutation):
    """Remove products from a collection."""
    
    class Input:
        collection_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
    
    collection = graphene.Field(CollectionNode)
    removed_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, collection_id, product_ids):
        """
        Remove products from a collection.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            collection_id: Collection ID
            product_ids: List of product IDs to remove
        
        Returns:
            RemoveProductsFromCollectionMutation instance
        """
        errors = {}
        removed_count = 0
        
        # Resolve collection
        try:
            pk = from_global_id(collection_id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['collection_id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['collection_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            for product_id in product_ids:
                try:
                    pk = from_global_id(product_id)[1]
                    
                    # Delete the CollectionProduct relation
                    deleted, _ = CollectionProduct.objects.filter(
                        collection=collection,
                        product_id=pk
                    ).delete()
                    
                    if deleted > 0:
                        removed_count += 1
                        
                except Exception as e:
                    errors.setdefault('product_ids', []).append(
                        f'Error removing product {product_id}: {str(e)}'
                    )
            
            return cls(
                collection=collection,
                removed_count=removed_count,
                success=len(errors) == 0,
                errors=errors
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Reorder Products in Collection Mutation
# =============================================================================

class ReorderCollectionProductsMutation(relay.ClientIDMutation):
    """Reorder products within a collection."""
    
    class Input:
        collection_id = graphene.ID(required=True)
        product_orders = graphene.String(required=True)
    
    collection = graphene.Field(CollectionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Reorder products within a collection.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            collection_id: Collection ID
            product_orders: List of product IDs with new sort orders
        
        Returns:
            ReorderCollectionProductsMutation instance
        """
        errors = {}
        
        # Resolve collection
        try:
            pk = from_global_id(collection_id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['collection_id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['collection_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            for order_data in product_orders:
                product_id = order_data.get('product_id')
                sort_order = order_data.get('sort_order')
                
                try:
                    pk = from_global_id(product_id)[1]
                    
                    # Update sort order
                    updated = CollectionProduct.objects.filter(
                        collection=collection,
                        product_id=pk
                    ).update(sort_order=sort_order)
                    
                    if updated == 0:
                        errors.setdefault('product_orders', []).append(
                            f'Product {product_id} not found in this collection.'
                        )
                        
                except Exception as e:
                    errors.setdefault('product_orders', []).append(
                        f'Error updating product {product_id}: {str(e)}'
                    )
            
            return cls(
                collection=collection,
                success=len(errors) == 0,
                errors=errors
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Collection Channel Listing Mutation
# =============================================================================

class UpdateCollectionChannelListingMutation(relay.ClientIDMutation):
    """Update channel listing for a collection."""
    
    class Input:
        collection_id = graphene.ID(required=True)
        channel_id = graphene.ID(required=True)
        is_published = graphene.Boolean(required=False)
        published_at = graphene.DateTime(required=False)
    
    channel_listing = graphene.Field(CollectionChannelListingNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update a collection channel listing.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            collection_id: Collection ID
            channel_id: Channel ID
            kwargs: Fields to update
        
        Returns:
            UpdateCollectionChannelListingMutation instance
        """
        errors = {}
        
        # Resolve collection
        try:
            pk = from_global_id(collection_id)[1]
            collection = Collection.objects.get(pk=pk)
        except Collection.DoesNotExist:
            errors['collection_id'] = ['Collection not found.']
            return cls(success=False, errors=errors)
        
        # Resolve channel
        try:
            pk = from_global_id(channel_id)[1]
            channel = Channel.objects.get(pk=pk)
        except Channel.DoesNotExist:
            errors['channel_id'] = ['Channel not found.']
            return cls(success=False, errors=errors)
        
        try:
            # Get or create listing
            listing, created = CollectionChannelListing.objects.get_or_create(
                collection=collection,
                channel=channel
            )
            
            # Update fields
            if 'is_published' in kwargs:
                listing.is_published = kwargs['is_published']
            if 'published_at' in kwargs:
                listing.published_at = kwargs['published_at']
            
            listing.save()
            
            return cls(
                channel_listing=listing,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Batch Delete Collections Mutation
# =============================================================================

class BulkDeleteCollectionsMutation(relay.ClientIDMutation):
    """Bulk delete multiple collections."""
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
    
    deleted_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids):
        """
        Delete multiple collections in bulk.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of collection IDs to delete
        
        Returns:
            BulkDeleteCollectionsMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        
        for collection_id in ids:
            try:
                pk = from_global_id(collection_id)[1]
                collection = Collection.objects.get(pk=pk)
                
                deleted_ids.append(collection_id)
                collection.delete()
                
            except Collection.DoesNotExist:
                failed_ids.append(collection_id)
                errors[collection_id] = ['Collection not found.']
            except Exception as e:
                failed_ids.append(collection_id)
                errors[collection_id] = [str(e)]
        
        success = len(failed_ids) == 0
        
        return cls(
            deleted_ids=deleted_ids,
            success=success,
            errors=errors if not success else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class CollectionMutations(graphene.ObjectType):
    """All collection mutations."""
    
    create_collection = CreateCollectionMutation.Field()
    update_collection = UpdateCollectionMutation.Field()
    delete_collection = DeleteCollectionMutation.Field()
    
    add_products_to_collection = AddProductsToCollectionMutation.Field()
    remove_products_from_collection = RemoveProductsFromCollectionMutation.Field()
    reorder_collection_products = ReorderCollectionProductsMutation.Field()
    
    update_collection_channel_listing = UpdateCollectionChannelListingMutation.Field()
    
    bulk_delete_collections = BulkDeleteCollectionsMutation.Field()