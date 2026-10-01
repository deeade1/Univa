import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.category import ( 
    CategoryNode,
    CategoryTranslationNode
)
# =============================================================================
# Schema Registration
# =============================================================================

# In your schema.py, you would register these nodes:

class CategoryQuery(graphene.ObjectType):
    # Node queries
    category = Node.Field(CategoryNode)
    all_categories = DjangoFilterConnectionField(CategoryNode)
    category_translation = Node.Field(CategoryTranslationNode)
    all_category_translations = DjangoFilterConnectionField(CategoryTranslationNode)
