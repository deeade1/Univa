// GraphQL mutations
import { gql } from '@apollo/client';

export const SIGNUP = gql`
  mutation SignUp($input: CreateUserMutationInput!) {
    signUp(input: $input) {
      token
      refreshToken
      verificationSent
      user {
        id
        email
        phoneNumber
      }
    }
  }
`;

export const VERIFY_ACCOUNT = gql`
  mutation VerifyAccount($token: String!) {
    verifyAccount(input: { token: $token }) {
      success
      user {
        id
        email
        phoneNumber
      }
    }
  }
`;

export const SIGNIN = gql`
  mutation SignIn($contact: String!, $password: String!, $rememberMe: Boolean) {
    signIn(input: { 
      contact: $contact, 
      password: $password, 
      rememberMe: $rememberMe 
    }) {
      token
      refreshToken
      user {
        id
        email
        phoneNumber
        avatarUrl
        firstName
        lastName
      }
    }
  }
`;

export const REFRESH_TOKEN = gql`
  mutation RefreshToken($refreshToken: String!) {
    refreshToken(input: { refreshToken: $refreshToken }) {
      token
      refreshToken
    }
  }
`;

export const REVOKE_TOKEN = gql`
  mutation RevokeToken($refreshToken: String!) {
    revokeToken(input: { refreshToken: $refreshToken }) {
      success
    }
  }
`;

export const LOGOUT = gql`
  mutation Logout {
    logout(input: {}) {
      success
    }
  }
`;

export const REVOKE_ALL_TOKENS = gql`
  mutation RevokeAllTokens($input: RevokeAllTokensMutationInput!) {
    revokeAllTokens(input: $input) {
      revokedCount
    }
  }
`;


export const UPDATE_USER = gql`
  mutation UpdateUser($userId: ID!, $firstName: String, $lastName: String, $group: String) {
    updateUser(input: { 
      userId: $userId,
      firstName: $firstName,
      lastName: $lastName,
      group: $group
    }) {
      user {
        id
        firstName
        lastName
        email
      }
      success
    }
  }
`;

export const GET_ALL_ADDRESSES = gql`
  query GetAllAddresses($first: Int, $after: String, $filter: AddressFilter) {
    allAddresses(first: $first, after: $after, filters: $filter) {
      edges {
        node {
          id
          addressType
          isDefault
          firstName
          lastName
          street_address_1    # ✅ use snake_case
          street_address_2    # ✅ use snake_case
          city
          postalCode
          country
          phone
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


export const REGISTER_FACE = gql`
  mutation RegisterFace($setAsPrimary: Boolean, $verifyImmediately: Boolean) {
    registerFace(input: { 
      setAsPrimary: $setAsPrimary, 
      verifyImmediately: $verifyImmediately 
    }) {
      success
      verification {
        verified
        confidence
        message
      }
      image {
        id
        image
      }
    }
  }
`;

export const VERIFY_FACE = gql`
  mutation VerifyFace($userId: ID) {
    verifyFace(input: { userId: $userId }) {
      verification {
        verified
        confidence
        threshold
        isNewFace
        message
        imageId
      }
    }
  }
`;

export const AUTHENTICATE_WITH_FACE = gql`
  mutation AuthenticateWithFace($contact: String!, $password: String!) {
    authenticateWithFace(input: { 
      contact: $contact, 
      password: $password 
    }) {
      token
      refreshToken
      user {
        id
        email
        phoneNumber
      }
      requiresFaceVerification
    }
  }
`;

export const SEND_MAGIC_LINK = gql`
  mutation SendMagicLink($contact: String!, $redirectTo: String, $channel: String) {
    sendMagicLink(input: { 
      contact: $contact, 
      redirectTo: $redirectTo, 
      channel: $channel 
    }) {
      success
      message
    }
  }
`;

export const VERIFY_MAGIC_LINK = gql`
  mutation VerifyMagicLink($token: String!) {
    verifyMagicLink(input: { token: $token }) {
      valid
      requiresFaceVerification
      requiresLivenessCheck
      user {
        id
        email
        phoneNumber
      }
      message
    }
  }
`;

export const BIOMETRIC_MAGIC_LINK = gql`
  mutation BiometricMagicLink($contact: String!, $redirectTo: String) {
    biometricMagicLink(input: { 
      contact: $contact, 
      redirectTo: $redirectTo 
    }) {
      success
      requiresFaceVerification
      token
      refreshToken
      message
    }
  }
`;

export const SAVE_FCM_TOKEN = gql`
  mutation SaveFcmToken($token: String!) {
    saveFcmToken(input: { token: $token }) {
      success
    }
  }
`;


export const UPDATE_LOYALTY_POINTS = gql`
  mutation UpdateLoyaltyPoints($delta: Int!) {
    updateLoyaltyPoints(input: { delta: $delta }) {
      success
      newPoints
    }
  }
`;

export const REDEEM_LOYALTY_REWARD = gql`
  mutation RedeemLoyaltyReward($rewardId: ID!) {
    redeemLoyaltyReward(input: { rewardId: $rewardId }) {
      success
      message
      remainingPoints
    }
  }
`;

export const NEXT_REWARD = gql`
  query {
    nextAvailableReward {
      reward
      pointsNeeded
    }
  }
`;

export const REDEEM_REWARD = gql`
  mutation Redeem($rewardId: ID!) {
    redeemLoyaltyReward(rewardId: $rewardId) {
      success
      message
      remainingPoints
    }
  }
`;