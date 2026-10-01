# apps/backend/realestate/models/__init__.py

"""
Real Estate domain models.

This package is the public model surface for the realestate application.

Models are defined in focused modules to avoid the previous monolithic
realestate/models.py architecture.

External code should normally import models from:

    from realestate.models import Listing
    from realestate.models import ListingImage

rather than importing implementation modules directly.
"""

# ---------------------------------------------------------------------------
# Base / constants
# ---------------------------------------------------------------------------



# realestate/models/__init__.py

from .base import (
    TimeStampedModel,
    listing_dir_path,
)
# ---------------------------------------------------------------------------
# Agents / clients
# ---------------------------------------------------------------------------

from .agent import Agent
from .agent_profile import AgentProfile
from .agent_commission import AgentCommission
from .agent_rating import AgentRating
from .client import Client

# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

from .listing_category import ListingCategory
from .listing_type import ListingType
from .listing import Listing
from .listing_image import ListingImage
from .listing_file import ListingFile

# ---------------------------------------------------------------------------
# Property / search
# ---------------------------------------------------------------------------

from .virtual_tour import VirtualTour
from .ar_model import ARModel

from .search import SearchProfile
from .saved_search import SavedSearch
from .subscription import PropertySubscription
from .location_preference import LocationPreference

from .property_rating import PropertyRating
from .property_proximity import PropertyProximity

# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------

from .offer import Offer
from .counter_offer import CounterOffer

# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

from .transaction import Transaction
from .transaction_milestone import TransactionMilestone

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

from .document_package import DocumentPackage
from .document import Document
from .document_signature import DocumentSignature

# ---------------------------------------------------------------------------
# Commission
# ---------------------------------------------------------------------------

from .commission import CommissionPlan

# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

from .message_thread import MessageThread
from .message import Message
from .message_attachment import MessageAttachment

# ---------------------------------------------------------------------------
# Tours
# ---------------------------------------------------------------------------

from .live_tour import LiveTourSchedule
from .live_tour_registration import LiveTourRegistration

# ---------------------------------------------------------------------------
# Location / market
# ---------------------------------------------------------------------------

from .neighborhood import Neighborhood
from .market_trend import MarketTrend
from .property_update_log import PropertyUpdateLog


__all__ = [
    # Base
    "TimeStampedModel",
    "listing_dir_path",
    
    "TransactionStatus",

    # Agents / clients
    "Agent",
    "AgentProfile",
    "AgentCommission",
    "AgentRating",
    "Client",

    # Listings
    "ListingCategory",
    "ListingType",
    "Listing",
    "ListingImage",
    "ListingFile",

    # Property / search
    "VirtualTour",
    "ARModel",
    "SearchProfile",
    "SavedSearch",
    "PropertySubscription",
    "LocationPreference",
    "PropertyRating",
    "PropertyProximity",

    # Offers
    "Offer",
    "CounterOffer",

    # Transactions
    "Transaction",
    "TransactionMilestone",

    # Documents
    "DocumentPackage",
    "Document",
    "DocumentSignature",

    # Commission
    "CommissionPlan",

    # Messaging
    "MessageThread",
    "Message",
    "MessageAttachment",

    # Tours
    "LiveTourSchedule",
    "LiveTourRegistration",

    # Location / market
    "Neighborhood",
    "MarketTrend",
    "PropertyUpdateLog",
]