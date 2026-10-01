import { gql } from "@apollo/client";

export const MARKET_ITEMS = gql`
  query {
    marketItems {
      edges {
        node {
          id
          name
          category
          subcategory
          pricePerUnit
          stock
        }
      }
    }
  }
`;
