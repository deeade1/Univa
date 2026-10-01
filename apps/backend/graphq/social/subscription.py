# apps/backend/graphq/social/subscription.py
"""
GraphQL subscriptions for the social domain.

Aligned against the current `social/models.py`. Subscriptions for
models that do not yet exist (FriendRequest, Friend, FriendshipInteraction,
Notification, VideoSound, VideoEffect) are omitted. Re-add them once
their models and apps are in place.
"""

import graphene
from channels_graphql_ws import Subscription
from graphql_relay import from_global_id

from social.models import (
    DuetVideo,
    Effect,
    Follow,
    Sound,
    StitchVideo,
    TrendingFeed,
    VideoComment,
    VideoContent,
    VideoLike,
    VideoProcessingQueue,
    VideoShare,
    VideoView,
)

from graphq.social.types import (
    DuetVideoNode,
    EffectNode,
    FollowNode,
    SoundNode,
    StitchVideoNode,
    TrendingFeedNode,
    VideoCommentNode,
    VideoContentNode,
    VideoLikeNode,
    VideoShareNode,
    VideoViewNode,
)


# =============================================================================
# Follow graph subscriptions
# =============================================================================

class NewFollowerSubscription(Subscription):
    """Real-time notification when someone follows you."""

    follower = graphene.Field(FollowNode)
    follower_id = graphene.ID()

    class Arguments:
        user_id = graphene.ID(required=True)  # the user being followed

    @staticmethod
    def subscribe(root, info, user_id):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        return [f"followers_user_{pk}"]

    @staticmethod
    def publish(payload, info, user_id):
        return NewFollowerSubscription(
            follower=payload.get("follower"),
            follower_id=payload.get("follower_id"),
        )

    @classmethod
    def trigger(cls, follow):
        """Broadcast when a new Follow row is created."""
        cls.broadcast(
            group=f"followers_user_{follow.following_id}",
            payload={
                "follower": follow,
                "follower_id": follow.follower_id,
            },
        )


# =============================================================================
# Video content subscriptions
# =============================================================================

class NewVideoPublishedSubscription(Subscription):
    """New video published by followed users."""

    video = graphene.Field(VideoContentNode)
    author = graphene.ID()
    is_following = graphene.Boolean()

    class Arguments:
        user_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, user_id):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        return [f"new_videos_{pk}"]

    @staticmethod
    def publish(payload, info, user_id):
        return NewVideoPublishedSubscription(
            video=payload.get("video"),
            author=payload.get("author"),
            is_following=payload.get("is_following"),
        )

    @classmethod
    def trigger(cls, video, follower):
        cls.broadcast(
            group=f"new_videos_{follower.id}",
            payload={
                "video": video,
                "author": video.user_id,
                "is_following": True,
            },
        )


class VideoLikeAddedSubscription(Subscription):
    """Real-time video like notifications."""

    like = graphene.Field(VideoLikeNode)
    video = graphene.Field(VideoContentNode)
    liked_by = graphene.ID()
    sentiment = graphene.String()

    class Arguments:
        video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, video_id):
        try:
            _, pk = from_global_id(video_id)
        except Exception:
            pk = video_id
        return [f"video_likes_{pk}"]

    @staticmethod
    def publish(payload, info, video_id):
        return VideoLikeAddedSubscription(
            like=payload.get("like"),
            video=payload.get("video"),
            liked_by=payload.get("liked_by"),
            sentiment=payload.get("sentiment"),
        )

    @classmethod
    def trigger(cls, video_like):
        cls.broadcast(
            group=f"video_likes_{video_like.video_id}",
            payload={
                "like": video_like,
                "video": video_like.video,
                "liked_by": video_like.user_id,
                "sentiment": video_like.sentiment,
            },
        )
        cls.broadcast(
            group=f"user_notifications_{video_like.video.user_id}",
            payload={
                "like": video_like,
                "video": video_like.video,
                "liked_by": video_like.user_id,
            },
        )


