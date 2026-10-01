import { gql } from '@apollo/client';


// Mutations
export const UPDATE_CLIENT_LOCATION = gql`
  mutation UpdateClientLocation($clientId: ID!, $latitude: Float!, $longitude: Float!) {
    updateClientLocation(
      clientId: $clientId
      latitude: $latitude
      longitude: $longitude
    ) {
      success
    }
  }
`;

export const UPDATE_AGENT_LOCATION = gql`
  mutation UpdateAgentLocation($agentId: ID!, $latitude: Float!, $longitude: Float!) {
    updateAgentLocation(
      agentId: $agentId
      latitude: $latitude
      longitude: $longitude
    ) {
      success
    }
  }
`;

export const CREATE_LISTING_TYPE = gql`
  mutation CreateListingType($propertyType: String!) {
    createListingType(propertyType: $propertyType) {
      success
      listingType {
        id
        propertyType
      }
    }
  }
`;

export const ADD_LISTING_IMAGE = gql`
  mutation AddListingImage($listingId: ID!, $shortDescription: String) {
    addListingImage(listingId: $listingId, shortDescription: $shortDescription) {
      success
      listingImage {
        id
        image
        shortDescription
      }
    }
  }
`;

export const ADD_LISTING_FILE = gql`
  mutation AddListingFile(
    $listingId: ID!
    $name: String!
    $shortDescription: String
    $forCustomer: Boolean = true
  ) {
    addListingFile(
      listingId: $listingId
      name: $name
      shortDescription: $shortDescription
      forCustomer: $forCustomer
    ) {
      success
      listingFile {
        id
        name
        file
        shortDescription
        forCustomer
      }
    }
  }
`;

export const CREATE_LISTING = gql`
  mutation CreateListing(
    $title: String!
    $description: String!
    $price: Decimal!
    $propertyArea: String!
    $listingTypeId: ID!
    $addressId: ID!
    $bedrooms: Int
    $ceilingHeight: Float
    $bathrooms: Int
    $garage: Int = 0
    $squareFeet: Float
    $lotSize: Float
    $propertyStatus: String = "draft"
    $propertyFor: String = "S"
    $yearBuilt: Int = 0
    $agentId: ID
    $ownerId: ID
    $reviewerId: ID
    $freeFrom: Date!
    $latitude: Float
    $longitude: Float
  ) {
    createListing(
      input: {
        title: $title
        description: $description
        price: $price
        propertyArea: $propertyArea
        listingTypeId: $listingTypeId
        addressId: $addressId
        bedrooms: $bedrooms
        ceilingHeight: $ceilingHeight
        bathrooms: $bathrooms
        garage: $garage
        squareFeet: $squareFeet
        lotSize: $lotSize
        propertyStatus: $propertyStatus
        propertyFor: $propertyFor
        yearBuilt: $yearBuilt
        agentId: $agentId
        ownerId: $ownerId
        reviewerId: $reviewerId
        freeFrom: $freeFrom
        latitude: $latitude
        longitude: $longitude
      }
    ) {
      id
      listing {
        id
        title
        price {
          amount
          currency
        }
        propertyStatus
      }
      listingType {
        id
        propertyType
      }
      address {
        id
        streetAddress
      }
      success
    }
  }
`;

export const UPDATE_LISTING = gql`
  mutation UpdateListing(
    $id: ID!
    $title: String
    $description: String
    $price: Decimal
    $propertyArea: String
    $listingTypeId: ID
    $addressId: ID
    $bedrooms: Int
    $ceilingHeight: Float
    $bathrooms: Int
    $garage: Int
    $squareFeet: Float
    $lotSize: Float
    $propertyStatus: String
    $propertyFor: String
    $yearBuilt: Int
    $agentId: ID
    $ownerId: ID
    $reviewerId: ID
    $freeFrom: Date
  ) {
    updateListing(
      input: {
        id: $id
        title: $title
        description: $description
        price: $price
        propertyArea: $propertyArea
        listingTypeId: $listingTypeId
        addressId: $addressId
        bedrooms: $bedrooms
        ceilingHeight: $ceilingHeight
        bathrooms: $bathrooms
        garage: $garage
        squareFeet: $squareFeet
        lotSize: $lotSize
        propertyStatus: $propertyStatus
        propertyFor: $propertyFor
        yearBuilt: $yearBuilt
        agentId: $agentId
        ownerId: $ownerId
        reviewerId: $reviewerId
        freeFrom: $freeFrom
      }
    ) {
      id
      listing {
        id
        title
        price {
          amount
          currency
        }
        propertyStatus
      }
      success
    }
  }
`;

export const DELETE_LISTING = gql`
  mutation DeleteListing($id: ID!) {
    deleteListing(id: $id) {
      id
      success
    }
  }
`;

export const NEARBY_PROPERTIES = gql`
  mutation UpdateNearbyProperties(
    $latitude: Float!
    $longitude: Float!
    $radiusKm: Int = 10
    $maxResults: Int = 20
  ) {
    nearbyProperties(
      latitude: $latitude
      longitude: $longitude
      radiusKm: $radiusKm
      maxResults: $maxResults
    ) {
      id
      title
      price {
        amount
        currency
      }
      distanceKm
      address {
        streetAddress
        city
      }
    }
  }
`;

export const CREATE_PROPERTY_SUBSCRIPTION = gql`
  mutation CreatePropertySubscription(
    $propertyType: String
    $latitude: Float
    $longitude: Float
    $radiusKm: Int = 10
  ) {
    createPropertySubscription(
      input: {
        propertyType: $propertyType
        latitude: $latitude
        longitude: $longitude
        radiusKm: $radiusKm
      }
    ) {
      subscription {
        id
        propertyType
        latitude
        longitude
        radiusKm
        createdAt
      }
    }
  }
`;

export const UPDATE_PROPERTY_SUBSCRIPTION = gql`
  mutation UpdatePropertySubscription(
    $subscriptionId: ID!
    $propertyType: String
    $latitude: Float
    $longitude: Float
    $radiusKm: Int
  ) {
    updatePropertySubscription(
      input: {
        subscriptionId: $subscriptionId
        propertyType: $propertyType
        latitude: $latitude
        longitude: $longitude
        radiusKm: $radiusKm
      }
    ) {
      subscription {
        id
        propertyType
        latitude
        longitude
        radiusKm
      }
    }
  }
`;

export const DELETE_PROPERTY_SUBSCRIPTION = gql`
  mutation DeletePropertySubscription($subscriptionId: ID!) {
    deletePropertySubscription(subscriptionId: $subscriptionId) {
      success
    }
  }
`;

export const CREATE_VIRTUAL_TOUR = gql`
  mutation CreateVirtualTour($input: CreateVirtualTourInput!) {
    createVirtualTour(input: $input) {
      virtualTour {
        id
        tourUrl
        isPrimary
        thumbnail
        createdAt
        property {
          id
          title
        }
      }
    }
  }
`;

export const SCHEDULE_LIVE_TOUR = gql`
  mutation ScheduleLiveTour($input: ScheduleLiveTourInput!) {
    scheduleLiveTour(input: $input) {
      liveTour {
        id
        scheduledTime
        durationMinutes
        meetingLink
        maxAttendees
        property {
          id
          title
        }
        agent {
          id
          fullName
        }
      }
    }
  }
`;

export const REGISTER_FOR_LIVE_TOUR = gql`
  mutation RegisterForLiveTour($input: RegisterForLiveTourInput!) {
    registerForLiveTour(input: $input) {
      registration {
        id
        registeredAt
        attended
        tour {
          id
          scheduledTime
          property {
            title
          }
        }
      }
    }
  }
`;
