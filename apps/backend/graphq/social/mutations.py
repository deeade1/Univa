# apps/backend/graphq/social/mutations.py
"""
Social domain mutations.

Aligned against the current `social/models.py`. Features whose
models do not exist yet (FriendRequest, Notification,
FriendSuggestionAlgorithm, FriendshipInteraction) are omitted —
add them back once their models/apps are in place.
"""

import graphene
from django.db import transaction
from django.db.models import Avg, F
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from accounts.models import UserProfile

from graphq.social.types import (
    DuetVideoNode,
    FollowNode,
    StitchVideoNode,
    VideoCommentNode,
    VideoContentNode,
    VideoLikeNode,
    VideoShareNode,
    VideoViewNode,
)

from social.models import (
    DuetVideo,
    Follow,
    StitchVideo,
    VideoComment,
    VideoContent,
    VideoLike,
    VideoShare,
    VideoView,
)

# Subscriptions (must exist in graphq/social/subscription.py)
from graphq.social.subscription import (
    VideoLikeAddedSubscription,
    NewVideoCommentSubscription,
    VideoViewCountUpdatedSubscription,
    VideoSharedSubscription,
    VideoDuetCreatedSubscription,
    VideoStitchCreatedSubscription,
    VideoProcessingStatusSubscription,
    VideoProcessingCompletedSubscription,
    VideoProcessingFailedSubscription,
    FeedUpdatedSubscription,
    TrendingFeedUpdatedSubscription,
    ForYouFeedUpdatedSubscription,
    NewVideoPublishedSubscription,
)


# =============================================================================
# Auth / ID helpers
# =============================================================================

class AuthMixin:
    """Reusable authentication and global-ID helpers."""

    @staticmethod
    def require_auth(info):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        return user

    @staticmethod
    def resolve_node(global_id, model):
        """
        Decode a Relay global ID and fetch the matching instance.

        Uses relay.Node.from_global_id which returns (type_name, pk).
        """
        try:
            _, pk = relay.Node.from_global_id(global_id)
        except Exception:
            raise GraphQLError("Invalid ID format.")

        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise GraphQLError(f"{model.__name__} not found.")


# =============================================================================
# Input types
# =============================================================================

class VideoUploadInput(graphene.InputObjectType):
    title = graphene.String()
    description = graphene.String()
    visibility = graphene.String(default_value="public")
    allow_duets = graphene.Boolean(default_value=True)
    allow_stitches = graphene.Boolean(default_value=True)
    allow_comments = graphene.Boolean(default_value=True)
    allow_download = graphene.Boolean(default_value=False)
    allow_remix = graphene.Boolean(default_value=True)
    hashtags = graphene.List(graphene.String)
    mentions = graphene.List(graphene.String)
    scheduled_for = graphene.DateTime()


class VideoUpdateInput(graphene.InputObjectType):
    title = graphene.String()
    description = graphene.String()
    visibility = graphene.String()
    allow_duets = graphene.Boolean()
    allow_stitches = graphene.Boolean()
    allow_comments = graphene.Boolean()
    allow_download = graphene.Boolean()
    allow_remix = graphene.Boolean()
    hashtags = graphene.List(graphene.String)
    mentions = graphene.List(graphene.String)


class CommentInput(graphene.InputObjectType):
    text = graphene.String(required=True)
    parent_comment_id = graphene.ID()


# =============================================================================
# Follow mutations (replace Friend / FriendRequest)
# =============================================================================

class FollowUser(AuthMixin, relay.ClientIDMutation):
    """Follow another user. Toggles off if already following."""

    class Input:
        user_id = graphene.ID(required=True)

    following = graphene.Boolean()
    follow = graphene.Field(FollowNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, user_id):
        me = cls.require_auth(info)

        try:
            _, target_pk = relay.Node.from_global_id(user_id)
        except Exception:
            raise GraphQLError("Invalid user ID.")

        if str(target_pk) == str(me.pk):
            raise GraphQLError("Cannot follow yourself.")

        try:
            target = me.__class__.objects.get(pk=target_pk)
        except me.__class__.DoesNotExist:
            raise GraphQLError("User not found.")

        follow, created = Follow.objects.get_or_create(
            follower=me, following=target
        )

        if not created:
            follow.delete()
            return cls(success=True, following=False, follow=None)

        return cls(success=True, following=True, follow=follow)


