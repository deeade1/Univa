# apps/backend/social/admin.py

"""
Enhanced Admin Interface for Social App
"""

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, F

from .models import (
    # Profile
    SocialProfile,
    # Follow
    Follow,
    # Video
    VideoContent,
    # Engagement
    VideoLike,
    VideoComment,
    VideoView,
    VideoShare,
    VideoSave,
    # Interactions
    DuetVideo,
    StitchVideo,
    # Processing
    VideoProcessingQueue,
    # Feed
    TrendingFeed,
    # Music
    Sound,
    Effect,
    # Recommendations
    UserInterest,
    ContentCategory,
    # Moderation
    VideoReport,
    # Analytics
    UserActivity,
)


# =============================================================================
# FILTERS
# =============================================================================

class ExpiredFilter(SimpleListFilter):
    title = 'expired status'
    parameter_name = 'expired'

    def lookups(self, request, model_admin):
        return (
            ('expired', 'Expired'),
            ('active', 'Active'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'expired':
            return queryset.filter(expires_at__lt=timezone.now())
        if self.value() == 'active':
            return queryset.filter(expires_at__gte=timezone.now())
        return queryset


class EngagementFilter(SimpleListFilter):
    title = 'engagement level'
    parameter_name = 'engagement'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High Engagement (>50)'),
            ('medium', 'Medium Engagement (10-50)'),
            ('low', 'Low Engagement (<10)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(engagement_rate__gt=50)
        if self.value() == 'medium':
            return queryset.filter(engagement_rate__range=(10, 50))
        if self.value() == 'low':
            return queryset.filter(engagement_rate__lt=10)
        return queryset


class ViralScoreFilter(SimpleListFilter):
    title = 'viral score'
    parameter_name = 'viral_score'

    def lookups(self, request, model_admin):
        return (
            ('viral', 'Viral (>80)'),
            ('trending', 'Trending (50-80)'),
            ('normal', 'Normal (<50)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'viral':
            return queryset.filter(viral_score__gt=80)
        if self.value() == 'trending':
            return queryset.filter(viral_score__range=(50, 80))
        if self.value() == 'normal':
            return queryset.filter(viral_score__lt=50)
        return queryset


# =============================================================================
# INLINES
# =============================================================================

class VideoLikeInline(admin.TabularInline):
    model = VideoLike
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'sentiment', 'created_at']
    raw_id_fields = ['user']


class VideoCommentInline(admin.TabularInline):
    model = VideoComment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['user', 'text', 'likes_count', 'is_pinned', 'moderation_status', 'created_at']
    raw_id_fields = ['user']
    max_num = 20


class VideoViewInline(admin.TabularInline):
    model = VideoView
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'watch_time', 'progress', 'completed', 'created_at']
    raw_id_fields = ['user']
    max_num = 20


class VideoSaveInline(admin.TabularInline):
    model = VideoSave
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'collection', 'created_at']
    raw_id_fields = ['user']


class VideoReportInline(admin.TabularInline):
    model = VideoReport
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['reported_by', 'reason', 'status', 'created_at']
    raw_id_fields = ['reported_by']


class DuetVideoInline(admin.TabularInline):
    model = DuetVideo
    fk_name = 'original_video'
    extra = 0
    readonly_fields = ['created_at']
    fields = ['duet_video', 'position', 'created_at']
    raw_id_fields = ['duet_video']


class StitchVideoInline(admin.TabularInline):
    model = StitchVideo
    fk_name = 'original_video'
    extra = 0
    readonly_fields = ['created_at']
    fields = ['stitch_video', 'clip_start', 'clip_duration', 'created_at']
    raw_id_fields = ['stitch_video']


# =============================================================================
# SOCIAL PROFILE ADMIN
# =============================================================================

@admin.register(SocialProfile)
class SocialProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'display_name', 'followers_count', 'following_count',
        'videos_count', 'likes_count', 'is_verified', 'is_private', 'created_at'
    ]
    list_filter = ['is_verified', 'is_private', 'allow_duet', 'allow_stitch', 'created_at']
    search_fields = ['user__email', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'created_at', 'updated_at', 'followers_count', 'following_count',
        'videos_count', 'likes_count', 'verified_at'
    ]
    raw_id_fields = ['user']
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Social Stats', {
            'fields': ['followers_count', 'following_count', 'videos_count', 'likes_count']
        }),
        ('Verification', {
            'fields': ['is_verified', 'verified_at']
        }),
        ('Privacy & Permissions', {
            'fields': ['is_private', 'allow_tagging', 'allow_duet', 'allow_stitch', 'allow_comment']
        }),
        ('Notifications', {
            'fields': ['push_notifications_enabled']
        }),
        ('Vector Data', {
            'fields': ['interest_vector'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['verify_users', 'unverify_users']

    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Display Name'

    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f"Verified {updated} users")
    verify_users.short_description = "Verify selected users"

    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False, verified_at=None)
        self.message_user(request, f"Unverified {updated} users")
    unverify_users.short_description = "Unverify selected users"


# =============================================================================
# FOLLOW ADMIN
# =============================================================================

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['follower__email', 'following__email', 'follower__username', 'following__username']
    readonly_fields = ['created_at', 'updated_at', 'id']
    raw_id_fields = ['follower', 'following']
    date_hierarchy = 'created_at'
    actions = ['unfollow_selected']

    def unfollow_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Removed {count} follow relationships")
    unfollow_selected.short_description = "Unfollow selected relationships"


# =============================================================================
# VIDEO CONTENT ADMIN
# =============================================================================

@admin.register(VideoContent)
class VideoContentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'status', 'visibility', 'views_count', 'likes_count',
        'comments_count', 'shares_count', 'engagement_rate', 'viral_score', 'created_at'
    ]
    list_filter = [
        'status', 'visibility', 'allow_duet', 'allow_stitch', 'allow_comment',
        'created_at', 'published_at', EngagementFilter, ViralScoreFilter
    ]
    search_fields = ['title', 'description', 'user__email', 'user__username', 'hashtags']
    readonly_fields = [
        'created_at', 'updated_at', 'published_at', 'views_count', 'likes_count',
        'comments_count', 'shares_count', 'saves_count', 'reports_count',
        'engagement_rate', 'viral_score', 'avg_watch_time', 'completion_rate'
    ]
    raw_id_fields = ['user', 'sound']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Basic Info', {
            'fields': ['user', 'title', 'description', 'hashtags', 'mentions', 'status', 'visibility']
        }),
        ('Video File', {
            'fields': ['video_file', 'duration', 'aspect_ratio', 'video_urls', 'thumbnail', 'thumbnails']
        }),
        ('Sound', {
            'fields': ['sound', 'sound_start_time', 'sound_end_time'],
            'classes': ['collapse']
        }),
        ('Permissions', {
            'fields': ['allow_duet', 'allow_stitch', 'allow_comment', 'allow_download', 'allow_remix'],
            'classes': ['collapse']
        }),
        ('Engagement Metrics', {
            'fields': [
                'views_count', 'likes_count', 'comments_count', 'shares_count',
                'saves_count', 'reports_count', 'engagement_rate', 'viral_score',
                'avg_watch_time', 'completion_rate'
            ]
        }),
        ('Vector Data', {
            'fields': ['interest_vector', 'content_vector'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'published_at'],
            'classes': ['collapse']
        })
    ]
    inlines = [
        VideoLikeInline, VideoCommentInline, VideoViewInline, VideoSaveInline,
        VideoReportInline, DuetVideoInline, StitchVideoInline
    ]
    actions = [
        'update_engagement_metrics', 'publish_videos', 'archive_videos',
        'block_videos', 'unblock_videos'
    ]

    def update_engagement_metrics(self, request, queryset):
        for video in queryset:
            video.update_engagement_metrics()
        self.message_user(request, f"Updated engagement metrics for {queryset.count()} videos")
    update_engagement_metrics.short_description = "Update engagement metrics"

    def publish_videos(self, request, queryset):
        updated = queryset.filter(status='draft').update(
            status='published',
            published_at=timezone.now()
        )
        self.message_user(request, f"Published {updated} videos")
    publish_videos.short_description = "Publish selected draft videos"

    def archive_videos(self, request, queryset):
        updated = queryset.update(status='archived')
        self.message_user(request, f"Archived {updated} videos")
    archive_videos.short_description = "Archive selected videos"

    def block_videos(self, request, queryset):
        updated = queryset.update(status='blocked')
        self.message_user(request, f"Blocked {updated} videos")
    block_videos.short_description = "Block selected videos"

    def unblock_videos(self, request, queryset):
        updated = queryset.filter(status='blocked').update(status='published')
        self.message_user(request, f"Unblocked {updated} videos")
    unblock_videos.short_description = "Unblock selected videos"


