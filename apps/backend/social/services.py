# apps/backend/social/services.py

"""
Enhanced Social Services for Univa Platform
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from datetime import timedelta
from typing import Dict, List, Optional, Any

import boto3
import requests
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from .models import (
    VideoContent, VideoProcessingQueue,
    VideoView, VideoLike, VideoComment, VideoShare, VideoSave,
    UserActivity, TrendingFeed, UserInterest
)

from notifications.events import emit_notification_event
from notifications.events import constants

from .algorithms import EnhancedContentAlgorithm, FriendSuggestionAlgorithm

logger = logging.getLogger(__name__)


# =============================================================================
# VIDEO PROCESSING SERVICE
# =============================================================================

class VideoProcessorService:
    """Enhanced video processing service."""
    
    @staticmethod
    @shared_task
    def process_video(video_id: str):
        """
        Process video: transcode, generate thumbnails, upload to CDN.
        
        Args:
            video_id: UUID of the video to process
        """
        try:
            video = VideoContent.objects.get(id=video_id)
            queue_item, created = VideoProcessingQueue.objects.get_or_create(
                video=video,
                defaults={'status': 'processing'}
            )
            
            queue_item.status = 'processing'
            queue_item.started_at = timezone.now()
            queue_item.save()
            
            # Process video
            result = VideoProcessorService._transcode_video(video)
            
            # Generate thumbnails
            thumbnail_paths = VideoProcessorService._generate_thumbnails(video)
            
            # Extract metadata
            metadata = VideoProcessorService._extract_metadata(video)
            
            # Upload to CDN
            cdn_urls = VideoProcessorService._upload_to_cdn(video, result['output_paths'])
            
            # Update video record
            video.duration = metadata['duration']
            video.aspect_ratio = metadata['aspect_ratio']
            video.video_urls = cdn_urls
            video.thumbnail = thumbnail_paths.get('medium')
            video.thumbnails = thumbnail_paths
            video.status = 'published'
            video.published_at = timezone.now()
            video.save()
            
            # Update queue
            queue_item.status = 'completed'
            queue_item.completed_at = timezone.now()
            queue_item.save()
            
            # Generate content vector
            VideoProcessorService._generate_content_vector(video)
            
            # Create notification
            '''Notification.objects.create(
                user=video.user,
                notification_type='video_processed',
                subject='Your video is ready!',
                message=f"Your video '{video.title or 'Untitled'}' has been processed and is now live.",
                channel='push',
                status='pending'
            )'''
            emit_notification_event(
                event_type=constants.SOCIAL_VIDEO_PROCESSED,
                module="social",
                actor=video.user,
                object_type="VideoContent",
                object_id=video.pk,
                payload={
                    "recipient_id": video.user.pk,
                    "video_id": video.pk,
                    "video_title": video.title or "Untitled",
                },
            )
            
            # Update user video count
            profile = getattr(video.user, 'social_profile', None)
            if profile:
                profile.videos_count = F('videos_count') + 1
                profile.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=video.user,
                activity_type='upload',
                video=video,
                metadata={'duration': metadata['duration']}
            )
            
            # Generate feed recommendations
            VideoProcessorService._update_recommendations(video)
            
        except Exception as e:
            logger.error(f"Video processing failed for {video_id}: {str(e)}")
            VideoProcessorService._handle_processing_failure(video, str(e))
    
    @staticmethod
    def _transcode_video(video: VideoContent) -> Dict:
        """Transcode video to multiple qualities."""
        if not video.video_file:
            raise ValueError("Video file not found")
        
        input_path = video.video_file.path
        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed', str(video.id))
        os.makedirs(output_dir, exist_ok=True)
        
        # Define quality profiles
        qualities = {
            'low': {'resolution': '480x854', 'bitrate': '800k', 'audio_bitrate': '96k'},
            'medium': {'resolution': '720x1280', 'bitrate': '1500k', 'audio_bitrate': '128k'},
            'high': {'resolution': '1080x1920', 'bitrate': '2500k', 'audio_bitrate': '192k'},
        }
        
        output_paths = {}
        
        for quality, settings in qualities.items():
            output_path = os.path.join(output_dir, f'{quality}.mp4')
            
            # FFmpeg command
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', f'scale={settings["resolution"]}:force_original_aspect_ratio=decrease,pad={settings["resolution"]}:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-b:v', settings['bitrate'],
                '-maxrate', str(int(settings['bitrate'].replace('k', '')) * 1.5) + 'k',
                '-bufsize', str(int(settings['bitrate'].replace('k', '')) * 2) + 'k',
                '-c:a', 'aac',
                '-b:a', settings['audio_bitrate'],
                '-movflags', '+faststart',
                output_path,
                '-y'
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                output_paths[quality] = output_path
            except subprocess.CalledProcessError as e:
                logger.error(f"Transcoding failed for {quality}: {e.stderr}")
                raise
        
        return {'output_paths': output_paths}
    
    @staticmethod
    def _generate_thumbnails(video: VideoContent) -> Dict[str, str]:
        """Generate multiple thumbnail sizes."""
        if not video.video_file:
            return {}
        
        input_path = video.video_file.path
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails', str(video.id))
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        # Define thumbnail sizes
        sizes = {
            'small': (150, 267),
            'medium': (320, 568),
            'large': (640, 1136),
            'xl': (1080, 1920),
        }
        
        thumbnails = {}
        
        for name, (width, height) in sizes.items():
            output_path = os.path.join(thumbnail_dir, f'{name}.jpg')
            
            # FFmpeg command for thumbnail extraction
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', '00:00:01',  # Capture at 1 second
                '-vframes', '1',
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                output_path,
                '-y'
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Save to Django storage
                with open(output_path, 'rb') as f:
                    thumbnails[name] = default_storage.save(
                        f'thumbnails/{video.id}/{name}.jpg',
                        ContentFile(f.read())
                    )
                
                # Clean up temp file
                os.remove(output_path)
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Thumbnail generation failed for {name}: {e}")
                continue
        
        return thumbnails
    
    @staticmethod
    def _extract_metadata(video: VideoContent) -> Dict:
        """Extract video metadata."""
        if not video.video_file:
            return {}
        
        input_path = video.video_file.path
        
        # FFprobe command
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            input_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract duration
            duration = float(data['format'].get('duration', 0))
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))
                aspect_ratio = f"{width}:{height}" if width and height else "9:16"
            else:
                aspect_ratio = "9:16"
            
            return {
                'duration': duration,
                'aspect_ratio': aspect_ratio,
                'width': width if video_stream else 0,
                'height': height if video_stream else 0,
            }
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {'duration': 0, 'aspect_ratio': '9:16'}
    
    @staticmethod
    def _upload_to_cdn(video: VideoContent, output_paths: Dict) -> Dict:
        """Upload processed videos to CDN."""
        if not settings.USE_CDN:
            return {}
        
        s3_client = boto3.client('s3')
        cdn_urls = {}
        
        for quality, local_path in output_paths.items():
            s3_key = f"videos/{video.user.id}/{video.id}/{quality}.mp4"
            
            try:
                s3_client.upload_file(
                    local_path,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'video/mp4',
                        'CacheControl': 'max-age=31536000'
                    }
                )
                
                cdn_urls[quality] = f"https://{settings.AWS_CDN_DOMAIN}/{s3_key}"
                
                # Clean up local file
                os.remove(local_path)
                
            except Exception as e:
                logger.error(f"CDN upload failed for {quality}: {e}")
        
        return cdn_urls
    
    @staticmethod
    def _generate_content_vector(video: VideoContent):
        """Generate content vector for recommendations."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create text representation
            text = f"{video.title or ''} {video.description or ''} {' '.join(video.hashtags or [])}"
            
            if text.strip():
                # Generate embedding
                embedding = model.encode(text)
                video.content_vector = embedding.tolist()
                video.save()
                
        except Exception as e:
            logger.error(f"Content vector generation failed: {e}")
    
    @staticmethod
    def _update_recommendations(video: VideoContent):
        """Update recommendation feeds with new video."""
        # Get active users
        from accounts.models import User
        
        # For now, only update trending feed
        TrendingFeed.objects.create(
            video=video,
            rank_score=video.viral_score or 50.0,
            expires_at=timezone.now() + timedelta(hours=24)
        )
    
    @staticmethod
    def _handle_processing_failure(video: VideoContent, error: str):
        """Handle video processing failure."""
        queue_item = getattr(video, 'processing_queue', None)
        if queue_item:
            queue_item.status = 'failed'
            queue_item.error_message = error
            queue_item.save()
        
        video.status = 'failed'
        video.save()
        
        # Notify user
        '''Notification.objects.create(
            user=video.user,
            notification_type='video_failed',
            subject='Video processing failed',
            message=f"We couldn't process your video. Please try again.",
            channel='push',
            status='pending'
        )'''
        emit_notification_event(
            event_type=constants.SOCIAL_VIDEO_PROCESSING_FAILED,
            module="social",
            actor=video.user,
            object_type="VideoContent",
            object_id=video.pk,
            payload={
                "recipient_id": video.user.pk,
                "video_id": video.pk,
                "video_title": video.title or "Untitled",
            },
        )


