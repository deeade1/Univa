# apps/backend/graphq/social/schema.py
"""
GraphQL queries for the social domain.

Aligned against the corrected `social/types.py` and the current
`social/models.py`. Friend-request / notification queries are omitted
because their models do not exist yet.
"""

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from accounts.models import User

from graphq.accounts.types.user import UserNode

from graphq.social.types import (
    ContentCategoryNode,
    DuetVideoNode,
    EffectNode,
    FollowNode,
    SocialProfileNode,
    SoundNode,
    StitchVideoNode,
    TrendingFeedNode,
    UserActivityNode,
    UserInterestNode,
    VideoCommentNode,
    VideoContentNode,
    VideoLikeNode,
    VideoReportNode,
    VideoSaveNode,
    VideoShareNode,
    VideoViewNode,
)

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
    VideoReport,
    VideoSave,
    VideoShare,
    VideoView,
)


class SocialQueries(graphene.ObjectType):

    # ------------------------------------------------------------------
    # Social graph
    # ------------------------------------------------------------------
    social_profile = relay.Node.Field(SocialProfileNode)
    all_social_profiles = DjangoFilterConnectionField(SocialProfileNode)

    follow = relay.Node.Field(FollowNode)
    all_follows = DjangoFilterConnectionField(FollowNode)

    # User suggestions — returns User nodes, not Follow nodes.
    user_suggestions = DjangoFilterConnectionField(UserNode)

    # ------------------------------------------------------------------
    # Video content
    # ------------------------------------------------------------------
    video = relay.Node.Field(VideoContentNode)
    all_videos = DjangoFilterConnectionField(VideoContentNode)
    video_feed = DjangoFilterConnectionField(VideoContentNode)
    trending_videos = DjangoFilterConnectionField(VideoContentNode)
    user_videos = DjangoFilterConnectionField(VideoContentNode)

    video_like = relay.Node.Field(VideoLikeNode)
    all_video_likes = DjangoFilterConnectionField(VideoLikeNode)

    video_comment = relay.Node.Field(VideoCommentNode)
    video_comments = DjangoFilterConnectionField(VideoCommentNode)

    video_view = relay.Node.Field(VideoViewNode)
    all_video_views = DjangoFilterConnectionField(VideoViewNode)

    video_share = relay.Node.Field(VideoShareNode)
    all_video_shares = DjangoFilterConnectionField(VideoShareNode)

    video_save = relay.Node.Field(VideoSaveNode)
    all_video_saves = DjangoFilterConnectionField(VideoSaveNode)

    duet_video = relay.Node.Field(DuetVideoNode)
    all_duet_videos = DjangoFilterConnectionField(DuetVideoNode)

    stitch_video = relay.Node.Field(StitchVideoNode)
    all_stitch_videos = DjangoFilterConnectionField(StitchVideoNode)

    # ------------------------------------------------------------------
    # Moderation
    # ------------------------------------------------------------------
    video_report = relay.Node.Field(VideoReportNode)
    all_video_reports = DjangoFilterConnectionField(VideoReportNode)

    # ------------------------------------------------------------------
    # Analytics / recommendations
    # ------------------------------------------------------------------
    user_activity = relay.Node.Field(UserActivityNode)
    all_user_activity = DjangoFilterConnectionField(UserActivityNode)

    user_interest = relay.Node.Field(UserInterestNode)
    all_user_interests = DjangoFilterConnectionField(UserInterestNode)

    trending_feed = DjangoFilterConnectionField(TrendingFeedNode)

    # ------------------------------------------------------------------
    # Sound / effect / categories
    # ------------------------------------------------------------------
    sound = relay.Node.Field(SoundNode)
    all_sounds = DjangoFilterConnectionField(SoundNode)

    effect = relay.Node.Field(EffectNode)
    all_effects = DjangoFilterConnectionField(EffectNode)

    content_category = relay.Node.Field(ContentCategoryNode)
    all_content_categories = DjangoFilterConnectionField(ContentCategoryNode)

    # ==================================================================
    # Resolvers
    # ==================================================================

    def resolve_user_suggestions(self, info, **kwargs):
        """
        Return User nodes that the current user does not yet follow.

        NOTE: only exposes basic exclusion — a real suggestion service
        (friend-of-friend graph, interest vectors, etc.) belongs in
        `social.services` / `social.algorithms`, not here.
        """
        user = info.context.user
        if not user.is_authenticated:
            return User.objects.none()

        already_following = Follow.objects.filter(
            follower=user
        ).values_list("following_id", flat=True)

        return (
            User.objects.exclude(pk=user.pk)
            .exclude(pk__in=already_following)
            .filter(is_active=True)
        )

    def resolve_video_feed(self, info, **kwargs):
        """
        Return the personalized video feed for the current user.

        Falls back to public, published videos ordered by viral score
        when the user is anonymous or no algorithm is wired up.
        """
        user = info.context.user

        base_qs = VideoContent.objects.filter(
            status="published", visibility="public"
        )

        if not user.is_authenticated:
            return base_qs.order_by("-viral_score", "-created_at")

        # Delegate to a service if available; keep ORM here only as fallback.
        try:
            from social.services import get_feed_for_user  # optional

            return get_feed_for_user(user)
        except ImportError:
            return base_qs.order_by("-viral_score", "-created_at")

    def resolve_trending_videos(self, info, **kwargs):
        return (
            VideoContent.objects.filter(
                status="published", visibility="public"
            )
            .order_by("-viral_score", "-created_at")
        )

    def resolve_user_videos(self, info, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            return VideoContent.objects.none()
        return VideoContent.objects.filter(user=user).order_by("-created_at")

    def resolve_personalized_feed(self, info, **kwargs):
        """TrendingFeed rows personalized for the current user."""
        user = info.context.user
        if not user.is_authenticated:
            return TrendingFeed.objects.none()
        return TrendingFeed.objects.filter(user=user).order_by("-rank_score")

    def resolve_video_comments(self, info, **kwargs):
        """
        Top-level comments only; replies are reachable via the
        `replies` field on VideoCommentNode.
        """
        video_id = kwargs.get("video_id")
        qs = VideoComment.objects.filter(
            parent_comment__isnull=True,
            is_removed=False,
        )
        if video_id:
            qs = qs.filter(video_id=video_id)
        return qs.order_by("-is_pinned", "created_at")