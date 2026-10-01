import graphene
from graphene import relay
from channels_graphql_ws import Subscription
from graphql_relay import from_global_id, to_global_id
from django.utils import timezone

from realestate.models import (
    Listing, Agent, Client, PropertySubscription, 
    PropertyUpdateLog, PropertyProximity, PropertySubscription,
    SavedSearch, LiveTourSchedule, LiveTourRegistration, VirtualTour,
    MessageThread, Message, MessageAttachment,
    Transaction, TransactionMilestone, Offer, CounterOffer,
    DocumentPackage, Document, DocumentSignature,  Neighborhood, 
    MarketTrend,
)
from graphq.realestate.types.agent import AgentNode
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



class ListingStatusChangedSubscription(Subscription):
    """Real-time listing status updates (draft -> published -> sold)"""
    listing = graphene.Field(ListingNode)
    old_status = graphene.String()
    new_status = graphene.String()
    changed_by = graphene.ID()
    
    class Arguments:
        listing_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, listing_id):
        _, pk = from_global_id(listing_id)
        return [f"listing_status_{pk}"]
    
    @staticmethod
    def publish(payload, info, listing_id):
        return ListingStatusChangedSubscription(
            listing=payload.get('listing'),
            old_status=payload.get('old_status'),
            new_status=payload.get('new_status'),
            changed_by=payload.get('changed_by')
        )
    
    @classmethod
    def trigger(cls, listing, old_status, new_status, changed_by):
        cls.broadcast(
            group=f"listing_status_{listing.id}",
            payload={
                'listing': listing,
                'old_status': old_status,
                'new_status': new_status,
                'changed_by': changed_by
            }
        )


class ListingPriceUpdatedSubscription(Subscription):
    """Real-time price updates for listings"""
    listing = graphene.Field(ListingNode)
    old_price = graphene.Decimal()
    new_price = graphene.Decimal()
    price_change_percent = graphene.Float()
    
    class Arguments:
        listing_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, listing_id):
        _, pk = from_global_id(listing_id)
        return [f"listing_price_{pk}"]
    
    @staticmethod
    def publish(payload, info, listing_id):
        return ListingPriceUpdatedSubscription(
            listing=payload.get('listing'),
            old_price=payload.get('old_price'),
            new_price=payload.get('new_price'),
            price_change_percent=payload.get('price_change_percent')
        )
    
    @classmethod
    def trigger(cls, listing, old_price, new_price):
        price_change = ((new_price - old_price) / old_price) * 100 if old_price else 0
        cls.broadcast(
            group=f"listing_price_{listing.id}",
            payload={
                'listing': listing,
                'old_price': old_price,
                'new_price': new_price,
                'price_change_percent': price_change
            }
        )


class NewMatchingListingSubscription(Subscription):
    """Real-time notifications when new listings match client criteria"""
    listing = graphene.Field(ListingNode)
    client = graphene.Field(ClientNode)
    match_score = graphene.Float()
    reason = graphene.List(graphene.String)
    
    class Arguments:
        client_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, client_id):
        _, pk = from_global_id(client_id)
        return [f"client_matches_{pk}"]
    
    @staticmethod
    def publish(payload, info, client_id):
        return NewMatchingListingSubscription(
            listing=payload.get('listing'),
            client=payload.get('client'),
            match_score=payload.get('match_score'),
            reason=payload.get('reason', [])
        )
    
    @classmethod
    def trigger(cls, listing, client, match_score, reasons):
        cls.broadcast(
            group=f"client_matches_{client.id}",
            payload={
                'listing': listing,
                'client': client,
                'match_score': match_score,
                'reason': reasons
            }
        )


class AgentAvailabilityChangedSubscription(Subscription):
    """Agent online/offline status"""
    agent = graphene.Field(AgentNode)
    is_available = graphene.Boolean()
    last_seen = graphene.DateTime()
    
    class Arguments:
        agent_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, agent_id):
        _, pk = from_global_id(agent_id)
        return [f"agent_availability_{pk}"]
    
    @staticmethod
    def publish(payload, info, agent_id):
        return AgentAvailabilityChangedSubscription(
            agent=payload.get('agent'),
            is_available=payload.get('is_available'),
            last_seen=payload.get('last_seen')
        )
    
    @classmethod
    def trigger(cls, agent, is_available, last_seen):
        cls.broadcast(
            group=f"agent_availability_{agent.id}",
            payload={
                'agent': agent,
                'is_available': is_available,
                'last_seen': last_seen
            }
        )
        

