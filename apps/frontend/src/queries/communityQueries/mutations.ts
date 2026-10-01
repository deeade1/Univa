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

// Notification Mutation
export const CREATE_COMMUNITY_NOTIFICATION_MUTATION = gql`
  mutation CreateCommunityNotification(
    $userId: ID!
    $notificationType: String!
    $subject: String!
    $message: String!
    $channel: String!
    $metadata: JSONString
  ) {
    createNotification(input: {
      userId: $userId
      notificationType: $notificationType
      subject: $subject
      message: $message
      channel: $channel
      metadata: $metadata
    }) {
      notification {
        id
        notificationType
        subject
        message
        channel
        status
        createdAt
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

export const NOTIFICATION_INPUT = gql`
  input NotificationInput {
    userId: ID!
    notificationType: String!
    subject: String!
    message: String!
    channel: String!
    metadata: JSONString
  }
`;