class NewVideoCommentSubscription(Subscription):
    """Real-time video comment notifications."""

    comment = graphene.Field(VideoCommentNode)
    video = graphene.Field(VideoContentNode)
    commenter = graphene.ID()
    is_reply = graphene.Boolean()
    parent_comment_id = graphene.ID()

    class Arguments:
        video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, video_id):
        try:
            _, pk = from_global_id(video_id)
        except Exception:
            pk = video_id
        return [f"video_comments_{pk}"]

    @staticmethod
    def publish(payload, info, video_id):
        return NewVideoCommentSubscription(
            comment=payload.get("comment"),
            video=payload.get("video"),
            commenter=payload.get("commenter"),
            is_reply=payload.get("is_reply", False),
            parent_comment_id=payload.get("parent_comment_id"),
        )

    @classmethod
    def trigger(cls, comment):
        cls.broadcast(
            group=f"video_comments_{comment.video_id}",
            payload={
                "comment": comment,
                "video": comment.video,
                "commenter": comment.user_id,
                "is_reply": bool(comment.parent_comment_id),
                "parent_comment_id": comment.parent_comment_id,
            },
        )

        # Notify video owner
        if comment.user_id != comment.video.user_id:
            cls.broadcast(
                group=f"user_notifications_{comment.video.user_id}",
                payload={
                    "comment": comment,
                    "video": comment.video,
                    "commenter": comment.user_id,
                },
            )

        # Notify parent commenter if this is a reply
        if (
            comment.parent_comment_id
            and comment.parent_comment
            and comment.parent_comment.user_id != comment.user_id
        ):
            cls.broadcast(
                group=f"user_notifications_{comment.parent_comment.user_id}",
                payload={
                    "comment": comment,
                    "video": comment.video,
                    "is_reply": True,
                },
            )


class VideoViewCountUpdatedSubscription(Subscription):
    """Real-time video view count updates."""

    video = graphene.Field(VideoContentNode)
    view_count = graphene.Int()
    unique_viewers = graphene.Int()
    watch_time_avg = graphene.Float()

    class Arguments:
        video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, video_id):
        try:
            _, pk = from_global_id(video_id)
        except Exception:
            pk = video_id
        return [f"video_views_{pk}"]

    @staticmethod
    def publish(payload, info, video_id):
        return VideoViewCountUpdatedSubscription(
            video=payload.get("video"),
            view_count=payload.get("view_count"),
            unique_viewers=payload.get("unique_viewers"),
            watch_time_avg=payload.get("watch_time_avg"),
        )

    @classmethod
    def trigger(cls, video, view_count, unique_viewers, watch_time_avg):
        cls.broadcast(
            group=f"video_views_{video.id}",
            payload={
                "video": video,
                "view_count": view_count,
                "unique_viewers": unique_viewers,
                "watch_time_avg": watch_time_avg,
            },
        )


class VideoSharedSubscription(Subscription):
    """Video share notifications."""

    share = graphene.Field(VideoShareNode)
    video = graphene.Field(VideoContentNode)
    shared_by = graphene.ID()
    platform = graphene.String()

    class Arguments:
        video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, video_id):
        try:
            _, pk = from_global_id(video_id)
        except Exception:
            pk = video_id
        return [f"video_shares_{pk}"]

    @staticmethod
    def publish(payload, info, video_id):
        return VideoSharedSubscription(
            share=payload.get("share"),
            video=payload.get("video"),
            shared_by=payload.get("shared_by"),
            platform=payload.get("platform"),
        )

    @classmethod
    def trigger(cls, video_share):
        if video_share.user_id != video_share.video.user_id:
            cls.broadcast(
                group=f"video_shares_{video_share.video_id}",
                payload={
                    "share": video_share,
                    "video": video_share.video,
                    "shared_by": video_share.user_id,
                    "platform": video_share.platform,
                },
            )
            cls.broadcast(
                group=f"user_notifications_{video_share.video.user_id}",
                payload={
                    "share": video_share,
                    "video": video_share.video,
                    "shared_by": video_share.user_id,
                    "platform": video_share.platform,
                },
            )


