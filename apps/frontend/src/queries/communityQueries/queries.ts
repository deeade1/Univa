import { gql } from "@apollo/client";

export const GET_FRIEND = gql`
  query GetFriend($id: ID!) {
    friend(id: $id) {
      id
      user {
        id
        firstName
        lastName
        avatar
      }
      friend {
        id
        firstName
        lastName
        avatar
      }
      createdAt
      isActive
      visibility
      relationshipType
    }
  }
`;

export const GET_ALL_FRIENDS = gql`
  query GetAllFriends($first: Int, $after: String) {
    allFriends(first: $first, after: $after) {
      edges {
        node {
          id
          user {
            id
            firstName
          }
          friend {
            id
            firstName
            lastName
            avatar
          }
          createdAt
          isActive
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_FRIEND_REQUEST = gql`
  query GetFriendRequest($id: ID!) {
    friendRequest(id: $id) {
      id
      sender {
        id
        firstName
        lastName
        avatar
      }
      receiver {
        id
        firstName
        lastName
        avatar
      }
      message
      createdAt
      status
      respondedAt
    }
  }
`;

export const GET_ALL_FRIEND_REQUESTS = gql`
  query GetAllFriendRequests($first: Int, $after: String) {
    allFriendRequests(first: $first, after: $after) {
      edges {
        node {
          id
          sender {
            id
            firstName
          }
          receiver {
            id
            firstName
          }
          status
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_NOTIFICATION = gql`
  query GetNotification($id: ID!) {
    notification(id: $id) {
      id
      notificationType
      subject
      message
      channel
      status
      createdAt
      sentAt
      user {
        id
        email
      }
    }
  }
`;

export const GET_ALL_NOTIFICATIONS = gql`
  query GetAllNotifications($first: Int, $after: String) {
    allNotifications(first: $first, after: $after) {
      edges {
        node {
          id
          notificationType
          subject
          status
          createdAt
          user {
            id
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_USER_FRIENDS = gql`
  query GetUserFriends($userId: ID!, $first: Int, $after: String) {
    allFriends(first: $first, after: $after, filters: {user: $userId, isActive: true}) {
      edges {
        node {
          id
          friend {
            id
            firstName
            lastName
            avatar
          }
          relationshipType
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_PENDING_FRIEND_REQUESTS = gql`
  query GetPendingFriendRequests($userId: ID!, $first: Int, $after: String) {
    allFriendRequests(
      first: $first
      after: $after
      filters: {receiver: $userId, status: "pending"}
    ) {
      edges {
        node {
          id
          sender {
            id
            firstName
            lastName
            avatar
          }
          message
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_USER_NOTIFICATIONS = gql`
  query GetUserNotifications($userId: ID!, $first: Int, $after: String) {
    allNotifications(
      first: $first
      after: $after
      filters: {user: $userId}
    ) {
      edges {
        node {
          id
          notificationType
          subject
          status
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;