# =============================================================================
# CONTENT DELIVERY SERVICE
# =============================================================================

class ContentDeliveryService:
    """Handle content delivery and streaming."""
    
    @staticmethod
    def get_stream_url(video: VideoContent, quality: str = 'auto', user=None) -> str:
        """Get streaming URL for video."""
        # Check user permissions
        if video.visibility == 'private' and video.user != user:
            return None
        
        if video.visibility == 'friends' and not ContentDeliveryService._is_friend(video.user, user):
            return None
        
        # Get CDN URL
        if video.video_urls:
            if quality == 'auto':
                # Select based on user's connection speed
                return video.video_urls.get('medium', video.video_urls.get('high'))
            return video.video_urls.get(quality, video.video_urls.get('medium'))
        
        return video.video_file.url
    
    @staticmethod
    def generate_hls_stream(video: VideoContent) -> Dict:
        """Generate HLS streaming manifest."""
        if not video.video_urls:
            return {}
        
        # Create master playlist
        master_playlist = "#EXTM3U\n#EXT-X-VERSION:3\n"
        
        variants = []
        for quality, url in video.video_urls.items():
            bandwidth = {
                'low': '800000',
                'medium': '1500000',
                'high': '2500000'
            }.get(quality, '1500000')
            
            resolution = {
                'low': '480x854',
                'medium': '720x1280',
                'high': '1080x1920'
            }.get(quality, '720x1280')
            
            variants.append({
                'url': url,
                'bandwidth': bandwidth,
                'resolution': resolution,
            })
        
        # Build HLS manifest
        # This is a simplified version - in production, use a proper HLS library
        return {
            'master': master_playlist,
            'variants': variants,
        }
    
    @staticmethod
    def _is_friend(user1, user2) -> bool:
        """Check if two users are friends."""
        if not user1 or not user2:
            return False
        
        return Follow.objects.filter(
            follower=user1,
            following=user2
        ).exists() or Follow.objects.filter(
            follower=user2,
            following=user1
        ).exists()