class PropertySubscriptionAlertSubscription(Subscription):
    """Real-time alerts for property subscriptions"""
    subscription = graphene.Field(PropertySubscriptionNode)
    matching_listings = graphene.List(graphene.ID)
    alert_type = graphene.String()  # 'new', 'price_drop', 'status_change'
    
    class Arguments:
        subscription_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, subscription_id):
        _, pk = from_global_id(subscription_id)
        return [f"subscription_alerts_{pk}"]
    
    @staticmethod
    def publish(payload, info, subscription_id):
        return PropertySubscriptionAlertSubscription(
            subscription=payload.get('subscription'),
            matching_listings=payload.get('matching_listings', []),
            alert_type=payload.get('alert_type')
        )
    
    @classmethod
    def trigger(cls, subscription, matching_listings, alert_type):
        cls.broadcast(
            group=f"subscription_alerts_{subscription.id}",
            payload={
                'subscription': subscription,
                'matching_listings': [listing.id for listing in matching_listings],
                'alert_type': alert_type
            }
        )


class PriceDropAlertSubscription(Subscription):
    """Price drop alerts for saved searches/subscriptions"""
    listing = graphene.Field(ListingNode)
    old_price = graphene.Decimal()
    new_price = graphene.Decimal()
    drop_percentage = graphene.Float()
    
    class Arguments:
        saved_search_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, saved_search_id):
        _, pk = from_global_id(saved_search_id)
        return [f"price_drop_alerts_{pk}"]
    
    @staticmethod
    def publish(payload, info, saved_search_id):
        return PriceDropAlertSubscription(
            listing=payload.get('listing'),
            old_price=payload.get('old_price'),
            new_price=payload.get('new_price'),
            drop_percentage=payload.get('drop_percentage')
        )
    
    @classmethod
    def trigger(cls, listing, saved_search, old_price, new_price):
        drop_percentage = ((old_price - new_price) / old_price) * 100
        cls.broadcast(
            group=f"price_drop_alerts_{saved_search.id}",
            payload={
                'listing': listing,
                'old_price': old_price,
                'new_price': new_price,
                'drop_percentage': drop_percentage
            }
        )


class NearbyPropertyAddedSubscription(Subscription):
    """New properties added within preferred locations"""
    listing = graphene.Field(ListingNode)
    distance_km = graphene.Float()
    proximity = graphene.Field(PropertyProximityNode)
    
    class Arguments:
        location_preference_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, location_preference_id):
        _, pk = from_global_id(location_preference_id)
        return [f"nearby_properties_{pk}"]
    
    @staticmethod
    def publish(payload, info, location_preference_id):
        return NearbyPropertyAddedSubscription(
            listing=payload.get('listing'),
            distance_km=payload.get('distance_km'),
            proximity=payload.get('proximity')
        )
    
    @classmethod
    def trigger(cls, listing, location_preference, distance_km):
        cls.broadcast(
            group=f"nearby_properties_{location_preference.id}",
            payload={
                'listing': listing,
                'distance_km': distance_km,
                'proximity': listing.proximities.filter(
                    buyer=location_preference.buyer
                ).first()
            }
        )
        

class LiveTourStartingSoonSubscription(Subscription):
    """Live tour starting soon notifications"""
    tour = graphene.Field(LiveTourScheduleNode)
    minutes_until_start = graphene.Int()
    meeting_link = graphene.String()
    
    class Arguments:
        tour_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, tour_id):
        _, pk = from_global_id(tour_id)
        return [f"live_tour_starting_{pk}"]
    
    @staticmethod
    def publish(payload, info, tour_id):
        return LiveTourStartingSoonSubscription(
            tour=payload.get('tour'),
            minutes_until_start=payload.get('minutes_until_start'),
            meeting_link=payload.get('meeting_link')
        )
    
    @classmethod
    def trigger(cls, tour, minutes_until_start):
        cls.broadcast(
            group=f"live_tour_starting_{tour.id}",
            payload={
                'tour': tour,
                'minutes_until_start': minutes_until_start,
                'meeting_link': tour.meeting_link
            }
        )


