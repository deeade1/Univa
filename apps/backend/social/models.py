# apps/backend/social/models.py

"""
Enhanced Social Models for Univa - TikTok-like Social Platform
Integrates with canonical User model and existing UserProfile
"""

import os
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import connection, models, transaction
from django.db.models import Count, F, Func, Q, Value, Avg, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from pgvector.django import VectorField

# Import the canonical User model
from django.contrib.auth import get_user_model
User = get_user_model()

# Import the canonical UserProfile if it exists
try:
    from accounts.models import UserProfile
except ImportError:
    # If UserProfile doesn't exist in accounts, we'll use a social profile extension
    UserProfile = None


# =============================================================================
# SOCIAL PROFILE EXTENSION (Optional - if UserProfile exists in accounts)
# =============================================================================

class SocialProfile(models.Model):
    """
    Social-specific profile extension.
    If canonical UserProfile exists in accounts, this extends it.
    Otherwise, this serves as the main profile.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='social_profile'
    )
    
    # Social-specific fields (not in canonical UserProfile)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    videos_count = models.PositiveIntegerField(default=0)
    
    # Social preferences
    allow_tagging = models.BooleanField(default=True)
    allow_duet = models.BooleanField(default=True)
    allow_stitch = models.BooleanField(default=True)
    allow_comment = models.BooleanField(default=True)
    push_notifications_enabled = models.BooleanField(default=True)
    
    # Social verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Social privacy
    is_private = models.BooleanField(default=False)
    
    # Vector for recommendations
    interest_vector = VectorField(dimensions=512, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_profiles'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['followers_count']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['is_private']),
        ]
    
    def __str__(self):
        return f"Social Profile for {self.user.email}"
    
    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create a social profile for a user."""
        profile, created = cls.objects.get_or_create(user=user)
        return profile



class Follow(models.Model):
    """Follow relationship between users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_follows'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                condition=~Q(follower=F('following')),
                name='follower_not_following_self'
            ),
        ]
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['following', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.follower} -> {self.following}"
    
    @classmethod
    def toggle_follow(cls, follower, following):
        """Toggle follow/unfollow."""
        if follower == following:
            raise ValueError("Cannot follow yourself")
        
        follow, created = cls.objects.get_or_create(
            follower=follower,
            following=following
        )
        
        if not created:
            follow.delete()
            return False  # Unfollowed
        
        return True  # Followed


# =============================================================================
# VIDEO CONTENT MODELS
# =============================================================================

class VideoContent(models.Model):
    """Enhanced video content model."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
        ('reported', 'Reported'),
        ('blocked', 'Blocked'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    
    # Basic info
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    hashtags = models.JSONField(default=list)
    mentions = models.JSONField(default=list)  # User mentions
    
    # Status & visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Video file
    video_file = models.FileField(upload_to='videos/', null=True, blank=True)
    duration = models.FloatField(default=0)  # in seconds
    aspect_ratio = models.CharField(max_length=20, default='9:16')
    video_urls = models.JSONField(default=dict)  # Different quality variants
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    thumbnails = models.JSONField(default=list)  # Multiple thumbnail sizes
    
    # Permissions
    allow_duet = models.BooleanField(default=True)
    allow_stitch = models.BooleanField(default=True)
    allow_comment = models.BooleanField(default=True)
    allow_download = models.BooleanField(default=False)
    allow_remix = models.BooleanField(default=True)
    
    # Engagement counters (denormalized)
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)
    reports_count = models.PositiveIntegerField(default=0)
    
    # Algorithmic scores
    engagement_rate = models.FloatField(default=0.0)
    viral_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)
    
    # Vector embeddings
    content_vector = VectorField(dimensions=512, null=True, blank=True)
    interest_vector = VectorField(dimensions=512, null=True, blank=True)
    
    # Music/Sound
    sound = models.ForeignKey(
        'Sound',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='videos'
    )
    sound_start_time = models.FloatField(default=0)
    sound_end_time = models.FloatField(null=True, blank=True)
    
    # Engagement metrics (denormalized)
    avg_watch_time = models.FloatField(default=0.0)
    completion_rate = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_videos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['viral_score', 'created_at']),
            models.Index(fields=['likes_count', 'created_at']),
            models.Index(fields=['views_count', 'created_at']),
            models.Index(fields=['engagement_rate']),
            GinIndex(fields=['hashtags'], name='video_hashtags_gin_idx'),
            GinIndex(fields=['mentions'], name='video_mentions_gin_idx'),
        ]
    
    def __str__(self):
        return f"{self.title or 'Untitled'} by {self.user.email}"
    
    def update_engagement_metrics(self):
        """Update engagement metrics based on current counts."""
        if self.views_count > 0:
            self.engagement_rate = (
                (self.likes_count * 1.0 + 
                 self.comments_count * 2.0 + 
                 self.shares_count * 3.0 + 
                 self.saves_count * 2.0) / self.views_count
            ) * 100
        
        if self.views_count > 0:
            share_ratio = self.shares_count / self.views_count
            self.viral_score = self.engagement_rate * (1 + share_ratio * 2)
        
        self.save()
    
    def increment_view(self, user=None, watch_time=None, progress=None):
        """Increment view count and update metrics."""
        self.views_count = F('views_count') + 1
        
        if watch_time:
            self.avg_watch_time = (self.avg_watch_time * (self.views_count - 1) + watch_time) / self.views_count
            self.completion_rate = min(100.0, (watch_time / self.duration) * 100 if self.duration > 0 else 0)
        
        self.save()
        
        VideoView.objects.create(
            video=self,
            user=user,
            watch_time=watch_time or 0,
            progress=progress or 0,
            session_id=user.id if user else str(uuid.uuid4())
        )


