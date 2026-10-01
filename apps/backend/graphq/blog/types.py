# schema.py
import graphene
from django.contrib.auth import get_user_model
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_optimizer import \
    OptimizedDjangoObjectType  # Import the optimizer

from blog import models
from blog.models import Comment, Post, Reply, Tag


class TagNode(OptimizedDjangoObjectType):  # Use OptimizedDjangoObjectType
    class Meta:
        model = Tag
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains", "istartswith"],
        }
        interfaces = (Node,)


class CommentNode(OptimizedDjangoObjectType):  # Use OptimizedDjangoObjectType
    class Meta:
        model = Comment
        fields = "__all__"
        filter_fields = {
            "post": ["exact"],
            "name": ["exact", "icontains", "istartswith"],
            "created_at": ["exact", "gte", "lte"],
        }
        interfaces = (Node,)


class PostNode(OptimizedDjangoObjectType):
    structured_data = graphene.JSONString()
    meta_tags = graphene.JSONString()
    canonical_url = graphene.String()

    class Meta:
        model = Post
        interfaces = (Node,)
        filter_fields = {
            'slug': ['exact'],
            'title': ['exact', 'icontains', 'istartswith'],
            'author__first_name': ['exact', 'icontains', 'istartswith'],
        }

    def resolve_structured_data(self, info):
        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.title,
            "description": self.meta_description,
            "datePublished": self.publish_date.isoformat(),
            "author": {
                "@type": "Person",
                "name": self.author.get_full_name()
            },
            "image": self.featured_image.url if self.featured_image else None
        }

    def resolve_meta_tags(self, info):
        return {
            "title": f"{self.title} | {SITE_NAME}",
            "description": self.meta_description,
            "og_type": "article",
            "twitter_card": "summary_large_image"
        }

    def resolve_canonical_url(self, info):
        return f"{SITE_URL}/blog/{self.slug}/"


class ReplyNode(OptimizedDjangoObjectType):  # Use OptimizedDjangoObjectType
    class Meta:
        model = Reply
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains", "istartswith"],
            "comment": ["exact"],
            "created_at": ["exact", "gte", "lte"],
        }
        interfaces = (Node,)