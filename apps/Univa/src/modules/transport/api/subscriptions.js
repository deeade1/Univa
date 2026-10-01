import { gql } from "@apollo/client";

/* ===========================================================
 🚦 Service Requests & Trips
=========================================================== */

export const SERVICE_REQUEST_UPDATED_SUBSCRIPTION = gql`
  subscription OnServiceRequestUpdated($serviceRequestId: ID!) {
    serviceRequestUpdated(serviceRequestId: $serviceRequestId) {
      id
      status
      origin
      destination
      createdAt
      updatedAt
    }
  }
`;

export const TRIP_STATUS_UPDATED_SUBSCRIPTION = gql`
  subscription OnTripStatusUpdated($tripId: ID!) {
    tripStatusUpdated(tripId: $tripId) {
      id
      status
      estimatedArrival
      startedAt
      completedAt
      updatedAt
    }
  }
`;

export const TRIP_UPDATES = gql`
  subscription TripUpdates($tripId: ID!) {
    tripUpdates(tripId: $tripId) {
      tripId
      payload
    }
  }
`;

/* ===========================================================
 🚌 Shared Trips & Waitlist
=========================================================== */

export const SHARED_TRIP_UPDATED_SUBSCRIPTION = gql`
  subscription OnSharedTripUpdated($sharedTripId: ID!) {
    sharedTripUpdated(sharedTripId: $sharedTripId) {
      id
      name
      totalSeats
      availableSeats
      status
      createdAt
      updatedAt
    }
  }
`;

export const WAITLIST_UPDATED_SUBSCRIPTION = gql`
  subscription OnWaitlistUpdated($sharedTripId: ID!) {
    waitlistUpdated(sharedTripId: $sharedTripId) {
      id
      status
      joinedAt
    }
  }
`;

/* ===========================================================
 📑 Bookings
=========================================================== */

export const BOOKING_UPDATED_SUBSCRIPTION = gql`
  subscription OnBookingUpdated($bookingId: ID!) {
    bookingUpdated(bookingId: $bookingId) {
      id
      status
      price
      createdAt
      updatedAt
    }
  }
`;

/* ===========================================================
 📦 Deliveries
=========================================================== */

export const DELIVERY_UPDATED_SUBSCRIPTION = gql`
  subscription OnDeliveryUpdated($deliveryId: ID!) {
    deliveryUpdated(deliveryId: $deliveryId) {
      id
      status
      trackingNumber
      dispatchedAt
      deliveredAt
    }
  }
`;

/* ===========================================================
 📍 Tracking & Events
=========================================================== */

export const TRACKING_UPDATED_SUBSCRIPTION = gql`
  subscription OnTrackingUpdated($trackingId: ID!) {
    trackingUpdated(trackingId: $trackingId) {
      id
      status
      currentLatitude
      currentLongitude
      lastUpdated
    }
  }
`;

export const TRACKING_EVENT_SUBSCRIPTION = gql`
  subscription OnTrackingEvent($trackingId: ID!) {
    trackingEvent(trackingId: $trackingId) {
      id
      eventType
      description
      latitude
      longitude
      timestamp
    }
  }
`;

/* ===========================================================
 💳 Receipts
=========================================================== */

export const RECEIPT_ISSUED_SUBSCRIPTION = gql`
  subscription OnReceiptIssued($receiptId: ID!) {
    receiptIssued(receiptId: $receiptId) {
      id
      total
      currency
      issuedAt
    }
  }
`;

/* ===========================================================
 🚗 Real-time Features
=========================================================== */

export const VEHICLE_LOCATION_UPDATED_SUBSCRIPTION = gql`
  subscription OnVehicleLocationUpdated($vehicleId: ID!) {
    vehicleLocationUpdated(vehicleId: $vehicleId)
  }
`;

export const NEARBY_VEHICLES_SUBSCRIPTION = gql`
  subscription NearbyVehicles($latitude: Float!, $longitude: Float!, $radiusKm: Float) {
    nearbyVehicles(latitude: $latitude, longitude: $longitude, radiusKm: $radiusKm)
  }
`;

export const REALTIME_TRACKING_SUBSCRIPTION = gql`
  subscription OnRealtimeTracking($serviceRequestId: ID!) {
    realtimeTracking(serviceRequestId: $serviceRequestId)
  }
`;

export const PROVIDER_STATUS_UPDATED_SUBSCRIPTION = gql`
  subscription OnProviderStatusUpdated($providerId: ID!) {
    providerStatusUpdated(providerId: $providerId)
  }
`;

/* ===========================================================
 🛑 Safety & Maintenance
=========================================================== */

export const EMERGENCY_ALERT_SUBSCRIPTION = gql`
  subscription OnEmergencyAlert($userId: ID!) {
    emergencyAlert(userId: $userId)
  }
`;

export const MAINTENANCE_ALERT_SUBSCRIPTION = gql`
  subscription OnMaintenanceAlert($vehicleId: ID!) {
    maintenanceAlert(vehicleId: $vehicleId)
  }
`;

/* ===========================================================
 ✨ Additional Features
=========================================================== */

export const TRAFFIC_CONDITIONS_SUBSCRIPTION = gql`
  subscription OnTrafficConditions($routeId: String!) {
    trafficConditions(routeId: $routeId)
  }
`;

export const LOYALTY_POINTS_UPDATED_SUBSCRIPTION = gql`
  subscription OnLoyaltyPointsUpdated($userId: ID!) {
    loyaltyPointsUpdated(userId: $userId)
  }
`;

export const FARE_UPDATED_SUBSCRIPTION = gql`
  subscription OnFareUpdated($serviceRequestId: ID!) {
    fareUpdated(serviceRequestId: $serviceRequestId)
  }
`;

export const COMPATIBILITY_UPDATED_SUBSCRIPTION = gql`
  subscription OnCompatibilityUpdated($tripId: ID!) {
    compatibilityUpdated(tripId: $tripId) {
      optimized
      timestamp
    }
  }
`;


export const DELIVERY_ASSIGNED_SUB = gql`
  subscription OnDeliveryAssignedToCourier($deliveryId: ID!) {
    onDeliveryAssignedToCourier(deliveryId: $deliveryId) {
      delivery { id status }
      courier { id fullName }
    }
  }
`;

export const DELIVERY_CANCELLED_SUB = gql`
  subscription OnDeliveryCancelled($deliveryId: ID!) {
    onDeliveryCancelled(deliveryId: $deliveryId) {
      delivery { id }
      reason
    }
  }
`;



export const DRIVER_LOCATION_SUB = gql`
  subscription DriverLocation($driverId: ID!) {
    driverLocationUpdated(driverId: $driverId) {
      driverId
      lat
      lng
      bearing
      timestamp
    }
  }
`;


