# graphql/ecommerce/types/collection.py

"""
GraphQL Nodes for Collection, CollectionProduct, CollectionChannelListing, and CollectionTranslation.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.collection import (
    Collection,
    CollectionProduct,
    CollectionChannelListing,
    CollectionTranslation,
)




class CollectionProductNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for CollectionProduct (through model for Collection -> Product).
    """
    
    class Meta:
        model = CollectionProduct
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'collection': ['exact'],
            'product': ['exact'],
            'sort_order': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_collection_details(self, info):
        """Resolve collection details."""
        return self.collection
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product


class CollectionChannelListingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for CollectionChannelListing.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_published_display = String(description="Human-readable published status display")
    is_visible = Boolean(description="Whether collection is visible in this channel")
    
    class Meta:
        model = CollectionChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'collection': ['exact'],
            'channel': ['exact'],
            'is_published': ['exact'],
            'published_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_is_published_display(self, info):
        """Resolve human-readable published status display."""
        return "Published" if self.is_published else "Unpublished"
    
    def resolve_is_visible(self, info):
        """Resolve whether collection is visible in this channel."""
        return self.is_published and self.collection.is_active if hasattr(self.collection, 'is_active') else self.is_published
    
    def resolve_collection_details(self, info):
        """Resolve collection details."""
        return self.collection
    
    def resolve_channel_details(self, info):
        """Resolve channel details."""
        return self.channel


class CollectionTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Collection Translation.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    has_name = Boolean(description="Whether translation has a name")
    has_description = Boolean(description="Whether translation has a description")
    description_plaintext = String(description="Plain text version of description")
    
     
    class Meta:
        model = CollectionTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'collection': ['exact'],
            
            # String fields
            'language_code': ['exact'],
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            
            # SEO fields
            'seo_title': ['exact', 'icontains'],
            'seo_description': ['exact', 'icontains'],
        }
        
    
    def resolve_has_name(self, info):
        """Resolve whether translation has a name."""
        return bool(self.name)
    
    def resolve_has_description(self, info):
        """Resolve whether translation has a description."""
        return bool(self.description)
    
    def resolve_description_plaintext(self, info):
        """Resolve plain text version of description."""
        if self.description:
            try:
                import json
                if isinstance(self.description, dict):
                    blocks = self.description.get('blocks', [])
                    texts = []
                    for block in blocks:
                        if block.get('type') == 'paragraph':
                            data = block.get('data', {})
                            if data.get('text'):
                                texts.append(data['text'])
                    return ' '.join(texts)
            except:
                pass
        return None
    
    


class CollectionNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Collection with full collection management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    product_count = Int(description="Number of products in this collection")
    is_active = Boolean(description="Whether collection has any published channel listings")
    has_products = Boolean(description="Whether collection has products")
    is_empty = Boolean(description="Whether collection has no products")
    description_plaintext = String(description="Plain text version of description")
    channel_availability_count = Int(description="Number of channels this collection is available on")
    published_channels = List(String, description="List of channel slugs where collection is published")
    
    
    class Meta:
        model = Collection
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            # foreignkey fields
            'products': ['exact'],
            
            
            
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_product_count(self, info):
        """Resolve number of products in this collection."""
        return self.products.count()
    
    def resolve_is_active(self, info):
        """Resolve whether collection has any published channel listings."""
        return self.channel_listings.filter(is_published=True).exists()
    
    def resolve_has_products(self, info):
        """Resolve whether collection has products."""
        return self.products.exists()
    
    def resolve_is_empty(self, info):
        """Resolve whether collection has no products."""
        return not self.products.exists()
    
    def resolve_description_plaintext(self, info):
        """Resolve plain text version of description."""
        if self.description:
            try:
                import json
                if isinstance(self.description, dict):
                    blocks = self.description.get('blocks', [])
                    texts = []
                    for block in blocks:
                        if block.get('type') == 'paragraph':
                            data = block.get('data', {})
                            if data.get('text'):
                                texts.append(data['text'])
                    return ' '.join(texts)
            except:
                pass
        return None
    
    def resolve_channel_availability_count(self, info):
        """Resolve number of channels this collection is available on."""
        return self.channel_listings.filter(is_published=True).count()
    
    def resolve_published_channels(self, info):
        """Resolve list of channel slugs where collection is published."""
        return list(
            self.channel_listings.filter(is_published=True)
            .values_list('channel__slug', flat=True)
        )
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_products(self, info):
        """Resolve products in this collection."""
        return self.products.all()
    
    def resolve_channel_listings(self, info):
        """Resolve channel listings for this collection."""
        return self.channel_listings.all()
    
    def resolve_translations(self, info):
        """Resolve collection translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve collection translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()
    
    def resolve_collection_products(self, info):
        """Resolve collection product relationships."""
        return self.collectionproduct.all()

