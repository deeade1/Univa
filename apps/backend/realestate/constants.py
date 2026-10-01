# apps/backend/realestate/models/constants.py

"""
Constants for real estate models.
"""

from django.utils.translation import gettext_lazy as _


# ============================================================================
# PROPERTY TYPES (Preserved)
# ============================================================================

PROPERTY_TYPES = (
    ("house", _("House")),
    ('residential_house', _('Residential House')),
    ("apartment", _("Apartment")),
    ("office", _("Office")),
    ("warehouse", _("Warehouse")),
    ("land", _("Land")),
    ("commercial_land", _("Commercial Land")),
    ("residential_land", _("Residential Land")),
    ("agricultural_land", _("Agricultural Land")),
    ("industrial_land", _("Industrial Land")),
    ("duplex", _("Duplex")),
    ("bungalow", _("Bungalow")),
    ("mansion", _("Mansion")),
    ("shop", _("Shop")),
    ("event_center", _("Event Center")),
    ("hotel", _("Hotel")),
)


# ============================================================================
# PROPERTY CONDITION (NEW - Used in Listing)
# ============================================================================

PROPERTY_CONDITION = (
    ("new", _("New Construction")),
    ("excellent", _("Excellent")),
    ("good", _("Good")),
    ("fair", _("Fair")),
    ("needs_renovation", _("Needs Renovation")),
)


# ============================================================================
# PROPERTY STATUS (USED in Listing)
# ============================================================================

PROPERTY_STATUS = (
    ("draft", _("Draft")),
    ("published", _("Published")),
    ("sold", _("Sold")),
    ("rented", _("Rented")),
    ("leased", _("Leased")),
    ("pending_review", _("Pending Review")),
    ("rejected", _("Rejected")),
    ("approved", _("Approved")),
    ("under_contract", _("Under Contract")),
)


# ============================================================================
# PROPERTY FOR (USED in Listing)
# ============================================================================

PROPERTY_FOR = (
    ("B", "Buy"),
    ("S", "Sale"),
    ("R", "Rent"),
    ("L", "Lease"),
    ("A", "Auction"),
)


# ============================================================================
# PROPERTY AREAS (USED in Listing)
# ============================================================================

PROPERTY_AREAS = (
    ("R", "Residential"),
    ("C", "Commercial"),
    ("A", "Agricultural"),
    ("I", "Industrial"),
    ("M", "Mixed Use"),
)


# ============================================================================
# LAND UNITS (USED in Listing)
# ============================================================================

LAND_UNITS = (
    ("plot", _("Plot")),
    ("acre", _("Acre")),
    ("hectare", _("Hectare")),
    ("square_meter", _("Square Meter")),
    ("square_feet", _("Square Feet")),
)


# ============================================================================
# PRICE METRICS (USED in Listing)
# ============================================================================

PRICE_METRICS = (
    ("total_price", _("Total Price")),
    ("price_per_plot", _("Price Per Plot")),
    ("price_per_acre", _("Price Per Acre")),
    ("price_per_hectare", _("Price Per Hectare")),
    ("price_per_sqm", _("Price Per Square Meter")),
    ("price_per_sqft", _("Price Per Square Foot")),
    ("annual_rent", _("Annual Rent")),
    ("monthly_rent", _("Monthly Rent")),
)


# ============================================================================
# CURRENCY CHOICES (For international support)
# ============================================================================

CURRENCY_CHOICES = (
    ("NGN", _("₦ Naira")),
    ("USD", _("$ US Dollar")),
    ("EUR", _("€ Euro")),
    ("GBP", _("£ British Pound")),
    ("CAD", _("C$ Canadian Dollar")),
    ("AUD", _("A$ Australian Dollar")),
    ("JPY", _("¥ Japanese Yen")),
    ("CNY", _("¥ Chinese Yuan")),
    ("INR", _("₹ Indian Rupee")),
    ("ZAR", _("R South African Rand")),
    ("KES", _("KSh Kenyan Shilling")),
    ("GHS", _("GH₵ Ghanaian Cedi")),
)


# ============================================================================
# NOTIFICATION FREQUENCY (Preserved)
# ============================================================================

NOTIFICATION_FREQUENCY = (
    ("instant", "Instant"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
)


# ============================================================================
# ANCHOR TYPES (For AR Models)
# ============================================================================

ANCHOR_TYPES = (
    ("plane", "Horizontal Plane"),
    ("image", "Image Target"),
    ("location", "GPS Location"),
)


# ============================================================================
# TRANSACTION STATUS
# ============================================================================

class TransactionStatus:
    PRE_OFFER = 'pre_offer'
    OFFER_PENDING = 'offer_pending'
    UNDER_CONTRACT = 'under_contract'
    DUE_DILIGENCE = 'due_diligence'
    CLOSING = 'closing'
    CLOSED = 'closed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PRE_OFFER, 'Pre-Offer'),
        (OFFER_PENDING, 'Offer Pending'),
        (UNDER_CONTRACT, 'Under Contract'),
        (DUE_DILIGENCE, 'Due Diligence'),
        (CLOSING, 'Closing'),
        (CLOSED, 'Closed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    TRANSITIONS = {
        PRE_OFFER: [OFFER_PENDING, CANCELLED],
        OFFER_PENDING: [UNDER_CONTRACT, CANCELLED],
        UNDER_CONTRACT: [DUE_DILIGENCE, CANCELLED],
        DUE_DILIGENCE: [CLOSING, CANCELLED],
        CLOSING: [CLOSED, CANCELLED],
        CLOSED: [],
        CANCELLED: [],
    }
    
    CANCELLABLE = [PRE_OFFER, OFFER_PENDING, UNDER_CONTRACT, DUE_DILIGENCE, CLOSING]
    REQUIRES_COMPLETION = [CLOSED]
    REQUIRES_AGREED_PRICE = [CLOSED]
    
    @classmethod
    def is_valid_transition(cls, from_status, to_status):
        if to_status == from_status:
            return True
        return to_status in cls.TRANSITIONS.get(from_status, [])
    
    @classmethod
    def get_available_transitions(cls, current_status):
        return cls.TRANSITIONS.get(current_status, [])
    
    @classmethod
    def is_terminal(cls, status):
        return status in [cls.CLOSED, cls.CANCELLED]
    
    @classmethod
    def is_active(cls, status):
        return status not in [cls.CLOSED, cls.CANCELLED]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_property_type_label(code):
    """Get the label for a property type code."""
    type_dict = dict(PROPERTY_TYPES)
    return type_dict.get(code, code)


def get_status_label(code):
    """Get the label for a property status code."""
    status_dict = dict(PROPERTY_STATUS)
    return status_dict.get(code, code)


def get_condition_label(code):
    """Get the label for a property condition code."""
    condition_dict = dict(PROPERTY_CONDITION)
    return condition_dict.get(code, code)


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "ANCHOR_TYPES",
    "CURRENCY_CHOICES",
    "LAND_UNITS",
    "NOTIFICATION_FREQUENCY",
    "PRICE_METRICS",
    "PROPERTY_AREAS",
    "PROPERTY_CONDITION",
    "PROPERTY_FOR",
    "PROPERTY_STATUS",
    "PROPERTY_TYPES",
    "TransactionStatus",
    "get_property_type_label",
    "get_status_label",
    "get_condition_label",
]