class UnfollowUser(AuthMixin, relay.ClientIDMutation):
    """Explicitly unfollow a user."""

    class Input:
        user_id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, user_id):
        me = cls.require_auth(info)

        try:
            _, target_pk = relay.Node.from_global_id(user_id)
        except Exception:
            raise GraphQLError("Invalid user ID.")

        deleted, _ = Follow.objects.filter(
            follower=me, following_id=target_pk
        ).delete()

        if not deleted:
            raise GraphQLError("You are not following this user.")

        return cls(success=True)


# =============================================================================
# Video mutations
# =============================================================================

class UploadVideo(AuthMixin, relay.ClientIDMutation):
    """Create a VideoContent record and queue it for processing."""

    class Input:
        video_file = graphene.String(required=True)  # storage key or base64 ref
        video_data = VideoUploadInput(required=True)

    video = graphene.Field(VideoContentNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_file, video_data):
        me = cls.require_auth(info)

        try:
            video = VideoContent.objects.create(
                user=me,
                title=video_data.get("title", "") or "",
                description=video_data.get("description", "") or "",
                visibility=video_data.get("visibility", "public"),
                allow_duet=video_data.get("allow_duets", True),
                allow_stitch=video_data.get("allow_stitches", True),
                allow_comment=video_data.get("allow_comments", True),
                allow_download=video_data.get("allow_download", False),
                allow_remix=video_data.get("allow_remix", True),
                hashtags=video_data.get("hashtags") or [],
                mentions=video_data.get("mentions") or [],
                status="draft",
            )

            VideoProcessingStatusSubscription.trigger(
                video=video,
                old_status="none",
                new_status="draft",
                progress=0,
                estimated_time=60,
            )

            return cls(
                video=video,
                success=True,
                message="Video uploaded. Processing queued.",
            )

        except Exception as exc:
            VideoProcessingFailedSubscription.trigger(
                video=None,
                error_message=str(exc),
                retry_count=0,
                can_retry=True,
            )
            return cls(
                video=None,
                success=False,
                message=f"Upload failed: {exc}",
            )


class LikeVideo(AuthMixin, relay.ClientIDMutation):
    """Toggle like on a video."""

    class Input:
        video_id = graphene.ID(required=True)
        sentiment = graphene.String(default_value="like")

    video = graphene.Field(VideoContentNode)
    liked = graphene.Boolean()
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_id, sentiment):
        me = cls.require_auth(info)
        video = cls.resolve_node(video_id, VideoContent)

        if video.status != "published":
            raise GraphQLError("Video is not available.")

        like, created = VideoLike.objects.get_or_create(
            user=me,
            video=video,
            defaults={"sentiment": sentiment},
        )

        if not created:
            like.delete()
            # Atomic decrement
            VideoContent.objects.filter(pk=video.pk).update(
                likes_count=F("likes_count") - 1
            )
            liked = False
        else:
            VideoContent.objects.filter(pk=video.pk).update(
                likes_count=F("likes_count") + 1
            )
            liked = True
            VideoLikeAddedSubscription.trigger(video_like=like)

        video.refresh_from_db()
        video.update_engagement_metrics()

        return cls(success=True, liked=liked, video=video)


class AddVideoComment(AuthMixin, relay.ClientIDMutation):
    """Add a comment (or reply) to a video."""

    class Input:
        video_id = graphene.ID(required=True)
        comment_data = CommentInput(required=True)

    comment = graphene.Field(VideoCommentNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_id, comment_data):
        me = cls.require_auth(info)
        video = cls.resolve_node(video_id, VideoContent)

        if video.status != "published":
            raise GraphQLError("Video is not available.")

        if not video.allow_comment:
            raise GraphQLError("Comments are disabled for this video.")

        parent_comment = None
        parent_id = comment_data.get("parent_comment_id")
        if parent_id:
            parent_comment = cls.resolve_node(parent_id, VideoComment)
            if parent_comment.video_id != video.pk:
                raise GraphQLError("Parent comment belongs to another video.")

        comment = VideoComment.objects.create(
            user=me,
            video=video,
            parent_comment=parent_comment,
            text=comment_data["text"],
        )

        VideoContent.objects.filter(pk=video.pk).update(
            comments_count=F("comments_count") + 1
        )
        video.refresh_from_db()
        video.update_engagement_metrics()

        NewVideoCommentSubscription.trigger(comment=comment)

        return cls(comment=comment, success=True)


