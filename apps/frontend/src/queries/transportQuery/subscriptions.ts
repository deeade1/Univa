import { gql } from '@apollo/client';

export const TRIP_LOCATION_SUBSCRIPTION = gql`
  subscription TripLocationUpdates($tripId: ID!) {
    tripLocationUpdates(tripId: $tripId) {
      latitude
      longitude
      timestamp
    }
  }
`;

export const MESSAGE_SUBSCRIPTION = gql`
  subscription OnMessageAdded($tripId: ID!) {
    messageAdded(tripId: $tripId) {
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