class LiveTourParticipantUpdateSubscription(Subscription):
    """Live tour participant updates (joining/leaving)"""
    tour = graphene.Field(LiveTourScheduleNode)
    participant = graphene.Field(LiveTourRegistrationNode)
    action = graphene.String()  # 'joined', 'left', 'raised_hand'
    current_participants = graphene.Int()
    
    class Arguments:
        tour_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, tour_id):
        _, pk = from_global_id(tour_id)
        return [f"tour_participants_{pk}"]
    
    @staticmethod
    def publish(payload, info, tour_id):
        return LiveTourParticipantUpdateSubscription(
            tour=payload.get('tour'),
            participant=payload.get('participant'),
            action=payload.get('action'),
            current_participants=payload.get('current_participants')
        )
    
    @classmethod
    def trigger(cls, tour, participant, action):
        cls.broadcast(
            group=f"tour_participants_{tour.id}",
            payload={
                'tour': tour,
                'participant': participant,
                'action': action,
                'current_participants': tour.attendees.count()
            }
        )


class VirtualTourViewCountSubscription(Subscription):
    """Virtual tour view count updates"""
    tour = graphene.Field(VirtualTourNode)
    view_count = graphene.Int()
    unique_viewers = graphene.Int()
    
    class Arguments:
        property_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, property_id):
        _, pk = from_global_id(property_id)
        return [f"virtual_tour_views_{pk}"]
    
    @staticmethod
    def publish(payload, info, property_id):
        return VirtualTourViewCountSubscription(
            tour=payload.get('tour'),
            view_count=payload.get('view_count'),
            unique_viewers=payload.get('unique_viewers')
        )
    
    @classmethod
    def trigger(cls, virtual_tour, view_count, unique_viewers):
        cls.broadcast(
            group=f"virtual_tour_views_{virtual_tour.property.id}",
            payload={
                'tour': virtual_tour,
                'view_count': view_count,
                'unique_viewers': unique_viewers
            }
        )


class NewMessageSubscription(Subscription):
    """Real-time messaging between users/agents"""
    message = graphene.Field(MessageNode)
    thread = graphene.Field(MessageThreadNode)
    sender = graphene.ID()
    
    class Arguments:
        thread_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, thread_id):
        _, pk = from_global_id(thread_id)
        return [f"message_thread_{pk}"]
    
    @staticmethod
    def publish(payload, info, thread_id):
        return NewMessageSubscription(
            message=payload.get('message'),
            thread=payload.get('thread'),
            sender=payload.get('sender')
        )
    
    @classmethod
    def trigger(cls, message):
        cls.broadcast(
            group=f"message_thread_{message.thread.id}",
            payload={
                'message': message,
                'thread': message.thread,
                'sender': message.sender.id
            }
        )


class MessageReadStatusSubscription(Subscription):
    """Message read status updates"""
    message = graphene.Field(MessageNode)
    reader = graphene.ID()
    read_at = graphene.DateTime()
    
    class Arguments:
        thread_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, thread_id):
        _, pk = from_global_id(thread_id)
        return [f"message_read_status_{pk}"]
    
    @staticmethod
    def publish(payload, info, thread_id):
        return MessageReadStatusSubscription(
            message=payload.get('message'),
            reader=payload.get('reader'),
            read_at=payload.get('read_at')
        )
    
    @classmethod
    def trigger(cls, message, reader):
        cls.broadcast(
            group=f"message_read_status_{message.thread.id}",
            payload={
                'message': message,
                'reader': reader.id,
                'read_at': message.timestamp
            }
        )


class TypingIndicatorSubscription(Subscription):
    """Typing indicators in chat"""
    thread = graphene.Field(MessageThreadNode)
    user = graphene.ID()
    is_typing = graphene.Boolean()
    
    class Arguments:
        thread_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, thread_id):
        _, pk = from_global_id(thread_id)
        return [f"typing_indicator_{pk}"]
    
    @staticmethod
    def publish(payload, info, thread_id):
        return TypingIndicatorSubscription(
            thread=payload.get('thread'),
            user=payload.get('user'),
            is_typing=payload.get('is_typing')
        )
    
    @classmethod
    def trigger(cls, thread, user, is_typing):
        cls.broadcast(
            group=f"typing_indicator_{thread.id}",
            payload={
                'thread': thread,
                'user': user.id,
                'is_typing': is_typing
            }
        )
        


