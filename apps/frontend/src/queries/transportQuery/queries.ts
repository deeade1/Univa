import { gql } from '@apollo/client';

// =====================
// Service Provider Queries
// =====================

export const SERVICE_PROVIDER_QUERY = gql`
  query ServiceProvider($id: ID!) {
    serviceProvider(id: $id) {
      id
      providerType
      licenseType
      isAvailable
      rating
      currentService {
        id
        serviceType
      }
      user {
        id
        name
        email
      }
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
          user {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Vehicle Queries
// =====================

export const VEHICLE_QUERY = gql`
  query Vehicle($id: ID!, $category: String) {
    vehicle(id: $id, category: $category) {
      id
      vehicleType
      make
      model
      year
      licensePlate
      isActive
      currentProvider {
        id
        user {
          name
        }
      }
    }
  }
`;

export const ALL_VEHICLES_QUERY = gql`
  query AllVehicles($category: String, $first: Int, $after: String) {
    allVehicles(category: $category, first: $first, after: $after) {
      edges {
        node {
          id
          vehicleType
          make
          model
          isActive
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Service Request Queries
// =====================

export const SERVICE_REQUEST_QUERY = gql`
  query ServiceRequest($id: ID!) {
    serviceRequest(id: $id) {
      id
      serviceType
      status
      customer {
        id
        name
      }
      provider {
        id
        user {
          name
        }
      }
      pickupAddress
      dropoffAddress
      created_at
    }
  }
`;

// =====================
// Trip Queries
// =====================

export const TRIP_QUERY = gql`
  query Trip($id: ID!) {
    trip(id: $id) {
      id
      shared
      availableSeats
      riderCount
      specialRequests
      serviceType
      status
      estimatedDistance
      estimatedDuration
    }
  }
`;

export const ACTIVE_TRIPS_QUERY = gql`
  query ActiveTrips($status: String, $first: Int, $after: String) {
    trips(status: $status, first: $first, after: $after) {
      edges {
        node {
          id
          shared
          status
          pickupAddress
          dropoffAddress
          estimatedDuration
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Shared Trip Queries
// =====================

export const SHARED_TRIP_QUERY = gql`
  query SharedTrip($id: ID!) {
    sharedTrip(id: $id) {
      id
      availableSeats
      dayTime
      status
      waitlistCount
      trip {
        id
        pickupAddress
        dropoffAddress
      }
    }
  }
`;

// Updated query in subscriptions.ts
export const AVAILABLE_SHARED_TRIPS_QUERY = gql`
  query AvailableSharedTrips($seatsRequired: Int = 1, $first: Int, $after: String) {
    sharedTrips(seatsRequired: $seatsRequired, first: $first, after: $after) {
      edges {
        node {
          id
          availableSeats
          totalSeats
          basePrice
          dayTime
          status
          created_at
          updated_at
          waitlistCount
          compatibilityScore
          matchedPreferences {
            music
            conversation
            temperature
          }
          trip {
            id
            pickupAddress
            dropoffAddress
            totalFare
            estimatedDuration
            vehicleType
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Booking Queries
// =====================

export const BOOKING_QUERY = gql`
  query Booking($id: ID!) {
    booking(id: $id) {
      id
      status
      bookedAt
      serviceRequest {
        id
        serviceType
      }
      user {
        id
        name
      }
    }
  }
`;

export const USER_BOOKINGS_QUERY = gql`
  query UserBookings($userId: ID!, $first: Int, $after: String) {
    userBookings(userId: $userId, first: $first, after: $after) {
      edges {
        node {
          id
          status
          bookedAt
          serviceRequest {
            id
            serviceType
            status
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Tracking Queries
// =====================

export const TRACKING_QUERY = gql`
  query Tracking($id: ID!) {
    tracking(id: $id) {
      id
      currentStatus
      estimatedDelivery
      lastUpdated
      serviceRequest {
        id
        serviceType
      }
      events {
        id
        status
        location
        timestamp
      }
    }
  }
`;

export const PACKAGE_TRACKING_QUERY = gql`
  query PackageTracking($first: Int, $after: String) {
    package(first: $first, after: $after) {
      edges {
        node {
          id
          currentStatus
          estimatedDelivery
          serviceRequest {
            id
            pickupAddress
            dropoffAddress
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Combined Transport Queries
// =====================

export const TRANSPORT_DASHBOARD_QUERY = gql`
  query TransportDashboard($userId: ID!) {
    userBookings(userId: $userId, first: 5) {
      edges {
        node {
          id
          status
          bookedAt
          serviceRequest {
            id
            serviceType
            status
            pickupAddress {
              rawAddress
            }
            dropoffAddress {
              rawAddress
            }
            totalFare
            vehicle {
              displayName
              licensePlate
            }
          }
        }
      }
    }
    activeTrips: serviceRequests(status: ["requested", "accepted", "in_progress"], first: 5) {
      edges {
        node {
          id
          serviceType
          status
          pickupAddress {
            rawAddress
          }
          dropoffAddress {
            rawAddress
          }
          estimatedDistance
          estimatedDuration
          totalFare
          customer {
            email
            phone
          }
          vehicle {
            displayName
            licensePlate
          }
        }
      }
    }
    recentDeliveries: serviceRequests(serviceType: "delivery", first: 5) {
      edges {
        node {
          id
          ... on Delivery {
            packageDescription
            packageWeight
            recipientName
            recipientPhone
            deliveryType
          }
        }
      }
    }
  }
`;

export const SERVICE_PROVIDER_DETAILS_QUERY = gql`
  query ServiceProviderDetails($id: ID!) {
    serviceProvider(id: $id) {
      id
      providerType
      rating
      currentService {
        id
        serviceType
        status
      }
      vehicles {
        id
        vehicleType
        make
        model
      }
      recentServices(first: 5) {
        edges {
          node {
            id
            serviceType
            status
            created_at
          }
        }
      }
    }
  }
`;

export const GET_COMPATIBILITY = gql`
  query GetCompatibility($tripId: ID!) {
    sharedTrip(id: $tripId) {
      id
      compatibilityScore
      matchedPreferences {
        music
        conversation
      }
    }
  }
`;

export const GET_CARBON_SAVINGS = gql`
  query GetCarbonSavings($tripId: ID!) {
    trip(id: $tripId) {
      carbonSavings
      equivalent
    }
  }
`;

// =====================
// Additional Queries for Logistics
// =====================

export const GET_SHIPMENT_STATUS = gql`
  query GetShipmentStatus($trackingNumber: String!) {
    shipmentStatus(trackingNumber: $trackingNumber) {
      trackingNumber
      currentStatus
      estimatedDelivery
      lastUpdated
      coordinates {
        latitude
        longitude
      }
      events {
        status
        location
        timestamp
        description
      }
    }
  }
`;

export const GET_WAREHOUSE_INVENTORY = gql`
  query GetWarehouseInventory($warehouseId: ID) {
    warehouseInventory(warehouseId: $warehouseId) {
      totalCapacity
      currentStock
      availableSpace
      utilizationRate
    }
  }
`;

export const GET_FLEET_STATUS = gql`
  query GetFleetStatus {
    fleetStatus {
      totalVehicles
      available
      inMaintenance
      onRoute
      byCategory {
        category
        count
      }
      byType {
        vehicleType
        count
      }
    }
  }
`;

export const GET_ACTIVE_SERVICE_REQUESTS = gql`
  query GetActiveServiceRequests($status: [String!]) {
    serviceRequests(status: $status) {
      edges {
        node {
          id
          serviceType
          status
          customer {
            email
            phone
          }
          provider {
            user {
              email
            }
          }
          vehicle {
            displayName
            licensePlate
          }
          createdAt
          estimatedDistance
          totalFare
        }
      }
    }
  }
`;