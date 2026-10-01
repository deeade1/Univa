import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.channel import ( 
    ChannelNode
)

# =============================================================================
# Schema Registration
# =============================================================================

class ChannelQuery(graphene.ObjectType):
    channel = Node.Field(ChannelNode)
    all_channels = DjangoFilterConnectionField(ChannelNode)
    channel_by_slug = graphene.Field(ChannelNode, slug=graphene.String(required=True))

    def resolve_channel_by_slug(self, info, slug):
        return Channel.objects.filter(slug=slug).first()