# =============================================================================
# VIDEO ENGAGEMENT MODELS (Keep as is - these are well structured)
# =============================================================================

class VideoLike(models.Model):
    """Video likes with sentiment tracking."""
    
    SENTIMENT_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('laugh', 'Laugh'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='likes')
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_likes'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'video'], name='unique_video_like')
        ]
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['sentiment']),
        ]


class VideoComment(models.Model):
    """Video comments with threading and moderation."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='comments')
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    text = models.TextField(max_length=1500)
    likes_count = models.PositiveIntegerField(default=0)
    
    is_pinned = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    moderation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('flagged', 'Flagged'),
        ],
        default='approved'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_comments'
        ordering = ['-is_pinned', 'created_at']
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['parent_comment']),
            models.Index(fields=['moderation_status']),
        ]


class VideoView(models.Model):
    """Track video views with watch time analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='views')
    session_id = models.CharField(max_length=255, db_index=True)
    watch_time = models.FloatField(default=0)
    progress = models.FloatField(default=0)
    completed = models.BooleanField(default=False)
    
    device_type = models.CharField(max_length=50, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=20, blank=True)
    device_info = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_views'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
        ]



class VideoShare(models.Model):
    """Track video shares"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='shares')
    platform = models.CharField(max_length=50, help_text="Platform shared to")
    shared_to = models.CharField(max_length=255, blank=True, help_text="Specific destination")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]



class DuetVideo(models.Model):
    """Duet video relationship"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='duets_received')
    duet_video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='duets_created')
    position = models.CharField(max_length=20, default='right', help_text="Layout position")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            
            models.UniqueConstraint(
                fields=['original_video', 'duet_video'],
                name='unique_original_duet_video'
            ),
        ]
        

class StitchVideo(models.Model):
    """Stitch video relationship"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='stitches_received')
    stitch_video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='stitches_created')
    clip_start = models.FloatField(default=0, help_text="Start time in original video")
    clip_duration = models.FloatField(default=15, help_text="Clip duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            
            models.UniqueConstraint(
                fields=['original_video', 'stitch_video'],
                name='unique_original_stitch_video'
            ),
        ]
        


# =============================================================================
# VIDEO SAVE (Bookmarks)
# =============================================================================

class VideoSave(models.Model):
    """Saved videos (bookmarks) for users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='saves')
    collection = models.CharField(max_length=100, blank=True, default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_saves'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'video'], name='unique_video_save')
        ]
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['collection']),
        ]


# =============================================================================
# MODERATION MODELS
# =============================================================================

class VideoReport(models.Model):
    """User reports for content moderation."""
    
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Infringement'),
        ('illegal', 'Illegal Content'),
        ('misinformation', 'Misinformation'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('actioned', 'Actioned'),
        ('dismissed', 'Dismissed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviewed_reports')
    action_taken = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'status']),
            models.Index(fields=['reported_by', 'created_at']),
            models.Index(fields=['reason']),
        ]


# =============================================================================
# ANALYTICS & METRICS
# =============================================================================

