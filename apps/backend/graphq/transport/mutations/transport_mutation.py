import graphene
from graphq.transport.mutations.analytics import AnalyticsMutations
from graphq.transport.mutations.boarding import BoardingTicketMutations
from graphq.transport.mutations.booking import BookingMutations
from graphq.transport.mutations.cancellation import CancellationMutations
from graphq.transport.mutations.delivery import DeliveryMutations
#from graphq.transport.mutations.dispatch import 
from graphq.transport.mutations.driver_profile import DriverProfileMutations
from graphq.transport.mutations.earnings import DriverEarningMutations
from graphq.transport.mutations.logistics import LogisticsMutations
from graphq.transport.mutations.maintenance_schedule import MaintenanceMutations
from graphq.transport.mutations.package import PackageMutations
from graphq.transport.mutations.pricing import PricingMutations
from graphq.transport.mutations.promo import PromoMutations
from graphq.transport.mutations.rating import RatingMutations
from graphq.transport.mutations.realtime import RealTimeTrackingMutations
from graphq.transport.mutations.schedule import TripScheduleTemplateMutations
from graphq.transport.mutations.service_provider import ServiceProviderProfileMutations
from graphq.transport.mutations.service_request import ServiceRequestMutations
from graphq.transport.mutations.shared_trip import SharedTripMutations
from graphq.transport.mutations.sustainability import SustainabilityMutations
from graphq.transport.mutations.telemetry import TelemetryMutations
from graphq.transport.mutations.tracking import TrackingMutations
from graphq.transport.mutations.trip import TripMutations
from graphq.transport.mutations.vehicle_inspection import VehicleInspectionMutations
from graphq.transport.mutations.vehicle import VehicleMutations
from graphq.transport.mutations.white_label import WhiteLabelMutations


class TransportMutations(
    AnalyticsMutations,
    BoardingTicketMutations,
    BookingMutations,
    CancellationMutations,
    DeliveryMutations,
    DriverProfileMutations,
    DriverEarningMutations,
    LogisticsMutations,
    MaintenanceMutations,
    PackageMutations,
    PricingMutations,
    PromoMutations,
    RealTimeTrackingMutations,
    TripScheduleTemplateMutations,
    ServiceProviderProfileMutations,
    ServiceRequestMutations,
    SustainabilityMutations,
    SharedTripMutations,
    TelemetryMutations,
    TrackingMutations,
    TripMutations,
    VehicleInspectionMutations,
    VehicleMutations,
    WhiteLabelMutations,
    graphene.ObjectType,
):
    pass
    