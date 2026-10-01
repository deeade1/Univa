# signals.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    Listing, PropertySubscription, Client, Agent, 
    PropertyUpdateLog, LocationPreference, UserProfile,
    PropertyProximity, Transaction, Offer, CounterOffer,
    PropertyRating, AgentRating, VirtualTour, LiveTourSchedule,
    LiveTourRegistration, Message, DocumentSignature,
    MarketTrend, SavedSearch, CommissionPlan, AgentCommission
)

# Import your subscription classes
from .subscriptions import (
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
    NewPropertyListedSubscription,
    PropertyViewCountSubscription,
    AgentPerformanceUpdateSubscription,
    PropertyBookmarkedSubscription,
    AppointmentScheduledSubscription,
    CommissionEarnedSubscription,
    MarketActivityHeatmapSubscription,
    PropertyInquirySubscription,
    ReviewReceivedSubscription
)


# ============ LISTING SIGNALS ============

@receiver(pre_save, sender=Listing)
def track_listing_changes(sender, instance, **kwargs):
    """Track listing changes for price and status updates"""
    if instance.pk:
        try:
            old_instance = Listing.objects.get(pk=instance.pk)
            instance._old_price = old_instance.price
            instance._old_status = old_instance.property_status
        except Listing.DoesNotExist:
            instance._old_price = None
            instance._old_status = None


@receiver(post_save, sender=Listing)
def handle_listing_updates(sender, instance, created, **kwargs):
    """Handle listing updates and trigger subscriptions"""
    
    if created:
        # Trigger new property listing subscription
        if instance.agent:
            NewPropertyListedSubscription.trigger(instance, instance.agent)
        
        # Trigger new matching listings for subscribed clients
        trigger_new_matching_listings(instance)
        
        # Update inventory stats
        update_inventory_stats(instance)
        
        # Trigger market heatmap updates
        trigger_market_activity(instance, 'new_listing')
    
    else:
        # Handle price changes
        if hasattr(instance, '_old_price') and instance._old_price != instance.price:
            handle_price_change(instance)
        
        # Handle status changes
        if hasattr(instance, '_old_status') and instance._old_status != instance.property_status:
            handle_status_change(instance)
        
        # Trigger property updates
        if not created:
            PropertyViewCountSubscription.trigger(
                instance, 
                instance.view_count if hasattr(instance, 'view_count') else 0,
                instance.unique_viewers if hasattr(instance, 'unique_viewers') else 0
            )
            
        # Update inventory stats
        update_inventory_stats(instance)


def handle_price_change(listing):
    """Handle price change subscriptions"""
    # Trigger price updated subscription
    ListingPriceUpdatedSubscription.trigger(
        listing, 
        listing._old_price, 
        listing.price
    )
    
    # Trigger price drop alerts for saved searches
    if listing._old_price and listing.price < listing._old_price:
        trigger_price_drop_alerts(listing)
    
    # Update price trends
    trigger_price_trends(listing)


def handle_status_change(listing):
    """Handle listing status change subscriptions"""
    # Trigger status changed subscription
    ListingStatusChangedSubscription.trigger(
        listing,
        listing._old_status,
        listing.property_status,
        listing.agent.user if listing.agent else None
    )
    
    # Update inventory stats
    update_inventory_stats(listing)
    
    # Trigger property subscription alerts
    trigger_property_subscription_alerts(listing, 'status_change')


def trigger_new_matching_listings(listing):
    """Trigger new matching listing alerts for clients"""
    if not listing.is_published:
        return
    
    # Find clients whose preferences match this listing
    matching_clients = Client.objects.filter(
        price_range_min__lte=listing.price,
        price_range_max__gte=listing.price,
        preferred_property_types__contains=[listing.listing_type.property_type]
    )
    
    for client in matching_clients:
        # Check location proximity
        if client.location_point and listing.location_point:
            distance = client.location_point.distance(listing.location_point) * 100
            if distance <= client.search_radius_km:
                NewMatchingListingSubscription.trigger(
                    listing,
                    client,
                    calculate_match_score(listing, client),
                    ['Location match', 'Price match', 'Property type match']
                )


def calculate_match_score(listing, client):
    """Calculate match score between listing and client preferences"""
    score = 0
    reasons = []
    
    # Price match (40% weight)
    if client.price_range_min <= listing.price <= client.price_range_max:
        score += 40
        reasons.append('Price within range')
    
    # Property type match (30% weight)
    if listing.listing_type.property_type in client.preferred_property_types:
        score += 30
        reasons.append('Preferred property type')
    
    # Location match (30% weight)
    if client.location_point and listing.location_point:
        distance = client.location_point.distance(listing.location_point) * 100
        if distance <= client.search_radius_km:
            location_score = max(0, 30 - (distance / client.search_radius_km * 10))
            score += location_score
            reasons.append(f'Within {distance:.1f}km of preferred location')
    
    return min(100, score)


