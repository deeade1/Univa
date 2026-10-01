import { gql } from "@apollo/client";

export const SEARCH_ALL = gql`
  query SearchAll($term: String!) {
    searchAll(term: $term) {
      __typename
      ... on UserProfileNode {
        id
        firstName
      }
      ... on ProductNode {
        id
        name
        slug
      }
      ... on PostNode {
        id
        title
        slug
      }
      ... on BankNode {
        id
        name
      }
      ... on ListingNode {
        id
        slug
      }
      ... on FriendNode {
        id
        friend {
          id
          firstName
        }
      }
      ... on ServiceRequestNode {
        id
        serviceType
      }
    }
  }
`;
