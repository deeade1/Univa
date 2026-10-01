
// =====================
// Updated Queries and Mutations
// =====================
import { gql } from '@apollo/client';

// Single Item Queries
export const LISTING_TYPE_QUERY = gql`
  query ListingType($id: ID!) {
    listingType(id: $id) {
      id
      propertyType
    }
  }
`;

export const LISTING_QUERY = gql`
  query Listing($id: ID!) {
    listing(id: $id) {
      id
      title
      description
      price
      bedrooms
      bathrooms
      squareFeet
      propertyStatus
      location {
        latitude
        longitude
      }
      images {
        edges {
          node {
            id
            imageUrl
          }
        }
      }
    }
  }
`;

export const LISTING_IMAGE_QUERY = gql`
  query ListingImage($id: ID!) {
    listingImage(id: $id) {
      id
      imageUrl
      shortDescription
      listing {
        id
        title
      }
    }
  }
`;

export const CLIENT_QUERY = gql`
  query Client($id: ID!) {
    client(id: $id) {
      id
      firstName
      lastName
      email
      phone
      location {
        latitude
        longitude
      }
    }
  }
`;

export const AGENT_QUERY = gql`
  query Agent($id: ID!) {
    agent(id: $id) {
      id
      firstName
      lastName
      email
      phone
      location {
        latitude
        longitude
      }
      listings {
        edges {
          node {
            id
            title
          }
        }
      }
    }
  }
`;

// List Queries
export const ALL_LISTINGS_QUERY = gql`
  query AllListings($first: Int, $after: String) {
    allListings(first: $first, after: $after) {
      edges {
        node {
          id
          title
          price
          bedrooms
          propertyStatus
          thumbnailUrl
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const ALL_CLIENTS_QUERY = gql`
  query AllClients($first: Int, $after: String) {
    allClients(first: $first, after: $after) {
      edges {
        node {
          id
          firstName
          lastName
          email
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const ALL_AGENTS_QUERY = gql`
  query AllAgents($first: Int, $after: String) {
    allAgents(first: $first, after: $after) {
      edges {
        node {
          id
          firstName
          lastName
          email
          listingsCount
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;


// Additional Entity Queries
export const VIRTUAL_TOUR_QUERY = gql`
  query VirtualTour($id: ID!) {
    virtualTour(id: $id) {
      id
      tourUrl
      thumbnailUrl
      isPrimary
      property {
        id
        title
      }
    }
  }
`;

export const DOCUMENT_PACKAGE_QUERY = gql`
  query DocumentPackage($id: ID!) {
    documentPackage(id: $id) {
      id
      title
      isCompleted
      documents {
        edges {
          node {
            id
            title
          }
        }
      }
    }
  }
`;

export const TRANSACTION_QUERY = gql`
  query Transaction($id: ID!) {
    transaction(id: $id) {
      id
      status
      offerPrice
      agreedPrice
      milestones {
        edges {
          node {
            id
            name
            dueDate
            completedDate
          }
        }
      }
    }
  }
`;

export const NEIGHBORHOOD_QUERY = gql`
  query Neighborhood($id: ID!) {
    neighborhood(id: $id) {
      id
      name
      avgPrice
      schoolRating
      boundary {
        coordinates
      }
    }
  }
`;

export const MARKET_TRENDS_QUERY = gql`
  query MarketTrends($neighborhoodId: ID!, $first: Int, $after: String) {
    marketTrends(neighborhoodId: $neighborhoodId, first: $first, after: $after) {
      edges {
        node {
          id
          date
          medianPrice
          listingsCount
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;


// ============================================================================
// Nearby Properties (uses PropertyProximityFilter)
// ============================================================================

export const GET_NEARBY_PROPERTIES_QUERY = gql`
  query GetNearbyProperties(
    $latitude: Float
    $longitude: Float
    $radiusKm: Float
    $maxResults: Int
    $first: Int
    $after: String
  ) {
    nearbyProperties(
      latitude: $latitude
      longitude: $longitude
      radiusKm: $radiusKm
      maxResults: $maxResults
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          distanceKm
          isNearPreferred
          listing {
            id
            title
            price
            propertyStatus
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// ============================================================================
// Properties in Neighborhood (uses ListingFilter)
// ============================================================================

export const PROPERTIES_IN_NEIGHBORHOOD_QUERY = gql`
  query PropertiesInNeighborhood(
    $neighborhoodId: ID
    $status: String
    $propertyType: String
    $first: Int
    $after: String
  ) {
    propertiesInNeighborhood(
      neighborhoodId: $neighborhoodId
      status: $status
      propertyType: $propertyType
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          title
          price
          propertyStatus
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// ============================================================================
// Upcoming Live Tours (uses LiveTourScheduleFilter)
// ============================================================================

export const UPCOMING_LIVE_TOURS_QUERY = gql`
  query UpcomingLiveTours(
    $daysAhead: Int
    $first: Int
    $after: String
  ) {
    upcomingLiveTours(
      daysAhead: $daysAhead
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          scheduledTime
          durationMinutes
          maxAttendees
          attendeesCount
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// ============================================================================
// Market Trends (uses MarketTrendFilter)
// ============================================================================

export const ALL_MARKET_TRENDS_QUERY = gql`
  query AllMarketTrends(
    $neighborhoodId: ID
    $first: Int
    $after: String
  ) {
    allMarketTrends(
      neighborhoodId: $neighborhoodId
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          date
          medianPrice
          listingsCount
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;