class TransactionStatusChangedSubscription(Subscription):
    """Transaction status updates"""
    transaction = graphene.Field(TransactionNode)
    old_status = graphene.String()
    new_status = graphene.String()
    updated_by = graphene.ID()
    
    class Arguments:
        transaction_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, transaction_id):
        _, pk = from_global_id(transaction_id)
        return [f"transaction_status_{pk}"]
    
    @staticmethod
    def publish(payload, info, transaction_id):
        return TransactionStatusChangedSubscription(
            transaction=payload.get('transaction'),
            old_status=payload.get('old_status'),
            new_status=payload.get('new_status'),
            updated_by=payload.get('updated_by')
        )
    
    @classmethod
    def trigger(cls, transaction, old_status, new_status, updated_by):
        cls.broadcast(
            group=f"transaction_status_{transaction.id}",
            payload={
                'transaction': transaction,
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': updated_by
            }
        )


class NewOfferReceivedSubscription(Subscription):
    """New property offer notifications"""
    offer = graphene.Field(OfferNode)
    property = graphene.Field(ListingNode)
    buyer = graphene.Field(ClientNode)
    
    class Arguments:
        property_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, property_id):
        _, pk = from_global_id(property_id)
        return [f"new_offers_{pk}"]
    
    @staticmethod
    def publish(payload, info, property_id):
        return NewOfferReceivedSubscription(
            offer=payload.get('offer'),
            property=payload.get('property'),
            buyer=payload.get('buyer')
        )
    
    @classmethod
    def trigger(cls, offer):
        cls.broadcast(
            group=f"new_offers_{offer.property.id}",
            payload={
                'offer': offer,
                'property': offer.property,
                'buyer': offer.buyer
            }
        )


class OfferStatusChangedSubscription(Subscription):
    """Offer status updates (accepted/rejected/countered)"""
    offer = graphene.Field(OfferNode)
    old_status = graphene.String()
    new_status = graphene.String()
    counter_offer = graphene.Field(CounterOfferNode)
    
    class Arguments:
        offer_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, offer_id):
        _, pk = from_global_id(offer_id)
        return [f"offer_status_{pk}"]
    
    @staticmethod
    def publish(payload, info, offer_id):
        return OfferStatusChangedSubscription(
            offer=payload.get('offer'),
            old_status=payload.get('old_status'),
            new_status=payload.get('new_status'),
            counter_offer=payload.get('counter_offer')
        )
    
    @classmethod
    def trigger(cls, offer, old_status, new_status, counter_offer=None):
        cls.broadcast(
            group=f"offer_status_{offer.id}",
            payload={
                'offer': offer,
                'old_status': old_status,
                'new_status': new_status,
                'counter_offer': counter_offer
            }
        )


class TransactionMilestoneCompletedSubscription(Subscription):
    """Transaction milestone completion updates"""
    milestone = graphene.Field(TransactionMilestoneNode)
    transaction = graphene.Field(TransactionNode)
    completed_by = graphene.ID()
    
    class Arguments:
        transaction_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, transaction_id):
        _, pk = from_global_id(transaction_id)
        return [f"transaction_milestones_{pk}"]
    
    @staticmethod
    def publish(payload, info, transaction_id):
        return TransactionMilestoneCompletedSubscription(
            milestone=payload.get('milestone'),
            transaction=payload.get('transaction'),
            completed_by=payload.get('completed_by')
        )
    
    @classmethod
    def trigger(cls, milestone, completed_by):
        cls.broadcast(
            group=f"transaction_milestones_{milestone.transaction.id}",
            payload={
                'milestone': milestone,
                'transaction': milestone.transaction,
                'completed_by': completed_by.id
            }
        )
        

class DocumentPackageStatusSubscription(Subscription):
    """Document package status updates"""
    package = graphene.Field(DocumentPackageNode)
    old_status = graphene.Boolean()
    new_status = graphene.Boolean()
    updated_by = graphene.ID()
    
    class Arguments:
        package_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, package_id):
        _, pk = from_global_id(package_id)
        return [f"document_package_{pk}"]
    
    @staticmethod
    def publish(payload, info, package_id):
        return DocumentPackageStatusSubscription(
            package=payload.get('package'),
            old_status=payload.get('old_status'),
            new_status=payload.get('new_status'),
            updated_by=payload.get('updated_by')
        )
    
    @classmethod
    def trigger(cls, package, old_status, new_status, updated_by):
        cls.broadcast(
            group=f"document_package_{package.id}",
            payload={
                'package': package,
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': updated_by
            }
        )