class VideoDuetCreatedSubscription(Subscription):
    """Duet video creation notifications."""

    duet = graphene.Field(DuetVideoNode)
    original_video = graphene.Field(VideoContentNode)
    duet_video = graphene.Field(VideoContentNode)
    created_by = graphene.ID()

    class Arguments:
        original_video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, original_video_id):
        try:
            _, pk = from_global_id(original_video_id)
        except Exception:
            pk = original_video_id
        return [f"video_duets_{pk}"]

    @staticmethod
    def publish(payload, info, original_video_id):
        return VideoDuetCreatedSubscription(
            duet=payload.get("duet"),
            original_video=payload.get("original_video"),
            duet_video=payload.get("duet_video"),
            created_by=payload.get("created_by"),
        )

    @classmethod
    def trigger(cls, duet_video):
        if duet_video.duet_video.user_id != duet_video.original_video.user_id:
            payload = {
                "duet": duet_video,
                "original_video": duet_video.original_video,
                "duet_video": duet_video.duet_video,
                "created_by": duet_video.duet_video.user_id,
            }
            cls.broadcast(
                group=f"video_duets_{duet_video.original_video_id}",
                payload=payload,
            )
            cls.broadcast(
                group=f"user_notifications_{duet_video.original_video.user_id}",
                payload=payload,
            )


class VideoStitchCreatedSubscription(Subscription):
    """Stitch video creation notifications."""

    stitch = graphene.Field(StitchVideoNode)
    original_video = graphene.Field(VideoContentNode)
    stitch_video = graphene.Field(VideoContentNode)
    created_by = graphene.ID()

    class Arguments:
        original_video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, original_video_id):
        try:
            _, pk = from_global_id(original_video_id)
        except Exception:
            pk = original_video_id
        return [f"video_stitches_{pk}"]

    @staticmethod
    def publish(payload, info, original_video_id):
        return VideoStitchCreatedSubscription(
            stitch=payload.get("stitch"),
            original_video=payload.get("original_video"),
            stitch_video=payload.get("stitch_video"),
            created_by=payload.get("created_by"),
        )

    @classmethod
    def trigger(cls, stitch_video):
        if stitch_video.stitch_video.user_id != stitch_video.original_video.user_id:
            payload = {
                "stitch": stitch_video,
                "original_video": stitch_video.original_video,
                "stitch_video": stitch_video.stitch_video,
                "created_by": stitch_video.stitch_video.user_id,
            }
            cls.broadcast(
                group=f"video_stitches_{stitch_video.original_video_id}",
                payload=payload,
            )
            cls.broadcast(
                group=f"user_notifications_{stitch_video.original_video.user_id}",
                payload=payload,
            )


# =============================================================================
# Video processing subscriptions
# =============================================================================

class VideoProcessingStatusSubscription(Subscription):
    """Real-time video processing status updates."""

    video = graphene.Field(VideoContentNode)
    old_status = graphene.String()
    new_status = graphene.String()
    progress = graphene.Float()
    estimated_time = graphene.Int()

    class Arguments:
        video_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, video_id):
        try:
            _, pk = from_global_id(video_id)
        except Exception:
            pk = video_id
        return [f"video_processing_{pk}"]

    @staticmethod
    def publish(payload, info, video_id):
        return VideoProcessingStatusSubscription(
            video=payload.get("video"),
            old_status=payload.get("old_status"),
            new_status=payload.get("new_status"),
            progress=payload.get("progress"),
            estimated_time=payload.get("estimated_time"),
        )

    @classmethod
    def trigger(cls, video, old_status, new_status, progress=0, estimated_time=0):
        cls.broadcast(
            group=f"video_processing_{video.id}",
            payload={
                "video": video,
                "old_status": old_status,
                "new_status": new_status,
                "progress": progress,
                "estimated_time": estimated_time,
            },
        )


class VideoProcessingCompletedSubscription(Subscription):
    """Video processing completed notifications."""

    video = graphene.Field(VideoContentNode)
    processing_time = graphene.Float()
    thumbnail_url = graphene.String()
    video_urls = graphene.JSONString()

    class Arguments:
        user_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, user_id):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        return [f"processing_completed_{pk}"]

    @staticmethod
    def publish(payload, info, user_id):
        return VideoProcessingCompletedSubscription(
            video=payload.get("video"),
            processing_time=payload.get("processing_time"),
            thumbnail_url=payload.get("thumbnail_url"),
            video_urls=payload.get("video_urls"),
        )

    @classmethod
    def trigger(cls, video, processing_time, thumbnail_url, video_urls):
        cls.broadcast(
            group=f"processing_completed_{video.user_id}",
            payload={
                "video": video,
                "processing_time": processing_time,
                "thumbnail_url": thumbnail_url,
                "video_urls": video_urls,
            },
        )


