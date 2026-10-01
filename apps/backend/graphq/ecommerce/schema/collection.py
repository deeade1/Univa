import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.collection import ( 
    CollectionNode,
    CollectionProductNode,
    CollectionChannelListingNode,
    CollectionTranslationNode,
    
)

# =============================================================================
# Schema Registration
# =============================================================================

# In your schema.py, you would register these nodes:
#
class CollectionQuery(graphene.ObjectType):
    # Node queries
    collection = Node.Field(CollectionNode)
    all_collections = DjangoFilterConnectionField(CollectionNode)
    collection_product = Node.Field(CollectionProductNode)
    all_collection_products = DjangoFilterConnectionField(CollectionProductNode)
    collection_channel_listing = Node.Field(CollectionChannelListingNode)
    all_collection_channel_listings = DjangoFilterConnectionField(CollectionChannelListingNode)
    collection_translation = Node.Field(CollectionTranslationNode)
    all_collection_translations = DjangoFilterConnectionField(CollectionTranslationNode)
     
    
   
    