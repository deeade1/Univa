// hooks/useSocialFeed.js
import { useState, useCallback } from 'react';
import { useQuery, useMutation, useSubscription } from '@apollo/client/react';
import {
  GET_FEED_QUERY,
  GET_USER_PROFILE_QUERY,
} from '@/modules/social/api/queries';
import {
  LIKE_POST_MUTATION,
  UNLIKE_POST_MUTATION,
  CREATE_NOTIFICATION_MUTATION,
} from '@/modules/social/api/mutations';
import { FEED_SUBSCRIPTION } from '@/modules/social/api/subscriptions';

export const useSocialFeed = (options = {}) => {
  const { limit = 10 } = options;
  const [refreshing, setRefreshing] = useState(false);

  // Get current user
  const { data: userData } = useQuery(GET_USER_PROFILE_QUERY);
  const currentUserId = userData?.me?.id;

  // Feed query
  const {
    data,
    loading,
    error,
    refetch: refetchQuery,
    fetchMore,
  } = useQuery(GET_FEED_QUERY, {
    variables: { limit, offset: 0 },
    notifyOnNetworkStatusChange: true,
    fetchPolicy: 'cache-and-network',
  });

  // Mutations
  const [likePost] = useMutation(LIKE_POST_MUTATION);
  const [unlikePost] = useMutation(UNLIKE_POST_MUTATION);
  const [createNotification] = useMutation(CREATE_NOTIFICATION_MUTATION);

  // Real-time subscription
  useSubscription(FEED_SUBSCRIPTION, {
    onData: ({ data: subscriptionData }) => {
      if (subscriptionData?.newPost) {
        console.log('New post received:', subscriptionData.newPost);
        // Optional: Add to cache directly instead of refetching
      }
    },
  });

  const posts = data?.feed || [];

  const handleLike = useCallback(
    async (postId, liked, doubleTap = false) => {
      try {
        if (liked) {
          await likePost({
            variables: { postId },
            optimisticResponse: {
              likePost: {
                success: true,
                message: 'Liked',
                __typename: 'LikeResponse',
              },
            },
            update: (cache, { data: likeData }) => {
              if (likeData?.likePost.success) {
                // Update cache optimistically
                cache.modify({
                  id: `Post:${postId}`,
                  fields: {
                    likes(existingLikes = 0) {
                      return existingLikes + 1;
                    },
                    isLiked() {
                      return true;
                    },
                  },
                });

                // Create notification if not current user's post
                const post = posts.find((p) => p.id === postId);
                if (post && post.user.id !== currentUserId) {
                  createNotification({
                    variables: {
                      userId: post.user.id,
                      notificationType: 'POST_LIKE',
                      subject: 'New Like',
                      message: `Someone liked your video`,
                      metadata: JSON.stringify({ postId }),
                    },
                  });
                }
              }
            },
          });
        } else {
          await unlikePost({
            variables: { postId },
            optimisticResponse: {
              unlikePost: {
                success: true,
                message: 'Unliked',
                __typename: 'UnlikeResponse',
              },
            },
          });
        }
      } catch (err) {
        console.error('Like error:', err);
      }
    },
    [likePost, unlikePost, createNotification, posts, currentUserId]
  );

  const handleShare = useCallback(async (postId) => {
    // Implement share logic
    console.log('Sharing post:', postId);
  }, []);

  const handleComment = useCallback((postId) => {
    // Navigation handled in component
    console.log('Commenting on post:', postId);
  }, []);

  const loadMore = useCallback(async () => {
    if (!loading && posts.length > 0) {
      try {
        await fetchMore({
          variables: {
            offset: posts.length,
          },
          updateQuery: (prev, { fetchMoreResult }) => {
            if (!fetchMoreResult) return prev;
            return {
              ...prev,
              feed: [...prev.feed, ...fetchMoreResult.feed],
            };
          },
        });
      } catch (err) {
        console.error('Error loading more:', err);
      }
    }
  }, [loading, posts.length, fetchMore]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refetchQuery();
    } catch (err) {
      console.error('Refresh error:', err);
    } finally {
      setRefreshing(false);
    }
  }, [refetchQuery]);

  return {
    posts,
    loading,
    error,
    refreshing,
    currentUserId,
    handleLike,
    handleShare,
    handleComment,
    loadMore,
    onRefresh,
    refetch: refetchQuery,
  };
};