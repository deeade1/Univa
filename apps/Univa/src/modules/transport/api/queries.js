/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/transport/api/queries.js                            */
/* -------------------------------------------------------------------------- */

import { gql } from "@apollo/client";

// ============================================================================
// Service Provider Queries
// ============================================================================

export const SERVICE_PROVIDER_QUERY = gql`
  query ServiceProvider($id: ID!) {
    serviceProvider(id: $id) {
      id
      providerType
      licenseType
      isAvailable
      rating
    }
  }
`;

export const ALL_SERVICE_PROVIDERS_QUERY = gql`
  query AllServiceProviders($first: Int, $after: String) {
    allServiceProviders(first: $first, after: $after) {
      edges {
        node {
          id
          providerType
          isAvailable
          rating
        }
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
// Service Request Queries
// ============================================================================

export const SERVICE_REQUEST_QUERY = gql`
  query ServiceRequest($id: ID!) {
    serviceRequest(id: $id) {
      id
      serviceType
      status
      createdAt
    }
  }
`;

// ============================================================================
// Trip Queries
// ============================================================================

export const TRIP_QUERY = gql`
  query Trip($id: ID!) {
    trip(id: $id) {
      id
      status
      serviceType
    }
  }
`;

export const INTERSTATE_TRIPS_QUERY = gql`
  query InterstateTrips($first: Int, $after: String) {
    interstateTrips(first: $first, after: $after) {
      edges {
        node {
          id
          status
          serviceType
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

export const ACTIVE_TRIPS_QUERY = gql`
  query ActiveTrips($first: Int, $after: String) {
    activeTrips(first: $first, after: $after) {
      edges {
        node {
          id
          status
          serviceType
        }
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
// Shared Trip Queries
// ============================================================================

export const SHARED_TRIP_QUERY = gql`
  query SharedTrip($id: ID!) {
    sharedTrip(id: $id) {
      id
      status
    }
  }
`;

export const AVAILABLE_SHARED_TRIPS_QUERY = gql`
  query AvailableSharedTrips(
    $seatsRequired: Int
    $first: Int
    $after: String
  ) {
    availableSharedTrips(
      seatsRequired: $seatsRequired
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          status
        }
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
// Booking Queries
// ============================================================================

export const BOOKING_QUERY = gql`
  query Booking($id: ID!) {
    booking(id: $id) {
      id
      status
      bookedAt
    }
  }
`;

export const ALL_BOOKINGS_QUERY = gql`
  query AllBookings($first: Int, $after: String) {
    allBookings(first: $first, after: $after) {
      edges {
        node {
          id
          status
          bookedAt
        }
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
// Tracking Queries
// ============================================================================

export const TRACKING_QUERY = gql`
  query Tracking($id: ID!) {
    tracking(id: $id) {
      id
    }
  }
`;

export const ALL_TRACKING_QUERY = gql`
  query AllTracking($first: Int, $after: String) {
    allTracking(first: $first, after: $after) {
      edges {
        node {
          id
        }
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
// Delivery Queries
// ============================================================================

export const ALL_DELIVERIES_QUERY = gql`
  query AllDeliveries($first: Int, $after: String) {
    allDeliveries(first: $first, after: $after) {
      edges {
        node {
          id
          serviceType
          status
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

export const DELIVERY_QUERY = gql`
  query Delivery($id: ID!) {
    delivery(id: $id) {
      id
      serviceType
      status
    }
  }
`;

// ============================================================================
// Vehicle Queries
// ============================================================================

export const VEHICLE_QUERY = gql`
  query Vehicle($id: ID!) {
    vehicle(id: $id) {
      id
    }
  }
`;

export const ALL_VEHICLES_QUERY = gql`
  query AllVehicles($first: Int, $after: String) {
    allVehicles(first: $first, after: $after) {
      edges {
        node {
          id
        }
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
// Pricing Profile Queries
// ============================================================================

export const PRICING_PROFILE_QUERY = gql`
  query PricingProfile($id: ID!) {
    pricingProfile(id: $id) {
      id
    }
  }
`;

export const ALL_PRICING_PROFILES_QUERY = gql`
  query AllPricingProfiles($first: Int, $after: String) {
    allPricingProfiles(first: $first, after: $after) {
      edges {
        node {
          id
        }
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
// Stop Point Queries
// ============================================================================

export const STOP_POINT_QUERY = gql`
  query StopPoint($id: ID!) {
    stopPoint(id: $id) {
      id
    }
  }
`;

export const ALL_STOP_POINTS_QUERY = gql`
  query AllStopPoints($first: Int, $after: String) {
    allStopPoints(first: $first, after: $after) {
      edges {
        node {
          id
        }
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
// Analytics Queries
// ============================================================================

export const ANALYTICS_PROFILE_QUERY = gql`
  query AnalyticsProfile($id: ID!) {
    analyticsProfile(id: $id) {
      id
    }
  }
`;

export const ALL_ANALYTICS_PROFILES_QUERY = gql`
  query AllAnalyticsProfiles($first: Int, $after: String) {
    allAnalyticsProfiles(first: $first, after: $after) {
      edges {
        node {
          id
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

export const RIDE_METRICS_QUERY = gql`
  query RideMetrics($id: ID!) {
    rideMetrics(id: $id) {
      id
    }
  }
`;

export const ALL_RIDE_METRICS_QUERY = gql`
  query AllRideMetrics($first: Int, $after: String) {
    allRideMetrics(first: $first, after: $after) {
      edges {
        node {
          id
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

export const KPI_QUERY = gql`
  query KPI($id: ID!) {
    kpi(id: $id) {
      id
    }
  }
`;

export const ALL_KPIS_QUERY = gql`
  query AllKPIs($first: Int, $after: String) {
    allKpis(first: $first, after: $after) {
      edges {
        node {
          id
        }
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
// Boarding Ticket Queries
// ============================================================================

export const BOARDING_TICKET_QUERY = gql`
  query BoardingTicket($id: ID!) {
    boardingTicket(id: $id) {
      id
    }
  }
`;

// ============================================================================
// Export All
// ============================================================================

export default {
  SERVICE_PROVIDER_QUERY,
  ALL_SERVICE_PROVIDERS_QUERY,
  SERVICE_REQUEST_QUERY,
  TRIP_QUERY,
  INTERSTATE_TRIPS_QUERY,
  ACTIVE_TRIPS_QUERY,
  SHARED_TRIP_QUERY,
  AVAILABLE_SHARED_TRIPS_QUERY,
  BOOKING_QUERY,
  ALL_BOOKINGS_QUERY,
  TRACKING_QUERY,
  ALL_TRACKING_QUERY,
  ALL_DELIVERIES_QUERY,
  DELIVERY_QUERY,
  VEHICLE_QUERY,
  ALL_VEHICLES_QUERY,
  PRICING_PROFILE_QUERY,
  ALL_PRICING_PROFILES_QUERY,
  STOP_POINT_QUERY,
  ALL_STOP_POINTS_QUERY,
  ANALYTICS_PROFILE_QUERY,
  ALL_ANALYTICS_PROFILES_QUERY,
  RIDE_METRICS_QUERY,
  ALL_RIDE_METRICS_QUERY,
  KPI_QUERY,
  ALL_KPIS_QUERY,
  BOARDING_TICKET_QUERY,
};