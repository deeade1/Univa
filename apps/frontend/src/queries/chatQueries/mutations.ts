import { gql } from '@apollo/client';

// Chat Mutations
export const SEND_MESSAGE_MUTATION = gql`
  mutation SendMessage(
    $chatroomId: String!
    $text: String
    $replyTo: String
    $isDisappearing: Boolean
  ) {
    sendMessage(input: {
      chatroomId: $chatroomId
      text: $text
      replyTo: $replyTo
      isDisappearing: $isDisappearing
    }) {
      message {
        id
        text
        createdAt
        sender {
          id
          username
        }
        chatroom {
          id
        }
      }
      success
    }
  }
`;

export const CREATE_CHATROOM_MUTATION = gql`
  mutation CreateChatRoom(
    $participantIds: [String!]!
    $name: String
    $isGroup: Boolean
  ) {
    createChatRoom(input: {
      participantIds: $participantIds
      name: $name
      isGroup: $isGroup
    }) {
      chatroom {
        id
        name
        isGroup
        participants {
          id
          username
        }
      }
    }
  }
`;

export const UPDATE_USER_STATUS_MUTATION = gql`
  mutation UpdateUserStatus(
    $online: Boolean
    $typing: Boolean
    $typingIn: String
  ) {
    updateUserStatus(input: {
      online: $online
      typing: $typing
      typingIn: $typingIn
    }) {
      status {
        id
        online
        typing
        typingIn {
          id
        }
        user {
          id
        }
      }
    }
  }
`;

export const MARK_MESSAGES_AS_READ_MUTATION = gql`
  mutation MarkMessagesAsRead($chatroomId: String!) {
    markMessagesAsRead(input: { chatroomId: $chatroomId }) {
      success
    }
  }
`;

export const REACT_TO_MESSAGE_MUTATION = gql`
  mutation ReactToMessage($messageId: String!, $reaction: String!) {
    reactToMessage(input: {
      messageId: $messageId
      reaction: $reaction
    }) {
      reaction {
        id
        reaction
        user {
          id
        }
        message {
          id
        }
      }
    }
  }
`;

export const TOGGLE_DISAPPEARING_MESSAGES_MUTATION = gql`
  mutation ToggleDisappearingMessages(
    $chatroomId: String!
    $durationSeconds: Int
  ) {
    toggleDisappearingMessages(input: {
      chatroomId: $chatroomId
      durationSeconds: $durationSeconds
    }) {
      chatroom {
        id
        disappearingMessagesDuration
      }
    }
  }
`;

// Status Updates
export const CREATE_STATUS_UPDATE_MUTATION = gql`
  mutation CreateStatusUpdate($type: String!, $text: String) {
    createStatusUpdate(input: {
      type: $type
      text: $text
    }) {
      status {
        id
        type
        text
        createdAt
        user {
          id
        }
      }
      success
    }
  }
`;

export const VIEW_STATUS_UPDATE_MUTATION = gql`
  mutation ViewStatusUpdate($statusId: String!) {
    viewStatusUpdate(input: { statusId: $statusId }) {
      success
    }
  }
`;

// Call Mutations
export const INITIATE_CALL_MUTATION = gql`
  mutation InitiateCall($recipientId: String!, $callType: String!) {
    initiateCall(input: {
      recipientId: $recipientId
      callType: $callType
    }) {
      call {
        id
        callType
        status
        caller {
          id
        }
        recipient {
          id
        }
      }
      iceServers
    }
  }
`;

export const ANSWER_CALL_MUTATION = gql`
  mutation AnswerCall($callId: String!, $answer: String!) {
    answerCall(input: {
      callId: $callId
      answer: $answer
    }) {
      call {
        id
        status
        sdpAnswer
      }
    }
  }
`;

export const END_CALL_MUTATION = gql`
  mutation EndCall($callId: String!) {
    endCall(input: { callId: $callId }) {
      success
    }
  }
`;

export const ADD_ICE_CANDIDATE_MUTATION = gql`
  mutation AddIceCandidate($callId: String!, $candidate: String!) {
    addIceCandidate(input: {
      callId: $callId
      candidate: $candidate
    }) {
      success
    }
  }
`;