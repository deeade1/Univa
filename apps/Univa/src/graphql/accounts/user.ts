
import { gql } from '@apollo/client';

/**
 * Load the currently authenticated user.
 * The request must include the access-token Authorization header.
 */
export const ME_QUERY = gql`
  query Me {
    me {
      id
      email
      firstName
      lastName
      phoneNumber
      fullName
      displayName
      isEmailVerified
      emailVerified
      isActive
      dateJoined
      lastLogin
    }
  }
`;


export const CONFIRM_EMAIL_MUTATION = gql`
  mutation ConfirmEmail($input: ConfirmEmailInput!) {
    confirmEmail(input: $input) {
      success
      message
      clientMutationId
    }
  }
`;