class VideoProcessingFailedSubscription(Subscription):
    """Video processing failure notifications."""

    video = graphene.Field(VideoContentNode)
    error_message = graphene.String()
    retry_count = graphene.Int()
    can_retry = graphene.Boolean()

    class Arguments:
        user_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, user_id):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        return [f"processing_failed_{pk}"]

    @staticmethod
    def publish(payload, info, user_id):
        return VideoProcessingFailedSubscription(
            video=payload.get("video"),
            error_message=payload.get("error_message"),
            retry_count=payload.get("retry_count"),
            can_retry=payload.get("can_retry"),
        )

    @classmethod
    def trigger(cls, video, error_message, retry_count, can_retry):
        """
        `video` may be None when the failure happens before the
        VideoContent row is created. In that case broadcast only to
        the acting user's generic notification channel.
        """
        if video is not None:
            group = f"processing_failed_{video.user_id}"
            payload = {
                "video": video,
                "error_message": error_message,
                "retry_count": retry_count,
                "can_retry": can_retry,
            }
        else:
            # No video yet — skip targeted broadcast. Caller should
            # trigger a user-scoped notification via another channel.
            return

        cls.broadcast(group=group, payload=payload)


# =============================================================================
# Feed subscriptions
# =============================================================================

class FeedUpdatedSubscription(Subscription):
    """Real-time feed updates for following users."""

    video = graphene.Field(VideoContentNode)
    feed_type = graphene.String()  # 'following', 'for_you', 'trending'
    position = graphene.Int()

    class Arguments:
        user_id = graphene.ID(required=True)
        feed_type = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id, feed_type=None):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        if feed_type:
            return [f"feed_updates_{pk}_{feed_type}"]
        return [f"feed_updates_{pk}"]

    @staticmethod
    def publish(payload, info, user_id, feed_type=None):
        return FeedUpdatedSubscription(
            video=payload.get("video"),
            feed_type=payload.get("feed_type"),
            position=payload.get("position"),
        )

    @classmethod
    def trigger(cls, video, user_id, feed_type, position):
        payload = {
            "video": video,
            "feed_type": feed_type,
            "position": position,
        }
        cls.broadcast(group=f"feed_updates_{user_id}_{feed_type}", payload=payload)
        cls.broadcast(group=f"feed_updates_{user_id}", payload=payload)


class TrendingFeedUpdatedSubscription(Subscription):
    """Real-time trending feed updates."""

    trending_item = graphene.Field(TrendingFeedNode)
    rank_change = graphene.Int()
    viral_score = graphene.Float()

    class Arguments:
        category = graphene.String()

    @staticmethod
    def subscribe(root, info, category=None):
        if category:
            return [f"trending_updates_{category}"]
        return ["trending_updates_all"]

    @staticmethod
    def publish(payload, info, category=None):
        return TrendingFeedUpdatedSubscription(
            trending_item=payload.get("trending_item"),
            rank_change=payload.get("rank_change"),
            viral_score=payload.get("viral_score"),
        )

    @classmethod
    def trigger(cls, trending_item, rank_change, viral_score, category=None):
        payload = {
            "trending_item": trending_item,
            "rank_change": rank_change,
            "viral_score": viral_score,
        }
        if category:
            cls.broadcast(group=f"trending_updates_{category}", payload=payload)
        cls.broadcast(group="trending_updates_all", payload=payload)


