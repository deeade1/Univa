// apps/Univa/graphql/queries/communityQueries/subscriptions.js
import { gql } from '@apollo/client';

/* ----------------------------------------------------------------------
 👥 FRIENDS & SOCIAL
---------------------------------------------------------------------- */

export const ON_FRIEND_REQUEST_RECEIVED = gql`
  subscription OnFriendRequestReceived($userId: ID!) {
    onFriendRequestReceived(userId: $userId) {
      friendRequest {
        id
        status
        message
        createdAt
        expiresAt
        sender {
          id
          firstName
          lastName
          profilePhoto
          username
          bio
        }
        receiver {
          id
          firstName
          lastName
        }
      }
    }
  }
`;

export const ON_FRIEND_REQUEST_UPDATED = gql`
  subscription OnFriendRequestUpdated($userId: ID!) {
    onFriendRequestUpdated(userId: $userId) {
      friendRequest {
        id
        status
        respondedAt
        updatedAt
        sender {
          id
          firstName
          lastName
          profilePhoto
        }
        receiver {
          id
          firstName
          lastName
        }
      }
      action
    }
  }
`;

export const ON_FRIENDSHIP_CREATED = gql`
  subscription OnFriendshipCreated($userId: ID!) {
    onFriendshipCreated(userId: $userId) {
      friendship {
        id
        created_at
        visibility
        relationshipType
        closenessScore
        lastInteraction
        user {
          id
          firstName
          lastName
          profilePhoto
          username
        }
        friend {
          id
          firstName
          lastName
          profilePhoto
          username
        }
      }
    }
  }
`;

export const ON_FRIENDSHIP_UPDATED = gql`
  subscription OnFriendshipUpdated($userId: ID!) {
    onFriendshipUpdated(userId: $userId) {
      friendship {
        id
        visibility
        relationshipType
        closenessScore
        lastInteraction
        isActive
        user {
          id
          firstName
          lastName
        }
        friend {
          id
          firstName
          lastName
          profilePhoto
        }
      }
    }
  }
`;

export const ON_FRIEND_SUGGESTIONS_UPDATED = gql`
  subscription OnFriendSuggestionsUpdated($userId: ID!) {
    onFriendSuggestionsUpdated(userId: $userId) {
      suggestions {
        id
        score
        reason
        user {
          id
          firstName
          lastName
          profilePhoto
          username
          bio
          mutualFriendsCount
        }
      }
      algorithmVersion
      generatedAt
    }
  }
`;

export const ON_FRIENDSHIP_INTERACTION = gql`
  subscription OnFriendshipInteraction($friendshipId: ID!) {
    onFriendshipInteraction(friendshipId: $friendshipId) {
      interaction {
        id
        interactionType
        weight
        createdAt
        metadata
        friendship {
          id
          closenessScore
        }
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 🔔 NOTIFICATIONS
---------------------------------------------------------------------- */

export const ON_NOTIFICATION_RECEIVED = gql`
  subscription OnNotificationReceived($userId: ID!) {
    onNotificationReceived(userId: $userId) {
      notification {
        id
        notificationType
        subject
        message
        channel
        status
        createdAt
        sentAt
        readAt
        priority
        metadata
        user {
          id
          firstName
          lastName
          profilePhoto
        }
      }
    }
  }
`;

export const ON_NOTIFICATION_STATUS_CHANGED = gql`
  subscription OnNotificationStatusChanged($userId: ID!) {
    onNotificationStatusChanged(userId: $userId) {
      notification {
        id
        status
        readAt
        sentAt
        notificationType
        subject
      }
      action
    }
  }