# =============================================================================
# RECOMMENDATION SERVICE
# =============================================================================

class RecommendationService:
    """Handle content recommendations."""
    
    @staticmethod
    def get_personalized_feed(user, limit: int = 50, offset: int = 0, context: Dict = None):
        """Get personalized feed for user."""
        # Check if feed is cached
        cached_feed = TrendingFeed.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-rank_score').values_list('video_id', flat=True)
        
        if cached_feed.exists():
            video_ids = list(cached_feed)
            videos = VideoContent.objects.filter(id__in=video_ids)
            # Maintain order
            video_dict = {v.id: v for v in videos}
            return [video_dict[id] for id in video_ids if id in video_dict][offset:offset + limit]
        
        # Generate new feed
        feed = EnhancedContentAlgorithm.get_personalized_feed(
            user, limit=limit * 2, offset=0, context=context
        )
        
        return feed
    
    @staticmethod
    def get_trending_feed(limit: int = 50, offset: int = 0) -> List[VideoContent]:
        """Get global trending feed."""
        # Get trending from cache
        trending = TrendingFeed.objects.filter(
            user__isnull=True,
            expires_at__gt=timezone.now()
        ).order_by('-rank_score')[:limit]
        
        if trending.exists():
            video_ids = [t.video_id for t in trending]
            videos = VideoContent.objects.filter(id__in=video_ids)
            video_dict = {v.id: v for v in videos}
            return [video_dict[id] for id in video_ids if id in video_dict]
        
        # Calculate trending
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        trending_videos = VideoContent.objects.filter(
            status='published',
            published_at__gte=seven_days_ago
        ).order_by('-viral_score', '-views_count')[:limit * 2]
        
        # Cache results
        for video in trending_videos:
            TrendingFeed.objects.create(
                video=video,
                rank_score=video.viral_score or 0,
                expires_at=timezone.now() + timedelta(hours=1)
            )
        
        return list(trending_videos[:limit])
    
    @staticmethod
    def get_friend_suggestions(user, limit: int = 10) -> List:
        """Get friend suggestions."""
        return FriendSuggestionAlgorithm.suggest_friends(user, limit)


# =============================================================================
# ANALYTICS SERVICE
# =============================================================================