class DocumentSignatureRequestedSubscription(Subscription):
    """Document signature request notifications"""
    document = graphene.Field(DocumentNode)
    package = graphene.Field(DocumentPackageNode)
    requested_by = graphene.ID()
    
    class Arguments:
        user_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, user_id):
        _, pk = from_global_id(user_id)
        return [f"signature_requests_{pk}"]
    
    @staticmethod
    def publish(payload, info, user_id):
        return DocumentSignatureRequestedSubscription(
            document=payload.get('document'),
            package=payload.get('package'),
            requested_by=payload.get('requested_by')
        )
    
    @classmethod
    def trigger(cls, document, requested_by):
        cls.broadcast(
            group=f"signature_requests_{document.package.property.owner.id}",
            payload={
                'document': document,
                'package': document.package,
                'requested_by': requested_by.id
            }
        )


class DocumentSignedSubscription(Subscription):
    """Document signed notifications"""
    signature = graphene.Field(DocumentSignatureNode)
    document = graphene.Field(DocumentNode)
    signed_by = graphene.ID()
    
    class Arguments:
        document_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, document_id):
        _, pk = from_global_id(document_id)
        return [f"document_signed_{pk}"]
    
    @staticmethod
    def publish(payload, info, document_id):
        return DocumentSignedSubscription(
            signature=payload.get('signature'),
            document=payload.get('document'),
            signed_by=payload.get('signed_by')
        )
    
    @classmethod
    def trigger(cls, signature):
        cls.broadcast(
            group=f"document_signed_{signature.document.id}",
            payload={
                'signature': signature,
                'document': signature.document,
                'signed_by': signature.user.id
            }
        )
        
class MarketTrendUpdateSubscription(Subscription):
    """Real-time market trend updates for neighborhoods"""
    neighborhood = graphene.Field(NeighborhoodNode)
    trend_data = graphene.JSONString()
    updated_at = graphene.DateTime()
    
    class Arguments:
        neighborhood_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, neighborhood_id):
        _, pk = from_global_id(neighborhood_id)
        return [f"market_trend_{pk}"]
    
    @staticmethod
    def publish(payload, info, neighborhood_id):
        return MarketTrendUpdateSubscription(
            neighborhood=payload.get('neighborhood'),
            trend_data=payload.get('trend_data'),
            updated_at=payload.get('updated_at')
        )
    
    @classmethod
    def trigger(cls, neighborhood, trend_data):
        cls.broadcast(
            group=f"market_trend_{neighborhood.id}",
            payload={
                'neighborhood': neighborhood,
                'trend_data': trend_data,
                'updated_at': timezone.now()
            }
        )


class InventoryChangeSubscription(Subscription):
    """Real-time inventory change notifications for agents/analysts"""
    neighborhood_id = graphene.ID()
    property_type = graphene.String()
    change_type = graphene.String()  # 'new_listing', 'price_change', 'sold', 'removed'
    count_change = graphene.Int()
    total_inventory = graphene.Int()
    
    class Arguments:
        neighborhood_id = graphene.ID()
        agent_id = graphene.ID()
    
    @staticmethod
    def subscribe(root, info, **kwargs):
        groups = []
        if 'neighborhood_id' in kwargs:
            _, pk = from_global_id(kwargs['neighborhood_id'])
            groups.append(f"inventory_neighborhood_{pk}")
        if 'agent_id' in kwargs:
            _, pk = from_global_id(kwargs['agent_id'])
            groups.append(f"inventory_agent_{pk}")
        return groups
    
    @staticmethod
    def publish(payload, info, **kwargs):
        return InventoryChangeSubscription(
            neighborhood_id=payload.get('neighborhood_id'),
            property_type=payload.get('property_type'),
            change_type=payload.get('change_type'),
            count_change=payload.get('count_change'),
            total_inventory=payload.get('total_inventory')
        )
    
    @classmethod
    def trigger_neighborhood(cls, neighborhood, property_type, change_type, count_change):
        cls.broadcast(
            group=f"inventory_neighborhood_{neighborhood.id}",
            payload={
                'neighborhood_id': to_global_id('NeighborhoodNode', neighborhood.id),
                'property_type': property_type,
                'change_type': change_type,
                'count_change': count_change,
                'total_inventory': Listing.objects.filter(
                    location_point__within=neighborhood.boundary,
                    property_type=property_type
                ).count()
            }
        )
    
    @classmethod
    def trigger_agent(cls, agent, property_type, change_type, count_change):
        cls.broadcast(
            group=f"inventory_agent_{agent.id}",
            payload={
                'agent_id': to_global_id('AgentNode', agent.id),
                'property_type': property_type,
                'change_type': change_type,
                'count_change': count_change,
                'total_inventory': Listing.objects.filter(agent=agent).count()
            }
        )