def trigger_price_drop_alerts(listing):
    """Trigger price drop alerts for saved searches"""
    saved_searches = SavedSearch.objects.filter(
        search_parameters__contains={'min_price': listing.price},
        is_active=True
    )
    
    for saved_search in saved_searches:
        PriceDropAlertSubscription.trigger(
            listing,
            saved_search,
            listing._old_price,
            listing.price
        )


def trigger_property_subscription_alerts(listing, alert_type):
    """Trigger alerts for property subscriptions"""
    subscriptions = PropertySubscription.objects.filter(
        property_type=listing.listing_type.property_type,
        location_point__distance_lte=(listing.location_point, D(km=100))
    )
    
    for subscription in subscriptions:
        if listing.location_point.distance(subscription.location_point) * 100 <= subscription.radius_km:
            PropertySubscriptionAlertSubscription.trigger(
                subscription,
                [listing],
                alert_type
            )


def update_inventory_stats(listing):
    """Update inventory statistics and trigger subscriptions"""
    # Update neighborhood inventory
    if hasattr(listing, 'neighborhood') and listing.neighborhood:
        neighborhood = listing.neighborhood
        inventory_count = Listing.objects.filter(
            neighborhood=neighborhood,
            property_type=listing.listing_type.property_type,
            is_published=True
        ).count()
        
        InventoryChangeSubscription.trigger_neighborhood(
            neighborhood,
            listing.listing_type.property_type,
            'inventory_update',
            inventory_count
        )


def trigger_price_trends(listing):
    """Trigger price trend updates"""
    if hasattr(listing, 'neighborhood') and listing.neighborhood:
        neighborhood = listing.neighborhood
        avg_price = Listing.objects.filter(
            neighborhood=neighborhood,
            property_type=listing.listing_type.property_type,
            is_published=True
        ).aggregate(avg=models.Avg('price'))['avg']
        
        PriceTrendSubscription.trigger_neighborhood(
            neighborhood,
            listing.listing_type.property_type,
            avg_price or listing.price,
            0  # You'd calculate actual change here
        )


def trigger_market_activity(listing, activity_type):
    """Trigger market activity updates"""
    coordinates = [[listing.longitude, listing.latitude]] if listing.longitude and listing.latitude else []
    
    MarketActivityHeatmapSubscription.trigger(
        coordinates,
        activity_type,
        1.0,  # intensity
        'city'  # area
    )


# ============ AGENT SIGNALS ============

@receiver(post_save, sender=Agent)
def handle_agent_updates(sender, instance, created, **kwargs):
    """Handle agent updates"""
    if created:
        # Initialize agent availability
        AgentAvailabilityChangedSubscription.trigger(
            instance,
            True,  # is_available
            timezone.now()
        )


@receiver(post_save, sender=AgentCommission)
def handle_commission_updates(sender, instance, created, **kwargs):
    """Handle commission updates"""
    if created and instance.paid_amount > 0:
        CommissionEarnedSubscription.trigger(
            instance.transaction,
            instance.agent,
            instance.paid_amount,
            instance.commission_plan.plan_type
        )


# ============ TRANSACTION SIGNALS ============

@receiver(pre_save, sender=Transaction)
def track_transaction_changes(sender, instance, **kwargs):
    """Track transaction changes"""
    if instance.pk:
        try:
            old_instance = Transaction.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Transaction.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=Transaction)
def handle_transaction_updates(sender, instance, created, **kwargs):
    """Handle transaction updates"""
    if not created and hasattr(instance, '_old_status') and instance._old_status != instance.status:
        TransactionStatusChangedSubscription.trigger(
            instance,
            instance._old_status,
            instance.status,
            instance.property.agent.user if instance.property.agent else None
        )


# ============ OFFER SIGNALS ============

@receiver(post_save, sender=Offer)
def handle_offer_updates(sender, instance, created, **kwargs):
    """Handle offer updates"""
    if created:
        NewOfferReceivedSubscription.trigger(instance)
    else:
        # Check for status changes
        try:
            old_instance = Offer.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                OfferStatusChangedSubscription.trigger(
                    instance,
                    old_instance.status,
                    instance.status
                )
        except Offer.DoesNotExist:
            pass


@receiver(post_save, sender=CounterOffer)
def handle_counter_offer_updates(sender, instance, created, **kwargs):
    """Handle counter offer updates"""
    if created:
        OfferStatusChangedSubscription.trigger(
            instance.original_offer,
            instance.original_offer.status,
            'countered',
            instance
        )


# ============ RATING SIGNALS ============

