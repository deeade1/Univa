# apps/backend/graphq/transport/schema.py
"""
Root transport query.

Composition only — resolver implementations that need model or
domain-service access perform those imports locally.
"""

import graphene
from graphene.relay import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_relay import from_global_id

# ---- Node types ---------------------------------------------------------
from graphq.transport.types.analytics import (
    AnalyticsProfileNode,
    RideMetricsNode,
    KPINode,
)
from graphq.transport.types.boarding import BoardingTicketNode
from graphq.transport.types.booking import BookingNode
from graphq.transport.types.cancellation import (
    CancellationPolicyNode,
    CancellationRecordNode,
)
from graphq.transport.types.delivery import DeliveryNode
from graphq.transport.types.driver_profile import DriverProfileNode
from graphq.transport.types.earnings import DriverEarningNode, IncentiveProgramNode
from graphq.transport.types.logistics import (
    StopPointNode,
    RouteNode,
    RouteStopNode,
)
from graphq.transport.types.maintenance_schedule import (
    MaintenanceScheduleNode,
    MaintenanceLogNode,
)
from graphq.transport.types.package import PackageNode
from graphq.transport.types.pricing import PricingProfileNode, ReceiptNode
from graphq.transport.types.promo import PromoCodeNode, PromoUsageNode
from graphq.transport.types.ratings import (
    RatingNode,
    ProviderRatingNode,
    CustomerRatingNode,
)
from graphq.transport.types.realtime import (
    RealTimeTrackingNode,
    TrafficConditionsNode,
    EmergencyAlertNode,
)
from graphq.transport.types.schedule import TripScheduleTemplateNode
from graphq.transport.types.service_provider import ServiceProviderProfileNode
from graphq.transport.types.service_request import ServiceRequestNode
from graphq.transport.types.shared_trip import (
    SharedTripNode,
    WaitlistEntryNode,
    UserPreferenceNode,
)
from graphq.transport.types.sustainability import (
    SustainabilityProfileNode,
    CarbonCreditNode,
)
from graphq.transport.types.telemetry import (
    VehicleTelemetryNode,
    PredictiveAlertNode,
)
from graphq.transport.types.tracking import TrackingEventNode, TrackingNode
from graphq.transport.types.trip import TripNode
from graphq.transport.types.vehicle_inspection import VehicleInspectionNode
from graphq.transport.types.vehicle import VehicleNode
from graphq.transport.types.white_label import (
    WhiteLabelClientNode,
    WhiteLabelConfigurationNode,
)

#from graphq.accounts.types import LoyaltyRewardNode

from graphq.transport.filters import (
    ServiceProviderProfileFilterSet,
    DeliveryFilterSet,
    BookingFilterSet,
    TrackingFilterSet,
)


class TransportQuery(graphene.ObjectType):
    """
    Read-side of the transport domain.

    Conventions:
        - `Node.Field(...)` exposes relay global-id lookups for a single
          instance.
        - `DjangoFilterConnectionField(...)` exposes a filterable list.
        - Custom fields (`user_carbon_footprint`, `platform_sustainability`,
          etc.) require a backing type — only add them once the type
          exists.
    """

    # ---- Single-node lookups -------------------------------------------
    service_provider = Node.Field(ServiceProviderProfileNode)
    vehicle = Node.Field(VehicleNode)
    service_request = Node.Field(ServiceRequestNode)
    trip = Node.Field(TripNode)
    delivery = Node.Field(DeliveryNode)
    shared_trip = Node.Field(SharedTripNode)
    booking = Node.Field(BookingNode)
    tracking = Node.Field(TrackingNode)
    pricing_profile = Node.Field(PricingProfileNode)
    stop_point = Node.Field(StopPointNode)
    #loyalty_reward = Node.Field(LoyaltyRewardNode)
    boarding_ticket = Node.Field(BoardingTicketNode)

    analytics_profile = Node.Field(AnalyticsProfileNode)
    ride_metrics = Node.Field(RideMetricsNode)
    kpi = Node.Field(KPINode)

    # ---- Filterable lists (custom filter sets) -------------------------
    all_service_providers = DjangoFilterConnectionField(
        ServiceProviderProfileNode,
        filterset_class=ServiceProviderProfileFilterSet,
    )
    all_deliveries = DjangoFilterConnectionField(
        DeliveryNode,
        filterset_class=DeliveryFilterSet,
    )
    all_bookings = DjangoFilterConnectionField(
        BookingNode,
        filterset_class=BookingFilterSet,
    )
    all_tracking = DjangoFilterConnectionField(
        TrackingNode,
        filterset_class=TrackingFilterSet,
    )

    # ---- Filterable lists (default node filters) -----------------------
    all_analytics_profiles = DjangoFilterConnectionField(AnalyticsProfileNode)
    all_ride_metrics = DjangoFilterConnectionField(RideMetricsNode)
    all_kpis = DjangoFilterConnectionField(KPINode)
    all_vehicles = DjangoFilterConnectionField(VehicleNode)
    all_pricing_profiles = DjangoFilterConnectionField(PricingProfileNode)
    all_stop_points = DjangoFilterConnectionField(StopPointNode)
    #all_loyalty_rewards = DjangoFilterConnectionField(LoyaltyRewardNode)

    interstate_trips = DjangoFilterConnectionField(TripNode)
    active_trips = DjangoFilterConnectionField(TripNode)
    available_shared_trips = DjangoFilterConnectionField(SharedTripNode)

    # ---- Resolvers -----------------------------------------------------

    def resolve_interstate_trips(self, info, **kwargs):
        from transport.models.rides.trip import Trip

        return Trip.objects.filter(
            service_type=Trip.ServiceType.INTERSTATE
        ).order_by("-created_at")

    def resolve_active_trips(self, info, **kwargs):
        from transport.models.rides.trip import Trip
        from transport.models.core.service_request import ServiceRequest

        active_statuses = (
            ServiceRequest.Status.REQUESTED,
            ServiceRequest.Status.ACCEPTED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.SCHEDULED,
            ServiceRequest.Status.DEPARTED,
            ServiceRequest.Status.IN_TRANSIT,
            ServiceRequest.Status.ARRIVED,
        )
        return Trip.objects.filter(status__in=active_statuses).order_by(
            "-created_at"
        )

    def resolve_available_shared_trips(self, info, seats_required=1, **kwargs):
        from transport.models.rides.shared_trip import SharedTrip

        if seats_required < 1:
            raise GraphQLError("seats_required must be at least 1.")

        return (
            SharedTrip.objects.filter(
                shared_status="available",
                # `shared_available_seats` is a property, not a column,
                # so filter on the JSON key via `shared_trip_data`.
            )
            .filter(shared_trip_data__available_seats__gte=seats_required)
            .order_by("-created_at")
        )