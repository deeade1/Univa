
import { gql } from '@apollo/client';

export const SIGN_IN_MUTATION = gql`
  mutation SignIn($input: ObtainJSONWebTokenMutationInput!) {
    signIn(input: $input) {
      token
      refreshToken
      user {
        id
        email
        firstName
        lastName
        phoneNumber
        isActive
        isEmailVerified
        displayName
      }
    }
  }
`;

export const REFRESH_TOKEN_MUTATION = gql`
  mutation RefreshToken($input: RefreshTokenMutationInput!) {
    refreshToken(input: $input) {
      token
      refreshToken
    }
  }
`;

export const REVOKE_TOKEN_MUTATION = gql`
  mutation RevokeToken($input: RevokeTokenMutationInput!) {
    revokeToken(input: $input) {
      success
    }
  }
`;

export const LOGOUT_MUTATION = gql`
  mutation Logout($input: LogoutMutationInput!) {
    logout(input: $input) {
      success
    }
  }
`;

export const CREATE_USER_MUTATION = gql`
  mutation CreateUser($input: CreateUserMutationInput!) {
    createUser(input: $input) {
      user {
        id
        email
        phoneNumber
        isActive
      }
      token
      refreshToken
      verificationSent
    }
  }
`;

export const SEND_PASSWORD_RESET_MUTATION = gql`
  mutation SendPasswordReset(
    $input: SendPasswordResetMutationInput!
  ) {
    sendPasswordReset(input: $input) {
      success
    }
  }
`;

export const SEND_MAGIC_LINK_MUTATION = gql`
  mutation SendMagicLink($input: SendMagicLinkMutationInput!) {
    sendMagicLink(input: $input) {
      success
      message
    }
  }
`;
