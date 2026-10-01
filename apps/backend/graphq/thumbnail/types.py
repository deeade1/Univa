import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from thumbnail import models


class ThumbnailType(DjangoObjectType):
    class Meta:
        model = models.Thumbnail
        interfaces = (relay.Node,)
        filter_fields = [
            "id",
            "size",
            "format",
            "category__id",
            "collection__id",
            "product_media__id",
            "user__id",
        ]