# =============================================================================
# VIDEO ENGAGEMENT ADMIN
# =============================================================================

@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'sentiment', 'created_at']
    list_filter = ['sentiment', 'created_at']
    search_fields = ['user__email', 'user__username', 'video__title']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['user', 'video']
    date_hierarchy = 'created_at'


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'text_preview', 'likes_count', 'is_pinned', 'moderation_status', 'created_at']
    list_filter = ['is_pinned', 'is_removed', 'is_edited', 'moderation_status', 'created_at']
    search_fields = ['user__email', 'user__username', 'video__title', 'text']
    readonly_fields = ['created_at', 'updated_at', 'id']
    raw_id_fields = ['user', 'video', 'parent_comment']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Comment', {
            'fields': ['user', 'video', 'parent_comment', 'text']
        }),
        ('Moderation', {
            'fields': ['is_pinned', 'is_removed', 'is_edited', 'moderation_status']
        }),
        ('Metrics', {
            'fields': ['likes_count']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        })
    ]
    actions = ['pin_comments', 'unpin_comments', 'approve_comments', 'reject_comments', 'remove_comments']

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text'

    def pin_comments(self, request, queryset):
        queryset.update(is_pinned=True)
        self.message_user(request, f"Pinned {queryset.count()} comments")
    pin_comments.short_description = "Pin selected comments"

    def unpin_comments(self, request, queryset):
        queryset.update(is_pinned=False)
        self.message_user(request, f"Unpinned {queryset.count()} comments")
    unpin_comments.short_description = "Unpin selected comments"

    def approve_comments(self, request, queryset):
        queryset.update(moderation_status='approved')
        self.message_user(request, f"Approved {queryset.count()} comments")
    approve_comments.short_description = "Approve selected comments"

    def reject_comments(self, request, queryset):
        queryset.update(moderation_status='rejected')
        self.message_user(request, f"Rejected {queryset.count()} comments")
    reject_comments.short_description = "Reject selected comments"

    def remove_comments(self, request, queryset):
        queryset.update(is_removed=True)
        self.message_user(request, f"Removed {queryset.count()} comments")
    remove_comments.short_description = "Remove selected comments"


