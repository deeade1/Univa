import graphene

from graphq.realestate.mutations.agent_commission import AgentCommissionMutations
from graphq.realestate.mutations.agent_profile import AgentProfileMutations
from graphq.realestate.mutations.agent_rating import AgentRatingMutations
from graphq.realestate.mutations.ar_model import ARModelMutations
from graphq.realestate.mutations.client import ClientMutations
from graphq.realestate.mutations.commission import CommissionPlanMutations
from graphq.realestate.mutations.counter_offer import CounterOfferMutations
from graphq.realestate.mutations.document_package import DocumentPackageMutations
from graphq.realestate.mutations.document_signature import DocumentSignatureMutations
from graphq.realestate.mutations.document import DocumentMutations
from graphq.realestate.mutations.listing_category import ListingCategoryMutations
from graphq.realestate.mutations.listing_file import ListingFileMutations
from graphq.realestate.mutations.listing_image import ListingImageMutations
from graphq.realestate.mutations.listing_type import ListingTypeMutations
from graphq.realestate.mutations.listing import ListingMutations
from graphq.realestate.mutations.live_tour_registration import LiveTourRegistrationMutations
from graphq.realestate.mutations.live_tour import LiveTourScheduleMutations
from graphq.realestate.mutations.location_preference import LocationPreferenceMutations
from graphq.realestate.mutations.market_trend import MarketTrendMutations
from graphq.realestate.mutations.message_attachment import MessageAttachmentMutations
from graphq.realestate.mutations.message_thread import MessageThreadMutations
from graphq.realestate.mutations.message import MessageMutations
from graphq.realestate.mutations.neighborhood import NeighborhoodMutations
from graphq.realestate.mutations.offer import OfferMutations
from graphq.realestate.mutations.property_proximity import PropertyProximityMutations
from graphq.realestate.mutations.property_rating import PropertyRatingMutations
from graphq.realestate.mutations.property_update_log import PropertyUpdateLogMutations
from graphq.realestate.mutations.recommendations import RecommendationMutations
from graphq.realestate.mutations.saved_search import SavedSearchMutations
from graphq.realestate.mutations.search import SearchProfileMutations
from graphq.realestate.mutations.subscription import PropertySubscriptionMutations
from graphq.realestate.mutations.transaction_milestone import TransactionMilestoneMutations
from graphq.realestate.mutations.transaction import TransactionMutations
from graphq.realestate.mutations.virtual_tour import VirtualTourMutations


class RealEstateMutations(          # <-- renamed: capital "E" in "Estate"
    AgentCommissionMutations,
    AgentProfileMutations,
    AgentRatingMutations,
    ARModelMutations,
    ClientMutations,
    CommissionPlanMutations,
    CounterOfferMutations,
    DocumentPackageMutations,
    DocumentSignatureMutations,
    DocumentMutations,
    ListingCategoryMutations,
    ListingFileMutations,
    ListingImageMutations,
    ListingTypeMutations,
    ListingMutations,
    LiveTourRegistrationMutations,
    LiveTourScheduleMutations,
    LocationPreferenceMutations,
    MarketTrendMutations,
    MessageAttachmentMutations,
    MessageThreadMutations,        # <-- added (was imported but missing)
    MessageMutations,
    NeighborhoodMutations,
    OfferMutations,
    PropertyProximityMutations,
    PropertyRatingMutations,
    PropertyUpdateLogMutations,
    RecommendationMutations,
    SavedSearchMutations,
    SearchProfileMutations,
    PropertySubscriptionMutations,
    TransactionMilestoneMutations,
    TransactionMutations,
    VirtualTourMutations,
    graphene.ObjectType,
):
    pass