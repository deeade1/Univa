import { useSubscription } from "@apollo/client/react";
import {
  TRIP_STATUS_UPDATED_SUBSCRIPTION,
  TRACKING_UPDATED_SUBSCRIPTION,
  BOOKING_UPDATED_SUBSCRIPTION,
} from "@/graphql/queries/transportQuery/subscriptions";

export function useTripRealtime(tripId, bookingId, trackingId) {
  const { data: tripData } = useSubscription(TRIP_STATUS_UPDATED_SUBSCRIPTION, { variables: { tripId } });
  const { data: trackingData } = useSubscription(TRACKING_UPDATED_SUBSCRIPTION, { variables: { trackingId } });
  const { data: bookingData } = useSubscription(BOOKING_UPDATED_SUBSCRIPTION, { variables: { bookingId } });

  return {
    trip: tripData?.tripStatusUpdated,
    tracking: trackingData?.trackingUpdated,
    booking: bookingData?.bookingUpdated,
  };
}
