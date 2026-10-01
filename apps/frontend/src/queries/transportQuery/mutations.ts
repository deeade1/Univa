import { gql } from '@apollo/client';

// Service Request Input Types
export const REQUEST_SERVICE_INPUT = gql`
  input RequestServiceInput {
    serviceType: String!
    pickupLat: Float!
    pickupLng: Float!
    dropoffLat: Float
    dropoffLng: Float
    pickupAddress: String!
    dropoffAddress: String
    # Trip specific
    riderCount: Int
    specialRequests: String
    # Delivery specific
    packageDescription: String
    packageWeight: Float
    recipientName: String
    recipientPhone: String
  }
`;

export const UPDATE_SERVICE_STATUS_INPUT = gql`
  input UpdateServiceStatusInput {
    requestId: ID!
    status: String!
  }
`;

export const UPDATE_LOCATION_INPUT = gql`
  input UpdateLocationInput {
    lat: Float!
    lng: Float!
  }
`;

export const BOOK_SHARED_TRIP_INPUT = gql`
  input BookSharedTripInput {
    sharedTripId: ID!
  }
`;

export const JOIN_WAITLIST_INPUT = gql`
  input JoinWaitlistInput {
    sharedTripId: ID!
  }
`;

export const UPDATE_SHARED_TRIP_STATUS_INPUT = gql`
  input UpdateSharedTripStatusInput {
    sharedTripId: ID!
    status: String!
  }
`;

// Transport Service Mutations
export const REQUEST_SERVICE = gql`
  mutation RequestService($input: RequestServiceInput!) {
    requestService(input: $input) {
      serviceRequest {
        id
        serviceType
        status
        createdAt
        ... on Trip {
          pickupAddress
          riderCount
        }
        ... on Delivery {
          packageDescription
          recipientName
        }
      }
    }
  }
`;

export const UPDATE_SERVICE_STATUS = gql`
  mutation UpdateServiceStatus($input: UpdateServiceStatusInput!) {
    updateServiceStatus(input: $input) {
      serviceRequest {
        id
        status
        updatedAt
      }
    }
  }
`;

export const UPDATE_LOCATION = gql`
  mutation UpdateLocation($input: UpdateLocationInput!) {
    updateLocation(input: $input) {
      success
    }
  }
`;

export const BOOK_SHARED_TRIP = gql`
  mutation BookSharedTrip($input: BookSharedTripInput!) {
    bookSharedTrip(input: $input) {
      booking {
        id
        status
        createdAt
      }
      receipt {
        id
        amount
        currency
      }
      sharedTrip {
        id
        availableSeats
      }
    }
  }
`;

export const JOIN_WAITLIST = gql`
  mutation JoinWaitlist($input: JoinWaitlistInput!) {
    joinWaitlist(input: $input) {
      waitlistEntry {
        id
        position
        createdAt
      }
      sharedTrip {
        id
        waitlistCount
      }
    }
  }
`;

export const UPDATE_SHARED_TRIP_STATUS = gql`
  mutation UpdateSharedTripStatus($input: UpdateSharedTripStatusInput!) {
    updateSharedTripStatus(input: $input) {
      sharedTrip {
        id
        status
        updatedAt
      }
    }
  }
`;

export const VERIFY_DRIVER = gql`
  mutation VerifyDriver($tripId: ID!, $image: String!) {
    trip(tripId: $tripId, image: $image) {
      success
      message
    }
  }
`;

export const EMERGENCY_ALERT = gql`
  mutation TriggerEmergency($tripId: ID!) {
    trip(tripId: $tripId) {
      success
      message
    }
  }
`;

export const SEND_MESSAGE = gql`
  mutation SendMessage($tripId: ID!, $message: String!) {
    sendTripMessage(tripId: $tripId, message: $message) {
      id
      message
      timestamp
      user {
        id
        name
      }
    }
  }
`;

// =====================
// Additional Mutations for Logistics
// =====================

export const CREATE_SHIPMENT = gql`
  mutation CreateShipment($input: ShipmentInput!) {
    createShipment(input: $input) {
      id
      trackingNumber
      status
      estimatedDelivery
    }
  }
`;

export const UPDATE_SHIPMENT_STATUS = gql`
  mutation UpdateShipmentStatus($trackingNumber: String!, $status: String!) {
    shipment(trackingNumber: $trackingNumber, status: $status) {
      id
      trackingNumber
      status
      lastUpdated
    }
  }
`;

export const SCHEDULE_MAINTENANCE = gql`
  mutation ScheduleMaintenance($vehicleId: ID!, $date: String!, $type: String!) {
    vehicle(vehicleId: $vehicleId, date: $date, type: $type) {
      id
      vehicleId
      scheduledDate
      maintenanceType
      status
    }
  }
`;