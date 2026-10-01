import { gql } from '@apollo/client';

// Friend Mutations
export const CREATE_FRIEND_MUTATION = gql`
  mutation CreateFriend(
    $friendId: ID!
    $visibility: String
    $relationshipType: String
    $isActive: Boolean
  ) {
    createFriend(input: {
      friendId: $friendId
      visibility: $visibility
      relationshipType: $relationshipType
      isActive: $isActive
    }) {
      friend {
        id
        user {
          id
          username
        }
        friend {
          id
          username
        }
        visibility
        relationshipType
        isActive
      }
      success
      message
    }
  }
`;

export const REMOVE_FRIEND_MUTATION = gql`
  mutation RemoveFriend($friendId: ID!) {
    removeFriend(input: { friendId: $friendId }) {
      success
      message
    }
  }
`;

// Friend Request Mutations
export const SEND_FRIEND_REQUEST_MUTATION = gql`
  mutation SendFriendRequest(
    $receiverId: ID!
    $message: String
  ) {
    sendFriendRequest(input: {
      receiverId: $receiverId
      message: $message
    }) {
      friendRequest {
        id
        sender {
          id
          username
        }
        receiver {
          id
          username
        }
        message
        status
        createdAt
      }
      success
      message
    }
  }
`;

export const RESPOND_FRIEND_REQUEST_MUTATION = gql`
  mutation RespondFriendRequest(
    $requestId: ID!
    $accept: Boolean!
  ) {
    respondFriendRequest(input: {
      requestId: $requestId
      accept: $accept
    }) {
      friendRequest {
        id
        status
        respondedAt
      }
      friendship {
        id
        user {
          id
          username
        }
        friend {
          id
          username
        }
      }
      success
      message
    }
  }
`;


// Input Types
export const FRIEND_INPUT = gql`
  input FriendInput {
    friendId: ID!
    visibility: String
    relationshipType: String
    isActive: Boolean
  }
`;

export const FRIEND_REQUEST_INPUT = gql`
  input FriendRequestInput {
    receiverId: ID!
    message: String
  }
`;

export const RESPOND_FRIEND_REQUEST_INPUT = gql`
  input RespondFriendRequestInput {
    requestId: ID!
    accept: Boolean!
  }
`;


export const LIKE_POST_MUTATION = gql`
  mutation LikePost($postId: ID!) {
    likePost(postId: $postId) {
      success
      message
    }
  }
`;

export const UNLIKE_POST_MUTATION = gql`
  mutation UnlikePost($postId: ID!) {
    unlikePost(postId: $postId) {
      success
      message
    }
  }
`;

export const CREATE_SOCIAL_POST_MUTATION = gql`
  mutation CreateSocialPost($input: CreatePostInput!) {
    createPost(input: $input) {
      success
      message
      post {
        id
        video
        description
        likes
        comments
        shares
        song
        createdAt
        user {
          id
          username
          avatar
          verified
        }
      }
    }
  }
`;