class ForYouFeedUpdatedSubscription(Subscription):
    """Personalized 'For You' feed updates."""

    video = graphene.Field(VideoContentNode)
    relevance_score = graphene.Float()
    reason = graphene.List(graphene.String)

    class Arguments:
        user_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, user_id):
        try:
            _, pk = from_global_id(user_id)
        except Exception:
            pk = user_id
        return [f"for_you_feed_{pk}"]

    @staticmethod
    def publish(payload, info, user_id):
        return ForYouFeedUpdatedSubscription(
            video=payload.get("video"),
            relevance_score=payload.get("relevance_score"),
            reason=payload.get("reason", []),
        )

    @classmethod
    def trigger(cls, video, user_id, relevance_score, reasons):
        cls.broadcast(
            group=f"for_you_feed_{user_id}",
            payload={
                "video": video,
                "relevance_score": relevance_score,
                "reason": reasons,
            },
        )


# =============================================================================
# Sound & effect subscriptions
# =============================================================================

class SoundTrendingSubscription(Subscription):
    """Trending sounds updates."""

    sound = graphene.Field(SoundNode)
    usage_count = graphene.Int()
    trend_position = graphene.Int()
    videos_count = graphene.Int()

    class Arguments:
        category = graphene.String()

    @staticmethod
    def subscribe(root, info, category=None):
        if category:
            return [f"trending_sounds_{category}"]
        return ["trending_sounds_all"]

    @staticmethod
    def publish(payload, info, category=None):
        return SoundTrendingSubscription(
            sound=payload.get("sound"),
            usage_count=payload.get("usage_count"),
            trend_position=payload.get("trend_position"),
            videos_count=payload.get("videos_count"),
        )

    @classmethod
    def trigger(cls, sound, usage_count, trend_position, videos_count, category=None):
        payload = {
            "sound": sound,
            "usage_count": usage_count,
            "trend_position": trend_position,
            "videos_count": videos_count,
        }
        if category:
            cls.broadcast(group=f"trending_sounds_{category}", payload=payload)
        cls.broadcast(group="trending_sounds_all", payload=payload)


class EffectTrendingSubscription(Subscription):
    """Trending effects updates."""

    effect = graphene.Field(EffectNode)
    usage_count = graphene.Int()
    trend_position = graphene.Int()
    is_new = graphene.Boolean()

    class Arguments:
        category = graphene.String()

    @staticmethod
    def subscribe(root, info, category=None):
        if category:
            return [f"trending_effects_{category}"]
        return ["trending_effects_all"]

    @staticmethod
    def publish(payload, info, category=None):
        return EffectTrendingSubscription(
            effect=payload.get("effect"),
            usage_count=payload.get("usage_count"),
            trend_position=payload.get("trend_position"),
            is_new=payload.get("is_new"),
        )

    @classmethod
    def trigger(cls, effect, usage_count, trend_position, is_new, category=None):
        payload = {
            "effect": effect,
            "usage_count": usage_count,
            "trend_position": trend_position,
            "is_new": is_new,
        }
        if category:
            cls.broadcast(group=f"trending_effects_{category}", payload=payload)
        cls.broadcast(group="trending_effects_all", payload=payload)


# =============================================================================
# Registration
# =============================================================================

class SocialSubscriptions(graphene.ObjectType):
    # Follow graph
    new_follower = NewFollowerSubscription.Field()

    # Video content
    new_video_published = NewVideoPublishedSubscription.Field()
    video_like_added = VideoLikeAddedSubscription.Field()
    new_video_comment = NewVideoCommentSubscription.Field()
    video_view_count_updated = VideoViewCountUpdatedSubscription.Field()
    video_shared = VideoSharedSubscription.Field()
    video_duet_created = VideoDuetCreatedSubscription.Field()
    video_stitch_created = VideoStitchCreatedSubscription.Field()

    # Video processing
    video_processing_status = VideoProcessingStatusSubscription.Field()
    video_processing_completed = VideoProcessingCompletedSubscription.Field()
    video_processing_failed = VideoProcessingFailedSubscription.Field()

    # Feeds
    feed_updated = FeedUpdatedSubscription.Field()
    trending_feed_updated = TrendingFeedUpdatedSubscription.Field()
    for_you_feed_updated = ForYouFeedUpdatedSubscription.Field()

    # Sound & effect
    sound_trending = SoundTrendingSubscription.Field()
    effect_trending = EffectTrendingSubscription.Field()