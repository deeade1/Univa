import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField

from blog import models
from graphq.accounts.types import UserNode
from graphq.blog.types import CommentNode, PostNode, ReplyNode, TagNode


class BlogQueries(graphene.ObjectType):
    all_posts = DjangoFilterConnectionField(PostNode)
    author_by_first_name = Node.Field(UserNode, first_name=graphene.String())
    post_by_slug = Node.Field(PostNode, slug=graphene.String())
    posts_by_author = Node.Field(PostNode, first_name=graphene.String())
    posts_by_tag = Node.Field(PostNode, tag=graphene.String())
    reply = Node.Field(ReplyNode)
    all_replies = DjangoFilterConnectionField(ReplyNode)
    comment = Node.Field(CommentNode)
    all_comments = DjangoFilterConnectionField(CommentNode)

    def resolve_all_posts(root, info):
        return (
            models.Post.objects.prefetch_related("tags").select_related("author").all()
        )

    def resolve_author_by_first_name(root, info, first_name):
        return models.User.objects.select_related("user").get(
            user__first_name=first_name
        )

    def resolve_post_by_slug(root, info, slug):
        return (
            models.Post.objects.prefetch_related("tags")
            .select_related("author")
            .get(slug=slug)
        )

    def resolve_posts_by_author(root, info, first_name):
        return (
            models.Post.objects.prefetch_related("tags")
            .select_related("author")
            .filter(author__user__first_name=first_name)
        )

    def resolve_posts_by_tag(root, info, tag):
        return (
            models.Post.objects.prefetch_related("tags")
            .select_related("author")
            .filter(tags__name__iexact=tag)
        )
