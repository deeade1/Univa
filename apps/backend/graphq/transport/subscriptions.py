'''import graphene
from channels_graphql_ws import Subscription
from graphql_relay import from_global_id
from django.utils import timezone

from transport.models.maintenance.maintenance_schedule import MaintenanceSchedule
from transport.models.maintenance.vehicle_inspection import VehicleInspection
from transport.models.maintenance.telemetry import VehicleTelemetry, PredictiveAlert
from transport.models.maintenance.vehicle import Vehicle
from transport.models.delivery.delivery import Delivery
from transport.models.delivery.tracking import Tracking, TrackingEvent
from transport.models.delivery.logistics import StopPoint
from transport.models.rides.schedule import TripScheduleTemplate
from transport.models.rides.booking import Booking
from transport.models.rides.boarding import BoardingTicket
from transport.models.financial.earnings import DriverEarning, IncentiveProgram
from transport.models.financial.cancellation import CancellationPolicy, CancellationRecord
from transport.models.financial.pricing import PricingProfile
from transport.models.shared.realtime import RealTimeTracking, TrafficConditions, EmergencyAlert
from transport.models.shared.analytics import RideMetrics, KPI

from graphq.transport.types import (
    BookingNode, DeliveryNode, ReceiptNode, RiderCompatibilityNode,
    ServiceRequestNode, SharedTripNode, TrackingEventNode,
    TrackingNode, TripNode, WaitlistEntryNode, MaintenanceScheduleNode,
    VehicleInspectionNode, CancellationRecordNode, DriverEarningNode,
    WalletNode, StopPointNode, TripScheduleTemplateNode,
    BoardingTicketNode, VehicleTelemetryNode, PredictiveAlertNode,
    VehicleNode, TransactionNode, IncentiveProgramNode,
    CancellationPolicyNode, PricingProfileNode, ServiceProviderProfileNode,
    RealTimeTrackingNode, TrafficConditionsNode,
    EmergencyAlertNode, RideMetricsNode, KPINode
)

from graphq.accounts.types import DriverProfileNode, UserNode
from .base import GenericSubscription




class VehicleMaintenanceDueSubscription(Subscription):
    """
    Subscription for upcoming vehicle maintenance alerts.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    maintenance = graphene.Field(MaintenanceScheduleNode)
    vehicle_id = graphene.ID()
    days_until_due = graphene.Int()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    def subscribe(self, info, vehicle_id):
        """Subscribe client to maintenance alerts for a specific vehicle."""
        return [f"vehicle_maintenance_{vehicle_id}"]

    def publish(self, info, vehicle_id):
        """Return the payload stored in self[...]"""
        return VehicleMaintenanceDueSubscription(
            maintenance=self["maintenance"],
            vehicle_id=vehicle_id,
            days_until_due=self.get("days_until_due")
        )

    @classmethod
    def trigger(cls, maintenance):
        """Broadcast maintenance alert to all subscribers watching this vehicle."""
        vehicle_id = maintenance.vehicle.id
        days_until_due = (maintenance.scheduled_date - timezone.now()).days

        cls.broadcast(
            group=f"vehicle_maintenance_{vehicle_id}",
            payload={
                "maintenance": maintenance,
                "days_until_due": days_until_due
            }  # accessible in publish as self["maintenance"], self["days_until_due"]
        )



class MaintenanceStatusChangedSubscription(Subscription):
    """
    Subscription for maintenance status changes.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    maintenance = graphene.Field(MaintenanceScheduleNode)
    old_status = graphene.String()
    new_status = graphene.String()

    class Arguments:
        maintenance_id = graphene.ID(required=True)

    def subscribe(self, info, maintenance_id):
        """Subscribe client to updates for a specific maintenance record."""
        return [f"maintenance_status_{maintenance_id}"]

    def publish(self, info, maintenance_id):
        """Return the payload stored in self[...]"""
        return MaintenanceStatusChangedSubscription(
            maintenance=self["maintenance"],
            old_status=self.get("old_status"),
            new_status=self.get("new_status")
        )

    @classmethod
    def trigger(cls, maintenance, old_status, new_status):
        """Broadcast maintenance status change to all subscribers."""
        cls.broadcast(
            group=f"maintenance_status_{maintenance.id}",
            payload={
                "maintenance": maintenance,
                "old_status": old_status,
                "new_status": new_status
            }  # accessible in publish as self["maintenance"], self["old_status"], self["new_status"]
        )



class VehicleInspectionUpdatedSubscription(Subscription):
    """
    Subscription for vehicle inspection updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    inspection = graphene.Field(VehicleInspectionNode)

    class Arguments:
        inspection_id = graphene.ID(required=True)

    def subscribe(self, info, inspection_id):
        """Subscribe client to updates for a specific vehicle inspection."""
        return [f"inspection_{inspection_id}"]

    def publish(self, info, inspection_id):
        """Return the payload stored in self[...]"""
        return VehicleInspectionUpdatedSubscription(
            inspection=self["inspection"]
        )

    @classmethod
    def trigger(cls, inspection):
        """Broadcast inspection updates to all subscribers watching this inspection."""
        cls.broadcast(
            group=f"inspection_{inspection.id}",
            payload={"inspection": inspection}  # accessible in publish as self["inspection"]
        )




class VehicleTelemetrySubscription(Subscription):
    """
    Real-time vehicle telemetry data subscription.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    telemetry = graphene.Field(VehicleTelemetryNode)
    vehicle_id = graphene.ID()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    def subscribe(self, info, vehicle_id):
        """Subscribe client to telemetry updates for a specific vehicle."""
        return [f"vehicle_telemetry_{vehicle_id}"]

    def publish(self, info, vehicle_id):
        """Return the payload stored in self[...]"""
        return VehicleTelemetrySubscription(
            telemetry=self["telemetry"],
            vehicle_id=vehicle_id
        )

    @classmethod
    def trigger(cls, telemetry):
        """Broadcast telemetry updates to all subscribers watching this vehicle."""
        cls.broadcast(
            group=f"vehicle_telemetry_{telemetry.vehicle.id}",
            payload={"telemetry": telemetry}  # accessible in publish as self["telemetry"]
        )




class PredictiveAlertSubscription(Subscription):
    """
    Predictive maintenance alerts subscription.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    alert = graphene.Field(PredictiveAlertNode)
    severity = graphene.String()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    def subscribe(self, info, vehicle_id):
        """Subscribe client to predictive alerts for a specific vehicle."""
        return [f"predictive_alert_{vehicle_id}"]

    def publish(self, info, vehicle_id):
        """Return the payload stored in self[...]"""
        return PredictiveAlertSubscription(
            alert=self["alert"],
            severity=self.get("severity")
        )

    @classmethod
    def trigger(cls, alert):
        """Broadcast predictive alert to all subscribers watching this vehicle."""
        cls.broadcast(
            group=f"predictive_alert_{alert.vehicle.id}",
            payload={
                "alert": alert,
                "severity": alert.severity
            }  # accessible in publish as self["alert"], self["severity"]
        )



class VehicleStatusUpdatedSubscription(Subscription):
    """
    Vehicle status updates subscription.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    vehicle = graphene.Field(VehicleNode)
    old_status = graphene.Boolean()
    new_status = graphene.Boolean()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    def subscribe(self, info, vehicle_id):
        """Subscribe client to status updates for a specific vehicle."""
        return [f"vehicle_status_{vehicle_id}"]

    def publish(self, info, vehicle_id):
        """Return the payload stored in self[...]"""
        return VehicleStatusUpdatedSubscription(
            vehicle=self["vehicle"],
            old_status=self.get("old_status"),
            new_status=self.get("new_status")
        )

    @classmethod
    def trigger(cls, vehicle, old_status, new_status):
        """Broadcast vehicle status update to all subscribers watching this vehicle."""
        cls.broadcast(
            group=f"vehicle_status_{vehicle.id}",
            payload={
                "vehicle": vehicle,
                "old_status": old_status,
                "new_status": new_status
            }  # accessible in publish as self["vehicle"], self["old_status"], self["new_status"]
        )




# =======================
# Delivery & Logistics Subscriptions
# =======================



class DeliveryPackageUpdatedSubscription(Subscription):
    """
    Subscription for updates to delivery packages.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    delivery = graphene.Field(DeliveryNode)
    updated_fields = graphene.List(graphene.String)

    class Arguments:
        delivery_id = graphene.ID(required=True)

    def subscribe(self, info, delivery_id):
        """Subscribe client to updates for a specific delivery package."""
        return [f"delivery_package_{delivery_id}"]

    def publish(self, info, delivery_id):
        """Return the payload stored in self[...]"""
        return DeliveryPackageUpdatedSubscription(
            delivery=self["delivery"],
            updated_fields=self.get("updated_fields", [])
        )

    @classmethod
    def trigger(cls, delivery, updated_fields):
        """Broadcast delivery package updates to all subscribers."""
        cls.broadcast(
            group=f"delivery_package_{delivery.id}",
            payload={
                "delivery": delivery,
                "updated_fields": updated_fields
            }  # accessible in publish as self["delivery"], self["updated_fields"]
        )



class TrackingEventCreatedSubscription(Subscription):
    """
    Subscription for new tracking events.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    event = graphene.Field(TrackingEventNode)
    tracking_id = graphene.ID()

    class Arguments:
        tracking_id = graphene.ID(required=True)

    def subscribe(self, info, tracking_id):
        """Subscribe client to new events for a specific tracking ID."""
        return [f"tracking_events_{tracking_id}"]

    def publish(self, info, tracking_id):
        """Return the payload stored in self[...]"""
        return TrackingEventCreatedSubscription(
            event=self["event"],
            tracking_id=tracking_id
        )

    @classmethod
    def trigger(cls, event):
        """Broadcast new tracking event to all subscribers."""
        cls.broadcast(
            group=f"tracking_events_{event.tracking.id}",
            payload={"event": event}  # accessible in publish as self["event"]
        )



class StopPointSequenceUpdatedSubscription(Subscription):
    """
    Subscription for stop point sequence changes in trips.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    stop = graphene.Field(StopPointNode)
    old_sequence = graphene.Int()
    new_sequence = graphene.Int()

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        """Subscribe client to stop sequence updates for a specific trip."""
        return [f"stop_sequence_{trip_id}"]

    def publish(self, info, trip_id):
        """Return the payload stored in self[...]"""
        return StopPointSequenceUpdatedSubscription(
            stop=self["stop"],
            old_sequence=self.get("old_sequence"),
            new_sequence=self.get("new_sequence")
        )

    @classmethod
    def trigger(cls, stop, old_sequence, new_sequence):
        """Broadcast stop sequence updates to all subscribers for this trip."""
        cls.broadcast(
            group=f"stop_sequence_{stop.trip.id}",
            payload={
                "stop": stop,
                "old_sequence": old_sequence,
                "new_sequence": new_sequence
            }  # accessible in publish as self["stop"], self["old_sequence"], self["new_sequence"]
        )



class DeliveryCapacitySubscription(Subscription):
    """
    Subscription for delivery capacity updates for a specific vehicle.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    delivery = graphene.Field(DeliveryNode)
    available_capacity = graphene.Float()
    utilized_capacity = graphene.Float()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    def subscribe(self, info, vehicle_id):
        """Subscribe client to capacity updates for a specific vehicle."""
        return [f"delivery_capacity_{vehicle_id}"]

    def publish(self, info, vehicle_id):
        """Return the payload stored in self[...]"""
        return DeliveryCapacitySubscription(
            delivery=self["delivery"],
            available_capacity=self.get("available_capacity"),
            utilized_capacity=self.get("utilized_capacity")
        )

    @classmethod
    def trigger(cls, delivery, vehicle, utilized_capacity):
        """Broadcast delivery capacity updates to all subscribers for this vehicle."""
        available_capacity = vehicle.cargo_capacity - utilized_capacity
        cls.broadcast(
            group=f"delivery_capacity_{vehicle.id}",
            payload={
                "delivery": delivery,
                "available_capacity": available_capacity,
                "utilized_capacity": utilized_capacity
            }  # accessible in publish as self["delivery"], etc.
        )


# =======================
# Service Requests & Trips
# =======================



class ServiceRequestUpdatedSubscription(Subscription):
    """
    Subscription for real-time updates to a specific ServiceRequest.
    Uses Pattern A: `publish` returns a GraphQL object using self[...] payload fields.
    """

    # Fields returned to the GraphQL client
    service_request = graphene.Field(ServiceRequestNode)

    class Arguments:
        service_request_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, service_request_id):
        """Subscribe client to a single request's group."""
        try:
            pk = from_global_id(service_request_id)[1]
            return [f"service_request_{pk}"]  # ✅ FIXED: Return list, not string
        except Exception:
            # If ID is invalid, return empty list
            return []

    def publish(self, info, service_request_id):
        """
        Convert payload to GraphQL object using classic Pattern A structure.
        `self[...]` contains the payload fields.
        """
        return ServiceRequestUpdatedSubscription(
            service_request=self["service_request"]
        )

    @classmethod
    def trigger(cls, service_request):
        """
        Broadcast an update to subscribers for this specific request.
        Pattern A: send dict payload.
        """
        pk = service_request.id
        cls.broadcast(
            group=f"service_request_{pk}",
            payload={
                "service_request": service_request,
            },
        )

# graphq/transport/subscriptions.py
class NewServiceRequestSubscription(Subscription):
    """Subscription for providers to receive new service requests in their area."""
    
    service_request = graphene.Field(ServiceRequestNode)
    
    class Arguments:
        provider_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, provider_id):
        """Subscribe provider to their own group"""
        return f"provider_{provider_id}_requests"
    
    def publish(self, info, provider_id):
        return NewServiceRequestSubscription(
            service_request=self["service_request"]
        )
    
    @classmethod
    def trigger_for_provider(cls, provider_id, service_request):
        """Trigger when a new request is created in provider's area"""
        cls.broadcast(
            group=f"provider_{provider_id}_requests",
            payload={
                "service_request": service_request,
            }
        )


class ServiceRequestStatusChangedSubscription(Subscription):
    """Subscription for status changes of a service request."""
    
    service_request = graphene.Field(ServiceRequestNode)
    old_status = graphene.String()
    new_status = graphene.String()
    changed_at = graphene.DateTime()
    
    class Arguments:
        service_request_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, service_request_id):
        pk = from_global_id(service_request_id)[1]
        return f"service_request_{pk}_status"
    
    def publish(self, info, service_request_id):
        return ServiceRequestStatusChangedSubscription(
            service_request=self["service_request"],
            old_status=self["old_status"],
            new_status=self["new_status"],
            changed_at=self["changed_at"]
        )
    
    @classmethod
    def trigger_status_change(cls, service_request, old_status):
        """Trigger when status changes"""
        cls.broadcast(
            group=f"service_request_{service_request.id}_status",
            payload={
                "service_request": service_request,
                "old_status": old_status,
                "new_status": service_request.status,
                "changed_at": timezone.now()
            }
        )

class TripStatusUpdatedSubscription(Subscription):
    """
    Subscription for real-time trip status updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    trip = graphene.Field(TripNode)

    class Arguments:
        trip_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, trip_id):
        """Client subscribes to one trip's updates."""
        pk = from_global_id(trip_id)[1]
        return f"trip_{pk}"

    def publish(self, info, trip_id):
        """Return GraphQL-object using the payload stored in `self`."""
        return TripStatusUpdatedSubscription(
            trip=self["trip"]
        )

    @classmethod
    def trigger(cls, trip):
        """
        Notify all subscribers of updates to a Trip.
        Pattern A: broadcast dict payload.
        """
        cls.broadcast(
            group=f"trip_{trip.id}",
            payload={
                "trip": trip,   # available inside publish as self["trip"]
            },
        )


class TripUpdatesSubscription(Subscription):
    """
    Unified Trip Updates Subscription.
    Use this for ANY change to a trip: status, driver updates, ETA, location, etc.
    Pattern A compliant.
    """

    trip = graphene.Field(TripNode)

    class Arguments:
        trip_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, trip_id):
        """Subscribe the client to a specific trip updates channel."""
        pk = from_global_id(trip_id)[1]
        return f"trip_updates_{pk}"

    def publish(self, info, trip_id):
        """Publish the update back to the client as a GraphQL object."""
        return TripUpdatesSubscription(
            trip=self["trip"]
        )

    @classmethod
    def trigger(cls, trip):
        """
        Emit a broadcast for ANY update on this trip.
        Pattern A requires dict payload.
        """
        cls.broadcast(
            group=f"trip_updates_{trip.id}",
            payload={
                "trip": trip,   # → accessible in publish via self["trip"]
            },
        )


class TripLocationUpdatedSubscription(Subscription):
    trip = graphene.Field(TripNode)
    location = graphene.JSONString()

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"trip_loc_{trip_id}"]

    def publish(self, info, trip_id):
        return TripLocationUpdatedSubscription(
            trip=self["trip"],
            location=self["location"]
        )

    @classmethod
    def trigger(cls, trip, location):
        cls.broadcast(
            group=f"trip_loc_{trip.id}",
            payload={
                "trip": trip,
                "location": location
            }
        )

class TripLocationSubscription(Subscription):
    trip = graphene.Field(TripNode)
    data = graphene.JSONString()   # full GPS payload

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"trip_location_stream_{trip_id}"]

    def publish(self, info, trip_id):
        return TripLocationSubscription(
            trip=self["trip"],
            data=self["data"]
        )

    @classmethod
    def trigger(cls, trip, gps_data):
        cls.broadcast(
            group=f"trip_location_stream_{trip.id}",
            payload={
                "trip": trip,
                "data": gps_data
            }
        )

class TripDriverAssignedSubscription(Subscription):
    trip = graphene.Field(TripNode)
    driver = graphene.Field(DriverProfileNode)

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"trip_driver_{trip_id}"]

    def publish(self, info, trip_id):
        return TripDriverAssignedSubscription(
            trip=self["trip"],
            driver=self["driver"]
        )

    @classmethod
    def trigger(cls, trip, driver):
        cls.broadcast(
            group=f"trip_driver_{trip.id}",
            payload={
                "trip": trip,
                "driver": driver
            }
        )


class TripFareUpdatedSubscription(Subscription):
    trip = graphene.Field(TripNode)
    fare = graphene.Decimal()

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"trip_fare_{trip_id}"]

    def publish(self, info, trip_id):
        return TripFareUpdatedSubscription(
            trip=self["trip"],
            fare=self["fare"]
        )

    @classmethod
    def trigger(cls, trip, fare):
        cls.broadcast(
            group=f"trip_fare_{trip.id}",
            payload={
                "trip": trip,
                "fare": fare
            }
        )


class TripRouteUpdatedSubscription(Subscription):
    trip = graphene.Field(TripNode)
    route = graphene.JSONString()

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"trip_route_{trip_id}"]

    def publish(self, info, trip_id):
        return TripRouteUpdatedSubscription(
            trip=self["trip"],
            route=self["route"]
        )

    @classmethod
    def trigger(cls, trip, route_data):
        cls.broadcast(
            group=f"trip_route_{trip.id}",
            payload={
                "trip": trip,
                "route": route_data
            }
        )


# =======================
# Shared Ride & Waitlist
# =======================




class SharedTripUpdatedSubscription(Subscription):
    """
    Subscription for real-time updates on a Shared Trip.
    Pattern A: payload dict → self[...] → return GraphQL node.
    """

    shared_trip = graphene.Field(SharedTripNode)

    class Arguments:
        shared_trip_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, shared_trip_id):
        """Subscribe client to updates for a specific shared trip."""
        pk = from_global_id(shared_trip_id)[1]
        return f"shared_trip_{pk}"

    def publish(self, info, shared_trip_id):
        """Return GraphQL object using the payload stored in self[...]"""
        return SharedTripUpdatedSubscription(
            shared_trip=self["shared_trip"]
        )

    @classmethod
    def trigger(cls, shared_trip):
        """Push updates to all subscribers of this shared trip."""
        cls.broadcast(
            group=f"shared_trip_{shared_trip.id}",
            payload={
                "shared_trip": shared_trip,   # available in publish as self["shared_trip"]
            },
        )

class SharedTripParticipantJoinedSubscription(Subscription):
    shared_trip = graphene.Field(SharedTripNode)
    participant = graphene.Field(UserNode)

    class Arguments:
        shared_id = graphene.ID(required=True)

    def subscribe(self, info, shared_id):
        return [f"shared_join_{shared_id}"]

    def publish(self, info, shared_id):
        return SharedTripParticipantJoinedSubscription(
            shared_trip=self["shared_trip"],
            participant=self["participant"]
        )

    @classmethod
    def trigger(cls, shared_trip, participant):
        cls.broadcast(
            group=f"shared_join_{shared_trip.id}",
            payload={
                "shared_trip": shared_trip,
                "participant": participant
            }
        )

class SharedTripParticipantLeftSubscription(Subscription):
    shared_trip = graphene.Field(SharedTripNode)
    participant = graphene.Field(UserNode)

    class Arguments:
        shared_id = graphene.ID(required=True)

    def subscribe(self, info, shared_id):
        return [f"shared_left_{shared_id}"]

    def publish(self, info, shared_id):
        return SharedTripParticipantLeftSubscription(
            shared_trip=self["shared_trip"],
            participant=self["participant"]
        )

    @classmethod
    def trigger(cls, shared_trip, participant):
        cls.broadcast(
            group=f"shared_left_{shared_trip.id}",
            payload={
                "shared_trip": shared_trip,
                "participant": participant
            }
        )


class SharedTripLiveUpdatesSubscription(Subscription):
    shared_trip = graphene.Field(SharedTripNode)
    event_type = graphene.String()
    payload = graphene.JSONString()

    class Arguments:
        shared_id = graphene.ID(required=True)

    def subscribe(self, info, shared_id):
        return [f"shared_live_{shared_id}"]

    def publish(self, info, shared_id):
        return SharedTripLiveUpdatesSubscription(
            shared_trip=self["shared_trip"],
            event_type=self["event_type"],
            payload=self["payload"]
        )

    @classmethod
    def trigger(cls, shared_trip, event_type, payload):
        cls.broadcast(
            group=f"shared_live_{shared_trip.id}",
            payload={
                "shared_trip": shared_trip,
                "event_type": event_type,
                "payload": payload
            }
        )


class WaitlistUpdatedSubscription(Subscription):
    """
    Subscription for real-time waitlist updates in a shared trip.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    entry = graphene.Field(WaitlistEntryNode)

    class Arguments:
        shared_trip_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, shared_trip_id):
        """Subscribe the client to a specific shared trip's waitlist."""
        pk = from_global_id(shared_trip_id)[1]
        return f"waitlist_{pk}"

    def publish(self, info, shared_trip_id):
        """Return the GraphQL node using the payload stored in self[...]"""
        return WaitlistUpdatedSubscription(
            entry=self["entry"]
        )

    @classmethod
    def trigger(cls, waitlist_entry):
        """Broadcast updates to all subscribers of this shared trip's waitlist."""
        cls.broadcast(
            group=f"waitlist_{waitlist_entry.shared_trip.id}",
            payload={
                "entry": waitlist_entry,  # available in publish as self["entry"]
            },
        )


# =======================
# Booking & Payments
# =======================



class BookingUpdatedSubscription(Subscription):
    """
    Subscription for real-time updates to a Booking.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    booking = graphene.Field(BookingNode)

    class Arguments:
        booking_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, booking_id):
        """Subscribe client to updates for a specific booking."""
        pk = from_global_id(booking_id)[1]
        return f"booking_{pk}"

    def publish(self, info, booking_id):
        """Return the GraphQL node using the payload stored in self[...]"""
        return BookingUpdatedSubscription(
            booking=self["booking"]
        )

    @classmethod
    def trigger(cls, booking):
        """Broadcast updates to all subscribers of this booking."""
        cls.broadcast(
            group=f"booking_{booking.id}",
            payload={
                "booking": booking,  # accessible in publish as self["booking"]
            },
        )



class ReceiptIssuedSubscription(Subscription):
    """
    Subscription for real-time updates when a Receipt is issued.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    receipt = graphene.Field(ReceiptNode)

    class Arguments:
        receipt_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, receipt_id):
        """Subscribe client to updates for a specific receipt."""
        pk = from_global_id(receipt_id)[1]
        return f"receipt_{pk}"

    def publish(self, info, receipt_id):
        """Return the GraphQL node using the payload stored in self[...]"""
        return ReceiptIssuedSubscription(
            receipt=self["receipt"]
        )

    @classmethod
    def trigger(cls, receipt):
        """Broadcast updates to all subscribers of this receipt."""
        cls.broadcast(
            group=f"receipt_{receipt.id}",
            payload={
                "receipt": receipt,  # accessible in publish as self["receipt"]
            },
        )


# =======================
# Real-Time Tracking
# =======================

class VehicleLocationUpdatedSubscription(Subscription):
    """
    Subscription for real-time vehicle location updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    location = graphene.JSONString()

    class Arguments:
        vehicle_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, vehicle_id):
        """Subscribe client to updates for a specific vehicle's location."""
        pk = from_global_id(vehicle_id)[1]
        return f"vehicle_location_{pk}"

    def publish(self, info, vehicle_id):
        """Return the location payload stored in self[...]"""
        return VehicleLocationUpdatedSubscription(
            location=self["location"]
        )

    @classmethod
    def trigger(cls, vehicle_id, location_payload):
        """
        Broadcast updates to all subscribers of this vehicle's location.

        `location_payload` is a dict containing location data, e.g.:
        {"lat": 6.5244, "lng": 3.3792, "speed": 40}
        """
        cls.broadcast(
            group=f"vehicle_location_{vehicle_id}",
            payload={"location": location_payload},
        )


# =======================
# Provider Status
# =======================

class OnProviderOnlineStatusChanged(Subscription):
    """
    Subscription for real-time updates when a provider goes online/offline.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    provider = graphene.Field(ServiceProviderProfileNode)

    class Arguments:
        provider_id = graphene.ID(required=True)

    def subscribe(self, info, provider_id):
        """Subscribe client to updates for a specific provider."""
        return [f"provider_online_{provider_id}"]

    def publish(self, info, provider_id):
        """Return the provider node stored in self[...]"""
        return OnProviderOnlineStatusChanged(
            provider=self["provider"]
        )

    @classmethod
    def trigger(cls, provider):
        """Broadcast updates to all subscribers watching this provider."""
        cls.broadcast(
            group=f"provider_online_{provider.id}",
            payload={"provider": provider},  # accessible in publish as self["provider"]
        )



class OnProviderLocationUpdated(Subscription):
    """
    Subscription for real-time updates when a provider's location changes.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    provider = graphene.Field(ServiceProviderProfileNode)

    class Arguments:
        provider_id = graphene.ID(required=True)

    def subscribe(self, info, provider_id):
        """Subscribe client to updates for a specific provider's location."""
        return [f"provider_location_{provider_id}"]

    def publish(self, info, provider_id):
        """Return the provider node stored in self[...]"""
        return OnProviderLocationUpdated(
            provider=self["provider"]
        )

    @classmethod
    def trigger(cls, provider):
        """Broadcast updates to all subscribers watching this provider's location."""
        cls.broadcast(
            group=f"provider_location_{provider.id}",
            payload={"provider": provider},  # accessible in publish as self["provider"]
        )

class ProviderEtaSubscription(Subscription):
    trip = graphene.Field(TripNode)
    eta_minutes = graphene.Float()

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        return [f"provider_eta_{trip_id}"]

    def publish(self, info, trip_id):
        return ProviderEtaSubscription(
            trip=self["trip"],
            eta_minutes=self["eta_minutes"]
        )

    @classmethod
    def trigger(cls, trip, eta):
        cls.broadcast(
            group=f"provider_eta_{trip.id}",
            payload={
                "trip": trip,
                "eta_minutes": eta
            }
        )


# =======================
# Delivery Status
# =======================


class OnDeliveryStatusUpdated(Subscription):
    """
    Subscription for real-time updates when a delivery's status changes.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    delivery = graphene.Field(DeliveryNode)

    class Arguments:
        delivery_id = graphene.ID(required=True)

    def subscribe(self, info, delivery_id):
        """Subscribe client to updates for a specific delivery."""
        return [f"delivery_status_{delivery_id}"]

    def publish(self, info, delivery_id):
        """Return the delivery node stored in self[...]"""
        return OnDeliveryStatusUpdated(
            delivery=self["delivery"]
        )

    @classmethod
    def trigger(cls, delivery):
        """Broadcast updates to all subscribers watching this delivery."""
        cls.broadcast(
            group=f"delivery_status_{delivery.id}",
            payload={"delivery": delivery},  # accessible in publish as self["delivery"]
        )



class OnDeliveryAssignedToCourier(Subscription):
    """
    Subscription for notifying clients when a courier is assigned to a delivery.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    delivery = graphene.Field(DeliveryNode)
    courier = graphene.Field(ServiceProviderProfileNode)

    class Arguments:
        delivery_id = graphene.ID(required=True)

    def subscribe(self, info, delivery_id):
        """Subscribe client to updates for a specific delivery assignment."""
        return [f"delivery_assignment_{delivery_id}"]

    def publish(self, info, delivery_id):
        """Return the payload stored in self[...]"""
        return OnDeliveryAssignedToCourier(
            delivery=self["delivery"],
            courier=self.get("courier")
        )

    @classmethod
    def trigger(cls, delivery, courier=None):
        """Broadcast courier assignment updates to all subscribers."""
        cls.broadcast(
            group=f"delivery_assignment_{delivery.id}",
            payload={"delivery": delivery, "courier": courier}  # accessible in publish
        )


class OnDeliveryCancelled(Subscription):
    """
    Subscription for notifying clients when a delivery is cancelled.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    delivery = graphene.Field(DeliveryNode)
    reason = graphene.String()

    class Arguments:
        delivery_id = graphene.ID(required=True)

    def subscribe(self, info, delivery_id):
        """Subscribe client to updates for a specific cancelled delivery."""
        return [f"delivery_cancelled_{delivery_id}"]

    def publish(self, info, delivery_id):
        """Return the payload stored in self[...]"""
        return OnDeliveryCancelled(
            delivery=self["delivery"],
            reason=self.get("reason")
        )

    @classmethod
    def trigger(cls, delivery, reason=None):
        """Broadcast cancellation updates to all subscribers."""
        cls.broadcast(
            group=f"delivery_cancelled_{delivery.id}",
            payload={"delivery": delivery, "reason": reason}  # accessible in publish
        )




# =======================
# Tracking & Stops
# =======================


class OnTrackingStatusChanged(Subscription):
    """
    Subscription for real-time updates when a tracking event's status changes.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    tracking = graphene.Field(TrackingNode)

    class Arguments:
        tracking_id = graphene.ID(required=True)

    def subscribe(self, info, tracking_id):
        """Subscribe client to updates for a specific tracking event."""
        return [f"tracking_status_{tracking_id}"]

    def publish(self, info, tracking_id):
        """Return the payload stored in self[...]"""
        return OnTrackingStatusChanged(
            tracking=self["tracking"]
        )

    @classmethod
    def trigger(cls, tracking):
        """Broadcast updates to all subscribers watching this tracking event."""
        cls.broadcast(
            group=f"tracking_status_{tracking.id}",
            payload={"tracking": tracking}  # accessible in publish as self["tracking"]
        )


class OnStopPointUpdated(Subscription):
    """
    Subscription for real-time updates when a stop point is updated.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    stop = graphene.Field(StopPointNode)

    class Arguments:
        trip_id = graphene.ID(required=True)

    def subscribe(self, info, trip_id):
        """Subscribe client to updates for a specific trip's stop points."""
        return [f"trip_stops_{trip_id}"]

    def publish(self, info, trip_id):
        """Return the payload stored in self[...]"""
        return OnStopPointUpdated(
            stop=self["stop"]
        )

    @classmethod
    def trigger(cls, stop):
        """Broadcast updates to all subscribers watching this trip's stop points."""
        cls.broadcast(
            group=f"trip_stops_{stop.trip.id}",
            payload={"stop": stop}  # accessible in publish as self["stop"]
        )

# =======================
# Financial Subscriptions
# =======================

class TransactionStatusSubscription(Subscription):
    """
    Subscription for transaction status updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    transaction = graphene.Field(TransactionNode)
    old_status = graphene.String()
    new_status = graphene.String()

    class Arguments:
        transaction_id = graphene.ID(required=True)

    def subscribe(self, info, transaction_id):
        """Subscribe client to updates for a specific transaction."""
        return [f"transaction_status_{transaction_id}"]

    def publish(self, info, transaction_id):
        """Return the payload stored in self[...]"""
        return TransactionStatusSubscription(
            transaction=self["transaction"],
            old_status=self.get("old_status"),
            new_status=self.get("new_status")
        )

    @classmethod
    def trigger(cls, transaction, old_status, new_status):
        """Broadcast transaction status changes to all subscribers for this transaction."""
        cls.broadcast(
            group=f"transaction_status_{transaction.id}",
            payload={
                "transaction": transaction,
                "old_status": old_status,
                "new_status": new_status
            }  # accessible in publish as self["transaction"], etc.
        )




class WalletBalanceSubscription(Subscription):
    """
    Subscription for real-time wallet balance updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    wallet = graphene.Field(WalletNode)
    old_balance = graphene.Decimal()
    new_balance = graphene.Decimal()
    delta = graphene.Decimal()

    class Arguments:
        wallet_id = graphene.ID(required=True)

    def subscribe(self, info, wallet_id):
        """Subscribe client to updates for a specific wallet."""
        return [f"wallet_balance_{wallet_id}"]

    def publish(self, info, wallet_id):
        """Return the payload stored in self[...]"""
        return WalletBalanceSubscription(
            wallet=self["wallet"],
            old_balance=self.get("old_balance"),
            new_balance=self.get("new_balance"),
            delta=self.get("delta")
        )

    @classmethod
    def trigger(cls, wallet, old_balance, new_balance):
        """Broadcast wallet balance updates to all subscribers for this wallet."""
        delta = new_balance - old_balance
        cls.broadcast(
            group=f"wallet_balance_{wallet.id}",
            payload={
                "wallet": wallet,
                "old_balance": old_balance,
                "new_balance": new_balance,
                "delta": delta
            }  # accessible in publish as self["wallet"], self["delta"], etc.
        )



class DriverAssignedSubscription(Subscription):
    driver = graphene.Field(DriverProfileNode)
    job = graphene.JSONString()

    class Arguments:
        driver_id = graphene.ID(required=True)

    def subscribe(self, info, driver_id):
        return [f"driver_assigned_{driver_id}"]

    def publish(self, info, driver_id):
        return DriverAssignedSubscription(
            driver=self["driver"],
            job=self["job"]
        )

    @classmethod
    def trigger(cls, driver, job_payload):
        cls.broadcast(
            group=f"driver_assigned_{driver.id}",
            payload={
                "driver": driver,
                "job": job_payload
            }
        )



class DriverEarningsUpdatedSubscription(Subscription):
    """
    Subscription for driver earnings updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    earning = graphene.Field(DriverEarningNode)
    period = graphene.String()
    payout_status = graphene.String()

    class Arguments:
        driver_id = graphene.ID(required=True)

    def subscribe(self, info, driver_id):
        """Subscribe client to updates for a specific driver."""
        return [f"driver_earnings_{driver_id}"]

    def publish(self, info, driver_id):
        """Return the payload stored in self[...]"""
        return DriverEarningsUpdatedSubscription(
            earning=self["earning"],
            period=self.get("period"),
            payout_status=self.get("payout_status")
        )

    @classmethod
    def trigger(cls, earning):
        """Broadcast driver earnings updates to all subscribers for this driver."""
        driver_id = earning.driver.id
        cls.broadcast(
            group=f"driver_earnings_{driver_id}",
            payload={
                "earning": earning,
                "period": earning.period,
                "payout_status": earning.payout_status
            }  # accessible in publish as self["earning"], etc.
        )




class IncentiveUnlockedSubscription(Subscription):
    """
    Subscription for driver incentive unlocked notifications.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    incentive = graphene.Field(IncentiveProgramNode)
    driver_id = graphene.ID()
    reward_amount = graphene.Decimal()

    class Arguments:
        driver_id = graphene.ID(required=True)

    def subscribe(self, info, driver_id):
        """Subscribe client to updates for a specific driver."""
        return [f"incentive_unlocked_{driver_id}"]

    def publish(self, info, driver_id):
        """Return the payload stored in self[...]"""
        return IncentiveUnlockedSubscription(
            incentive=self["incentive"],
            driver_id=self.get("driver_id"),
            reward_amount=self.get("reward_amount")
        )

    @classmethod
    def trigger(cls, incentive, driver, reward_amount):
        """Broadcast incentive unlocked updates to all subscribers for this driver."""
        cls.broadcast(
            group=f"incentive_unlocked_{driver.id}",
            payload={
                "incentive": incentive,
                "driver_id": driver.id,
                "reward_amount": reward_amount
            }  # accessible in publish as self["incentive"], self["reward_amount"], etc.
        )




class PricingUpdateSubscription(Subscription):
    """
    Subscription for dynamic pricing updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    pricing = graphene.Field(PricingProfileNode)
    service_type = graphene.String()
    surge_multiplier = graphene.Decimal()

    class Arguments:
        service_type = graphene.String(required=True)

    def subscribe(self, info, service_type):
        """Subscribe clients to updates for a specific service type."""
        return [f"pricing_updates_{service_type}"]

    def publish(self, info, service_type):
        """Return the payload stored in self[...]"""
        return PricingUpdateSubscription(
            pricing=self["pricing"],
            service_type=service_type,
            surge_multiplier=self.get("surge_multiplier")
        )

    @classmethod
    def trigger(cls, pricing_profile):
        """Broadcast pricing updates for this service type."""
        cls.broadcast(
            group=f"pricing_updates_{pricing_profile.service_type}",
            payload={
                "pricing": pricing_profile,
                "surge_multiplier": pricing_profile.surge_multiplier
            }  # accessible in publish as self["pricing"], self["surge_multiplier"]
        )



class CancellationFeeAppliedSubscription(Subscription):
    """
    Subscription for cancellation fee updates.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    cancellation = graphene.Field(CancellationRecordNode)
    fee_amount = graphene.Decimal()
    refund_amount = graphene.Decimal()

    class Arguments:
        user_id = graphene.ID(required=True)

    def subscribe(self, info, user_id):
        """Subscribe clients to updates for a specific user."""
        return [f"cancellation_fee_{user_id}"]

    def publish(self, info, user_id):
        """Return the payload stored in self[...]"""
        return CancellationFeeAppliedSubscription(
            cancellation=self["cancellation"],
            fee_amount=self.get("fee_amount"),
            refund_amount=self.get("refund_amount")
        )

    @classmethod
    def trigger(cls, cancellation_record):
        """Broadcast cancellation fee updates to all subscribers for this user."""
        user_id = cancellation_record.cancelled_by.id
        cls.broadcast(
            group=f"cancellation_fee_{user_id}",
            payload={
                "cancellation": cancellation_record,
                "fee_amount": cancellation_record.cancellation_fee,
                "refund_amount": cancellation_record.refund_amount
            }  # accessible in publish as self["cancellation"], self["fee_amount"], self["refund_amount"]
        )




class DispatchUpdatesSubscription(Subscription):
    """
    Broadcasts ALL dispatch events.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    request_id = graphene.ID()
    provider_id = graphene.ID()
    match_score = graphene.Float()
    estimated_eta = graphene.Float()
    success = graphene.Boolean()
    mode_used = graphene.String()
    timestamp = graphene.DateTime()
    message = graphene.String()

    class Arguments:
        pass

    def subscribe(self, info):
        """Subscribe to all dispatch events."""
        return ["dispatch_updates"]

    def publish(self, info):
        """Return the payload stored in self[...]"""
        return DispatchUpdatesSubscription(
            request_id=self.get("request_id"),
            provider_id=self.get("provider_id"),
            match_score=self.get("match_score"),
            estimated_eta=self.get("estimated_eta"),
            success=self.get("success"),
            mode_used=self.get("mode_used"),
            timestamp=self.get("timestamp"),
            message=self.get("message"),
        )

    @classmethod
    def trigger(cls, event):
        """
        Trigger a global dispatch update.
        'event' is a dict with all dispatch details.
        """
        cls.broadcast(
            group="dispatch_updates",
            payload=event  # accessible in publish via self[...]
        )


class DispatchRequestUpdatesSubscription(Subscription):
    """
    Broadcasts dispatch events for a specific request.
    Pattern A: payload dict -> self[...] -> return GraphQL node.
    """

    request_id = graphene.ID()
    provider_id = graphene.ID()
    match_score = graphene.Float()
    estimated_eta = graphene.Float()
    success = graphene.Boolean()
    mode_used = graphene.String()
    timestamp = graphene.DateTime()
    message = graphene.String()

    class Arguments:
        request_id = graphene.ID(required=True)

    def subscribe(self, info, request_id):
        """Subscribe clients to a specific dispatch request."""
        return [f"dispatch_req_{request_id}"]

    def publish(self, info, request_id):
        """Return the payload stored in self[...]"""
        return DispatchRequestUpdatesSubscription(
            request_id=self.get("request_id"),
            provider_id=self.get("provider_id"),
            match_score=self.get("match_score"),
            estimated_eta=self.get("estimated_eta"),
            success=self.get("success"),
            mode_used=self.get("mode_used"),
            timestamp=self.get("timestamp"),
            message=self.get("message"),
        )

    @classmethod
    def trigger(cls, request_id, event):
        """
        Trigger a dispatch update for a specific request.
        'event' is a dict with all dispatch details.
        """
        cls.broadcast(
            group=f"dispatch_req_{request_id}",
            payload=event  # accessible in publish via self[...]
        )


class DispatchAssignmentEvent(graphene.ObjectType):
    request_id = graphene.ID()
    provider_id = graphene.ID()
    match_score = graphene.Float()
    estimated_eta = graphene.Float()
    success = graphene.Boolean()
    mode_used = graphene.String()
    timestamp = graphene.DateTime()
    message = graphene.String()

 
# =======================
# Transport Subscription Main Class
# =======================

class TransportSubscriptions(graphene.ObjectType):
    
    transport_event = GenericSubscription.Field()
    # Service Requests & Trips
    service_request_updated = ServiceRequestUpdatedSubscription.Field()
    trip_status_updated = TripStatusUpdatedSubscription.Field()
    trip_updates = TripUpdatesSubscription.Field()

    # Shared Ride & Waitlist
    shared_trip_updated = SharedTripUpdatedSubscription.Field()
    waitlist_updated = WaitlistUpdatedSubscription.Field()
    shared_trip_live_updates = SharedTripLiveUpdatesSubscription.Field()
    shared_trip_participant_joined = SharedTripParticipantJoinedSubscription.Field()
    shared_trip_participant_left = SharedTripParticipantLeftSubscription.Field()

    # Booking & Payments
    booking_updated = BookingUpdatedSubscription.Field()
    receipt_issued = ReceiptIssuedSubscription.Field()

    # Real-time tracking
    vehicle_location_updated = VehicleLocationUpdatedSubscription.Field()
    trip_location_updated = TripLocationUpdatedSubscription.Field()
    trip_location_stream = TripLocationSubscription.Field()
    
    # Provider status
    on_provider_online_status_changed = OnProviderOnlineStatusChanged.Field()
    on_provider_location_updated = OnProviderLocationUpdated.Field()
    driver_assigned = DriverAssignedSubscription.Field()
    provider_eta_updated = ProviderEtaSubscription.Field()

    # Delivery
    on_delivery_status_updated = OnDeliveryStatusUpdated.Field()
    on_delivery_assigned_to_courier = OnDeliveryAssignedToCourier.Field()
    on_delivery_cancelled = OnDeliveryCancelled.Field()

    # Tracking
    on_tracking_status_changed = OnTrackingStatusChanged.Field()
    on_stop_point_updated = OnStopPointUpdated.Field()

    # Maintenance subscriptions
    vehicle_maintenance_due = VehicleMaintenanceDueSubscription.Field()
    maintenance_status_changed = MaintenanceStatusChangedSubscription.Field()
    vehicle_inspection_updated = VehicleInspectionUpdatedSubscription.Field()
    vehicle_telemetry = VehicleTelemetrySubscription.Field()
    predictive_alert = PredictiveAlertSubscription.Field()
    vehicle_status_updated = VehicleStatusUpdatedSubscription.Field()

    # Delivery & logistics
    delivery_package_updated = DeliveryPackageUpdatedSubscription.Field()
    tracking_event_created = TrackingEventCreatedSubscription.Field()
    stop_point_sequence_updated = StopPointSequenceUpdatedSubscription.Field()
    delivery_capacity = DeliveryCapacitySubscription.Field()

    # Financial
  
    driver_earnings_updated = DriverEarningsUpdatedSubscription.Field()
    incentive_unlocked = IncentiveUnlockedSubscription.Field()
    pricing_update = PricingUpdateSubscription.Field()
    cancellation_fee_applied = CancellationFeeAppliedSubscription.Field()
    dispatch_updates = DispatchUpdatesSubscription.Field()
    dispatch_request_updates = DispatchRequestUpdatesSubscription.Field()
    
    # Trip extra
    trip_driver_assigned = TripDriverAssignedSubscription.Field()
    trip_fare_updated = TripFareUpdatedSubscription.Field()
    trip_route_updated = TripRouteUpdatedSubscription.Field()'''
