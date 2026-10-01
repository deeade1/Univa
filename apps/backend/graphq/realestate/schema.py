import logging

import graphene
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

from graphene import Node, ObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError

from univa_jwt.decorators import login_required

from graphq.realestate.types.agent import AgentNode
from graphq.realestate.types.agent_profile import  AgentProfileNode
from graphq.realestate.types.ar_model import ARModelNode
from graphq.realestate.types.client import ClientNode
from graphq.realestate.types.document import DocumentNode
from graphq.realestate.types.document_package import DocumentPackageNode
from graphq.realestate.types.document_signature import DocumentSignatureNode
from graphq.realestate.types.listing_file import ListingFileNode
from graphq.realestate.types.listing_image import ListingImageNode
from graphq.realestate.types.listing import ListingNode 
from graphq.realestate.types.listing_type import ListingTypeNode
from graphq.realestate.types.listing_category import ListingCategoryNode
from graphq.realestate.types.live_tour_registration import LiveTourRegistrationNode
from graphq.realestate.types.live_tour import LiveTourScheduleNode
from graphq.realestate.types.location_preference import LocationPreferenceNode
from graphq.realestate.types.market_trend import MarketTrendNode
from graphq.realestate.types.message_attachment import MessageAttachmentNode
from graphq.realestate.types.message import MessageNode
from graphq.realestate.types.message_thread import  MessageThreadNode
from graphq.realestate.types.neighborhood import NeighborhoodNode
from graphq.realestate.types.property_proximity import PropertyProximityNode
from graphq.realestate.types.subscription import PropertySubscriptionNode 
from graphq.realestate.types.property_update_log import PropertyUpdateLogNode
from graphq.realestate.types.transaction_milestone import TransactionMilestoneNode
from graphq.realestate.types.transaction import TransactionNode 
from graphq.realestate.types.virtual_tour import VirtualTourNode
from graphq.realestate.types.saved_search import SavedSearchNode
from graphq.realestate.types.commission import CommissionPlanNode   
from graphq.realestate.types.agent_commission import AgentCommissionNode
from graphq.realestate.types.property_rating import PropertyRatingNode
from graphq.realestate.types.agent_rating import AgentRatingNode
from graphq.realestate.types.offer import OfferNode
from graphq.realestate.types.counter_offer import CounterOfferNode
from graphq.realestate.types.search import SearchProfileNode     


logger = logging.getLogger(__name__)

class RealestateQueries(ObjectType):
    # =====================
    # Single Item Queries
    # =====================
    listing_type = Node.Field(ListingTypeNode)
    listing = Node.Field(ListingNode)
    listing_image = Node.Field(ListingImageNode)
    listing_file = Node.Field(ListingFileNode)
    client = Node.Field(ClientNode)
    agent = Node.Field(AgentNode)
    property_subscription = Node.Field(PropertySubscriptionNode)
    property_proximity = Node.Field(PropertyProximityNode)
    property_update_log = Node.Field(PropertyUpdateLogNode)
    location_preference = Node.Field(LocationPreferenceNode)
    virtual_tour = Node.Field(VirtualTourNode)
    live_tour_schedule = Node.Field(LiveTourScheduleNode)
    live_tour_registration = Node.Field(LiveTourRegistrationNode)
    document_package = Node.Field(DocumentPackageNode)
    document = Node.Field(DocumentNode)
    document_signature = Node.Field(DocumentSignatureNode)
    message_thread = Node.Field(MessageThreadNode)
    message = Node.Field(MessageNode)
    message_attachment = Node.Field(MessageAttachmentNode)
    neighborhood = Node.Field(NeighborhoodNode)
    market_trend = Node.Field(MarketTrendNode)
    ar_model = Node.Field(ARModelNode)
    transaction = Node.Field(TransactionNode)
    transaction_milestone = Node.Field(TransactionMilestoneNode)
    listing_category = Node.Field(ListingCategoryNode)            # NEW
    saved_search = Node.Field(SavedSearchNode)                    # NEW
    commission_plan = Node.Field(CommissionPlanNode)              # NEW
    agent_commission = Node.Field(AgentCommissionNode)            # NEW
    property_rating = Node.Field(PropertyRatingNode)              # NEW
    agent_rating = Node.Field(AgentRatingNode)                    # NEW
    offer = Node.Field(OfferNode)                                 # NEW
    counter_offer = Node.Field(CounterOfferNode)                  # NEW
    search_profile = Node.Field(SearchProfileNode)  

    # =====================
    # List Queries
    # =====================
    all_listing_types = DjangoFilterConnectionField(ListingTypeNode)
    all_listings = DjangoFilterConnectionField(ListingNode)
    all_listing_images = DjangoFilterConnectionField(ListingImageNode)
    all_listing_files = DjangoFilterConnectionField(ListingFileNode)
    all_clients = DjangoFilterConnectionField(ClientNode)
    all_agents = DjangoFilterConnectionField(AgentNode)
    all_property_subscriptions = DjangoFilterConnectionField(PropertySubscriptionNode)
    all_property_proximities = DjangoFilterConnectionField(PropertyProximityNode)
    all_property_update_logs = DjangoFilterConnectionField(PropertyUpdateLogNode)
    all_location_preferences = DjangoFilterConnectionField(LocationPreferenceNode)
    all_virtual_tours = DjangoFilterConnectionField(VirtualTourNode)
    all_live_tour_schedules = DjangoFilterConnectionField(LiveTourScheduleNode)
    all_live_tour_registrations = DjangoFilterConnectionField(LiveTourRegistrationNode)
    all_document_packages = DjangoFilterConnectionField(DocumentPackageNode)
    all_documents = DjangoFilterConnectionField(DocumentNode)
    all_document_signatures = DjangoFilterConnectionField(DocumentSignatureNode)
    all_message_threads = DjangoFilterConnectionField(MessageThreadNode)
    all_messages = DjangoFilterConnectionField(MessageNode)
    all_message_attachments = DjangoFilterConnectionField(MessageAttachmentNode)
    all_neighborhoods = DjangoFilterConnectionField(NeighborhoodNode)
    all_market_trends = DjangoFilterConnectionField(MarketTrendNode)
    all_ar_models = DjangoFilterConnectionField(ARModelNode)
    all_transactions = DjangoFilterConnectionField(TransactionNode)
    all_transaction_milestones = DjangoFilterConnectionField(TransactionMilestoneNode)
    nearby_properties = DjangoFilterConnectionField(PropertyProximityNode)
    properties_in_neighborhood = DjangoFilterConnectionField(ListingNode)
    upcoming_live_tours = DjangoFilterConnectionField(LiveTourScheduleNode)
    all_listing_categories = DjangoFilterConnectionField(ListingCategoryNode)    
    all_saved_searches = DjangoFilterConnectionField(SavedSearchNode)             
    all_commission_plans = DjangoFilterConnectionField(CommissionPlanNode)        
    all_agent_commissions = DjangoFilterConnectionField(AgentCommissionNode)     
    all_property_ratings = DjangoFilterConnectionField(PropertyRatingNode)        
    all_agent_ratings = DjangoFilterConnectionField(AgentRatingNode)              
    all_offers = DjangoFilterConnectionField(OfferNode)                           
    all_counter_offers = DjangoFilterConnectionField(CounterOfferNode)            
    all_search_profiles = DjangoFilterConnectionField(SearchProfileNode)
    