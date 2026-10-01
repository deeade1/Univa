import { gql } from "@apollo/client";

export const LISTING_BASIC_FIELDS = gql`
  fragment ListingBasicFields on ListingNode {
    id
    title
    description
    price
    propertyStatus
    propertyFor
    created
  }
`;

export const LISTING_IMAGE_FIELDS = gql`
  fragment ListingImageFields on ListingImageNode {
    id
    shortDescription
  }
`;

export const LISTING_FILE_FIELDS = gql`
  fragment ListingFileFields on ListingFileNode {
    id
    name
    shortDescription
  }
`;