class UserActivity(models.Model):
    """Track user activity for analytics."""
    
    ACTIVITY_TYPES = [
        ('view', 'Video View'),
        ('like', 'Video Like'),
        ('comment', 'Video Comment'),
        ('share', 'Video Share'),
        ('save', 'Video Save'),
        ('follow', 'Follow'),
        ('upload', 'Video Upload'),
        ('duet', 'Duet'),
        ('stitch', 'Stitch'),
        ('report', 'Report'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    video = models.ForeignKey(VideoContent, on_delete=models.SET_NULL, null=True, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_activity')
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type', 'created_at']),
            models.Index(fields=['video', 'activity_type']),
            models.Index(fields=['created_at']),
        ]


# =============================================================================
# RECOMMENDATION & FEED MODELS
# =============================================================================

class TrendingFeed(models.Model):
    """Cached trending feed for users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trending_feeds',
        null=True,
        blank=True
    )
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='feed_entries')
    rank_score = models.FloatField(default=0.0)
    reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'social_trending_feed'
        ordering = ['-rank_score']
        indexes = [
            models.Index(fields=['user', 'rank_score']),
            models.Index(fields=['rank_score', 'created_at']),
            models.Index(fields=['expires_at']),
        ]


class UserInterest(models.Model):
    """User interest vector and preferences."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interests')
    
    interest_vector = VectorField(dimensions=512, null=True, blank=True)
    
    content_preferences = models.JSONField(default=dict)
    watch_patterns = models.JSONField(default=dict)
    category_preferences = models.JSONField(default=dict)
    creator_preferences = models.JSONField(default=dict)
    
    total_watch_time = models.FloatField(default=0)
    avg_session_duration = models.FloatField(default=0)
    engagement_score = models.FloatField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_user_interests'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['engagement_score']),
        ]
    
    def __str__(self):
        return f"Interests for {self.user.email}"


# =============================================================================
# VIDEO PROCESSING
# =============================================================================

class VideoProcessingQueue(models.Model):
    """Queue for video processing tasks."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.OneToOneField(VideoContent, on_delete=models.CASCADE, related_name='processing_queue')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    processing_log = models.JSONField(default=list)
    
    class Meta:
        db_table = 'social_processing_queue'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['video']),
        ]


# =============================================================================
# MUSIC & AUDIO MODELS
# =============================================================================

class Sound(models.Model):
    """Music and sound effects."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, blank=True)
    album = models.CharField(max_length=255, blank=True)
    audio_file = models.FileField(upload_to='sounds/')
    duration = models.FloatField()
    waveform = models.JSONField(default=list)
    usage_count = models.PositiveIntegerField(default=0)
    is_original = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sounds')
    
    license_type = models.CharField(
        max_length=50,
        choices=[
            ('royalty_free', 'Royalty Free'),
            ('creative_commons', 'Creative Commons'),
            ('commercial', 'Commercial'),
            ('custom', 'Custom'),
        ],
        default='royalty_free'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_sounds'
        ordering = ['-usage_count']
        indexes = [
            models.Index(fields=['artist', 'title']),
            models.Index(fields=['usage_count', 'created_at']),
            models.Index(fields=['is_trending', 'is_verified']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.artist or 'Unknown'}"


class Effect(models.Model):
    """Video effects and filters."""
    
    CATEGORY_CHOICES = [
        ('beauty', 'Beauty'),
        ('funny', 'Funny'),
        ('ar', 'AR Effect'),
        ('filter', 'Filter'),
        ('transition', 'Transition'),
        ('text', 'Text Effect'),
        ('sticker', 'Sticker'),
        ('green_screen', 'Green Screen'),
        ('special', 'Special Effect'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    preview_url = models.URLField(max_length=500, blank=True)
    preview_video = models.FileField(upload_to='effect_previews/', null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_trending = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_ar = models.BooleanField(default=False)
    parameters = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_effects'
        ordering = ['-usage_count']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['usage_count', 'created_at']),
            models.Index(fields=['is_trending', 'category']),
            models.Index(fields=['is_ar']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


# =============================================================================
# CONTENT CATEGORY
# =============================================================================

class ContentCategory(models.Model):
    """Content categories for organization and recommendation."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    popularity_score = models.FloatField(default=0.0)
    video_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_categories'
        ordering = ['-popularity_score']
        indexes = [
            models.Index(fields=['popularity_score']),
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return self.name

