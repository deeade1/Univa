import { gql } from "@apollo/client";

export const LISTING_BASIC_FIELDS = gql`
  fragment ListingBasicFields on ListingType {
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
  fragment ListingImageFields on ListingImageType {
    id
    shortDescription
  }
`;

export const LISTING_FILE_FIELDS = gql`
  fragment ListingFileFields on ListingFileType {
    id
    name
    shortDescription
  }
`;

