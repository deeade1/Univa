# apps/backend/social/algorithms.py

"""
Enhanced Recommendation Algorithms for Univa Social Platform
"""

import math
import logging
from collections import Counter, defaultdict
from datetime import timedelta
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from django.db import models
from django.db.models import Avg, Count, F, Q, StdDev, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import (
    VideoContent, VideoView, VideoLike, VideoComment, VideoShare, VideoSave,
    Friend, Follow, UserInterest, UserProfile, TrendingFeed
)

logger = logging.getLogger(__name__)


class ContentAlgorithm:
    """
    Enhanced recommendation algorithm with multiple ranking signals.
    """
    
    # Weights for different ranking factors
    WEIGHTS = {
        'engagement': 0.25,
        'recency': 0.15,
        'personalization': 0.25,
        'diversity': 0.10,
        'creator_quality': 0.10,
        'social': 0.10,
        'trending': 0.05,
    }
    
    @classmethod
    def get_personalized_feed(
        cls,
        user,
        limit: int = 50,
        offset: int = 0,
        context: Optional[Dict] = None
    ) -> List[VideoContent]:
        """
        Generate personalized feed using multi-stage ranking.
        
        Args:
            user: The user object
            limit: Number of videos to return
            offset: Pagination offset
            context: Additional context (session tags, device info)
        
        Returns:
            List of VideoContent objects
        """
        # Stage 1: Candidate Generation
        candidates = cls._generate_candidates(user, context)
        
        if not candidates:
            return []
        
        # Stage 2: Feature Extraction
        features = cls._extract_features(candidates, user, context)
        
        # Stage 3: Ranking
        ranked = cls._rank_candidates(features, user)
        
        # Stage 4: Diversity & Freshness
        final_feed = cls._apply_diversity_filter(ranked, limit)
        
        # Stage 5: Cache results
        cls._cache_feed(user, final_feed)
        
        return final_feed[offset:offset + limit]
    
    @classmethod
    def _generate_candidates(
        cls,
        user,
        context: Optional[Dict] = None
    ) -> List[VideoContent]:
        """Multi-source candidate generation."""
        candidate_pool = []
        seen_ids = set()
        
        # Source 1: Personalized Trending (40%)
        trending = cls._get_personalized_trending(user, limit=800)
        candidate_pool.extend(trending)
        seen_ids.update(v.id for v in trending)
        
        # Source 2: Social Graph (25%)
        social = cls._get_social_content(user, limit=500)
        for v in social:
            if v.id not in seen_ids:
                candidate_pool.append(v)
                seen_ids.add(v.id)
        
        # Source 3: Exploration (20%)
        exploration = cls._get_exploration_content(user, limit=400)
        for v in exploration:
            if v.id not in seen_ids:
                candidate_pool.append(v)
                seen_ids.add(v.id)
        
        # Source 4: Session-based (15%)
        if context and context.get('session_tags'):
            session = cls._get_session_content(user, context['session_tags'], limit=300)
            for v in session:
                if v.id not in seen_ids:
                    candidate_pool.append(v)
                    seen_ids.add(v.id)
        
        return candidate_pool
    
    @classmethod
    def _get_personalized_trending(cls, user, limit: int = 800) -> List[VideoContent]:
        """Get trending content personalized to user interests."""
        # Get user interests
        user_interests = cls._get_user_interests(user)
        
        # Base query for trending content (last 7 days)
        base_qs = VideoContent.objects.filter(
            status='published',
            visibility='public',
            published_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('user')
        
        # If user has no interests, return pure trending
        if not user_interests or not user_interests.get('hashtags'):
            return list(base_qs.order_by('-viral_score')[:limit])
        
        # Score videos by interest match
        scored = []
        user_hashtags = set(user_interests.get('hashtags', []))
        user_categories = set(user_interests.get('categories', []))
        
        for video in base_qs[:limit * 2]:
            # Calculate interest score
            video_hashtags = set(video.hashtags or [])
            hashtag_match = len(video_hashtags & user_hashtags) / max(1, len(user_hashtags))
            
            # Combine with engagement score
            engagement_score = video.viral_score / 100.0
            
            # Combined score
            combined_score = (engagement_score * 0.6) + (hashtag_match * 0.4)
            scored.append((video, combined_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in scored[:limit]]
    
    @classmethod
    def _get_social_content(cls, user, limit: int = 500) -> List[VideoContent]:
        """Get content from social connections."""
        # Get followed users
        followed_ids = cls._get_followed_users(user)
        
        if not followed_ids:
            return []
        
        # Get recent content from followed users
        social_content = VideoContent.objects.filter(
            user_id__in=followed_ids,
            status='published'
        ).order_by('-created_at')[:limit * 2]
        
        # Get closeness scores
        closeness_scores = cls._get_friend_closeness(user)
        
        # Score content
        scored = []
        for video in social_content:
            closeness = closeness_scores.get(video.user_id, 1.0)
            recency = cls._calculate_recency_score(video.published_at or video.created_at)
            
            # Boost content from close friends
            score = recency * (1 + closeness * 0.5)
            scored.append((video, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in scored[:limit]]
    
    @classmethod
    def _get_exploration_content(cls, user, limit: int = 400) -> List[VideoContent]:
        """Get diverse content for exploration."""
        # Get content from various sources
        followed_ids = cls._get_followed_users(user)
        
        # Avoid content from followed users
        base_qs = VideoContent.objects.filter(
            status='published',
            visibility='public',
            published_at__gte=timezone.now() - timedelta(days=3)
        )
        
        if followed_ids:
            base_qs = base_qs.exclude(user_id__in=followed_ids)
        
        # Ensure diversity by sampling from different engagement levels
        high = list(base_qs.filter(viral_score__gte=70)[:limit//3])
        mid = list(base_qs.filter(viral_score__gte=30, viral_score__lt=70)[:limit//3])
        low = list(base_qs.filter(viral_score__lt=30)[:limit//3])
        
        return high + mid + low
    
    @classmethod
    def _get_session_content(cls, user, session_tags: List[str], limit: int = 300) -> List[VideoContent]:
        """Get session-aware content."""
        if not session_tags:
            return []
        
        # Find content matching session tags
        session_content = VideoContent.objects.filter(
            status='published',
            visibility='public',
            hashtags__overlap=session_tags[:5]
        ).order_by('-viral_score')[:limit * 2]
        
        # Score by tag relevance
        scored = []
        session_set = set(session_tags)
        
        for video in session_content:
            video_hashtags = set(video.hashtags or [])
            tag_overlap = len(video_hashtags & session_set) / max(1, len(session_set))
            
            recency = cls._calculate_recency_score(video.published_at or video.created_at)
            
            score = (recency * 0.6) + (tag_overlap * 0.4)
            scored.append((video, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in scored[:limit]]
    
    @classmethod
    def _extract_features(cls, candidates: List[VideoContent], user, context: Optional[Dict] = None) -> List[Dict]:
        """Extract comprehensive features for ranking."""
        features = []
        
        for video in candidates:
            feature_set = {
                'video': video,
                'video_id': video.id,
                'engagement_metrics': cls._get_engagement_metrics(video),
                'content_features': cls._get_content_features(video),
                'creator_features': cls._get_creator_features(video.user),
                'user_context': cls._get_user_context(user, video),
                'temporal_features': cls._get_temporal_features(video),
                'social_features': cls._get_social_features(user, video),
            }
            features.append(feature_set)
        
        return features
    
    @classmethod
    def _rank_candidates(cls, features: List[Dict], user) -> List[VideoContent]:
        """Rank candidates using multi-objective scoring."""
        scored = []
        
        for feature_set in features:
            score = cls._calculate_ranking_score(feature_set, user)
            scored.append((feature_set['video'], score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in scored]
    
    @classmethod
    def _calculate_ranking_score(cls, features: Dict, user) -> float:
        """Calculate final ranking score."""
        weights = cls.WEIGHTS
        
        # Engagement score
        engagement_score = (
            features['engagement_metrics']['viral_score'] * 0.4 +
            features['engagement_metrics']['engagement_rate'] * 0.3 +
            features['engagement_metrics']['completion_rate'] * 0.2 +
            features['engagement_metrics']['share_ratio'] * 0.1
        )
        
        # Personalization score
        personalization_score = cls._calculate_personalization_score(features, user)
        
        # Recency score
        recency_score = features['temporal_features']['recency']
        
        # Diversity score
        diversity_score = cls._calculate_diversity_score(features)
        
        # Creator quality score
        creator_score = (
            min(1.0, features['creator_features']['engagement_rate'] / 100.0) * 0.5 +
            min(1.0, features['creator_features']['viral_score'] / 100.0) * 0.3 +
            (1.0 if features['creator_features']['is_verified'] else 0.0) * 0.2
        )
        
        # Social score
        social_score = features['social_features']['social_boost']
        
        # Trending score
        trending_score = cls._calculate_trending_score(features)
        
        # Final score
        final_score = (
            engagement_score * weights['engagement'] +
            personalization_score * weights['personalization'] +
            recency_score * weights['recency'] +
            diversity_score * weights['diversity'] +
            creator_score * weights['creator_quality'] +
            social_score * weights['social'] +
            trending_score * weights['trending']
        )
        
        # Apply penalties
        penalties = cls._calculate_penalties(features, user)
        final_score *= penalties
        
        return max(0.0, min(1.0, final_score))
    
    @classmethod
    def _get_engagement_metrics(cls, video: VideoContent) -> Dict:
        """Get normalized engagement metrics."""
        return {
            'viral_score': min(1.0, video.viral_score / 100.0),
            'engagement_rate': min(1.0, video.engagement_rate / 100.0),
            'completion_rate': min(1.0, video.completion_rate / 100.0),
            'share_ratio': video.shares_count / max(1, video.views_count),
            'like_ratio': video.likes_count / max(1, video.views_count),
            'comment_ratio': video.comments_count / max(1, video.views_count),
            'save_ratio': video.saves_count / max(1, video.views_count),
        }
    
    @classmethod
    def _get_content_features(cls, video: VideoContent) -> Dict:
        """Get content-based features."""
        return {
            'duration': video.duration or 15,
            'hashtag_count': len(video.hashtags or []),
            'hashtag_diversity': len(set(video.hashtags or [])),
            'description_length': len(video.description or ''),
            'has_sound': video.sound is not None,
            'has_effects': hasattr(video, 'video_effects') and video.video_effects.exists(),
            'is_duet': hasattr(video, 'duets_created') and video.duets_created.exists(),
            'is_stitch': hasattr(video, 'stitches_created') and video.stitches_created.exists(),
        }
    
    @classmethod
    def _get_creator_features(cls, creator) -> Dict:
        """Get creator reputation features."""
        # Get creator stats
        stats = VideoContent.objects.filter(user=creator).aggregate(
            avg_engagement=Avg('engagement_rate'),
            video_count=Count('id'),
            avg_viral=Avg('viral_score'),
            total_views=Sum('views_count'),
        )
        
        profile = getattr(creator, 'social_profile', None)
        
        return {
            'engagement_rate': stats['avg_engagement'] or 0,
            'video_count': stats['video_count'] or 0,
            'viral_score': stats['avg_viral'] or 0,
            'total_views': stats['total_views'] or 0,
            'is_verified': profile.is_verified if profile else False,
            'followers_count': profile.followers_count if profile else 0,
            'content_consistency': min(1.0, (stats['video_count'] or 0) / 10),
        }
    
    @classmethod
    def _get_user_context(cls, user, video: VideoContent) -> Dict:
        """Get user-specific context."""
        return {
            'previously_watched': VideoView.objects.filter(user=user, video=video).exists(),
            'previously_liked': VideoLike.objects.filter(user=user, video=video).exists(),
            'previously_saved': VideoSave.objects.filter(user=user, video=video).exists(),
            'previously_commented': VideoComment.objects.filter(user=user, video=video).exists(),
            'watch_count': VideoView.objects.filter(user=user, video=video).count(),
            'last_watch': VideoView.objects.filter(user=user, video=video).first(),
        }
    
    @classmethod
    def _get_temporal_features(cls, video: VideoContent) -> Dict:
        """Get time-based features."""
        now = timezone.now()
        published = video.published_at or video.created_at
        video_age = (now - published).total_seconds() / 3600  # hours
        
        return {
            'recency': 1.0 / (1.0 + (video_age / 24.0)),
            'age_hours': video_age,
            'is_peak_hours': cls._is_peak_hours(now),
            'day_of_week': now.weekday(),
            'hour_of_day': now.hour,
            'published_at': published,
        }
    
    @classmethod
    def _get_social_features(cls, user, video: VideoContent) -> Dict:
        """Get social connection features."""
        is_following = Follow.objects.filter(
            follower=user,
            following=video.user
        ).exists()
        
        friend_closeness = cls._get_friend_closeness(user).get(video.user_id, 1.0)
        
        return {
            'is_following': is_following,
            'friend_closeness': friend_closeness,
            'social_boost': 1.5 if is_following else (1.0 + friend_closeness * 0.3),
        }
    
    @classmethod
    def _calculate_personalization_score(cls, features: Dict, user) -> float:
        """Calculate personalization score."""
        video = features['video']
        user_context = features['user_context']
        score = 0.0
        
        # User interest match
        user_interests = cls._get_user_interests(user)
        if user_interests and video.hashtags:
            match = len(set(video.hashtags) & set(user_interests.get('hashtags', [])))
            score += match / max(1, len(user_interests.get('hashtags', []))) * 0.4
        
        # Historical engagement
        if user_context['previously_watched']:
            score += 0.3
        
        if user_context['previously_liked']:
            score += 0.2
        
        # Social connection
        if features['social_features']['is_following']:
            score += 0.1
        
        return min(1.0, score)
    
    @classmethod
    def _calculate_diversity_score(cls, features: Dict) -> float:
        """Calculate diversity score."""
        content_features = features['content_features']
        score = 0.0
        
        # Hashtag diversity
        score += min(1.0, content_features['hashtag_diversity'] / 10.0) * 0.3
        
        # Content type diversity
        if content_features['has_sound']:
            score += 0.2
        if content_features['has_effects']:
            score += 0.2
        if content_features['is_duet']:
            score += 0.15
        if content_features['is_stitch']:
            score += 0.15
        
        return min(1.0, score)
    
    @classmethod
    def _calculate_trending_score(cls, features: Dict) -> float:
        """Calculate trending score."""
        engagement = features['engagement_metrics']
        temporal = features['temporal_features']
        
        # More recent trending gets higher score
        recency = temporal['recency']
        engagement_score = engagement['viral_score']
        
        return recency * 0.5 + engagement_score * 0.5
    
    @classmethod
    def _calculate_penalties(cls, features: Dict, user) -> float:
        """Apply penalties."""
        penalty = 1.0
        user_context = features['user_context']
        
        # Repeat content penalty
        if user_context['previously_watched']:
            # Heavy penalty for recently watched
            last_watch = user_context.get('last_watch')
            if last_watch:
                hours_ago = (timezone.now() - last_watch.created_at).total_seconds() / 3600
                if hours_ago < 24:
                    penalty *= 0.1  # Very heavy penalty for content watched in last 24 hours
                elif hours_ago < 72:
                    penalty *= 0.3
                else:
                    penalty *= 0.5
        
        # Over-saturation penalty (same creator)
        creator_saturation = cls._get_creator_saturation(user, features['video'].user_id)
        penalty *= (1.0 - creator_saturation * 0.7)
        
        # Low quality penalty
        if features['engagement_metrics']['engagement_rate'] < 0.1:
            penalty *= 0.5
        
        return max(0.05, penalty)
    
    @classmethod
    def _apply_diversity_filter(cls, ranked: List[VideoContent], limit: int) -> List[VideoContent]:
        """Apply diversity filter to final feed."""
        final = []
        used_creators = set()
        used_hashtags = set()
        
        for video in ranked:
            # Limit same creator
            if video.user_id in used_creators and len(used_creators) >= 3:
                continue
            
            # Ensure mix of recent content
            if len(final) >= limit * 0.8:
                published = video.published_at or video.created_at
                if (timezone.now() - published).total_seconds() / 3600 > 48:
                    continue
            
            final.append(video)
            used_creators.add(video.user_id)
            used_hashtags.update(video.hashtags or [])
            
            if len(final) >= limit:
                break
        
        return final
    
    @classmethod
    def _cache_feed(cls, user, feed: List[VideoContent]):
        """Cache feed for faster retrieval."""
        # Clean old cache
        TrendingFeed.objects.filter(
            user=user,
            created_at__lt=timezone.now() - timedelta(hours=1)
        ).delete()
        
        # Cache new feed
        for idx, video in enumerate(feed):
            TrendingFeed.objects.create(
                user=user,
                video=video,
                rank_score=len(feed) - idx,
                expires_at=timezone.now() + timedelta(hours=1)
            )
    
    # Helper Methods
    
    @classmethod
    def _get_user_interests(cls, user) -> Dict:
        """Get user interests from multiple signals."""
        interests = {
            'hashtags': [],
            'categories': [],
            'creators': [],
            'interaction_types': [],
        }
        
        # Get from UserInterest model
        user_interest = getattr(user, 'interests', None)
        if user_interest:
            if user_interest.content_preferences:
                interests['hashtags'] = user_interest.content_preferences.get('hashtags', [])
                interests['categories'] = user_interest.content_preferences.get('categories', [])
            return interests
        
        # Fallback: Analyze watch history
        recent_views = VideoView.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('video')
        
        # Extract hashtags
        all_hashtags = []
        for view in recent_views:
            if view.video.hashtags:
                all_hashtags.extend(view.video.hashtags)
        
        # Get top hashtags
        if all_hashtags:
            interests['hashtags'] = [
                tag for tag, _ in Counter(all_hashtags).most_common(10)
            ]
        
        return interests
    
    @classmethod
    def _get_followed_users(cls, user) -> List[int]:
        """Get list of followed user IDs."""
        return list(
            Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        )
    
    @classmethod
    def _get_friend_closeness(cls, user) -> Dict[int, float]:
        """Get closeness scores for friends."""
        friendships = Friend.objects.filter(
            Q(user=user) | Q(friend=user),
            is_active=True
        )
        
        closeness = {}
        for friendship in friendships:
            friend_id = (
                friendship.friend_id if friendship.user_id == user.id
                else friendship.user_id
            )
            closeness[friend_id] = friendship.closeness_score / 100.0
        
        return closeness
    
    @classmethod
    def _get_creator_saturation(cls, user, creator_id: int) -> float:
        """Check if user has seen too much content from this creator."""
        recent_views = VideoView.objects.filter(
            user=user,
            video__user_id=creator_id,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Normalize to 0-1
        return min(1.0, recent_views / 5.0)
    
    @classmethod
    def _calculate_recency_score(cls, created_at) -> float:
        """Calculate recency score with exponential decay."""
        hours_ago = (timezone.now() - created_at).total_seconds() / 3600
        return math.exp(-hours_ago / 48.0)  # Half-life of 48 hours
    
    @classmethod
    def _is_peak_hours(cls, dt) -> bool:
        """Check if current time is peak usage hours."""
        hour = dt.hour
        return (12 <= hour <= 14) or (18 <= hour <= 22)  # Lunch and evening


class FriendSuggestionAlgorithm:
    """
    Enhanced friend suggestion algorithm with multiple signals.
    """
    
    @classmethod
    def suggest_friends(cls, user, limit: int = 20) -> List:
        """Suggest friends using multiple signals."""
        suggestions = []
        excluded_ids = cls._get_excluded_ids(user)
        
        # Algorithm 1: Mutual friends (highest weight)
        mutual = cls._suggest_by_mutual_friends(user, excluded_ids, limit * 2)
        suggestions.extend(mutual)
        
        # Algorithm 2: Similar interests
        interest = cls._suggest_by_interests(user, excluded_ids, limit)
        suggestions.extend(interest)
        
        # Algorithm 3: Location proximity
        location = cls._suggest_by_location(user, excluded_ids, limit // 2)
        suggestions.extend(location)
        
        # Algorithm 4: Activity patterns
        activity = cls._suggest_by_activity(user, excluded_ids, limit // 2)
        suggestions.extend(activity)
        
        # Rank and deduplicate
        ranked = cls._rank_suggestions(suggestions)
        return ranked[:limit]
    
    @classmethod
    def _suggest_by_mutual_friends(cls, user, excluded_ids, limit):
        """Suggest based on mutual friends."""
        # Get user's friends
        friends = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        
        if not friends:
            return []
        
        # Find friends of friends
        friends_of_friends = Follow.objects.filter(
            follower__in=friends
        ).exclude(
            following__in=excluded_ids
        ).values('following_id').annotate(
            mutual_count=Count('id')
        ).order_by('-mutual_count')[:limit]
        
        # Get user objects
        from accounts.models import User
        user_ids = [item['following_id'] for item in friends_of_friends]
        users = User.objects.filter(id__in=user_ids)
        
        suggestions = []
        for user_obj in users:
            mutual_count = next(
                (item['mutual_count'] for item in friends_of_friends if item['following_id'] == user_obj.id),
                0
            )
            score = min(100, mutual_count * 20)
            suggestions.append((user_obj, score, f"{mutual_count} mutual friends"))
        
        return suggestions
    
    @classmethod
    def _suggest_by_interests(cls, user, excluded_ids, limit):
        """Suggest based on similar interests."""
        # Get user's interests
        user_interests = cls._get_user_interests(user)
        if not user_interests:
            return []
        
        # Find users with similar interests
        from .models import UserInterest
        similar_users = UserInterest.objects.exclude(
            user_id__in=excluded_ids
        ).filter(
            content_preferences__hashtags__overlap=user_interests
        ).values('user_id').annotate(
            interest_match=Count('id')
        ).order_by('-interest_match')[:limit]
        
        # Get user objects
        from accounts.models import User
        user_ids = [item['user_id'] for item in similar_users]
        users = User.objects.filter(id__in=user_ids)
        
        suggestions = []
        for user_obj in users:
            match_count = next(
                (item['interest_match'] for item in similar_users if item['user_id'] == user_obj.id),
                0
            )
            score = min(100, match_count * 15)
            suggestions.append((user_obj, score, "Similar interests"))
        
        return suggestions
    
    @classmethod
    def _suggest_by_location(cls, user, excluded_ids, limit):
        """Suggest based on location proximity."""
        # Get user's location
        profile = getattr(user, 'social_profile', None)
        if not profile or not profile.location_point:
            return []
        
        # Find users nearby
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.measure import D
        
        nearby_users = UserProfile.objects.exclude(
            user_id__in=excluded_ids
        ).filter(
            location_point__distance_lte=(profile.location_point, D(km=10))
        ).annotate(
            distance=Distance('location_point', profile.location_point)
        ).order_by('distance')[:limit]
        
        suggestions = []
        for user_profile in nearby_users:
            distance_km = user_profile.distance.km
            score = max(0, 100 - distance_km * 10)
            suggestions.append((
                user_profile.user,
                score,
                f"{distance_km:.1f} km away"
            ))
        
        return suggestions
    
    @classmethod
    def _suggest_by_activity(cls, user, excluded_ids, limit):
        """Suggest based on activity patterns."""
        # Get user's activity patterns
        user_activities = UserActivity.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).values('activity_type').count()
        
        if not user_activities:
            return []
        
        # Find users with similar activity patterns
        similar_activity_users = UserActivity.objects.filter(
            activity_type__in=user_activities.keys(),
            created_at__gte=timezone.now() - timedelta(days=7)
        ).exclude(
            user_id__in=excluded_ids
        ).values('user_id').annotate(
            activity_match=Count('id')
        ).order_by('-activity_match')[:limit]
        
        from accounts.models import User
        user_ids = [item['user_id'] for item in similar_activity_users]
        users = User.objects.filter(id__in=user_ids)
        
        suggestions = []
        for user_obj in users:
            match_count = next(
                (item['activity_match'] for item in similar_activity_users if item['user_id'] == user_obj.id),
                0
            )
            score = min(100, match_count * 10)
            suggestions.append((user_obj, score, "Similar activity"))
        
        return suggestions
    
    @classmethod
    def _rank_suggestions(cls, suggestions):
        """Rank and deduplicate suggestions."""
        ranked = {}
        for user_obj, score, reason in suggestions:
            if user_obj.id not in ranked:
                ranked[user_obj.id] = (user_obj, score, [reason])
            else:
                existing_user, existing_score, reasons = ranked[user_obj.id]
                ranked[user_obj.id] = (
                    user_obj,
                    existing_score + score * 0.5,
                    reasons + [reason]
                )
        
        return sorted(
            ranked.values(),
            key=lambda x: x[1],
            reverse=True
        )
    
    @classmethod
    def _get_excluded_ids(cls, user):
        """Get IDs to exclude from suggestions."""
        excluded = {user.id}
        
        # Existing friends
        friend_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        excluded.update(friend_ids)
        
        # Pending friend requests
        from .models import FriendRequest
        pending = FriendRequest.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status='pending'
        ).values_list('sender_id', 'receiver_id')
        
        for sender_id, receiver_id in pending:
            excluded.add(sender_id)
            excluded.add(receiver_id)
        
        return excluded
    
    @classmethod
    def _get_user_interests(cls, user):
        """Get user interests from interests model."""
        user_interest = getattr(user, 'interests', None)
        if user_interest and user_interest.content_preferences:
            return user_interest.content_preferences.get('hashtags', [])
        return []
    