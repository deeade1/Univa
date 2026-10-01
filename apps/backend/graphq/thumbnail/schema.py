import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .mutations import ThumbnailMutations
from .types import ThumbnailType


class ThumbnailQueries(graphene.ObjectType):
    thumbnail = relay.Node.Field(ThumbnailType)
    all_thumbnails = DjangoFilterConnectionField(ThumbnailType)
