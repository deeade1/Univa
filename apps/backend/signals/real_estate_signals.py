# signals.py
import logging

from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from twilio.rest import Client

from .models import NotificationPreference, NotificationQueue

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Listing)
def handle_property_notifications(sender, instance, created, **kwargs):
    from .tasks import (queue_email_notification, queue_sms_notification,
                        send_websocket_notification)

    # Get the update log if this isn't a creation
    update_log = None
    if not created:
        update_log = instance.propertyupdatelog_set.order_by('-timestamp').first()
        if not update_log:
            return
    
    # Get subscribers who should be notified
    subscribers = get_subscribers_for_property(instance)
    
    for subscriber in subscribers:
        # Don't notify the user who made the change
        if update_log and update_log.updated_by == subscriber.user:
            continue
            
        try:
            preferences = subscriber.user.notification_preferences
        except NotificationPreference.DoesNotExist:
            preferences = NotificationPreference.objects.create(user=subscriber.user)
        
        # Prepare notification data
        notification_data = prepare_notification_data(instance, created, update_log)
        
        # Send via preferred channels
        if 'websocket' in preferences.preferred_channels:
            send_websocket_notification.delay(
                user_id=subscriber.user.id,
                notification_data=notification_data
            )
        
        if preferences.email_notifications:
            queue_email_notification.delay(
                user_id=subscriber.user.id,
                notification_data=notification_data
            )
        
        if preferences.sms_notifications and preferences.phone_number:
            queue_sms_notification.delay(
                phone_number=preferences.phone_number,
                notification_data=notification_data
            )

def get_subscribers_for_property(property):
    """Get all users subscribed to this property type/location"""
    from django.contrib.gis.db.models.functions import Distance
    from django.contrib.gis.geos import Point

    from .models import PropertySubscription

    # Get subscribers to this property type
    type_subscribers = PropertySubscription.objects.filter(
        property_type=property.listing_type.property_type
    )
    
    # Get location-based subscribers
    location_subscribers = PropertySubscription.objects.filter(
        location__isnull=False
    )
    if property.address and property.address.location:
        location_subscribers = location_subscribers.annotate(
            distance=Distance('location', property.address.location)
        ).filter(distance__lte=100000)  # 100km in meters
    
    # Combine and return unique subscribers
    return (type_subscribers | location_subscribers).distinct()

def prepare_notification_data(property, is_new, update_log=None):
    """Prepare standardized notification data"""
    data = {
        'property_id': property.id,
        'property_title': property.title,
        'property_type': property.listing_type.property_type,
        'price': str(property.price),
        'is_new_property': is_new,
        'changed_fields': {},
        'timestamp': property.created.isoformat() if is_new else update_log.timestamp.isoformat(),
        'url': f"{settings.FRONTEND_URL}/properties/{property.id}"
    }
    
    if update_log:
        data['changed_fields'] = update_log.changed_fields
        data['updated_by'] = {
            'id': update_log.updated_by.id,
            'name': update_log.updated_by.get_full_name()
        } if update_log.updated_by else None
    
    return data