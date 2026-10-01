'''from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.db import transaction
from transport.models import ServiceRequest, Trip, Booking, WaitlistEntry, SharedTrip
from accounts.models import LoyaltyReward
#from transport.services.seat_reallocation import SeatReallocator
from transport.tasks import (
    handle_seat_open,
    notify_waitlist_users,
    dispatch_service_request,
    batch_dispatch_requests
)

@receiver(post_save, sender=ServiceRequest)
def handle_service_completion(sender, instance, created, **kwargs):
    """Handle service completion and award loyalty points"""
    if not created and instance.status == 'completed':
        # Award loyalty points for completed trips
        if hasattr(instance, 'award_loyalty_points'):
            instance.award_loyalty_points()
        
        # Free up provider for new requests
        if instance.provider:
            instance.provider.is_available = True
            instance.provider.current_service = None
            instance.provider.save()'''

'''@receiver(post_save, sender=Booking)
def handle_booking_changes(sender, instance, created, **kwargs):
    """Handle booking changes for seat reallocation"""
    if not created:
        SeatReallocator.handle_booking_update(instance)
    
    # Trigger seat availability check for shared trips
    if hasattr(instance, 'trip') and hasattr(instance.trip, 'shared_info'):
        handle_seat_open.delay(instance.trip.id)

@receiver(post_save, sender=Trip)
def handle_trip_optimization(sender, instance, created, **kwargs):
    """Optimize route when trip is created or updated"""
    if instance.route and hasattr(instance, 'optimize_route'):
        instance.optimize_route()
    
    # Trigger dispatch for service requests
    if created and hasattr(instance, 'service_request'):
        dispatch_service_request.delay(instance.service_request.id)

@receiver(post_save, sender=WaitlistEntry)
def handle_waitlist_entry(sender, instance, created, **kwargs):
    """Handle new waitlist entries"""
    if created and instance.shared_trip:
        # Check if seats are immediately available
        if instance.shared_trip.available_seats > 0:
            notify_waitlist_users.delay(instance.shared_trip.id)

@receiver(post_save, sender=SharedTrip)
def handle_shared_trip_updates(sender, instance, created, **kwargs):
    """Handle shared trip capacity changes"""
    if not created:
        # Notify waitlist if seats become available
        if instance.available_seats > 0:
            notify_waitlist_users.delay(instance.id)

@receiver(post_delete, sender=Booking)
def handle_booking_cancellation(sender, instance, **kwargs):
    """Handle booking cancellations"""
    if hasattr(instance, 'trip') and hasattr(instance.trip, 'shared_info'):
        # Trigger seat availability check when booking is cancelled
        handle_seat_open.delay(instance.trip.id)

@receiver(post_save, sender=ServiceRequest)
def trigger_dispatch_on_creation(sender, instance, created, **kwargs):
    """Trigger dispatch for new service requests"""
    if created and instance.status == ServiceRequest.Status.REQUESTED:
        # Use batch processing for better performance
        cache_key = f"dispatch_batch_{timezone.now().hour}"
        if not cache.get(cache_key):
            batch_dispatch_requests.delay()
            cache.set(cache_key, True, timeout=3500)  # Cache for ~1 hour'''