import { gql } from "@apollo/client";

export const GET_CHATROOM = gql`
  query GetChatRoom($id: ID!) {
    chatroom(id: $id) {
      id
      name
      isGroup
      groupPhoto
      created_at
      updated_at
      disappearingMessagesDuration
      admin {
        id
        username
      }
      participants {
        edges {
          node {
            id
            username
            status {
              online
              lastSeen
            }
          }
        }
      }
    }
  }
`;

export const GET_MESSAGE = gql`
  query GetMessage($id: ID!) {
    message(id: $id) {
      id
      text
      image
      file
      timestamp
      isDisappearing
      disappearAt
      sender {
        id
        username
      }
      chatroom {
        id
        name
      }
      replyTo {
        id
        text
        sender {
          id
          username
        }
      }
      reactions {
        edges {
          node {
            id
            reaction
            user {
              id
              username
            }
          }
        }
      }
    }
  }
`;

export const GET_USER_STATUS = gql`
  query GetUserStatus($id: ID!) {
    userStatus(id: $id) {
      id
      online
      lastSeen
      typing
      typingIn {
        id
        name
      }
      user {
        id
        username
      }
    }
  }
`;

export const GET_MESSAGE_REACTION = gql`
  query GetMessageReaction($id: ID!) {
    messageReaction(id: $id) {
      id
      reaction
      createdAt
      message {
        id
        text
      }
      user {
        id
        username
      }
    }
  }
`;

export const GET_STATUS_UPDATE = gql`
  query GetStatusUpdate($id: ID!) {
    statusUpdate(id: $id) {
      id
      type
      text
      image
      video
      createdAt
      expiresAt
      user {
        id
        username
      }
      views {
        edges {
          node {
            id
            user {
              id
              username
            }
            viewedAt
          }
        }
      }
    }
  }
`;

export const GET_CALL = gql`
  query GetCall($id: ID!) {
    call(id: $id) {
      id
      callType
      status
      startTime
      endTime
      duration
      caller {
        id
        username
      }
      recipient {
        id
        username
      }
    }
  }
`;

export const GET_ALL_CHATROOMS = gql`
  query GetAllChatRooms($first: Int, $after: String) {
    allChatrooms(first: $first, after: $after) {
      edges {
        node {
          id
          name
          isGroup
          updated_at
          participants {
            edges {
              node {
                id
                username
              }
            }
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

export const GET_ALL_MESSAGES = gql`
  query GetAllMessages($first: Int, $after: String) {
    allMessages(first: $first, after: $after) {
      edges {
        node {
          id
          text
          timestamp
          sender {
            id
            username
          }
          chatroom {
            id
            name
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

export const GET_ALL_MESSAGE_REACTIONS = gql`
  query GetAllMessageReactions($first: Int, $after: String) {
    allMessageReactions(first: $first, after: $after) {
      edges {
        node {
          id
          reaction
          createdAt
          message {
            id
          }
          user {
            id
            username
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

export const GET_ALL_USER_STATUSES = gql`
  query GetAllUserStatuses($first: Int, $after: String) {
    allUserStatuses(first: $first, after: $after) {
      edges {
        node {
          id
          online
          lastSeen
          user {
            id
            username
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

export const GET_ALL_STATUS_UPDATES = gql`
  query GetAllStatusUpdates($first: Int, $after: String) {
    allStatusUpdates(first: $first, after: $after) {
      edges {
        node {
          id
          type
          text
          createdAt
          expiresAt
          user {
            id
            username
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

export const GET_ALL_STATUS_VIEWS = gql`
  query GetAllStatusViews($first: Int, $after: String) {
    allStatusViews(first: $first, after: $after) {
      edges {
        node {
          id
          viewedAt
          status {
            id
            text
          }
          user {
            id
            username
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

export const GET_ALL_CALLS = gql`
  query GetAllCalls($first: Int, $after: String) {
    allCalls(first: $first, after: $after) {
      edges {
        node {
          id
          callType
          status
          startTime
          duration
          caller {
            id
            username
          }
          recipient {
            id
            username
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

export const GET_CHATROOM_WITH_MESSAGES = gql`
  query GetChatRoomWithMessages($id: ID!, $first: Int, $after: String) {
    chatroom(id: $id) {
      id
      name
      participants {
        edges {
          node {
            id
            username
            status {
              online
              lastSeen
            }
          }
        }
      }
      messages(first: $first, after: $after) {
        edges {
          node {
            id
            text
            timestamp
            sender {
              id
              username
            }
            reactions {
              edges {
                node {
                  id
                  reaction
                  user {
                    id
                    username
                  }
                }
              }
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
  }
`;