class AnalyticsService:
    """Track and analyze user behavior."""
    
    @staticmethod
    def track_view(user, video: VideoContent, watch_time: float = 0, progress: float = 0):
        """Track video view."""
        # Create view record
        view = VideoView.objects.create(
            user=user,
            video=video,
            watch_time=watch_time,
            progress=progress,
            completed=progress >= 90,
            session_id=user.id if user else str(uuid.uuid4())
        )
        
        # Update video metrics
        video.views_count = F('views_count') + 1
        video.avg_watch_time = (
            (video.avg_watch_time * (video.views_count - 1) + watch_time) / video.views_count
            if video.views_count > 0 else watch_time
        )
        video.completion_rate = (
            (video.completion_rate * (video.views_count - 1) + (progress / 100)) / video.views_count
            if video.views_count > 0 else progress / 100
        )
        video.save()
        
        # Update user activity
        UserActivity.objects.create(
            user=user,
            activity_type='view',
            video=video,
            metadata={
                'watch_time': watch_time,
                'progress': progress,
                'completed': progress >= 90,
            }
        )
        
        # Update user interests
        AnalyticsService._update_user_interests(user, video)
        
        return view
    
    @staticmethod
    def track_like(user, video: VideoContent, sentiment: str = 'like'):
        """Track video like."""
        like, created = VideoLike.objects.get_or_create(
            user=user,
            video=video,
            defaults={'sentiment': sentiment}
        )
        
        if created:
            # Update video metrics
            video.likes_count = F('likes_count') + 1
            video.update_engagement_metrics()
            
            # Update user activity
            UserActivity.objects.create(
                user=user,
                activity_type='like',
                video=video,
                metadata={'sentiment': sentiment}
            )
        
        return like
    
    @staticmethod
    def track_share(user, video: VideoContent, platform: str, shared_to: str = ''):
        """Track video share."""
        share = VideoShare.objects.create(
            user=user,
            video=video,
            platform=platform,
            shared_to=shared_to
        )
        
        # Update video metrics
        video.shares_count = F('shares_count') + 1
        video.update_engagement_metrics()
        
        # Update user activity
        UserActivity.objects.create(
            user=user,
            activity_type='share',
            video=video,
            metadata={'platform': platform, 'shared_to': shared_to}
        )
        
        return share
    
    @staticmethod
    def track_save(user, video: VideoContent, collection: str = 'default'):
        """Track video save."""
        save, created = VideoSave.objects.get_or_create(
            user=user,
            video=video,
            defaults={'collection': collection}
        )
        
        if created:
            # Update video metrics
            video.saves_count = F('saves_count') + 1
            video.save()
            
            # Update user activity
            UserActivity.objects.create(
                user=user,
                activity_type='save',
                video=video,
                metadata={'collection': collection}
            )
        
        return save
    
    @staticmethod
    def _update_user_interests(user, video: VideoContent):
        """Update user interests based on viewing behavior."""
        try:
            user_interest, created = UserInterest.objects.get_or_create(user=user)
            
            # Update content preferences
            preferences = user_interest.content_preferences or {}
            
            # Update hashtags
            hashtags = preferences.get('hashtags', [])
            for tag in video.hashtags or []:
                if tag not in hashtags:
                    hashtags.append(tag)
            
            # Keep only top 20
            preferences['hashtags'] = hashtags[:20]
            
            # Update categories
            categories = preferences.get('categories', [])
            if video.interest_vector:
                # This would use category classification
                pass
            
            user_interest.content_preferences = preferences
            user_interest.save()
            
        except Exception as e:
            logger.error(f"Failed to update user interests: {e}") 
            



# apps/backend/social/algorithms.py - Updated to use canonical User

from django.contrib.auth import get_user_model
User = get_user_model()

class EnhancedContentAlgorithm:
    """Enhanced recommendation algorithm using canonical User model."""
    
    @classmethod
    def _get_user_interests(cls, user):
        """Get user interests from canonical User's social profile."""
        interests = {
            'hashtags': [],
            'categories': [],
            'creators': [],
        }
        
        # Get from SocialProfile
        social_profile = getattr(user, 'social_profile', None)
        if social_profile and social_profile.interest_vector:
            # Use the interest vector
            pass
        
        # Get from UserInterest model
        user_interest = getattr(user, 'interests', None)
        if user_interest and user_interest.content_preferences:
            interests['hashtags'] = user_interest.content_preferences.get('hashtags', [])
            interests['categories'] = user_interest.content_preferences.get('categories', [])
            return interests
        
        # Fallback: Analyze watch history
        recent_views = VideoView.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('video')
        
        all_hashtags = []
        for view in recent_views:
            if view.video.hashtags:
                all_hashtags.extend(view.video.hashtags)
        
        if all_hashtags:
            interests['hashtags'] = [
                tag for tag, _ in Counter(all_hashtags).most_common(10)
            ]
        
        return interests
    
    @classmethod
    def _get_followed_users(cls, user):
        """Get list of followed user IDs using Follow model."""
        return list(
            Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        )