@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'watch_time', 'progress', 'completed', 'created_at']
    list_filter = ['completed', 'created_at']
    search_fields = ['user__email', 'video__title', 'session_id']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['user', 'video']
    date_hierarchy = 'created_at'


@admin.register(VideoShare)
class VideoShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'platform', 'shared_to', 'created_at']
    list_filter = ['platform', 'created_at']
    search_fields = ['user__email', 'video__title', 'platform', 'shared_to']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['user', 'video']
    date_hierarchy = 'created_at'


@admin.register(VideoSave)
class VideoSaveAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'collection', 'created_at']
    list_filter = ['collection', 'created_at']
    search_fields = ['user__email', 'video__title', 'collection']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['user', 'video']
    date_hierarchy = 'created_at'


# =============================================================================
# VIDEO INTERACTION ADMIN
# =============================================================================

@admin.register(DuetVideo)
class DuetVideoAdmin(admin.ModelAdmin):
    list_display = ['original_video', 'duet_video', 'position', 'created_at']
    list_filter = ['position', 'created_at']
    search_fields = ['original_video__title', 'duet_video__title']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['original_video', 'duet_video']


@admin.register(StitchVideo)
class StitchVideoAdmin(admin.ModelAdmin):
    list_display = ['original_video', 'stitch_video', 'clip_start', 'clip_duration', 'created_at']
    list_filter = ['created_at']
    search_fields = ['original_video__title', 'stitch_video__title']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['original_video', 'stitch_video']