class PriceTrendSubscription(Subscription):
    """Real-time price trend updates"""
    area = graphene.String()  # 'city', 'neighborhood', 'zip_code'
    area_id = graphene.ID()
    property_type = graphene.String()
    avg_price = graphene.Decimal()
    price_change_percent = graphene.Float()
    updated_at = graphene.DateTime()
    
    class Arguments:
        area = graphene.String(required=True)
        area_id = graphene.ID()
        property_type = graphene.String()
    
    @staticmethod
    def subscribe(root, info, area, area_id=None, property_type=None):
        groups = [f"price_trend_{area}"]
        if area_id:
            _, pk = from_global_id(area_id)
            groups.append(f"price_trend_{area}_{pk}")
        if property_type:
            groups.append(f"price_trend_{area}_{property_type}")
        return groups
    
    @staticmethod
    def publish(payload, info, **kwargs):
        return PriceTrendSubscription(
            area=payload.get('area'),
            area_id=payload.get('area_id'),
            property_type=payload.get('property_type'),
            avg_price=payload.get('avg_price'),
            price_change_percent=payload.get('price_change_percent'),
            updated_at=payload.get('updated_at')
        )
    
    @classmethod
    def trigger_city(cls, city_name, property_type, avg_price, price_change_percent):
        cls.broadcast(
            group=f"price_trend_city_{city_name}",
            payload={
                'area': 'city',
                'area_id': None,
                'property_type': property_type,
                'avg_price': avg_price,
                'price_change_percent': price_change_percent,
                'updated_at': timezone.now()
            }
        )
    
    @classmethod
    def trigger_neighborhood(cls, neighborhood, property_type, avg_price, price_change_percent):
        cls.broadcast(
            group=f"price_trend_neighborhood_{neighborhood.id}",
            payload={
                'area': 'neighborhood',
                'area_id': to_global_id('NeighborhoodNode', neighborhood.id),
                'property_type': property_type,
                'avg_price': avg_price,
                'price_change_percent': price_change_percent,
                'updated_at': timezone.now()
            }
        )
        
        
class PropertyBookmarkedSubscription(Subscription):
    """Real-time notifications when properties are bookmarked"""
    listing = graphene.Field(ListingNode)
    user = graphene.ID()
    bookmark_count = graphene.Int()
    
    class Arguments:
        listing_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, listing_id):
        _, pk = from_global_id(listing_id)
        return [f"property_bookmarks_{pk}"]
    
    @staticmethod
    def publish(payload, info, listing_id):
        return PropertyBookmarkedSubscription(
            listing=payload.get('listing'),
            user=payload.get('user'),
            bookmark_count=payload.get('bookmark_count')
        )
    
    @classmethod
    def trigger(cls, listing, user, bookmark_count):
        cls.broadcast(
            group=f"property_bookmarks_{listing.id}",
            payload={
                'listing': listing,
                'user': user.id,
                'bookmark_count': bookmark_count
            }
        )


class AppointmentScheduledSubscription(Subscription):
    """Property viewing appointment scheduled"""
    property = graphene.Field(ListingNode)
    agent = graphene.Field(AgentNode)
    client = graphene.Field(ClientNode)
    appointment_time = graphene.DateTime()
    
    class Arguments:
        agent_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, agent_id):
        _, pk = from_global_id(agent_id)
        return [f"appointments_agent_{pk}"]
    
    @staticmethod
    def publish(payload, info, agent_id):
        return AppointmentScheduledSubscription(
            property=payload.get('property'),
            agent=payload.get('agent'),
            client=payload.get('client'),
            appointment_time=payload.get('appointment_time')
        )
    
    @classmethod
    def trigger(cls, property, agent, client, appointment_time):
        cls.broadcast(
            group=f"appointments_agent_{agent.id}",
            payload={
                'property': property,
                'agent': agent,
                'client': client,
                'appointment_time': appointment_time
            }
        )


