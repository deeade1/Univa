import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.checkout import ( 
    CheckoutNode,
    CheckoutLineNode
)

# =============================================================================
# Schema Registration
# =============================================================================

# In your schema.py, you would register these nodes:

class CheckoutQuery(graphene.ObjectType):
    # Node queries
    checkout = Node.Field(CheckoutNode)
    all_checkouts = DjangoFilterConnectionField(CheckoutNode)
    checkout_line = Node.Field(CheckoutLineNode)
    all_checkout_lines = DjangoFilterConnectionField(CheckoutLineNode)