# =============================================================================
# VIDEO PROCESSING ADMIN
# =============================================================================

@admin.register(VideoProcessingQueue)
class VideoProcessingQueueAdmin(admin.ModelAdmin):
    list_display = ['video', 'status', 'priority', 'retry_count', 'created_at', 'started_at', 'completed_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['video__title', 'error_message']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'id']
    raw_id_fields = ['video']
    fieldsets = [
        ('Processing Info', {
            'fields': ['video', 'status', 'priority']
        }),
        ('Retry Info', {
            'fields': ['retry_count', 'max_retries']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'started_at', 'completed_at']
        }),
        ('Error Details', {
            'fields': ['error_message', 'processing_log'],
            'classes': ['collapse']
        })
    ]
    actions = ['retry_processing', 'cancel_processing']

    def retry_processing(self, request, queryset):
        queryset.update(status='pending', error_message='', processing_log=[], retry_count=0)
        self.message_user(request, f"Queued {queryset.count()} videos for reprocessing")
    retry_processing.short_description = "Retry processing for selected videos"

    def cancel_processing(self, request, queryset):
        queryset.update(status='failed', error_message='Cancelled by admin')
        self.message_user(request, f"Cancelled {queryset.count()} processing tasks")
    cancel_processing.short_description = "Cancel selected processing tasks"


# =============================================================================
# FEED ADMIN
# =============================================================================

@admin.register(TrendingFeed)
class TrendingFeedAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'rank_score', 'reason', 'created_at', 'expires_at']
    list_filter = ['created_at', 'expires_at', ExpiredFilter]
    search_fields = ['user__email', 'video__title', 'reason']
    readonly_fields = ['created_at', 'id']
    raw_id_fields = ['user', 'video']
    ordering = ['-rank_score']
    actions = ['clear_expired_feeds']

    def clear_expired_feeds(self, request, queryset):
        count = queryset.filter(expires_at__lt=timezone.now()).delete()[0]
        self.message_user(request, f"Cleared {count} expired feed entries")
    clear_expired_feeds.short_description = "Clear expired feed entries"


# =============================================================================
# MUSIC & AUDIO ADMIN
# =============================================================================

