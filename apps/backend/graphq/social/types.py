"""
GraphQL nodes for the social domain.

Every node is aligned against the current `social/models.py`.
Nodes for models that do not yet exist (`FriendRequest`,
`FriendshipInteraction`, `Notification`) are intentionally omitted —
add them back once their models are defined.
"""

import django_filters
import graphene
from django.db.models import F
from graphene import Node, relay
from graphene_django import DjangoObjectType

from accounts.models import UserProfile

from social.models import (
    ContentCategory,
    DuetVideo,
    Effect,
    Follow,
    SocialProfile,
    Sound,
    StitchVideo,
    TrendingFeed,
    UserActivity,
    UserInterest,
    VideoComment,
    VideoContent,
    VideoLike,
    VideoProcessingQueue,
    VideoReport,
    VideoSave,
    VideoShare,
    VideoView,
)

from graphq.accounts.types import UserProfileNode


# =============================================================================
# Social Profile / Follow graph
# =============================================================================

class SocialProfileNode(DjangoObjectType):
    class Meta:
        model = SocialProfile
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "is_verified": ["exact"],
            "is_private": ["exact"],
            "followers_count": ["exact", "gte", "lte"],
            "following_count": ["exact", "gte", "lte"],
            "created_at": ["exact", "lt", "gt"],
        }


class FollowNode(DjangoObjectType):
    mutual_followers_count = graphene.Int()

    class Meta:
        model = Follow
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "follower": ["exact"],
            "following": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }

    def resolve_mutual_followers_count(self, info):
        """
        Number of users that both `follower` and `following` follow.

        Kept intentionally simple; if this becomes hot, move it to
        a manager/service and cache per pair.
        """
        follower_ids = Follow.objects.filter(
            follower_id=self.follower_id
        ).values_list("following_id", flat=True)

        return Follow.objects.filter(
            follower_id=self.following_id,
            following_id__in=follower_ids,
        ).count()


# =============================================================================
# Video content
# =============================================================================

class VideoContentNode(DjangoObjectType):
    """Video content with engagement metrics and viewer-relative flags."""

    # Viewer-relative flags
    is_liked = graphene.Boolean()
    is_viewed = graphene.Boolean()
    is_bookmarked = graphene.Boolean()

    # URL helpers
    video_url = graphene.String(quality=graphene.String())
    thumbnail_url = graphene.String()
    thumbnail_urls = graphene.List(graphene.String)

    # Recommendation helpers
    recommendation_score = graphene.Float()
    recommendation_reasons = graphene.List(graphene.String)

    class Meta:
        model = VideoContent
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "id": ["exact"],
            "status": ["exact"],
            "visibility": ["exact"],
            "created_at": ["exact", "lt", "gt"],
            "published_at": ["exact", "lt", "gt", "isnull"],
            "viral_score": ["exact", "gte", "lte"],
            "engagement_rate": ["exact", "gte", "lte"],
            "likes_count": ["exact", "gte", "lte"],
            "comments_count": ["exact", "gte", "lte"],
            "views_count": ["exact", "gte", "lte"],
            "shares_count": ["exact", "gte", "lte"],
            "saves_count": ["exact", "gte", "lte"],
        }

    # ---- Viewer flags -------------------------------------------------

    def resolve_is_liked(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()

    def resolve_is_viewed(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return False
        return self.views.filter(user=user).exists()

    def resolve_is_bookmarked(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return False
        return self.saves.filter(user=user).exists()

    # ---- URL helpers --------------------------------------------------

    def resolve_video_url(self, info, quality=None):
        if self.video_urls:
            if quality and quality in self.video_urls:
                return self.video_urls[quality]
            # Prefer "default", then first available variant
            return (
                self.video_urls.get("default")
                or next(iter(self.video_urls.values()), None)
            )
        if self.video_file:
            return info.context.build_absolute_uri(self.video_file.url)
        return None

    def resolve_thumbnail_url(self, info):
        if self.thumbnail:
            return info.context.build_absolute_uri(self.thumbnail.url)
        return None

    def resolve_thumbnail_urls(self, info):
        return self.thumbnails or []

    # ---- Recommendation helpers --------------------------------------

    def resolve_recommendation_score(self, info):
        return self.viral_score or 0.0

    def resolve_recommendation_reasons(self, info):
        # Placeholder — real reasons come from the recommender service.
        return []


class VideoLikeNode(DjangoObjectType):
    class Meta:
        model = VideoLike
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "video": ["exact"],
            "sentiment": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


class VideoCommentNode(DjangoObjectType):
    reply_count = graphene.Int()

    class Meta:
        model = VideoComment
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "video": ["exact"],
            "parent_comment": ["exact", "isnull"],
            "is_pinned": ["exact"],
            "is_removed": ["exact"],
            "moderation_status": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }

    def resolve_reply_count(self, info):
        return self.replies.count()


class VideoViewNode(DjangoObjectType):
    class Meta:
        model = VideoView
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "video": ["exact"],
            "session_id": ["exact"],
            "completed": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


class VideoShareNode(DjangoObjectType):
    class Meta:
        model = VideoShare
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "video": ["exact"],
            "platform": ["exact", "icontains"],
            "created_at": ["exact", "lt", "gt"],
        }


class VideoSaveNode(DjangoObjectType):
    class Meta:
        model = VideoSave
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "video": ["exact"],
            "collection": ["exact", "icontains"],
            "created_at": ["exact", "lt", "gt"],
        }