class CommissionEarnedSubscription(Subscription):
    """Commission earned notifications for agents"""
    transaction = graphene.Field(TransactionNode)
    agent = graphene.Field(AgentNode)
    commission_amount = graphene.Decimal()
    commission_type = graphene.String()
    
    class Arguments:
        agent_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, agent_id):
        _, pk = from_global_id(agent_id)
        return [f"commissions_agent_{pk}"]
    
    @staticmethod
    def publish(payload, info, agent_id):
        return CommissionEarnedSubscription(
            transaction=payload.get('transaction'),
            agent=payload.get('agent'),
            commission_amount=payload.get('commission_amount'),
            commission_type=payload.get('commission_type')
        )
    
    @classmethod
    def trigger(cls, transaction, agent, commission_amount, commission_type):
        cls.broadcast(
            group=f"commissions_agent_{agent.id}",
            payload={
                'transaction': transaction,
                'agent': agent,
                'commission_amount': commission_amount,
                'commission_type': commission_type
            }
        )


class MarketActivityHeatmapSubscription(Subscription):
    """Real-time market activity heatmap updates"""
    coordinates = graphene.List(graphene.List(graphene.Float))
    activity_type = graphene.String()  # 'views', 'bookmarks', 'inquiries'
    intensity = graphene.Float()
    
    class Arguments:
        area = graphene.String(required=True)  # 'city', 'region', 'neighborhood'
    
    @staticmethod
    def subscribe(root, info, area):
        return [f"market_heatmap_{area}"]
    
    @staticmethod
    def publish(payload, info, area):
        return MarketActivityHeatmapSubscription(
            coordinates=payload.get('coordinates'),
            activity_type=payload.get('activity_type'),
            intensity=payload.get('intensity')
        )
    
    @classmethod
    def trigger(cls, coordinates, activity_type, intensity, area):
        cls.broadcast(
            group=f"market_heatmap_{area}",
            payload={
                'coordinates': coordinates,
                'activity_type': activity_type,
                'intensity': intensity
            }
        )


class PropertyInquirySubscription(Subscription):
    """New property inquiry notifications"""
    listing = graphene.Field(ListingNode)
    inquirer = graphene.Field(ClientNode)
    message = graphene.String()
    inquiry_type = graphene.String()  # 'general', 'viewing', 'offer'
    
    class Arguments:
        property_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, property_id):
        _, pk = from_global_id(property_id)
        return [f"inquiries_property_{pk}"]
    
    @staticmethod
    def publish(payload, info, property_id):
        return PropertyInquirySubscription(
            listing=payload.get('listing'),
            inquirer=payload.get('inquirer'),
            message=payload.get('message'),
            inquiry_type=payload.get('inquiry_type')
        )
    
    @classmethod
    def trigger(cls, listing, inquirer, message, inquiry_type):
        cls.broadcast(
            group=f"inquiries_property_{listing.id}",
            payload={
                'listing': listing,
                'inquirer': inquirer,
                'message': message,
                'inquiry_type': inquiry_type
            }
        )


class ReviewReceivedSubscription(Subscription):
    """New review/rating received notifications"""
    rating = graphene.Field(PropertyRatingNode)
    reviewed_item_type = graphene.String()  # 'property', 'agent'
    reviewer = graphene.Field(ClientNode)
    
    class Arguments:
        user_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, user_id):
        _, pk = from_global_id(user_id)
        return [f"reviews_user_{pk}"]
    
    @staticmethod
    def publish(payload, info, user_id):
        return ReviewReceivedSubscription(
            rating=payload.get('rating'),
            reviewed_item_type=payload.get('reviewed_item_type'),
            reviewer=payload.get('reviewer')
        )
    
    @classmethod
    def trigger(cls, rating, reviewed_item_type, reviewer):
        if reviewed_item_type == 'property':
            item_id = rating.property.owner.id
        else:  # agent
            item_id = rating.agent.agent_profile.profile.user.id
        
        cls.broadcast(
            group=f"reviews_user_{item_id}",
            payload={
                'rating': rating,
                'reviewed_item_type': reviewed_item_type,
                'reviewer': reviewer
            }
        )
   
   
class NewPropertyListedSubscription(Subscription):
    """New property listing alerts for agents"""
    listing = graphene.Field(ListingNode)
    agent = graphene.Field(AgentNode)
    
    class Arguments:
        agent_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, agent_id):
        _, pk = from_global_id(agent_id)
        return [f"new_listings_agent_{pk}"]
    
    @staticmethod
    def publish(payload, info, agent_id):
        return NewPropertyListedSubscription(
            listing=payload.get('listing'),
            agent=payload.get('agent')
        )
    
    @classmethod
    def trigger(cls, listing, agent):
        """Trigger when a new property is listed"""
        cls.broadcast(
            group=f"new_listings_agent_{agent.id}",
            payload={
                'listing': listing,
                'agent': agent
            }
        )