@admin.register(Sound)
class SoundAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'duration', 'usage_count', 'is_verified', 'is_trending', 'created_by', 'created_at']
    list_filter = ['is_verified', 'is_original', 'is_trending', 'license_type', 'created_at']
    search_fields = ['title', 'artist', 'album', 'created_by__email']
    readonly_fields = ['usage_count', 'created_at', 'updated_at', 'id']
    raw_id_fields = ['created_by']
    fieldsets = [
        ('Sound Info', {
            'fields': ['title', 'artist', 'album', 'audio_file', 'duration']
        }),
        ('Visualization', {
            'fields': ['waveform']
        }),
        ('Metadata', {
            'fields': ['usage_count', 'is_original', 'is_verified', 'is_trending', 'created_by']
        }),
        ('Licensing', {
            'fields': ['license_type']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['verify_sounds', 'mark_as_trending']

    def verify_sounds(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"Verified {queryset.count()} sounds")
    verify_sounds.short_description = "Verify selected sounds"

    def mark_as_trending(self, request, queryset):
        queryset.update(is_trending=True)
        self.message_user(request, f"Marked {queryset.count()} sounds as trending")
    mark_as_trending.short_description = "Mark selected sounds as trending"


# =============================================================================
# EFFECTS ADMIN
# =============================================================================

@admin.register(Effect)
class EffectAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'usage_count', 'is_trending', 'is_verified', 'is_ar', 'created_at']
    list_filter = ['category', 'is_trending', 'is_verified', 'is_ar', 'created_at']
    search_fields = ['name', 'category']
    readonly_fields = ['usage_count', 'created_at', 'id']
    raw_id_fields = ['created_by']
    fieldsets = [
        ('Effect Info', {
            'fields': ['name', 'category', 'preview_url', 'preview_video']
        }),
        ('Settings', {
            'fields': ['is_trending', 'is_verified', 'is_ar', 'parameters']
        }),
        ('Usage', {
            'fields': ['usage_count', 'created_by']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['verify_effects', 'mark_as_trending']

    def verify_effects(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"Verified {queryset.count()} effects")
    verify_effects.short_description = "Verify selected effects"

    def mark_as_trending(self, request, queryset):
        queryset.update(is_trending=True)
        self.message_user(request, f"Marked {queryset.count()} effects as trending")
    mark_as_trending.short_description = "Mark selected effects as trending"


# =============================================================================
# RECOMMENDATION ADMIN
# =============================================================================

@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_watch_time', 'avg_session_duration', 'engagement_score', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['updated_at', 'id']
    raw_id_fields = ['user']
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Preferences', {
            'fields': ['interest_vector', 'content_preferences', 'watch_patterns', 'category_preferences', 'creator_preferences']
        }),
        ('Analytics', {
            'fields': ['total_watch_time', 'avg_session_duration', 'engagement_score']
        }),
        ('Metadata', {
            'fields': ['updated_at']
        })
    ]


@admin.register(ContentCategory)
class ContentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'video_count', 'popularity_score', 'created_at']
    list_filter = ['created_at', 'parent']
    search_fields = ['name', 'description', 'slug']
    readonly_fields = ['created_at', 'updated_at', 'id']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = [
        ('Category Info', {
            'fields': ['name', 'slug', 'description', 'icon', 'parent']
        }),
        ('Metrics', {
            'fields': ['popularity_score', 'video_count']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['recalculate_video_counts']

    def recalculate_video_counts(self, request, queryset):
        for category in queryset:
            category.video_count = VideoContent.objects.filter(
                hashtags__contains=[category.slug],
                status='published'
            ).count()
            category.save()
        self.message_user(request, f"Recalculated video counts for {queryset.count()} categories")
    recalculate_video_counts.short_description = "Recalculate video counts"


# =============================================================================
# MODERATION ADMIN
# =============================================================================

@admin.register(VideoReport)
class VideoReportAdmin(admin.ModelAdmin):
    list_display = ['video', 'reported_by', 'reason', 'status', 'created_at', 'reviewed_by']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['video__title', 'reported_by__email', 'description']
    readonly_fields = ['created_at', 'updated_at', 'id']
    raw_id_fields = ['video', 'reported_by', 'reviewed_by']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Report Info', {
            'fields': ['video', 'reported_by', 'reason', 'description']
        }),
        ('Review', {
            'fields': ['status', 'reviewed_by', 'action_taken']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['mark_as_reviewed', 'mark_as_actioned', 'dismiss_reports']

    def mark_as_reviewed(self, request, queryset):
        queryset.update(status='reviewed', reviewed_by=request.user)
        self.message_user(request, f"Marked {queryset.count()} reports as reviewed")
    mark_as_reviewed.short_description = "Mark selected reports as reviewed"

    def mark_as_actioned(self, request, queryset):
        queryset.update(status='actioned', reviewed_by=request.user)
        self.message_user(request, f"Marked {queryset.count()} reports as actioned")
    mark_as_actioned.short_description = "Mark selected reports as actioned"

    def dismiss_reports(self, request, queryset):
        queryset.update(status='dismissed', reviewed_by=request.user)
        self.message_user(request, f"Dismissed {queryset.count()} reports")
    dismiss_reports.short_description = "Dismiss selected reports"


# =============================================================================
# ANALYTICS ADMIN
# =============================================================================

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'video', 'target_user', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email', 'video__title', 'target_user__email']
    readonly_fields = ['created_at', 'id', 'metadata']
    raw_id_fields = ['user', 'video', 'target_user']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        # Activities are auto-generated, not manually added
        return False

    def has_change_permission(self, request, obj=None):
        # Activities are read-only
        return False