class TrackVideoView(relay.ClientIDMutation):
    """Record a view / update watch-time metrics."""

    class Input:
        video_id = graphene.ID(required=True)
        watch_time = graphene.Float(required=True)
        progress = graphene.Float(required=True)
        session_id = graphene.String(required=True)

    success = graphene.Boolean()
    views_count = graphene.Int()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, video_id, watch_time, progress, session_id
    ):
        user = info.context.user
        viewer = user if user.is_authenticated else None

        try:
            _, video_pk = relay.Node.from_global_id(video_id)
        except Exception:
            return cls(success=False, views_count=0)

        try:
            video = VideoContent.objects.get(pk=video_pk, status="published")
        except VideoContent.DoesNotExist:
            return cls(success=False, views_count=0)

        view, created = VideoView.objects.get_or_create(
            user=viewer,
            video=video,
            session_id=session_id,
            defaults={
                "watch_time": watch_time,
                "progress": progress,
                "device_info": cls._get_device_info(info.context),
            },
        )

        if not created:
            view.watch_time = max(view.watch_time, watch_time)
            view.progress = max(view.progress, progress)
            view.save(update_fields=["watch_time", "progress"])
        else:
            VideoContent.objects.filter(pk=video.pk).update(
                views_count=F("views_count") + 1
            )
            video.refresh_from_db()
            video.update_engagement_metrics()

            avg_watch_time = (
                VideoView.objects.filter(video=video)
                .aggregate(avg_watch=Avg("watch_time"))["avg_watch"]
                or 0
            )

            VideoViewCountUpdatedSubscription.trigger(
                video=video,
                view_count=video.views_count,
                unique_viewers=VideoView.objects.filter(video=video).count(),
                watch_time_avg=avg_watch_time,
            )

        return cls(success=True, views_count=video.views_count)

    @staticmethod
    def _get_device_info(context):
        request = context
        return {
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "ip_address": request.META.get("REMOTE_ADDR", ""),
        }


class ShareVideo(AuthMixin, relay.ClientIDMutation):
    """Record a share."""

    class Input:
        video_id = graphene.ID(required=True)
        platform = graphene.String(required=True)
        shared_to = graphene.String()

    success = graphene.Boolean()
    shares_count = graphene.Int()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_id, platform, shared_to=None):
        me = cls.require_auth(info)
        video = cls.resolve_node(video_id, VideoContent)

        if video.status != "published":
            raise GraphQLError("Video is not available.")

        share = VideoShare.objects.create(
            user=me,
            video=video,
            platform=platform,
            shared_to=shared_to or "",
        )

        VideoContent.objects.filter(pk=video.pk).update(
            shares_count=F("shares_count") + 1
        )
        video.refresh_from_db()
        video.update_engagement_metrics()

        VideoSharedSubscription.trigger(video_share=share)

        return cls(success=True, shares_count=video.shares_count)


class CreateDuetVideo(AuthMixin, relay.ClientIDMutation):
    """Link two videos as a duet."""

    class Input:
        original_video_id = graphene.ID(required=True)
        duet_video_id = graphene.ID(required=True)
        position = graphene.String(default_value="right")

    duet = graphene.Field(DuetVideoNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, original_video_id, duet_video_id, position
    ):
        me = cls.require_auth(info)

        original_video = cls.resolve_node(original_video_id, VideoContent)
        if original_video.status != "published":
            raise GraphQLError("Original video is not published.")
        if not original_video.allow_duet:
            raise GraphQLError("Duets are not allowed for this video.")

        duet_video = cls.resolve_node(duet_video_id, VideoContent)
        if duet_video.user_id != me.pk:
            raise GraphQLError("You can only duet with your own video.")

        duet = DuetVideo.objects.create(
            original_video=original_video,
            duet_video=duet_video,
            position=position,
        )

        VideoDuetCreatedSubscription.trigger(duet_video=duet)

        return cls(duet=duet, success=True)