class PropertyViewCountSubscription(Subscription):
    """Property view count updates"""
    listing = graphene.Field(ListingNode)
    view_count = graphene.Int()
    unique_viewers = graphene.Int()
    
    class Arguments:
        listing_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, listing_id):
        _, pk = from_global_id(listing_id)
        return [f"property_views_{pk}"]
    
    @staticmethod
    def publish(payload, info, listing_id):
        return PropertyViewCountSubscription(
            listing=payload.get('listing'),
            view_count=payload.get('view_count'),
            unique_viewers=payload.get('unique_viewers')
        )
    
    @classmethod
    def trigger(cls, listing, view_count, unique_viewers):
        """Trigger when view count updates"""
        cls.broadcast(
            group=f"property_views_{listing.id}",
            payload={
                'listing': listing,
                'view_count': view_count,
                'unique_viewers': unique_viewers
            }
        )


class AgentPerformanceUpdateSubscription(Subscription):
    """Agent performance metric updates"""
    agent = graphene.Field(AgentNode)
    metrics = graphene.JSONString()
    period = graphene.String()  # 'daily', 'weekly', 'monthly'
    
    class Arguments:
        agent_id = graphene.ID(required=True)
    
    @staticmethod
    def subscribe(root, info, agent_id):
        _, pk = from_global_id(agent_id)
        return [f"agent_performance_{pk}"]
    
    @staticmethod
    def publish(payload, info, agent_id):
        return AgentPerformanceUpdateSubscription(
            agent=payload.get('agent'),
            metrics=payload.get('metrics'),
            period=payload.get('period')
        )
    
    @classmethod
    def trigger(cls, agent, metrics, period):
        """Trigger when agent performance metrics update"""
        cls.broadcast(
            group=f"agent_performance_{agent.id}",
            payload={
                'agent': agent,
                'metrics': metrics,
                'period': period
            }
        )
        
             
class RealEstateSubscriptions(graphene.ObjectType):
    # Core subscriptions
    listing_status_changed = ListingStatusChangedSubscription.Field()
    listing_price_updated = ListingPriceUpdatedSubscription.Field()
    new_matching_listing = NewMatchingListingSubscription.Field()
    agent_availability_changed = AgentAvailabilityChangedSubscription.Field()
    
    # Alert subscriptions
    property_subscription_alert = PropertySubscriptionAlertSubscription.Field()
    price_drop_alert = PriceDropAlertSubscription.Field()
    nearby_property_added = NearbyPropertyAddedSubscription.Field()
    
    # Analytics subscriptions
    market_trend_update = MarketTrendUpdateSubscription.Field()  # Now defined
    inventory_change = InventoryChangeSubscription.Field()       # Now defined
    price_trend = PriceTrendSubscription.Field()                 # Now defined
    
    # Tour subscriptions
    live_tour_starting_soon = LiveTourStartingSoonSubscription.Field()
    live_tour_participant_update = LiveTourParticipantUpdateSubscription.Field()
    virtual_tour_view_count = VirtualTourViewCountSubscription.Field()
    
    # Messaging subscriptions
    new_message = NewMessageSubscription.Field()
    message_read_status = MessageReadStatusSubscription.Field()
    typing_indicator = TypingIndicatorSubscription.Field()
    
    # Transaction subscriptions
    transaction_status_changed = TransactionStatusChangedSubscription.Field()
    new_offer_received = NewOfferReceivedSubscription.Field()
    offer_status_changed = OfferStatusChangedSubscription.Field()
    transaction_milestone_completed = TransactionMilestoneCompletedSubscription.Field()
    
    # Document subscriptions
    document_package_status = DocumentPackageStatusSubscription.Field()
    document_signature_requested = DocumentSignatureRequestedSubscription.Field()
    document_signed = DocumentSignedSubscription.Field()
    
    new_property_listed = NewPropertyListedSubscription.Field()
    property_view_count = PropertyViewCountSubscription.Field()
    agent_performance_update = AgentPerformanceUpdateSubscription.Field()
    property_bookmarked = PropertyBookmarkedSubscription.Field()
    appointment_scheduled = AppointmentScheduledSubscription.Field()
    commission_earned = CommissionEarnedSubscription.Field()
    market_activity_heatmap = MarketActivityHeatmapSubscription.Field()
    property_inquiry = PropertyInquirySubscription.Field()
    review_received = ReviewReceivedSubscription.Field()