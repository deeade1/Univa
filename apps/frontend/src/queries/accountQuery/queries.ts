import { gql } from "@apollo/client";

export const GET_USER = gql`
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      email
      phoneNumber
      firstName
      lastName
      avatarUrl
      dateJoined
      roles {
        id
        name
        appName
      }
    }
  }
`;


export const GET_USER_PROFILE = gql`
  query GetUserProfile($userId: ID) {
    userProfile(userId: $userId) {
      id
      profilePicture
      rating
      isOnline
      lastActive
      isVerified
      verificationLevel
      dateOfBirth
      gender
      loyaltyPoints
      preferredNotificationMethod
      user {
        id
        email
        firstName
        lastName
      }
    }
  }
`;

export const GET_ALL_USERS = gql`
  query GetAllUsers($first: Int, $after: String, $filter: UserFilter) {
    allUsers(first: $first, after: $after, filters: $filter) {
      edges {
        node {
          id
          email
          firstName
          lastName
          isActive
          profile {
            id
            isVerified
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
          street_address_1
          street_Address_2
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

export const GET_ALL_ROLES = gql`
  query GetAllRoles($first: Int, $after: String) {
    allRoles(first: $first, after: $after) {
      edges {
        node {
          id
          name
          appName
          description
          isDefault
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

export const GET_USER_ROLES = gql`
  query GetUserRoles($first: Int, $after: String) {
    userRoles(first: $first, after: $after) {
      edges {
        node {
          id
          isActive
          role {
            id
            name
            appName
          }
          verifiedAt
          expiresAt
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

export const GET_PROFILE_IMAGES = gql`
  query GetProfileImages($first: Int, $after: String) {
    profileImages(first: $first, after: $after) {
      edges {
        node {
          id
          image
          isVerified
          faceDetected
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

export const GET_FACE_ENCODINGS = gql`
  query GetFaceEncodings($first: Int, $after: String) {
    faceEncodings(first: $first, after: $after) {
      edges {
        node {
          id
          version
          isActive
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

export const GET_FACE_VERIFICATION = gql`
  query GetFaceVerification {
    faceVerification {
      isVerified
      verificationMethod
      lastVerifiedAt
      verificationAttempts
    }
  }
`;

export const GET_PAGINATED_ROLES = gql`
  query GetPaginatedRoles($page: Int, $pageSize: Int) {
    paginatedRoles(page: $page, pageSize: $pageSize) {
      totalCount
      page
      pageSize
      hasNext
      hasPrev
      results {
        id
        name
        appName
      }
    }
  }
`;

export const GET_STATES_BY_COUNTRY = gql`
  query GetStatesByCountry($countryCode: String!) {
    statesByCountry(countryCode: $countryCode)
  }
`;

export const GET_LOYALTY_HISTORY = gql`
  query GetLoyaltyHistory($userId: ID!, $first: Int, $after: String) {
    loyaltyHistory(userId: $userId, first: $first, after: $after) {
      edges {
        node {
          id
          reward
          dateRedeemed
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

export const GET_LOYALTY_REWARD_TIERS = gql`
  query GetLoyaltyRewardTiers($first: Int, $after: String) {
    loyaltyRewardTiers(first: $first, after: $after) {
      edges {
        node {
          id
          pointsNeeded
          reward
          description
          active
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

export const GET_ALL_REWARDS = gql`
  query GetAllRewards($first: Int, $after: String) {
    allRewards(first: $first, after: $after) {
      edges {
        node {
          id
          pointsNeeded
          reward
          description
          active
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

export const GET_NEXT_AVAILABLE_REWARD = gql`
  query GetNextAvailableReward {
    nextAvailableReward {
      pointsNeeded
      reward
    }
  }
`;

export const GET_MY_FACE_VERIFICATION = gql`
  query GetMyFaceVerification {
    myFaceVerification {
      isVerified
      verificationMethod
      lastVerifiedAt
      verificationAttempts
      lockedUntil
    }
  }
`;