class CreateStitchVideo(AuthMixin, relay.ClientIDMutation):
    """Link two videos as a stitch."""

    class Input:
        original_video_id = graphene.ID(required=True)
        stitch_video_id = graphene.ID(required=True)
        clip_start = graphene.Float(default_value=0)
        clip_duration = graphene.Float(default_value=15)

    stitch = graphene.Field(StitchVideoNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        original_video_id,
        stitch_video_id,
        clip_start=0,
        clip_duration=15,
    ):
        me = cls.require_auth(info)

        original_video = cls.resolve_node(original_video_id, VideoContent)
        if original_video.status != "published":
            raise GraphQLError("Original video is not published.")
        if not original_video.allow_stitch:
            raise GraphQLError("Stitches are not allowed for this video.")

        stitch_video = cls.resolve_node(stitch_video_id, VideoContent)
        if stitch_video.user_id != me.pk:
            raise GraphQLError("You can only stitch with your own video.")

        stitch = StitchVideo.objects.create(
            original_video=original_video,
            stitch_video=stitch_video,
            clip_start=clip_start,
            clip_duration=clip_duration,
        )

        VideoStitchCreatedSubscription.trigger(stitch_video=stitch)

        return cls(stitch=stitch, success=True)


class UpdateVideo(AuthMixin, relay.ClientIDMutation):
    """Update video metadata. Owner only."""

    class Input:
        video_id = graphene.ID(required=True)
        video_data = VideoUpdateInput(required=True)

    video = graphene.Field(VideoContentNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_id, video_data):
        me = cls.require_auth(info)
        video = cls.resolve_node(video_id, VideoContent)

        if video.user_id != me.pk:
            raise GraphQLError("Not authorized to edit this video.")

        field_map = {
            "title": "title",
            "description": "description",
            "visibility": "visibility",
            "allow_duets": "allow_duet",
            "allow_stitches": "allow_stitch",
            "allow_comments": "allow_comment",
            "allow_download": "allow_download",
            "allow_remix": "allow_remix",
            "hashtags": "hashtags",
            "mentions": "mentions",
        }

        updated = []
        for input_key, model_field in field_map.items():
            if input_key in video_data and video_data[input_key] is not None:
                setattr(video, model_field, video_data[input_key])
                updated.append(model_field)

        if updated:
            video.save(update_fields=updated + ["updated_at"])

        return cls(video=video, success=True)


class DeleteVideo(AuthMixin, relay.ClientIDMutation):
    """Soft-delete (archive) a video. Owner only."""

    class Input:
        video_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, video_id):
        me = cls.require_auth(info)
        video = cls.resolve_node(video_id, VideoContent)

        if video.user_id != me.pk:
            raise GraphQLError("Not authorized to delete this video.")

        video.status = "archived"
        video.save(update_fields=["status", "updated_at"])

        return cls(success=True, message="Video archived successfully.")


class PinComment(AuthMixin, relay.ClientIDMutation):
    """Pin/unpin a comment. Video owner only."""

    class Input:
        comment_id = graphene.ID(required=True)
        pin = graphene.Boolean(required=True)

    comment = graphene.Field(VideoCommentNode)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, comment_id, pin):
        me = cls.require_auth(info)
        comment = cls.resolve_node(comment_id, VideoComment)

        if comment.video.user_id != me.pk:
            raise GraphQLError("Not authorized to pin comments on this video.")

        comment.is_pinned = pin
        comment.save(update_fields=["is_pinned", "updated_at"])

        return cls(comment=comment, success=True)


# =============================================================================
# Subscription service helpers
# =============================================================================

class SubscriptionService:
    """Fan-out helpers used by async processing tasks."""

    @staticmethod
    def trigger_video_published(video):
        if video.status != "published":
            return

        followers = Follow.objects.filter(
            following=video.user
        ).select_related("follower")

        for follow in followers:
            FeedUpdatedSubscription.trigger(
                video=video,
                user_id=follow.follower_id,
                feed_type="following",
                position=0,
            )
            NewVideoPublishedSubscription.trigger(
                video=video,
                follower=follow.follower,
            )

        viral_score = video.viral_score or 0
        if viral_score > 50:
            TrendingFeedUpdatedSubscription.trigger(
                trending_item=None,
                rank_change=1,
                viral_score=viral_score,
            )


# =============================================================================
# Registration
# =============================================================================

class SocialMutations(graphene.ObjectType):
    # Follow graph
    follow_user = FollowUser.Field()
    unfollow_user = UnfollowUser.Field()

    # Video
    upload_video = UploadVideo.Field()
    like_video = LikeVideo.Field()
    add_video_comment = AddVideoComment.Field()
    track_video_view = TrackVideoView.Field()
    share_video = ShareVideo.Field()
    create_duet_video = CreateDuetVideo.Field()
    create_stitch_video = CreateStitchVideo.Field()
    update_video = UpdateVideo.Field()
    delete_video = DeleteVideo.Field()
    pin_comment = PinComment.Field()