`;

export const ON_FRIEND_SUGGESTION_NOTIFICATION = gql`
  subscription OnFriendSuggestionNotification($userId: ID!) {
    onFriendSuggestionNotification(userId: $userId) {
      notification {
        id
        subject
        message
        createdAt
        metadata
        user {
          id
          firstName
          lastName
        }
      }
      suggestedFriends {
        id
        firstName
        lastName
        profilePhoto
        username
        mutualFriendsCount
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 🎥 VIDEO CONTENT
---------------------------------------------------------------------- */

export const ON_NEW_VIDEO_PUBLISHED = gql`
  subscription OnNewVideoPublished($userId: ID) {
    onNewVideoPublished(userId: $userId) {
      video {
        id
        title
        description
        hashtags
        created_at
        published_at
        viral_score
        engagement_rate
        likes_count
        comments_count
        views_count
        shares_count
        user {
          id
          firstName
          lastName
          profilePhoto
          username
        }
      }
      source
    }
  }
`;

export const ON_VIDEO_ENGAGEMENT_UPDATED = gql`
  subscription OnVideoEngagementUpdated($videoId: ID!) {
    onVideoEngagementUpdated(videoId: $videoId) {
      video {
        id
        likes_count
        comments_count
        views_count
        shares_count
        engagement_rate
        viral_score
      }
      engagementType
      delta
      updatedAt
    }
  }
`;

export const ON_TRENDING_VIDEOS_UPDATED = gql`
  subscription OnTrendingVideosUpdated($category: String) {
    onTrendingVideosUpdated(category: $category) {
      trendingVideos {
        rank
        score
        video {
          id
          title
          description
          viral_score
          engagement_rate
          likes_count
          views_count
          user {
            id
            firstName
            lastName
            profilePhoto
            username
          }
        }
      }
      category
      updatedAt
    }
  }
`;

/* ----------------------------------------------------------------------
 ❤️ VIDEO LIKES
---------------------------------------------------------------------- */

export const ON_VIDEO_LIKE_ADDED = gql`
  subscription OnVideoLikeAdded($videoId: ID!) {
    onVideoLikeAdded(videoId: $videoId) {
      like {
        id
        sentiment
        createdAt
        user {
          id
          firstName
          lastName
          profilePhoto
          username
        }
        video {
          id
          title
          likes_count
        }
      }
    }
  }
`;

export const ON_VIDEO_LIKE_REMOVED = gql`
  subscription OnVideoLikeRemoved($videoId: ID!) {
    onVideoLikeRemoved(videoId: $videoId) {
      videoId
      userId
      removedAt
      video {
        id
        likes_count
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 💬 VIDEO COMMENTS
---------------------------------------------------------------------- */

export const ON_VIDEO_COMMENT_ADDED = gql`
  subscription OnVideoCommentAdded($videoId: ID!) {
    onVideoCommentAdded(videoId: $videoId) {
      comment {
        id
        text
        likes_count
        created_at
        is_edited
        is_pinned
        user {
          id
          firstName
          lastName
          profilePhoto
          username
        }
        video {
          id
          title
          comments_count
        }
        parent_comment {
          id
          text
          user {
            id
            firstName
            lastName
          }
        }
      }
    }
  }
`;

export const ON_VIDEO_COMMENT_UPDATED = gql`
  subscription OnVideoCommentUpdated($videoId: ID!) {
    onVideoCommentUpdated(videoId: $videoId) {
      comment {
        id
        text
        likes_count
        updated_at
        is_edited
        is_pinned
        is_removed
        user {
          id
          firstName
          lastName
        }
      }
      action
    }
  }
`;

export const ON_COMMENT_LIKE_ADDED = gql`
  subscription OnCommentLikeAdded($commentId: ID!) {
    onCommentLikeAdded(commentId: $commentId) {
      comment {
        id
        likes_count
        text
        video {
          id
          title
        }
      }
      user {
        id
        firstName
        lastName
        profilePhoto
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 👀 VIDEO VIEWS
---------------------------------------------------------------------- */

export const ON_VIDEO_VIEW_ADDED = gql`
  subscription OnVideoViewAdded($videoId: ID!) {
    onVideoViewAdded(videoId: $videoId) {
      view {
        id
        watch_time
        progress
        created_at
        device_info
        user {
          id
          firstName
          lastName
          profilePhoto
        }
        session_id
        video {
          id
          views_count
          title
        }
      }
    }
  }
`;

export const ON_VIDEO_VIEW_PROGRESS_UPDATED = gql`
  subscription OnVideoViewProgressUpdated($videoId: ID!, $sessionId: String) {
    onVideoViewProgressUpdated(videoId: $videoId, sessionId: $sessionId) {
      view {
        id
        watch_time
        progress
        session_id
        video {
          id
          views_count
        }
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 🔄 VIDEO SHARES
---------------------------------------------------------------------- */

export const ON_VIDEO_SHARED = gql`
  subscription OnVideoShared($videoId: ID!) {
    onVideoShared(videoId: $videoId) {
      share {
        id
        platform
        shared_to
        created_at
        user {
          id
          firstName
          lastName
          profilePhoto
          username
        }
        video {
          id
          title
          shares_count
        }
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 🎭 DUETS & STITCHES
---------------------------------------------------------------------- */

export const ON_DUET_CREATED = gql`
  subscription OnDuetCreated($originalVideoId: ID!) {
    onDuetCreated(originalVideoId: $originalVideoId) {
      duet {
        id
        position
        created_at
        original_video {
          id
          title
          user {
            id
            firstName
            lastName
            username
          }
        }
        duet_video {
          id
          title
          user {
            id
            firstName
            lastName
            username
            profilePhoto
          }
        }
      }
    }
  }
`;

export const ON_STITCH_CREATED = gql`
  subscription OnStitchCreated($originalVideoId: ID!) {
    onStitchCreated(originalVideoId: $originalVideoId) {
      stitch {
        id
        clip_start
        clip_duration
        created_at
        original_video {
          id
          title
          user {
            id
            firstName
            lastName
            username
          }
        }
        stitch_video {
          id
          title
          user {
            id
            firstName
            lastName
            username
            profilePhoto
          }
        }
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 ⚙️ VIDEO PROCESSING
---------------------------------------------------------------------- */

export const ON_VIDEO_PROCESSING_STATUS_CHANGED = gql`
  subscription OnVideoProcessingStatusChanged($videoId: ID!) {
    onVideoProcessingStatusChanged(videoId: $videoId) {
      processingJob {
        id
        status
        started_at
        completed_at
        error_message
        processing_log
        video {
          id
          title
          user {
            id
            firstName
            lastName
          }
        }
      }
      progress
      estimatedCompletion
    }
  }
`;

export const ON_VIDEO_PROCESSING_COMPLETED = gql`
  subscription OnVideoProcessingCompleted($userId: ID!) {
    onVideoProcessingCompleted(userId: $userId) {
      video {
        id
        title
        published_at
        user {
          id
          firstName
          lastName
        }
      }
      processingTime
      result
    }
  }
`;

/* ----------------------------------------------------------------------
 📊 TRENDING & FEEDS
---------------------------------------------------------------------- */

export const ON_PERSONALIZED_FEED_UPDATED = gql`
  subscription OnPersonalizedFeedUpdated($userId: ID!) {
    onPersonalizedFeedUpdated(userId: $userId) {
      feed {
        id
        rank_score
        created_at
        video {
          id
          title
          description
          viral_score
          engagement_rate
          likes_count
          views_count
          user {
            id
            firstName
            lastName
            profilePhoto
            username
          }
        }
      }
      algorithm
      updatedAt
    }
  }
`;

export const ON_VIDEO_GOES_VIRAL = gql`
  subscription OnVideoGoesViral($threshold: Float) {
    onVideoGoesViral(threshold: $threshold) {
      video {
        id
        title
        viral_score
        engagement_rate
        likes_count
        views_count
        shares_count
        created_at
        user {
          id
          firstName
          lastName
          username
          profilePhoto
        }
      }
      viralMetrics
      reachedAt
    }
  }
`;

/* ----------------------------------------------------------------------
 🎯 COMBINED SUBSCRIPTIONS
---------------------------------------------------------------------- */

export const USER_SOCIAL_UPDATES = gql`
  subscription UserSocialUpdates($userId: ID!) {
    onFriendRequestReceived(userId: $userId) {
      friendRequest {
        id
        status
        sender {
          id
          firstName
          lastName
          profilePhoto
        }
      }
    }
    onNotificationReceived(userId: $userId) {
      notification {
        id
        notificationType
        subject
        message
        createdAt
      }
    }
    onFriendshipCreated(userId: $userId) {
      friendship {
        id
        friend {
          id
          firstName
          lastName
          profilePhoto
        }
      }
    }
  }
`;

export const VIDEO_ENGAGEMENT_UPDATES = gql`
  subscription VideoEngagementUpdates($videoId: ID!) {
    onVideoLikeAdded(videoId: $videoId) {
      like {
        id
        user {
          id
          firstName
          lastName
        }
      }
    }
    onVideoCommentAdded(videoId: $videoId) {
      comment {
        id
        text
        user {
          id
          firstName
          lastName
        }
      }
    }
    onVideoShared(videoId: $videoId) {
      share {
        id
        platform
        user {
          id
          firstName
          lastName
        }
      }
    }
    onVideoEngagementUpdated(videoId: $videoId) {
      video {
        id
        likes_count
        comments_count
        shares_count
        engagement_rate
      }
    }
  }
`;

export const CONTENT_CREATOR_UPDATES = gql`
  subscription ContentCreatorUpdates($userId: ID!) {
    onVideoProcessingCompleted(userId: $userId) {
      video {
        id
        title
        published_at
      }
    }
    onVideoEngagementUpdated(videoId: $userId) {
      video {
        id
        title
        engagement_rate
        viral_score
      }
      engagementType
    }
    onVideoGoesViral {
      video {
        id
        title
        viral_score
      }
    }
    onDuetCreated(originalVideoId: $userId) {
      duet {
        id
        duet_video {
          id
          title
          user {
            id
            firstName
            lastName
          }
        }
      }
    }
  }
`;

/* ----------------------------------------------------------------------
 📈 ANALYTICS & INSIGHTS
---------------------------------------------------------------------- */

export const ON_ENGAGEMENT_ANALYTICS_UPDATED = gql`
  subscription OnEngagementAnalyticsUpdated($userId: ID!) {
    onEngagementAnalyticsUpdated(userId: $userId) {
      analytics {
        totalLikes
        totalViews
        totalComments
        totalShares
        engagementRate
        followerGrowth
        topPerformingVideos {
          id
          title
          viral_score
          engagement_rate
        }
        period
      }
      updatedAt
    }
  }
`;

export const ON_CONTENT_RECOMMENDATIONS_UPDATED = gql`
  subscription OnContentRecommendationsUpdated($userId: ID!) {
    onContentRecommendationsUpdated(userId: $userId) {
      recommendations {
        video {
          id
          title
          description
          viral_score
          user {
            id
            firstName
            lastName
            username
          }
        }
        score
        reason
        matchType
      }
      algorithmVersion
      generatedAt
    }
  }
`;

export const FEED_SUBSCRIPTION = gql`
  subscription OnNewVideo {
    newVideo {
      id
      title
      description
      hashtags
      likesCount
      commentsCount
      viewsCount
      sharesCount
      viralScore
      engagementRate
      createdAt
      publishedAt
      videoUrl
      user {
        id
        username
        firstName
        lastName
        profilePhoto
        verified
      }
    }
  }
`;
// Export all subscriptions as a single object for easy importing
export const SOCIAL_SUBSCRIPTION = {
  // Friends & Social
  ON_FRIEND_REQUEST_RECEIVED,
  ON_FRIEND_REQUEST_UPDATED,
  ON_FRIENDSHIP_CREATED,
  ON_FRIENDSHIP_UPDATED,
  ON_FRIEND_SUGGESTIONS_UPDATED,
  ON_FRIENDSHIP_INTERACTION,
  
  // Notifications
  ON_NOTIFICATION_RECEIVED,
  ON_NOTIFICATION_STATUS_CHANGED,
  ON_FRIEND_SUGGESTION_NOTIFICATION,
  
  // Video Content
  ON_NEW_VIDEO_PUBLISHED,
  ON_VIDEO_ENGAGEMENT_UPDATED,
  ON_TRENDING_VIDEOS_UPDATED,
  
  // Video Likes
  ON_VIDEO_LIKE_ADDED,
  ON_VIDEO_LIKE_REMOVED,
  
  // Video Comments
  ON_VIDEO_COMMENT_ADDED,
  ON_VIDEO_COMMENT_UPDATED,
  ON_COMMENT_LIKE_ADDED,
  
  // Video Views
  ON_VIDEO_VIEW_ADDED,
  ON_VIDEO_VIEW_PROGRESS_UPDATED,
  
  // Video Shares
  ON_VIDEO_SHARED,
  
  // Duets & Stitches
  ON_DUET_CREATED,
  ON_STITCH_CREATED,
  
  // Video Processing
  ON_VIDEO_PROCESSING_STATUS_CHANGED,
  ON_VIDEO_PROCESSING_COMPLETED,
  
  // Trending & Feeds
  ON_PERSONALIZED_FEED_UPDATED,
  ON_VIDEO_GOES_VIRAL,
  
  // Combined
  USER_SOCIAL_UPDATES,
  VIDEO_ENGAGEMENT_UPDATES,
  CONTENT_CREATOR_UPDATES,
  
  // Analytics
  ON_ENGAGEMENT_ANALYTICS_UPDATED,
  ON_CONTENT_RECOMMENDATIONS_UPDATED,
  FEED_SUBSCRIPTION
};

export default SOCIAL_SUBSCRIPTION;