class DuetVideoNode(DjangoObjectType):
    class Meta:
        model = DuetVideo
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "original_video": ["exact"],
            "duet_video": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


class StitchVideoNode(DjangoObjectType):
    class Meta:
        model = StitchVideo
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "original_video": ["exact"],
            "stitch_video": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


# =============================================================================
# Moderation & analytics
# =============================================================================

class VideoReportNode(DjangoObjectType):
    class Meta:
        model = VideoReport
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "video": ["exact"],
            "reported_by": ["exact"],
            "reviewed_by": ["exact"],
            "reason": ["exact"],
            "status": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


class UserActivityNode(DjangoObjectType):
    class Meta:
        model = UserActivity
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "activity_type": ["exact"],
            "video": ["exact"],
            "target_user": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


# =============================================================================
# Recommendation / feed
# =============================================================================

class TrendingFeedNode(DjangoObjectType):
    class Meta:
        model = TrendingFeed
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact", "isnull"],
            "video": ["exact"],
            "rank_score": ["exact", "gte", "lte"],
            "created_at": ["exact", "lt", "gt"],
            "expires_at": ["exact", "lt", "gt"],
        }


class UserInterestNode(DjangoObjectType):
    class Meta:
        model = UserInterest
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "user": ["exact"],
            "engagement_score": ["exact", "gte", "lte"],
            "updated_at": ["exact", "lt", "gt"],
        }


# =============================================================================
# Processing queue
# =============================================================================

class VideoProcessingQueueNode(DjangoObjectType):
    class Meta:
        model = VideoProcessingQueue
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "video": ["exact"],
            "status": ["exact"],
            "priority": ["exact", "gte", "lte"],
            "created_at": ["exact", "lt", "gt"],
            "started_at": ["exact", "lt", "gt", "isnull"],
            "completed_at": ["exact", "lt", "gt", "isnull"],
        }


# =============================================================================
# Music / audio
# =============================================================================

class SoundNode(DjangoObjectType):
    class Meta:
        model = Sound
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "title": ["exact", "icontains"],
            "artist": ["exact", "icontains"],
            "album": ["exact", "icontains"],
            "duration": ["exact", "gte", "lte"],
            "created_by": ["exact"],
            "license_type": ["exact"],
            "is_original": ["exact"],
            "is_verified": ["exact"],
            "is_trending": ["exact"],
            "usage_count": ["exact", "gte", "lte"],
            "created_at": ["exact", "lt", "gt"],
        }


# =============================================================================
# Effects
# =============================================================================

class EffectNode(DjangoObjectType):
    class Meta:
        model = Effect
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains"],
            "category": ["exact"],
            "created_by": ["exact"],
            "usage_count": ["exact", "gte", "lte"],
            "is_trending": ["exact"],
            "is_verified": ["exact"],
            "is_ar": ["exact"],
            "created_at": ["exact", "lt", "gt"],
        }


# =============================================================================
# Content categories
# =============================================================================

class ContentCategoryNode(DjangoObjectType):
    class Meta:
        model = ContentCategory
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "icontains"],
            "slug": ["exact"],
            "parent": ["exact", "isnull"],
            "popularity_score": ["exact", "gte", "lte"],
            "video_count": ["exact", "gte", "lte"],
            "created_at": ["exact", "lt", "gt"],
        }