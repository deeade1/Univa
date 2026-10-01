
import json
import logging

import graphene
from graphene import relay, Boolean, String, Field, ID, Decimal, Int
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry, Point
from django.db import transaction
from django.shortcuts import get_object_or_404
from graphene import ObjectType, relay
from graphene_gis.scalars import LineStringScalar
from graphql import GraphQLError
from graphql_relay import from_global_id, to_global_id
from django.utils import timezone
from accounts.models import Address
from univa_jwt.decorators import login_required
from graphq.accounts.types import AddressNode
from graphq.realestate.types import (
    ClientNode, CMAReportType,
    ComplianceCheckType, ListingFileNode,
    ListingImageNode, ListingNode,
    ListingTypeNode, LiveTourRegistrationNode,
    LiveTourScheduleNode, PropertyUpdateLogNode,
    MortgageCalculationType,
    PropertySubscriptionNode,
    PropertyWithProximityNode,
    ROICalculationType, ValuationEstimateType,
    VirtualTourNode, ListingCategoryNode, LocationPreferenceNode,
    SavedSearchNode, DocumentPackageNode,
    DocumentNode, DocumentSignatureNode, MessageThreadNode,
    MessageNode, MessageAttachmentNode, TransactionNode,
    TransactionMilestoneNode, PropertyRatingNode, OfferNode,
    CounterOfferNode, NeighborhoodNode, MarketTrendNode,
    ARModelNode, PropertyProximityNode, CommissionPlanNode, 
    AgentCommissionNode, AgentRatingNode,  
)
from realestate.models import (
    Agent, Client, Listing, ListingFile,
    ListingImage, ListingType, PropertySubscription,
    PropertyUpdateLog, LocationPreference, SavedSearch,
    DocumentPackage, Document, DocumentSignature,
    MessageThread, Message, MessageAttachment,
    Transaction, TransactionMilestone, PropertyRating,
    Offer, CounterOffer, ListingCategory, Neighborhood,
    MarketTrend, LiveTourSchedule, LiveTourRegistration,
    VirtualTour, ARModel, PropertyProximity, 
    CommissionPlan, AgentCommission, AgentRating,  
)

# Import subscriptions
from graphq.realestate.subscriptions import (
    ListingStatusChangedSubscription,
    ListingPriceUpdatedSubscription,
    NewMatchingListingSubscription,
    AgentAvailabilityChangedSubscription,
    PropertySubscriptionAlertSubscription,
    PriceDropAlertSubscription,
    NearbyPropertyAddedSubscription,
    LiveTourStartingSoonSubscription,
    LiveTourParticipantUpdateSubscription,
    VirtualTourViewCountSubscription,
    NewMessageSubscription,
    MessageReadStatusSubscription,
    TypingIndicatorSubscription,
    TransactionStatusChangedSubscription,
    NewOfferReceivedSubscription,
    OfferStatusChangedSubscription,
    TransactionMilestoneCompletedSubscription,
    DocumentPackageStatusSubscription,
    DocumentSignatureRequestedSubscription,
    DocumentSignedSubscription,
    MarketTrendUpdateSubscription,
    InventoryChangeSubscription,
    PriceTrendSubscription,
    PropertyBookmarkedSubscription,
    AppointmentScheduledSubscription,
    CommissionEarnedSubscription,
    MarketActivityHeatmapSubscription,
    PropertyInquirySubscription,
    ReviewReceivedSubscription,
    NewPropertyListedSubscription,
    PropertyViewCountSubscription,
    AgentPerformanceUpdateSubscription
)

logger = logging.getLogger(__name__)
User = get_user_model()

# --- Utility Function ---
def get_instance_from_global_id(model, global_id, required=True):
    try:
        instance_id = from_global_id(global_id)[1]
        return get_object_or_404(model, pk=instance_id) if required else model.objects.filter(pk=instance_id).first()
    except Exception:
        raise GraphQLError(f"Invalid ID provided for {model.__name__}.")

# --- Helper Functions for Triggers ---
def trigger_matching_listing_alerts(listing):
    """Trigger alerts for matching saved searches and subscriptions"""
    # Check saved searches
    saved_searches = SavedSearch.objects.filter(
        is_active=True
    )
    
    for saved_search in saved_searches:
        # Check if listing matches saved search criteria
        try:
            search_params = saved_search.search_parameters
            matches = True
            
            if 'property_type' in search_params and listing.listing_type:
                matches = matches and (listing.listing_type.property_type in search_params['property_type'])
            
            if 'min_price' in search_params:
                matches = matches and (listing.price >= search_params['min_price'])
            
            if 'max_price' in search_params:
                matches = matches and (listing.price <= search_params['max_price'])
            
            if 'bedrooms' in search_params:
                matches = matches and (listing.bedrooms == search_params['bedrooms'])
            
            if matches:
                # Could trigger a specific subscription here
                NewMatchingListingSubscription.trigger(
                    listing=listing,
                    client=saved_search.user.client if hasattr(saved_search.user, 'client') else None,
                    match_score=0.85,  # Calculate actual match score
                    reasons=['Price match', 'Location match', 'Property type match']
                )
        except Exception as e:
            logger.error(f"Error checking saved search {saved_search.id}: {e}")
    
    # Check property subscriptions
    subscriptions = PropertySubscription.objects.filter(
        is_active=True
    )
    
    for subscription in subscriptions:
        try:
            if subscription.matches_listing(listing):
                PropertySubscriptionAlertSubscription.trigger(
                    subscription=subscription,
                    matching_listings=[listing],
                    alert_type='new'
                )
        except Exception as e:
            logger.error(f"Error checking subscription {subscription.id}: {e}")

def check_nearby_properties(listing):
    """Check and trigger nearby property alerts"""
    location_preferences = LocationPreference.objects.all()
    
    for preference in location_preferences:
        if listing.location_point and preference.location_point:
            distance = listing.location_point.distance(preference.location_point) * 100  # Convert to km
            distance_km = distance
            
            if distance_km <= preference.radius_km:
                NearbyPropertyAddedSubscription.trigger(
                    listing=listing,
                    location_preference=preference,
                    distance_km=distance_km
                )

# --- Abstract Location Update Mutation ---
class UpdateLocationMixin:
    success = graphene.Boolean()

    @classmethod
    def update_location(cls, model, instance_id, latitude, longitude):
        try:
            instance = get_instance_from_global_id(model, instance_id)
            instance.update_location(latitude, longitude)
            
            # Trigger agent availability if it's an agent
            if model == Agent:
                AgentAvailabilityChangedSubscription.trigger(
                    agent=instance,
                    is_available=True,
                    last_seen=timezone.now()
                )
            
            return cls(success=True)
        except model.DoesNotExist:
            raise GraphQLError(f"{model.__name__} not found.")
        except Exception as e:
            logger.error(f"Error updating location for {model.__name__}: {e}")
            return cls(success=False)