@receiver(post_save, sender=PropertyRating)
def handle_property_rating(sender, instance, created, **kwargs):
    """Handle property rating updates"""
    if created:
        ReviewReceivedSubscription.trigger(
            instance,
            'property',
            instance.user.profile.client if hasattr(instance.user.profile, 'client') else None
        )


@receiver(post_save, sender=AgentRating)
def handle_agent_rating(sender, instance, created, **kwargs):
    """Handle agent rating updates"""
    if created:
        ReviewReceivedSubscription.trigger(
            instance,
            'agent',
            instance.user.profile.client if hasattr(instance.user.profile, 'client') else None
        )


# ============ TOUR SIGNALS ============

@receiver(post_save, sender=LiveTourSchedule)
def handle_live_tour_updates(sender, instance, created, **kwargs):
    """Handle live tour updates"""
    if created:
        # Schedule start notification (10 minutes before)
        from datetime import timedelta
        start_time = instance.scheduled_time
        notify_time = start_time - timedelta(minutes=10)
        
        # You'd schedule a Celery task here to trigger at notify_time
        # For now, we'll trigger immediately for demo
        LiveTourStartingSoonSubscription.trigger(instance, 10)


@receiver(post_save, sender=LiveTourRegistration)
def handle_live_tour_registration(sender, instance, created, **kwargs):
    """Handle live tour registration"""
    if created:
        LiveTourParticipantUpdateSubscription.trigger(
            instance.tour,
            instance,
            'joined'
        )


@receiver(post_save, sender=VirtualTour)
def handle_virtual_tour_updates(sender, instance, created, **kwargs):
    """Handle virtual tour updates"""
    if created:
        VirtualTourViewCountSubscription.trigger(instance, 0, 0)


# ============ MESSAGE SIGNALS ============

@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """Handle new messages"""
    if created:
        NewMessageSubscription.trigger(instance)


# ============ DOCUMENT SIGNALS ============

@receiver(post_save, sender=DocumentSignature)
def handle_document_signature(sender, instance, created, **kwargs):
    """Handle document signatures"""
    if created:
        DocumentSignedSubscription.trigger(instance)


# ============ MARKET TREND SIGNALS ============

@receiver(post_save, sender=MarketTrend)
def handle_market_trend_updates(sender, instance, created, **kwargs):
    """Handle market trend updates"""
    if created or kwargs.get('update_fields'):
        MarketTrendUpdateSubscription.trigger(
            instance.neighborhood,
            {
                'date': str(instance.date),
                'median_price': float(instance.median_price),
                'listings_count': instance.listings_count,
                'avg_days_on_market': instance.avg_days_on_market,
                'price_per_sqft': float(instance.price_per_sqft)
            }
        )


# ============ PROXIMITY SIGNALS ============

@receiver(post_save, sender=LocationPreference)
def handle_location_preference_updates(sender, instance, created, **kwargs):
    """Handle location preference updates"""
    if created:
        # Find nearby properties and trigger notifications
        nearby_properties = Listing.objects.filter(
            location_point__distance_lte=(instance.location_point, D(km=instance.radius_km)),
            is_published=True
        )
        
        for property in nearby_properties:
            distance = property.location_point.distance(instance.location_point) * 100
            NearbyPropertyAddedSubscription.trigger(property, instance, distance)


# ============ INITIALIZATION ============

def init_signals():
    """Initialize all signals"""
    # This function ensures signals are connected
    pass


# ============ SIGNAL DISCONNECTION (for testing) ============

def disconnect_signals():
    """Disconnect all signals (for testing purposes)"""
    post_save.disconnect(handle_listing_updates, sender=Listing)
    pre_save.disconnect(track_listing_changes, sender=Listing)
    post_save.disconnect(handle_agent_updates, sender=Agent)
    pre_save.disconnect(track_transaction_changes, sender=Transaction)
    post_save.disconnect(handle_transaction_updates, sender=Transaction)
    post_save.disconnect(handle_offer_updates, sender=Offer)
    post_save.disconnect(handle_counter_offer_updates, sender=CounterOffer)
    post_save.disconnect(handle_property_rating, sender=PropertyRating)
    post_save.disconnect(handle_agent_rating, sender=AgentRating)
    post_save.disconnect(handle_live_tour_updates, sender=LiveTourSchedule)
    post_save.disconnect(handle_live_tour_registration, sender=LiveTourRegistration)
    post_save.disconnect(handle_virtual_tour_updates, sender=VirtualTour)
    post_save.disconnect(handle_new_message, sender=Message)
    post_save.disconnect(handle_document_signature, sender=DocumentSignature)
    post_save.disconnect(handle_market_trend_updates, sender=MarketTrend)
    post_save.disconnect(handle_location_preference_updates, sender=LocationPreference)